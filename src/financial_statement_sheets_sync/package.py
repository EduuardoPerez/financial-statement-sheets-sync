"""Read and validate processor reconciliation packages."""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal, overload


@dataclass(frozen=True)
class ReconciliationPackage:
    manifest: dict[str, Any]
    observations: tuple[dict[str, Any], ...]


def _fail(location: str, message: str) -> None:
    raise ValueError(f"{location}: {message}")


def _object(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(location, "expected an object")
    return value


def _required(item: dict[str, Any], field: str, location: str) -> Any:
    if field not in item:
        _fail(f"{location}.{field}", "missing required field")
    return item[field]


def _array(value: Any, location: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(location, "expected an array")
    return value


@overload
def _string(value: Any, location: str, *, nullable: Literal[False] = False) -> str: ...


@overload
def _string(value: Any, location: str, *, nullable: Literal[True]) -> str | None: ...


def _string(value: Any, location: str, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if not isinstance(value, str) or not value:
        _fail(location, "expected a nonempty string" + (" or null" if nullable else ""))
    return value


def _integer(value: Any, location: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _fail(location, "expected a nonnegative integer")
    return value


def _version(value: Any, location: str) -> str:
    version = _string(value, location)
    assert version is not None
    if re.fullmatch(r"1\.(0|[1-9][0-9]*)", version) is None:
        _fail(location, "unsupported schema version")
    return version


def _digest(value: Any, location: str, *, nullable: bool = False) -> None:
    digest = (
        _string(value, location, nullable=True)
        if nullable
        else _string(value, location)
    )
    if digest is not None and re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        _fail(location, "expected a lowercase SHA-256 digest")


def _relative_path(value: Any, location: str, directory: Path) -> Path:
    name = _string(value, location)
    assert name is not None
    path = Path(name)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in (".", "..") for part in path.parts)
    ):
        _fail(location, "expected a safe relative path")
    resolved = (directory / path).resolve()
    if not resolved.is_relative_to(directory.resolve()):
        _fail(location, "path escapes package directory")
    return resolved


def _diagnostics(value: Any, location: str) -> None:
    for index, item in enumerate(_array(value, location)):
        item_path = f"{location}[{index}]"
        diagnostic = _object(item, item_path)
        for field in ("code", "message"):
            _string(diagnostic.get(field), f"{item_path}.{field}")
        if "locator" in diagnostic:
            _string(diagnostic["locator"], f"{item_path}.locator")


def _coverage(value: Any, location: str) -> list[dict[str, Any]]:
    intervals = _array(value, location)
    for index, item in enumerate(intervals):
        item_path = f"{location}[{index}]"
        interval = _object(item, item_path)
        _string(interval.get("kind"), f"{item_path}.kind")
        try:
            start = date.fromisoformat(
                _string(interval.get("start"), f"{item_path}.start")
            )
            end = date.fromisoformat(_string(interval.get("end"), f"{item_path}.end"))
        except ValueError as exc:
            _fail(item_path, f"invalid coverage date: {exc}")
        if end < start:
            _fail(item_path, "coverage end precedes start")
    return intervals


def _file_entries(
    manifest: dict[str, Any], directory: Path
) -> dict[str, dict[str, Any]]:
    entries = _array(manifest.get("expected_files"), "manifest.expected_files")
    files: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(entries):
        location = f"manifest.expected_files[{index}]"
        entry = _object(item, location)
        file_id = _string(entry.get("file_id"), f"{location}.file_id")
        assert file_id is not None
        if file_id in files:
            _fail(f"{location}.file_id", "duplicate file ID")
        files[file_id] = entry
        _relative_path(entry.get("path"), f"{location}.path", directory)
        _string(entry.get("system"), f"{location}.system")
        status = _string(entry.get("status"), f"{location}.status")
        if status not in ("complete", "partial", "missing", "unreadable"):
            _fail(f"{location}.status", "invalid status")
        _digest(
            _required(entry, "sha256", location),
            f"{location}.sha256",
            nullable=True,
        )
        if status in ("complete", "partial") and entry["sha256"] is None:
            _fail(f"{location}.sha256", "readable file needs a digest")
        _coverage(entry.get("expected_coverage"), f"{location}.expected_coverage")
        _coverage(entry.get("observed_coverage"), f"{location}.observed_coverage")
        for field in ("rows_read", "rows_emitted", "rows_discarded"):
            _integer(entry.get(field), f"{location}.{field}")
        if entry["rows_emitted"] + entry["rows_discarded"] > entry["rows_read"]:
            _fail(location, "row counts exceed rows read")
        if status in ("missing", "unreadable") and entry["rows_emitted"]:
            _fail(f"{location}.rows_emitted", "unavailable file emitted records")
        _diagnostics(entry.get("errors"), f"{location}.errors")
        _diagnostics(entry.get("warnings"), f"{location}.warnings")
    return files


def _observation(
    record: Any, location: str, version: str, files: dict[str, dict[str, Any]]
) -> str:
    item = _object(record, location)
    if _version(item.get("schema_version"), f"{location}.schema_version") != version:
        _fail(f"{location}.schema_version", "mixed package versions")
    observation_id = _string(item.get("observation_id"), f"{location}.observation_id")
    assert observation_id is not None
    source = _object(item.get("source"), f"{location}.source")
    for field in ("system", "record_type", "file_id", "locator"):
        _string(source.get(field), f"{location}.source.{field}")
    file_id = source["file_id"]
    if file_id not in files:
        _fail(f"{location}.source.file_id", "undeclared file ID")
    if source["system"] != files[file_id]["system"]:
        _fail(f"{location}.source.system", "differs from declared file system")
    if "account_mask" in source:
        _string(source["account_mask"], f"{location}.source.account_mask")
    native_ids = _object(item.get("native_ids"), f"{location}.native_ids")
    for native_key, value in native_ids.items():
        _string(native_key, f"{location}.native_ids key")
        _string(value, f"{location}.native_ids.{native_key}")
    identity = _object(item.get("source_identity"), f"{location}.source_identity")
    status = identity.get("status")
    if status not in ("confirmed", "unconfirmed"):
        _fail(f"{location}.source_identity.status", "invalid identity status")
    key = _required(identity, "key", f"{location}.source_identity")
    basis = _array(identity.get("basis"), f"{location}.source_identity.basis")
    for index, field in enumerate(basis):
        _string(field, f"{location}.source_identity.basis[{index}]")
    if status == "confirmed":
        _string(key, f"{location}.source_identity.key")
        if not basis:
            _fail(
                f"{location}.source_identity.basis", "confirmed identity needs a basis"
            )
    elif key is not None or basis:
        _fail(
            f"{location}.source_identity",
            "unconfirmed identity needs null key and empty basis",
        )
    raw = _object(item.get("raw"), f"{location}.raw")
    for field in ("date", "amount", "currency", "description"):
        _string(
            _required(raw, field, f"{location}.raw"),
            f"{location}.raw.{field}",
            nullable=True,
        )
    parsed = _object(item.get("parsed"), f"{location}.parsed")
    amount = _string(parsed.get("amount"), f"{location}.parsed.amount")
    if re.fullmatch(r"-?[0-9]+(?:\.[0-9]+)?", amount) is None:
        _fail(f"{location}.parsed.amount", "invalid decimal amount")
    currency = _string(
        _required(parsed, "currency", f"{location}.parsed"),
        f"{location}.parsed.currency",
        nullable=True,
    )
    if currency is not None and re.fullmatch(r"[A-Z]{3}", currency) is None:
        _fail(f"{location}.parsed.currency", "invalid currency code")
    _string(
        _required(parsed, "description", f"{location}.parsed"),
        f"{location}.parsed.description",
        nullable=True,
    )
    for index, item_date in enumerate(
        _array(parsed.get("dates"), f"{location}.parsed.dates")
    ):
        date_path = f"{location}.parsed.dates[{index}]"
        dated = _object(item_date, date_path)
        _string(dated.get("role"), f"{date_path}.role")
        value = _string(dated.get("value"), f"{date_path}.value")
        try:
            date.fromisoformat(value)
        except ValueError:
            try:
                datetime.fromisoformat(value)
            except ValueError:
                _fail(f"{date_path}.value", "invalid ISO date or datetime")
    _object(item.get("references"), f"{location}.references")
    _diagnostics(item.get("diagnostics"), f"{location}.diagnostics")
    return observation_id


def load_package(directory: Path) -> ReconciliationPackage:
    """Load a v1 package, rejecting inconsistent evidence with a located error."""
    manifest_path = directory / "manifest.json"
    try:
        manifest = _object(
            json.loads(manifest_path.read_text(encoding="utf-8")), "manifest"
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail("manifest.json", str(exc))
    version = _version(manifest.get("schema_version"), "manifest.schema_version")
    _string(manifest.get("batch_id"), "manifest.batch_id")
    generated_at = _string(manifest.get("generated_at"), "manifest.generated_at")
    try:
        if datetime.fromisoformat(generated_at).utcoffset() is None:
            _fail("manifest.generated_at", "timestamp needs an offset")
    except ValueError:
        _fail("manifest.generated_at", "invalid ISO timestamp")
    movements = _object(manifest.get("movements"), "manifest.movements")
    movement_path = _relative_path(
        movements.get("path"), "manifest.movements.path", directory
    )
    _digest(movements.get("sha256"), "manifest.movements.sha256")
    expected_count = _integer(
        movements.get("record_count"), "manifest.movements.record_count"
    )
    files = _file_entries(manifest, directory)
    if not isinstance(manifest.get("complete"), bool):
        _fail("manifest.complete", "expected a boolean")
    if manifest["complete"] and any(
        file["status"] != "complete" for file in files.values()
    ):
        _fail("manifest.complete", "noncomplete expected file")
    if manifest["complete"] and any(file["rows_discarded"] for file in files.values()):
        _fail("manifest.complete", "discarded source rows")
    for file_id, entry in files.items():
        if entry["status"] == "complete" and not all(
            any(
                actual["kind"] == interval["kind"]
                and actual["start"] <= interval["start"]
                and actual["end"] >= interval["end"]
                for actual in entry["observed_coverage"]
            )
            for interval in entry["expected_coverage"]
        ):
            _fail(f"manifest.expected_files[{file_id}].status", "unmet coverage")
    try:
        payload = movement_path.read_bytes()
    except OSError as exc:
        _fail("manifest.movements.path", str(exc))
    if hashlib.sha256(payload).hexdigest() != movements["sha256"]:
        _fail("manifest.movements.sha256", "digest mismatch")
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    counts = dict.fromkeys(files, 0)
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeError as exc:
        _fail("manifest.movements.path", str(exc))
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        location = f"{movements['path']}:{number}"
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            _fail(location, f"invalid JSON: {exc}")
        observation_id = _observation(record, location, version, files)
        if observation_id in seen:
            _fail(f"{location}.observation_id", "duplicate observation ID")
        seen.add(observation_id)
        counts[record["source"]["file_id"]] += 1
        records.append(record)
    if len(records) != expected_count:
        _fail("manifest.movements.record_count", "record count mismatch")
    if sum(file["rows_emitted"] for file in files.values()) != expected_count:
        _fail(
            "manifest.expected_files", "emitted row total differs from movement count"
        )
    for file_id, count in counts.items():
        if count != files[file_id]["rows_emitted"]:
            _fail(
                f"manifest.expected_files[{file_id}].rows_emitted",
                "file record count mismatch",
            )
    return ReconciliationPackage(manifest, tuple(records))
