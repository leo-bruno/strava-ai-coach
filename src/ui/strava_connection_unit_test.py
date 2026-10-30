"""Deterministic tests for the local Strava OAuth session boundary."""

from concurrent.futures import ThreadPoolExecutor

from src.ui.strava_connection import (
    ACCESS_TOKEN_KEY,
    ACTIVITY_PREVIEW_KEY,
    ATHLETE_PREVIEW_KEY,
    EXPIRES_AT_KEY,
    SCOPES_KEY,
    disconnect_from_strava,
    load_first_page_preview,
    OAuthStateStore,
    clear_connection_state,
    consume_oauth_callback,
    revocation_is_configured,
    start_authorization,
)


class QueryParamsStub(dict):
    def get_all(self, key):
        value = self.get(key)
        if value is None:
            return []
        return value if isinstance(value, list) else [value]


def test_start_authorization_uses_configured_redirect_and_random_state(monkeypatch):
    monkeypatch.setenv("STRAVA_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setattr("src.ui.strava_connection.secrets.token_urlsafe", lambda size: f"state-{size}")
    store = OAuthStateStore(clock=lambda: 100.0)

    url = start_authorization(
        environ={
            "STRAVA_CLIENT_ID": "test-client-id",
            "STRAVA_CLIENT_SECRET": "test-client-secret",
            "STRAVA_REDIRECT_URI": "http://localhost:8501",
        },
        state_store=store,
    )

    assert "state=state-32" in url
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8501" in url
    assert store.consume("state-32") == "consumed"


def test_valid_callback_consumes_state_and_keeps_only_access_token_fields():
    session = {}
    store = OAuthStateStore(clock=lambda: 100.0)
    expected_state = store.issue()
    params = QueryParamsStub(
        code="one-time-code",
        state=expected_state,
        scope="read,activity:read_all",
    )
    calls = []

    status = consume_oauth_callback(
        session,
        params,
        state_store=store,
        exchange_code=lambda code: calls.append(code) or {
            "access_token": "short-lived-access-token",
            "refresh_token": "must-not-be-kept",
            "expires_at": 2_100_000_000,
            "scope": "read activity:read_all",
        },
    )

    assert status == "connected"
    assert calls == ["one-time-code"]
    assert not params
    assert session == {
        ACCESS_TOKEN_KEY: "short-lived-access-token",
        EXPIRES_AT_KEY: 2_100_000_000,
        SCOPES_KEY: ("read", "activity:read_all"),
    }
    assert "one-time-code" not in session.values()
    assert "must-not-be-kept" not in session.values()


def test_callback_with_unknown_state_is_rejected_and_clears_query():
    store = OAuthStateStore(clock=lambda: 100.0)
    params = QueryParamsStub(code="old-code", state="old-state", scope="read,activity:read_all")

    status = consume_oauth_callback({}, params, state_store=store, exchange_code=lambda _code: None)

    assert status == "state_mismatch"
    assert not params


def test_callback_replay_does_not_exchange_code_again():
    store = OAuthStateStore(clock=lambda: 100.0)
    state = store.issue()
    first = QueryParamsStub(code="first-code", state=state, scope="read,activity:read_all")
    token_data = {
        "access_token": "token",
        "refresh_token": "unused",
        "expires_at": 2_100_000_000,
        "scope": "read,activity:read_all",
    }
    assert consume_oauth_callback({}, first, state_store=store, exchange_code=lambda _code: token_data) == "connected"

    replay = QueryParamsStub(code="second-code", state=state, scope="read,activity:read_all")
    calls = []
    assert consume_oauth_callback(
        {}, replay, state_store=store, exchange_code=lambda code: calls.append(code)
    ) == "replay"
    assert not calls
    assert not replay


def test_expired_callback_state_is_consumed_without_exchanging_code():
    now = [100.0]
    store = OAuthStateStore(ttl_seconds=5, clock=lambda: now[0])
    state = store.issue()
    now[0] = 106.0
    params = QueryParamsStub(code="code", state=state, scope="read,activity:read_all")
    calls = []

    status = consume_oauth_callback(
        {},
        params,
        state_store=store,
        exchange_code=lambda code: calls.append(code),
    )

    assert status == "expired"
    assert not calls
    assert not params


def test_callback_rejects_state_mismatch_without_exchange():
    session = {}
    store = OAuthStateStore(clock=lambda: 100.0)
    store.issue()
    params = QueryParamsStub(code="code", state="other", scope="read,activity:read_all")
    calls = []

    status = consume_oauth_callback(session, params, state_store=store, exchange_code=lambda code: calls.append(code))

    assert status == "state_mismatch"
    assert not calls
    assert not params


def test_callback_handles_missing_state_code_and_insufficient_scopes_without_exchange():
    cases = (
        (QueryParamsStub(code="code", scope="read,activity:read_all"), "missing_state"),
        (QueryParamsStub(state="expected", scope="read,activity:read_all"), "missing_code"),
        (QueryParamsStub(code="code", state="expected", scope="read"), "insufficient_scope"),
        (QueryParamsStub(code="code", state="expected"), "insufficient_scope"),
    )
    for params, expected in cases:
        session = {}
        store = OAuthStateStore(clock=lambda: 100.0)
        expected_state = store.issue()
        if params.get("state") == "expected":
            params["state"] = expected_state
        calls = []
        assert consume_oauth_callback(
            session, params, state_store=store, exchange_code=lambda code: calls.append(code)
        ) == expected
        assert not calls
        assert not params


def test_callback_handles_access_denied_before_exchange():
    session = {}
    store = OAuthStateStore(clock=lambda: 100.0)
    expected_state = store.issue()
    params = QueryParamsStub(state=expected_state, error="access_denied")
    calls = []

    status = consume_oauth_callback(session, params, state_store=store, exchange_code=lambda code: calls.append(code))

    assert status == "access_denied"
    assert not calls
    assert not params


def test_callback_rejects_insufficient_grant_in_exchange_response():
    session = {}
    store = OAuthStateStore(clock=lambda: 100.0)
    expected_state = store.issue()
    params = QueryParamsStub(code="code", state=expected_state, scope="read,activity:read_all")
    status = consume_oauth_callback(
        session,
        params,
        state_store=store,
        exchange_code=lambda _code: {
            "access_token": "token",
            "refresh_token": "unused",
            "expires_at": 2_100_000_000,
            "scope": "read",
        },
    )

    assert status == "invalid_token_response"
    assert ACCESS_TOKEN_KEY not in session
    assert SCOPES_KEY not in session


def test_callback_rejects_exchange_error_without_exposing_error_or_code():
    session = {}
    store = OAuthStateStore(clock=lambda: 100.0)
    expected_state = store.issue()
    params = QueryParamsStub(code="secret-code", state=expected_state, scope="read,activity:read_all")

    def fail(_code):
        raise RuntimeError("provider diagnostic must not be exposed")

    status = consume_oauth_callback(session, params, state_store=store, exchange_code=fail)

    assert status == "exchange_failed"
    assert "secret-code" not in str(session)
    assert "provider diagnostic" not in status


def test_state_store_expires_pending_state_and_consumes_replay_once():
    now = [10.0]
    store = OAuthStateStore(ttl_seconds=5, max_entries=3, clock=lambda: now[0])
    state = store.issue()

    now[0] = 16.0
    assert store.consume(state) == "expired"
    assert store.consume(state) == "mismatch"

    now[0] = 20.0
    state = store.issue()
    assert store.consume(state) == "consumed"
    assert store.consume(state) == "replay"


def test_state_store_enforces_capacity_and_reclaims_expired_nonces():
    now = [10.0]
    store = OAuthStateStore(ttl_seconds=5, max_entries=1, clock=lambda: now[0])
    store.issue()

    try:
        store.issue()
    except RuntimeError as error:
        assert "Too many pending" in str(error)
    else:
        raise AssertionError("Store should reject when its bound is reached.")

    now[0] = 16.0
    store.issue()


def test_state_store_consumes_nonce_atomically_under_concurrent_callbacks():
    store = OAuthStateStore(clock=lambda: 100.0)
    state = store.issue()

    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(lambda _index: store.consume(state), range(8)))

    assert statuses.count("consumed") == 1
    assert statuses.count("replay") == 7


def test_multiple_callback_state_values_are_rejected_without_exchange():
    store = OAuthStateStore(clock=lambda: 100.0)
    first = store.issue()
    second = store.issue()
    session = {}
    params = QueryParamsStub(code="code", state=[first, second], scope="read,activity:read_all")
    calls = []

    status = consume_oauth_callback(
        session,
        params,
        state_store=store,
        exchange_code=lambda code: calls.append(code),
    )

    assert status == "multiple_state"
    assert not calls
    assert not params
    assert store.consume(first) == "replay"
    assert store.consume(second) == "replay"


def test_duplicate_code_values_are_rejected_without_exchange():
    store = OAuthStateStore(clock=lambda: 100.0)
    state = store.issue()
    params = QueryParamsStub(
        code=["first-code", "second-code"],
        state=state,
        scope="read,activity:read_all",
    )
    calls = []

    status = consume_oauth_callback(
        {},
        params,
        state_store=store,
        exchange_code=lambda code: calls.append(code),
    )

    assert status == "invalid_callback"
    assert not calls
    assert not params


def test_clear_connection_state_returns_only_access_token_and_removes_all_session_data():
    session = {
        ACCESS_TOKEN_KEY: "access-token",
        EXPIRES_AT_KEY: 2_100_000_000,
        SCOPES_KEY: ("read",),
        ATHLETE_PREVIEW_KEY: {"id": 10},
        ACTIVITY_PREVIEW_KEY: [],
    }

    token = clear_connection_state(session)

    assert token == "access-token"
    assert session == {}


def test_revocation_requires_both_client_credentials():
    assert not revocation_is_configured({"STRAVA_CLIENT_ID": "id"})
    assert revocation_is_configured(
        {"STRAVA_CLIENT_ID": "id", "STRAVA_CLIENT_SECRET": "secret"}
    )


def test_preview_uses_supplied_token_and_fetches_exactly_profile_and_first_activity_page():
    from datetime import datetime, timezone

    from src.models.activity import Activity

    session = {ACCESS_TOKEN_KEY: "session-token", EXPIRES_AT_KEY: 2_100_000_000}
    calls = []

    class FakeClient:
        def __init__(self, *, access_token):
            calls.append(("client", access_token))

        def get_athlete(self):
            calls.append(("athlete",))
            return {
                "id": 42,
                "firstname": "Runner",
                "lastname": "Example",
                "username": "runner",
                "weight": 62.0,
                "city": "Madrid",
            }

        def get_activities(self, *, page, per_page):
            calls.append(("activities", page, per_page))
            return [Activity(1, "Run", "Run", datetime(2026, 10, 20, tzinfo=timezone.utc), 5000, 1500)]

    load_first_page_preview(session, client_factory=FakeClient, now=2_000_000_000)

    assert calls == [("client", "session-token"), ("athlete",), ("activities", 1, 30)]
    assert session[ATHLETE_PREVIEW_KEY] == {
        "id": 42,
        "firstname": "Runner",
        "lastname": "Example",
        "username": "runner",
    }
    assert session[ACTIVITY_PREVIEW_KEY] == [{
        "id": 1,
        "name": "Run",
        "sport_type": "Run",
        "start_date": "2026-10-20T00:00:00+00:00",
        "distance_meters": 5000,
        "moving_time_seconds": 1500,
    }]
    assert all("refresh_token" not in str(value) for value in session.values())


def test_preview_rejects_expired_session_without_creating_client():
    session = {
        ACCESS_TOKEN_KEY: "session-token",
        EXPIRES_AT_KEY: 100,
        ATHLETE_PREVIEW_KEY: {"id": 1},
        ACTIVITY_PREVIEW_KEY: [{"id": 2}],
    }
    calls = []

    try:
        load_first_page_preview(session, client_factory=lambda **_kwargs: calls.append("client"), now=101)
    except ValueError as error:
        assert "expired" in str(error)
    else:
        raise AssertionError("Expired session should be rejected.")

    assert not calls
    assert ATHLETE_PREVIEW_KEY not in session
    assert ACTIVITY_PREVIEW_KEY not in session


def test_disconnect_clears_session_and_attempts_revoke_only_when_configured():
    session = {
        ACCESS_TOKEN_KEY: "session-token",
        EXPIRES_AT_KEY: 2_100_000_000,
        SCOPES_KEY: ("read", "activity:read_all"),
        ATHLETE_PREVIEW_KEY: {"id": 1},
        ACTIVITY_PREVIEW_KEY: [{"id": 2}],
    }
    revoked = []

    status = disconnect_from_strava(
        session,
        environ={"STRAVA_CLIENT_ID": "id", "STRAVA_CLIENT_SECRET": "secret"},
        revoke=lambda token: revoked.append(token),
    )

    assert status == "revocation_requested"
    assert revoked == ["session-token"]
    assert session == {}


def test_disconnect_reports_manual_revocation_when_unconfigured():
    session = {ACCESS_TOKEN_KEY: "session-token"}
    revoked = []

    status = disconnect_from_strava(
        session,
        environ={},
        revoke=lambda token: revoked.append(token),
    )

    assert status == "manual_revocation"
    assert not revoked
    assert session == {}


def test_disconnect_reports_failed_revocation_after_clearing_local_state():
    session = {ACCESS_TOKEN_KEY: "session-token", ATHLETE_PREVIEW_KEY: {"id": 1}}

    def fail(_token):
        raise RuntimeError("private provider detail")

    status = disconnect_from_strava(
        session,
        environ={"STRAVA_CLIENT_ID": "id", "STRAVA_CLIENT_SECRET": "secret"},
        revoke=fail,
    )

    assert status == "revocation_failed"
    assert session == {}
