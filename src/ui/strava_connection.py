"""Session-only OAuth callback handling for the local Streamlit flow."""

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from datetime import datetime, timezone
import os
import secrets
from threading import Lock
import time
from typing import Any

import streamlit as st

from src.strava.auth import (
    CLIENT_CONFIGURATION_VARIABLES,
    REQUESTED_AUTHORIZATION_SCOPES,
    build_authorization_url,
    exchange_authorization_code,
    revoke_access_token,
)
from src.strava.activity_mapper import activity_from_strava
from src.strava.client import StravaClient
from src.strava.training_analysis import training_analysis_from_strava
from src.ui.timezone_preference import ATHLETE_TIMEZONE_KEY, is_valid_iana_timezone_name


ACCESS_TOKEN_KEY = "strava_access_token"
EXPIRES_AT_KEY = "strava_access_token_expires_at"
SCOPES_KEY = "strava_granted_scopes"
ATHLETE_PREVIEW_KEY = "strava_athlete_preview"
ACTIVITY_PREVIEW_KEY = "strava_activity_preview"
TRAINING_ANALYSIS_KEY = "strava_training_analysis"
SELECTED_ACTIVITY_ID_KEY = "selected_strava_activity_id"
CALLBACK_KEYS = ("code", "state", "scope", "error")
OAUTH_STATE_TTL_SECONDS = 600
OAUTH_STATE_MAX_ENTRIES = 1024


@dataclass(frozen=True)
class _PendingOAuthState:
    expires_at: float
    timezone_preference: str | None


class OAuthStateStore:
    """Thread-safe, bounded one-time state store shared across browser tabs."""

    def __init__(
        self,
        *,
        ttl_seconds: int = OAUTH_STATE_TTL_SECONDS,
        max_entries: int = OAUTH_STATE_MAX_ENTRIES,
        clock=time.time,
    ) -> None:
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._clock = clock
        self._lock = Lock()
        self._pending: dict[str, _PendingOAuthState] = {}
        self._consumed: dict[str, float] = {}

    def issue(self, timezone_preference: object = None) -> str:
        now = self._clock()
        snapshot = (
            timezone_preference
            if is_valid_iana_timezone_name(timezone_preference)
            else None
        )
        with self._lock:
            self._remove_expired(now)
            if len(self._pending) + len(self._consumed) >= self._max_entries:
                raise RuntimeError("Too many pending Strava authorizations.")
            state = secrets.token_urlsafe(32)
            while state in self._pending or state in self._consumed:
                state = secrets.token_urlsafe(32)
            self._pending[state] = _PendingOAuthState(
                expires_at=now + self._ttl_seconds,
                timezone_preference=snapshot,
            )
            return state

    def consume(self, state: str) -> str:
        """Return consumed, expired, replay, or mismatch; consume atomically."""
        status, _ = self.consume_with_preference(state)
        return status

    def consume_with_preference(self, state: str) -> tuple[str, str | None]:
        """Atomically consume a nonce and return its one-use timezone snapshot."""
        now = self._clock()
        with self._lock:
            pending = self._pending.pop(state, None)
            if pending is not None:
                self._remove_expired(now)
                if pending.expires_at <= now:
                    return "expired", None
                self._consumed[state] = pending.expires_at
                return "consumed", pending.timezone_preference
            self._remove_expired(now)
            if state in self._consumed:
                return "replay", None
            return "mismatch", None

    def _remove_expired(self, now: float) -> None:
        self._pending = {
            state: pending
            for state, pending in self._pending.items()
            if pending.expires_at > now
        }
        self._consumed = {state: expiry for state, expiry in self._consumed.items() if expiry > now}

    def clear(self) -> None:
        """Remove pending and consumed nonces, primarily for deterministic tests."""
        with self._lock:
            self._pending.clear()
            self._consumed.clear()


@st.cache_resource
def get_oauth_state_store() -> OAuthStateStore:
    """Return the process-local bounded state store shared by Streamlit tabs."""
    return OAuthStateStore()


def start_authorization(
    *,
    environ: Mapping[str, str] | None = None,
    state_store: OAuthStateStore | None = None,
    timezone_preference: object = None,
) -> str:
    """Create a short-lived, one-time state and authorization URL."""
    configuration = os.environ if environ is None else environ
    redirect_uri = configuration.get("STRAVA_REDIRECT_URI", "").strip()
    if not redirect_uri:
        raise RuntimeError("STRAVA_REDIRECT_URI is not configured.")
    if not all(configuration.get(name) for name in CLIENT_CONFIGURATION_VARIABLES):
        raise RuntimeError("Strava client configuration is incomplete.")
    store = state_store if state_store is not None else get_oauth_state_store()
    state = store.issue(timezone_preference)
    authorization_url = build_authorization_url(redirect_uri, state=state)
    return authorization_url


def _single_value(query_params: Any, key: str) -> str | None:
    values = query_params.get_all(key)
    if len(values) != 1 or not values[0]:
        return None
    return values[0]


def _parse_scopes(scope_value: object) -> tuple[str, ...] | None:
    if not isinstance(scope_value, str) or not scope_value.strip():
        return None
    scopes = tuple(dict.fromkeys(scope for scope in scope_value.replace(",", " ").split() if scope))
    return scopes or None


def _has_required_scopes(scopes: tuple[str, ...]) -> bool:
    return set(REQUESTED_AUTHORIZATION_SCOPES) <= set(scopes)


def _valid_token_response(token_data: object) -> tuple[str, int, tuple[str, ...]] | None:
    if not isinstance(token_data, dict):
        return None
    access_token = token_data.get("access_token")
    expires_at = token_data.get("expires_at")
    scopes = _parse_scopes(token_data.get("scope"))
    if (
        not isinstance(access_token, str)
        or not access_token.strip()
        or type(expires_at) is not int
        or expires_at <= int(datetime.now(timezone.utc).timestamp())
        or scopes is None
        or not _has_required_scopes(scopes)
    ):
        return None
    return access_token, expires_at, scopes


def consume_oauth_callback(
    session_state: MutableMapping[str, Any],
    query_params: Any,
    *,
    state_store: OAuthStateStore | None = None,
    exchange_code=None,
) -> str | None:
    """Consume a callback once, clear its URL parameters, and retain safe fields.

    Returns a fixed UI status key or ``None`` when the current URL is not an
    OAuth callback. Authorization codes, refresh tokens and provider payloads
    are never stored in session state or returned to the caller.
    """
    if not any(key in query_params for key in CALLBACK_KEYS):
        return None
    exchange = exchange_authorization_code if exchange_code is None else exchange_code

    store = state_store if state_store is not None else get_oauth_state_store()
    state_values = query_params.get_all("state")
    returned_state = _single_value(query_params, "state")
    code = _single_value(query_params, "code")
    error = _single_value(query_params, "error")
    callback_scopes = _parse_scopes(_single_value(query_params, "scope"))
    duplicate_callback_values = any(
        len(query_params.get_all(key)) > 1 for key in ("code", "scope", "error")
    )
    query_params.clear()

    if len(state_values) > 1:
        for value in state_values:
            store.consume_with_preference(value)
        return "multiple_state"
    if returned_state is None:
        return "missing_state"
    state_status, timezone_preference = store.consume_with_preference(returned_state)
    if state_status == "mismatch":
        return "state_mismatch"
    if state_status != "consumed":
        return state_status
    if duplicate_callback_values:
        return "invalid_callback"
    if is_valid_iana_timezone_name(timezone_preference):
        session_state[ATHLETE_TIMEZONE_KEY] = timezone_preference
    if error == "access_denied":
        return "access_denied"
    if error is not None:
        return "authorization_failed"
    if code is None:
        return "missing_code"
    if callback_scopes is None or not _has_required_scopes(callback_scopes):
        return "insufficient_scope"

    try:
        token_data = exchange(code)
    except RuntimeError:
        return "exchange_failed"

    validated = _valid_token_response(token_data)
    if validated is None:
        return "invalid_token_response"
    access_token, expires_at, scopes = validated
    session_state[ACCESS_TOKEN_KEY] = access_token
    session_state[EXPIRES_AT_KEY] = expires_at
    session_state[SCOPES_KEY] = scopes
    return "connected"


def clear_connection_state(session_state: MutableMapping[str, Any]) -> str | None:
    """Discard all session credentials and previews; return token for revocation."""
    access_token = session_state.get(ACCESS_TOKEN_KEY)
    for key in (
        ACCESS_TOKEN_KEY,
        EXPIRES_AT_KEY,
        SCOPES_KEY,
        ATHLETE_PREVIEW_KEY,
        ACTIVITY_PREVIEW_KEY,
        TRAINING_ANALYSIS_KEY,
    ):
        session_state.pop(key, None)
    return access_token if isinstance(access_token, str) and access_token else None


def clear_activity_analysis(session_state: MutableMapping[str, Any]) -> None:
    """Discard a prior individual result when the selection changes."""
    session_state.pop(TRAINING_ANALYSIS_KEY, None)


def clear_expired_activity_analysis(
    session_state: MutableMapping[str, Any], *, now: float | None = None
) -> None:
    """Hide detailed analysis when its session token is absent or expired."""
    expires_at = session_state.get(EXPIRES_AT_KEY)
    current_time = time.time() if now is None else now
    if type(expires_at) is not int or expires_at <= current_time:
        clear_activity_analysis(session_state)


def load_selected_activity_analysis(
    session_state: MutableMapping[str, Any],
    activity_id: int | None,
    *,
    client_factory=None,
    now: float | None = None,
) -> None:
    """Fetch and analyze one selected Run detail, retaining it only in session."""
    clear_activity_analysis(session_state)
    token = session_state.get(ACCESS_TOKEN_KEY)
    expires_at = session_state.get(EXPIRES_AT_KEY)
    current_time = time.time() if now is None else now
    if not isinstance(token, str) or not token.strip() or type(expires_at) is not int:
        raise ValueError("Connect Strava again before analyzing an activity.")
    if expires_at <= current_time:
        raise ValueError("The Strava session has expired. Connect again to analyze an activity.")
    if not isinstance(activity_id, int) or isinstance(activity_id, bool):
        raise ValueError("Select a valid activity from the preview.")

    preview = session_state.get(ACTIVITY_PREVIEW_KEY)
    if not isinstance(preview, list):
        raise ValueError("Load the Strava preview before selecting an activity.")
    selected_activity = next(
        (
            activity
            for activity in preview
            if isinstance(activity, dict)
            and activity.get("id") == activity_id
            and activity.get("sport_type") == "Run"
        ),
        None,
    )
    if selected_activity is None:
        raise ValueError("Select a Run from the loaded Strava preview.")

    client = (StravaClient if client_factory is None else client_factory)(access_token=token)
    detail = client.get_activity(activity_id)
    if not isinstance(detail, dict):
        raise ValueError("Strava returned an invalid activity detail.")
    activity = activity_from_strava(detail)
    if activity.id != activity_id:
        raise ValueError("Strava returned a different activity than the selected Run.")
    analysis = training_analysis_from_strava(activity, detail)
    session_state[TRAINING_ANALYSIS_KEY] = analysis


def disconnect_from_strava(
    session_state: MutableMapping[str, Any],
    *,
    environ: Mapping[str, str] | None = None,
    revoke=None,
) -> str:
    """Clear local state first, then make a best-effort remote revoke request."""
    access_token = clear_connection_state(session_state)
    from src.ui.strava_weekly_overview import clear_weekly_overview

    clear_weekly_overview(session_state)
    if access_token is None:
        return "disconnected"
    if not revocation_is_configured(environ):
        return "manual_revocation"
    try:
        (revoke_access_token if revoke is None else revoke)(access_token)
    except RuntimeError:
        return "revocation_failed"
    return "revocation_requested"


def load_first_page_preview(
    session_state: MutableMapping[str, Any],
    *,
    client_factory=None,
    now: float | None = None,
) -> None:
    """Load only a whitelisted athlete summary and the first 30 activity summaries."""
    clear_activity_analysis(session_state)
    token = session_state.get(ACCESS_TOKEN_KEY)
    expires_at = session_state.get(EXPIRES_AT_KEY)
    current_time = time.time() if now is None else now
    if not isinstance(token, str) or not token.strip() or type(expires_at) is not int:
        raise ValueError("Connect Strava again before loading a preview.")
    if expires_at <= current_time:
        session_state.pop(ATHLETE_PREVIEW_KEY, None)
        session_state.pop(ACTIVITY_PREVIEW_KEY, None)
        raise ValueError("The Strava session has expired. Connect again to load a preview.")

    session_state.pop(ATHLETE_PREVIEW_KEY, None)
    session_state.pop(ACTIVITY_PREVIEW_KEY, None)
    client = (StravaClient if client_factory is None else client_factory)(access_token=token)
    athlete = client.get_athlete()
    if not isinstance(athlete, dict):
        raise RuntimeError("Strava returned an invalid athlete profile.")
    activities = client.get_activities(page=1, per_page=30)

    athlete_preview = {
        name: athlete.get(name)
        for name in ("id", "firstname", "lastname", "username")
    }
    activity_preview = [
        {
            "id": activity.id,
            "name": activity.name,
            "sport_type": activity.sport_type,
            "start_date": activity.start_date.isoformat(),
            "distance_meters": activity.distance_meters,
            "moving_time_seconds": activity.moving_time_seconds,
        }
        for activity in activities
    ]
    session_state[ATHLETE_PREVIEW_KEY] = athlete_preview
    session_state[ACTIVITY_PREVIEW_KEY] = activity_preview


def revocation_is_configured(environ: Mapping[str, str] | None = None) -> bool:
    """Whether local client credentials are available for best-effort revoke."""
    configuration = os.environ if environ is None else environ
    return all(configuration.get(name) for name in CLIENT_CONFIGURATION_VARIABLES)
