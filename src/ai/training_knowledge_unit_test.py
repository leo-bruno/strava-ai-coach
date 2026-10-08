"""Fixed knowledge document integrity, without network access or selection."""

from dataclasses import FrozenInstanceError
import json

import pytest

from src.ai import training_knowledge


@pytest.fixture
def package_data():
    return json.loads(training_knowledge._PACKAGE_PATH.read_text(encoding="utf-8"))


def load_document(tmp_path, monkeypatch, text):
    path = tmp_path / "knowledge.json"
    path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(training_knowledge, "_PACKAGE_PATH", path)
    return training_knowledge.load_training_knowledge()


def load_data(tmp_path, monkeypatch, data):
    return load_document(tmp_path, monkeypatch, json.dumps(data, ensure_ascii=False))


def test_loads_exactly_the_approved_package_and_item_revisions():
    package = training_knowledge.load_training_knowledge()
    assert package.reference == "AI_COACH_V1_KNOWLEDGE@1.0.0"
    assert tuple(item.reference for item in package.actionable_items) == (
        "TK_RETURN_AFTER_REPORTED_INTERRUPTION@1.0.0",
        "TK_EASY_RUNNING_PRIORITY@1.0.0",
    )
    assert all(item.actionable is True and item.status == "approved" for item in package.actionable_items)
    assert len(package.application_limitations) == 4
    assert all(limitation.actionable is False for limitation in package.application_limitations)
    assert package.content_sha256 == "cd1ca708d103307c9c84c74a7622edd4319fdee3f0d549fc3980a45b3cc6a839"


def test_sources_have_specific_reviewed_locators_and_resolve_from_items():
    package = training_knowledge.load_training_knowledge()
    sources = {source.id: source for source in package.sources}
    assert len(sources) == 8
    assert {source_id for item in package.actionable_items for source_id in item.source_ids} == set(sources)
    assert all(source.locator and source.supporting_guidance and source.review_notes for source in sources.values())
    assert sources["HHS_PHYSICAL_ACTIVITY_GUIDELINES_2018"].locator.endswith("printed page 90")
    assert sources["RRCA_TRAIN_DONT_STRAIN"].publication_date is None
    assert all(source.supporting_guidance.startswith("Reviewed paraphrase:") for source in sources.values())


def test_loading_is_repeatable_and_records_are_deeply_immutable():
    first = training_knowledge.load_training_knowledge()
    second = training_knowledge.load_training_knowledge()
    assert first == second
    assert first is not second
    with pytest.raises(FrozenInstanceError):
        first.version = "2.0.0"
    with pytest.raises(FrozenInstanceError):
        first.actionable_items[0].guidance = "altered"
    with pytest.raises(FrozenInstanceError):
        first.sources[0].locator = "altered"
    with pytest.raises(FrozenInstanceError):
        first.application_limitations[0].actionable = True
    with pytest.raises(TypeError):
        first.actionable_items[0].prerequisites[0] = "altered"


def test_json_formatting_does_not_change_the_release_fingerprint(tmp_path, monkeypatch, package_data):
    original = training_knowledge.load_training_knowledge()
    text = json.dumps(package_data, ensure_ascii=True, indent=4, sort_keys=True)
    assert load_document(tmp_path, monkeypatch, text) == original


@pytest.mark.parametrize("text", ["{", "[]", "null", "{}", '{"version":"1.0.0","version":"2.0.0"}', '{"x":NaN}', '{"x":Infinity}'])
def test_rejects_malformed_nonstandard_duplicate_or_nonobject_json(tmp_path, monkeypatch, text):
    with pytest.raises(ValueError):
        load_document(tmp_path, monkeypatch, text)


@pytest.mark.parametrize("path,value", [
    (("package_id",), "OTHER_PACKAGE"),
    (("version",), "1.0.1"),
    (("status",), "draft"),
    (("population",), " "),
    (("application_boundary",), []),
    (("application_boundary",), "instructions"),
    (("application_boundary",), [False]),
    (("sources",), None),
    (("sources",), []),
    (("sources", 0, "title"), ""),
    (("sources", 0, "publication_date"), 2018),
    (("sources", 0, "url"), "http://example.org"),
    (("sources", 0, "url"), "https:///missing-host"),
    (("sources", 0, "review_notes"), []),
    (("actionable_items",), []),
    (("actionable_items", 0, "status"), "candidate"),
    (("actionable_items", 0, "revision"), "0.1.0"),
    (("actionable_items", 0, "actionable"), False),
    (("actionable_items", 0, "actionable"), 1),
    (("actionable_items", 0, "id"), "UNAPPROVED_ITEM"),
    (("actionable_items", 0, "guidance"), None),
    (("actionable_items", 0, "source_ids"), ["UNKNOWN_SOURCE"]),
    (("actionable_items", 0, "source_ids"), ["HHS_PHYSICAL_ACTIVITY_GUIDELINES_2018"] * 2),
    (("actionable_items", 0, "prerequisites"), []),
    (("actionable_items", 0, "permitted_conclusions"), [None]),
    (("application_limitations",), []),
    (("application_limitations", 0, "actionable"), True),
    (("application_limitations", 0, "actionable"), 0),
    (("application_limitations", 0, "status"), "draft"),
    (("application_limitations", 0, "revision"), "2.0.0"),
    (("application_limitations", 0, "id"), "UNKNOWN_LIMITATION"),
    (("application_limitations", 0, "statements"), []),
    (("application_limitations", 0, "topic"), 4),
])
def test_rejects_unexpected_identity_classification_types_or_references(tmp_path, monkeypatch, package_data, path, value):
    parent = package_data
    for part in path[:-1]:
        parent = parent[part]
    parent[path[-1]] = value
    with pytest.raises(ValueError):
        load_data(tmp_path, monkeypatch, package_data)


@pytest.mark.parametrize("path", [(), ("sources", 0), ("actionable_items", 0), ("application_limitations", 0)])
@pytest.mark.parametrize("operation", ["extra", "missing"])
def test_rejects_extra_or_missing_fields_at_every_record_boundary(tmp_path, monkeypatch, package_data, path, operation):
    record = package_data
    for part in path:
        record = record[part]
    if operation == "extra":
        record["unexpected"] = "value"
    else:
        del record[next(iter(record))]
    with pytest.raises(ValueError, match="expected fields"):
        load_data(tmp_path, monkeypatch, package_data)


@pytest.mark.parametrize("section", ["actionable_items", "application_limitations", "sources"])
def test_rejects_duplicate_records(tmp_path, monkeypatch, package_data, section):
    package_data[section].append(package_data[section][0])
    with pytest.raises(ValueError):
        load_data(tmp_path, monkeypatch, package_data)


def test_rejects_unreferenced_sources(tmp_path, monkeypatch, package_data):
    package_data["actionable_items"][0]["source_ids"].pop()
    with pytest.raises(ValueError, match="unused sources"):
        load_data(tmp_path, monkeypatch, package_data)


def test_rejects_structurally_valid_changes_to_released_guidance(tmp_path, monkeypatch, package_data):
    package_data["actionable_items"][0]["guidance"] = "Immediately recover previous volume."
    with pytest.raises(ValueError, match="pinned approved revision"):
        load_data(tmp_path, monkeypatch, package_data)


@pytest.mark.parametrize("kind", ["missing", "directory", "invalid_utf8"])
def test_reports_unreadable_local_package_clearly(tmp_path, monkeypatch, kind):
    path = tmp_path / "package.json"
    if kind == "directory":
        path.mkdir()
    elif kind == "invalid_utf8":
        path.write_bytes(b"\xff")
    monkeypatch.setattr(training_knowledge, "_PACKAGE_PATH", path)
    with pytest.raises(ValueError, match="Cannot read the fixed"):
        training_knowledge.load_training_knowledge()


def test_unapproved_research_candidates_are_absent_from_runtime_document():
    text = training_knowledge._PACKAGE_PATH.read_text(encoding="utf-8")
    for candidate in (
        "TK_DEFER_QUALITY_REINTRODUCTION",
        "TK_DEFER_QUALITY_DURING_REPORTED_RETURN",
        "TK_CONSIDER_REDUCTION_WITH_REPORTED_STRESS",
    ):
        assert candidate not in text
