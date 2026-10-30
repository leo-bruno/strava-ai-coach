"""Tests for conservative best-effort local IANA timezone detection."""

from datetime import timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from src.ui.timezone_preference import (
    ATHLETE_TIMEZONE_KEY,
    IANA_TIMEZONE_OPTIONS,
    detect_local_iana_timezone,
    is_valid_iana_timezone_name,
)


def test_valid_iana_ids_exclude_bare_abbreviations_and_offsets():
    assert is_valid_iana_timezone_name("Europe/Madrid")
    assert is_valid_iana_timezone_name("UTC")
    assert not is_valid_iana_timezone_name("PST")
    assert not is_valid_iana_timezone_name("EST")
    assert not is_valid_iana_timezone_name("+0530")
    assert all("/" in item or item == "UTC" for item in IANA_TIMEZONE_OPTIONS)
    assert ATHLETE_TIMEZONE_KEY == "athlete_timezone"


def test_detects_explicit_zoneinfo_key_before_environment():
    assert detect_local_iana_timezone(
        local_tzinfo=ZoneInfo("Pacific/Honolulu"),
        environ={"TZ": "Asia/Tokyo"},
        localtime_path=Path("/missing/localtime"),
    ) == "Pacific/Honolulu"


def test_detects_valid_tz_environment_when_local_tzinfo_has_no_key():
    assert detect_local_iana_timezone(
        local_tzinfo=timezone.utc,
        environ={"TZ": "Asia/Tokyo"},
        localtime_path=Path("/missing/localtime"),
    ) == "Asia/Tokyo"


def test_detects_iana_suffix_from_localtime_symlink(tmp_path):
    zone_target = tmp_path / "zoneinfo" / "America" / "New_York"
    zone_target.parent.mkdir(parents=True)
    zone_target.touch()
    localtime = tmp_path / "localtime"
    localtime.symlink_to(zone_target)

    assert detect_local_iana_timezone(
        local_tzinfo=timezone.utc,
        environ={},
        localtime_path=localtime,
    ) == "America/New_York"


@pytest.mark.parametrize("timezone_name", ["PST", "EST", "GMT+3", "+0530", "CET"])
def test_ambiguous_timezone_environment_does_not_guess(timezone_name, tmp_path):
    assert detect_local_iana_timezone(
        local_tzinfo=timezone.utc,
        environ={"TZ": timezone_name},
        localtime_path=tmp_path / "not-a-symlink",
    ) is None


def test_unknown_symlink_suffix_and_missing_system_zone_return_none(tmp_path):
    unknown_zone = tmp_path / "zoneinfo" / "Unknown" / "Place"
    unknown_zone.parent.mkdir(parents=True)
    unknown_zone.touch()
    localtime = tmp_path / "localtime"
    localtime.symlink_to(unknown_zone)

    assert detect_local_iana_timezone(
        local_tzinfo=timezone.utc,
        environ={},
        localtime_path=localtime,
    ) is None
    assert detect_local_iana_timezone(
        local_tzinfo=timezone.utc,
        environ={},
        localtime_path=tmp_path / "missing",
    ) is None
