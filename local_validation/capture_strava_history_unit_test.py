"""Deterministic checks for the manual tool; no authentication or network."""
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest

from local_validation.capture_strava_history import analyze, reconcile, record, retrieve
from src.models.activity import Activity


def activity(identifier=1, when=None, sport="Run"):
    return Activity(identifier, "Example", sport, when or datetime(2026, 4, 20, tzinfo=timezone.utc), 1000.5, 300)


def test_short_pages_continue_to_empty_and_duplicates_remain():
    client = Mock()
    first, second = activity(), activity(2)
    client.get_activities.side_effect = [[first], [first, second], []]
    start = first.start_date
    end = start + timedelta(days=7)
    records, pages = retrieve(client, start, end, 30)
    assert records == [first, first, second]
    assert [p["returned_count"] for p in pages] == [1, 2, 0]
    assert [c.kwargs["page"] for c in client.get_activities.call_args_list] == [1, 2, 3]
    assert client.get_activities.call_args_list[0].kwargs["after"] == int(start.timestamp()) - 1
    assert client.get_activities.call_args_list[0].kwargs["before"] == int(end.timestamp())


def test_failure_is_not_end_of_pagination():
    client = Mock()
    client.get_activities.side_effect = [[activity()], RuntimeError("sensitive body")]
    with pytest.raises(RuntimeError, match="page 2 failed") as error:
        retrieve(client, activity().start_date, activity().start_date + timedelta(days=7), 30)
    assert "sensitive" not in str(error.value)


def test_repeated_page_aborts_instead_of_looping():
    client = Mock()
    client.get_activities.side_effect = [[activity()], [activity()]]
    with pytest.raises(RuntimeError, match="Repeated page"):
        retrieve(client, activity().start_date, activity().start_date + timedelta(days=7), 30)


def test_independent_local_grouping_and_open_week():
    tz = ZoneInfo("Europe/Madrid")
    start = datetime(2026, 4, 20, tzinfo=tz)
    end = start + timedelta(days=14)
    records = [record(activity(1, start)), record(activity(2, start + timedelta(days=7))),
               record(activity(3, start, "TrailRun"))]
    weeks = analyze(records, start, end, start + timedelta(days=8), tz)
    assert [w["source_ids"] for w in weeks] == [[1], [2]]
    assert all(w["passed"] for w in weeks)
    assert [w["period_closed_at_extraction"] for w in weeks] == [True, False]
    assert weeks[0]["running_distance_meters"] == 1000.5


def test_id_comparison_preserves_multiplicity_changes_and_removals():
    first, second, third = map(record, [activity(1), activity(2), activity(3)])
    differences = reconcile([first, first, third], [first, second])
    assert [(d["id"], d["status"], d["distance_delta_meters"]) for d in differences] == [
        (1, "changed", "1000.5"), (2, "removed", "-1000.5"), (3, "added", "1000.5")]


def test_capture_exact_boundaries_all_sports_and_safe_output(monkeypatch, tmp_path):
    import json
    import sys
    from local_validation import capture_strava_history as module
    tz = ZoneInfo("Europe/Madrid")
    start = datetime(2026, 4, 20, tzinfo=tz)
    end = start + timedelta(days=7)
    old = tmp_path / "old.json"
    old.write_text('{"activities": []}')
    output = tmp_path / "new.json"
    monkeypatch.setattr(sys, "argv", ["capture", "--start", "2026-04-20", "--end-exclusive", "2026-04-27",
                                     "--timezone", "Europe/Madrid", "--previous", str(old),
                                     "--output", str(output), "--strava-display-km", "1.0"])
    client = Mock()
    client._access_token = "never-export-this"
    client.get_activities.side_effect = [[activity(1, start - timedelta(seconds=1)),
                                         activity(2, start), activity(3, end),
                                         activity(4, start, "Walk")], []]
    monkeypatch.setattr(module, "StravaClient", lambda: client)
    module.main()
    report = json.loads(output.read_text())
    assert [r['id'] for r in report['activities']] == [2, 4]
    assert [r['id'] for r in report['out_of_interval']] == [1, 3]
    assert report['run_count'] == 1
    assert report['sports']['Walk']['count'] == 1
    assert 'never-export-this' not in output.read_text()
    assert report['delta_reconciled'] and report['weekly_total_matches']
    with pytest.raises(SystemExit):
        module.main()
    assert old.read_text() == '{"activities": []}'


def test_capture_page_failure_leaves_no_snapshot(monkeypatch, tmp_path):
    import sys
    from local_validation import capture_strava_history as module
    old = tmp_path / 'old.json'
    old.write_text('{"activities": []}')
    output = tmp_path / 'new.json'
    monkeypatch.setattr(sys, 'argv', ['capture', '--start', '2026-04-20', '--end-exclusive', '2026-04-27',
                                     '--timezone', 'Europe/Madrid', '--previous', str(old),
                                     '--output', str(output), '--strava-display-km', '1.0'])
    client = Mock()
    client.get_activities.side_effect = [[activity()], RuntimeError('secret-body')]
    monkeypatch.setattr(module, 'StravaClient', lambda: client)
    with pytest.raises(SystemExit, match='page 2 failed'):
        module.main()
    assert not output.exists()
