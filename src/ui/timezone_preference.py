"""Helpers for an explicit, session-only IANA timezone preference."""

from datetime import datetime
import os
from pathlib import Path
from collections.abc import Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones


ATHLETE_TIMEZONE_KEY = "athlete_timezone"
IANA_TIMEZONE_OPTIONS = tuple(
    sorted(name for name in available_timezones() if "/" in name or name == "UTC")
)


def is_valid_iana_timezone_name(value: object) -> bool:
    """Accept known IANA IDs, excluding bare abbreviations and offsets."""
    if not isinstance(value, str) or value not in IANA_TIMEZONE_OPTIONS:
        return False
    if "/" not in value and value != "UTC":
        return False
    try:
        return ZoneInfo(value).key == value
    except (ValueError, ZoneInfoNotFoundError):
        return False


def detect_local_iana_timezone(
    *,
    environ: Mapping[str, str] | None = None,
    local_tzinfo=None,
    localtime_path: Path = Path("/etc/localtime"),
) -> str | None:
    """Best-effort local zone detection without guessing from abbreviations."""
    environment = os.environ if environ is None else environ
    tzinfo = datetime.now().astimezone().tzinfo if local_tzinfo is None else local_tzinfo

    zone_key = getattr(tzinfo, "key", None)
    if is_valid_iana_timezone_name(zone_key):
        return zone_key

    environment_zone = environment.get("TZ")
    if is_valid_iana_timezone_name(environment_zone):
        return environment_zone

    try:
        if not localtime_path.is_symlink():
            return None
        resolved_parts = localtime_path.resolve(strict=True).parts
    except (OSError, RuntimeError):
        return None
    zoneinfo_indexes = [
        index for index, part in enumerate(resolved_parts[:-1]) if part == "zoneinfo"
    ]
    if zoneinfo_indexes:
        candidate = "/".join(resolved_parts[zoneinfo_indexes[-1] + 1 :])
        if is_valid_iana_timezone_name(candidate):
            return candidate
    return None
