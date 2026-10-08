"""Load only the immutable, locally approved AI Coach V1 knowledge package.

This is a fixed document parser, not a knowledge-selection or application
engine. No source URLs are fetched and no prerequisites are evaluated here.
"""

from dataclasses import dataclass, fields
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit


_PACKAGE_PATH = Path(__file__).parent / "knowledge" / "v1.0.0.json"
_APPROVED_CONTENT_SHA256 = "cd1ca708d103307c9c84c74a7622edd4319fdee3f0d549fc3980a45b3cc6a839"
_ITEM_IDS = (
    "TK_RETURN_AFTER_REPORTED_INTERRUPTION",
    "TK_EASY_RUNNING_PRIORITY",
)
_LIMITATION_IDS = (
    "LIMIT_PERSISTENT_WEEKLY_RUNNING_DISTANCE_INCREASE",
    "LIMIT_QUALITY_ORIENTED_RUNNING",
    "LIMIT_RELATIVELY_LONGER_RUNS",
    "LIMIT_RUNNING_DAY_FREQUENCY",
)


@dataclass(frozen=True)
class SourceRecord:
    id: str
    title: str
    author: str
    publication_date: str | None
    url: str
    locator: str
    supporting_guidance: str
    knowledge_basis: str
    review_notes: tuple[str, ...]


@dataclass(frozen=True)
class KnowledgeItem:
    id: str
    revision: str
    status: str
    actionable: bool
    guidance: str
    knowledge_basis: str
    source_ids: tuple[str, ...]
    prerequisites: tuple[str, ...]
    permitted_conclusions: tuple[str, ...]
    limitations_exceptions: tuple[str, ...]
    reviewed_conflicts_differences: tuple[str, ...]

    @property
    def reference(self) -> str:
        return f"{self.id}@{self.revision}"


@dataclass(frozen=True)
class ApplicationLimitation:
    id: str
    revision: str
    status: str
    actionable: bool
    topic: str
    statements: tuple[str, ...]


@dataclass(frozen=True)
class TrainingKnowledgePackage:
    package_id: str
    version: str
    status: str
    population: str
    application_boundary: tuple[str, ...]
    sources: tuple[SourceRecord, ...]
    actionable_items: tuple[KnowledgeItem, ...]
    application_limitations: tuple[ApplicationLimitation, ...]
    content_sha256: str

    @property
    def reference(self) -> str:
        return f"{self.package_id}@{self.version}"


def _object(value: object, keys: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{label} must contain exactly the expected fields.")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be nonblank text.")
    return value


def _texts(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a nonempty list of text.")
    return tuple(_text(entry, label) for entry in value)


def _records(value: object, label: str) -> list:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a nonempty list of records.")
    return value


def _source(value: object) -> SourceRecord:
    data = _object(value, {field.name for field in fields(SourceRecord)}, "Source record")
    parsed = {
        key: _text(entry, f"Source {key}")
        for key, entry in data.items()
        if key not in {"publication_date", "review_notes"}
    }
    publication_date = data["publication_date"]
    if publication_date is not None:
        publication_date = _text(publication_date, "Source publication_date")
    url = urlsplit(parsed["url"])
    if url.scheme != "https" or not url.netloc:
        raise ValueError("Source URL must be an HTTPS locator.")
    return SourceRecord(
        **parsed,
        publication_date=publication_date,
        review_notes=_texts(data["review_notes"], "Source review_notes"),
    )


def _item(value: object) -> KnowledgeItem:
    data = _object(value, {field.name for field in fields(KnowledgeItem)}, "Knowledge item")
    if data["actionable"] is not True or data["status"] != "approved" or data["revision"] != "1.0.0":
        raise ValueError("Knowledge items must be approved actionable revision 1.0.0.")
    list_fields = {
        "source_ids", "prerequisites", "permitted_conclusions",
        "limitations_exceptions", "reviewed_conflicts_differences",
    }
    parsed = {
        key: _texts(entry, f"Item {key}") if key in list_fields else _text(entry, f"Item {key}")
        for key, entry in data.items()
        if key != "actionable"
    }
    return KnowledgeItem(**parsed, actionable=True)


def _limitation(value: object) -> ApplicationLimitation:
    data = _object(value, {field.name for field in fields(ApplicationLimitation)}, "Application limitation")
    if data["actionable"] is not False or data["status"] != "approved" or data["revision"] != "1.0.0":
        raise ValueError("Application limitations must be approved non-actionable revision 1.0.0.")
    parsed = {
        key: _texts(entry, "Limitation statements") if key == "statements" else _text(entry, f"Limitation {key}")
        for key, entry in data.items()
        if key != "actionable"
    }
    return ApplicationLimitation(**parsed, actionable=False)


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}.")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"Nonstandard JSON constant: {value}.")


def load_training_knowledge() -> TrainingKnowledgePackage:
    """Read and validate exactly AI_COACH_V1_KNOWLEDGE@1.0.0 locally.

    The canonical JSON fingerprint pins the reviewed contents, not formatting.
    Even structurally valid edits cannot silently replace a released revision.
    Missing/unreadable files and malformed/unexpected data raise ValueError.
    Each load creates immutable records; there is no mutable shared cache.
    """
    try:
        raw = _PACKAGE_PATH.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValueError("Cannot read the fixed Training Knowledge package.") from error
    try:
        data = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except ValueError as error:
        raise ValueError(f"Invalid Training Knowledge JSON: {error}") from error

    data = _object(data, {
        "package_id", "version", "status", "population", "application_boundary",
        "sources", "actionable_items", "application_limitations",
    }, "Knowledge package")
    if data["package_id"] != "AI_COACH_V1_KNOWLEDGE" or data["version"] != "1.0.0" or data["status"] != "approved":
        raise ValueError("Expected approved AI_COACH_V1_KNOWLEDGE@1.0.0.")
    population = _text(data["population"], "Package population")
    boundary = _texts(data["application_boundary"], "Package application_boundary")
    sources = tuple(_source(entry) for entry in _records(data["sources"], "Sources"))
    items = tuple(_item(entry) for entry in _records(data["actionable_items"], "Actionable items"))
    limitations = tuple(_limitation(entry) for entry in _records(data["application_limitations"], "Application limitations"))
    if tuple(item.id for item in items) != _ITEM_IDS:
        raise ValueError("Package must contain exactly the two approved actionable items in release order.")
    if tuple(limitation.id for limitation in limitations) != _LIMITATION_IDS:
        raise ValueError("Package must contain exactly the four approved application limitations in release order.")
    source_ids = {source.id for source in sources}
    if len(source_ids) != len(sources):
        raise ValueError("Source identifiers must be unique.")
    referenced_ids = set()
    for item in items:
        if len(set(item.source_ids)) != len(item.source_ids) or not set(item.source_ids) <= source_ids:
            raise ValueError("Item source references must be unique and resolve to package sources.")
        referenced_ids.update(item.source_ids)
    if referenced_ids != source_ids:
        raise ValueError("Every source must support an approved item; unused sources are forbidden.")

    canonical = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    content_sha256 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if content_sha256 != _APPROVED_CONTENT_SHA256:
        raise ValueError("Package contents differ from the pinned approved revision; a reviewed new release is required.")
    return TrainingKnowledgePackage(
        package_id=data["package_id"], version=data["version"], status=data["status"],
        population=population, application_boundary=boundary, sources=sources,
        actionable_items=items, application_limitations=limitations,
        content_sha256=content_sha256,
    )
