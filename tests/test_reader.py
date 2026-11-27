"""Synthetic package compatibility and rejection cases."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from financial_statement_sheets_sync import load_package


def package(tmp_path: Path) -> tuple[dict, dict]:
    record = {
        "schema_version": "1.0",
        "observation_id": "observation-1",
        "source": {
            "system": "example",
            "record_type": "export_transaction",
            "file_id": "file-1",
            "locator": "row:2",
        },
        "native_ids": {},
        "source_identity": {"status": "unconfirmed", "key": None, "basis": []},
        "raw": {
            "date": "2026-01-01",
            "amount": "10,00",
            "currency": "$",
            "description": "Example",
        },
        "parsed": {
            "amount": "10.00",
            "currency": "ARS",
            "dates": [{"role": "posted", "value": "2026-01-01"}],
            "description": "Example",
        },
        "references": {},
        "diagnostics": [],
        "extra_v1": {"kept": True},
    }
    manifest = {
        "schema_version": "1.0",
        "batch_id": "batch-1",
        "generated_at": "2026-01-01T12:00:00+00:00",
        "movements": {"path": "movements.jsonl", "sha256": "", "record_count": 1},
        "expected_files": [
            {
                "file_id": "file-1",
                "path": "input.csv",
                "system": "example",
                "sha256": "a" * 64,
                "expected_coverage": [],
                "status": "complete",
                "observed_coverage": [],
                "rows_read": 1,
                "rows_emitted": 1,
                "rows_discarded": 0,
                "errors": [],
                "warnings": [],
            }
        ],
        "complete": True,
        "extra_v1": {"kept": True},
    }
    write_package(tmp_path, manifest, [record])
    return manifest, record


def write_package(directory: Path, manifest: dict, records: list[dict]) -> None:
    payload = b"".join((json.dumps(row) + "\n").encode() for row in records)
    (directory / "movements.jsonl").write_bytes(payload)
    manifest["movements"]["sha256"] = hashlib.sha256(payload).hexdigest()
    manifest["movements"]["record_count"] = len(records)
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_loads_ordered_records_and_preserves_v1_additions(tmp_path: Path) -> None:
    manifest, first = package(tmp_path)
    second = deepcopy(first)
    second["observation_id"] = "observation-2"
    second["source"]["locator"] = "row:3"
    second["schema_version"] = manifest["schema_version"] = "1.1"
    first["schema_version"] = "1.1"
    manifest["expected_files"][0]["rows_read"] = 2
    manifest["expected_files"][0]["rows_emitted"] = 2
    write_package(tmp_path, manifest, [first, second])

    result = load_package(tmp_path)

    assert result.manifest == manifest
    assert result.observations == (first, second)
    assert load_package(tmp_path) == result


def test_accepts_incomplete_package_without_inventing_records(tmp_path: Path) -> None:
    manifest, record = package(tmp_path)
    manifest["complete"] = False
    manifest["expected_files"].append(
        {
            "file_id": "missing",
            "path": "missing.pdf",
            "system": "example",
            "sha256": None,
            "expected_coverage": [],
            "status": "missing",
            "observed_coverage": [],
            "rows_read": 0,
            "rows_emitted": 0,
            "rows_discarded": 0,
            "errors": [{"code": "missing_file", "message": "Missing"}],
            "warnings": [],
        }
    )
    write_package(tmp_path, manifest, [record])

    result = load_package(tmp_path)

    assert result.manifest["complete"] is False
    assert result.observations == (record,)


@pytest.mark.parametrize(
    "change,location",
    [
        ("digest", "manifest.movements.sha256"),
        ("count", "manifest.movements.record_count"),
        ("version", "manifest.schema_version"),
        ("path", "manifest.movements.path"),
        ("file_id", "movements.jsonl:1.source.file_id"),
        ("duplicate_id", "movements.jsonl:2.observation_id"),
        ("total", "manifest.expected_files"),
    ],
)
def test_rejects_corrupt_packages(tmp_path: Path, change: str, location: str) -> None:
    manifest, record = package(tmp_path)
    records = [record]
    if change == "digest":
        manifest["movements"]["sha256"] = "0" * 64
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    elif change == "count":
        manifest["movements"]["record_count"] = 2
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    elif change == "version":
        manifest["schema_version"] = "2.0"
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    elif change == "path":
        manifest["movements"]["path"] = "../outside.jsonl"
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    elif change == "file_id":
        record["source"]["file_id"] = "undeclared"
        write_package(tmp_path, manifest, records)
    elif change == "duplicate_id":
        records.append(deepcopy(record))
        manifest["expected_files"][0]["rows_read"] = 2
        manifest["expected_files"][0]["rows_emitted"] = 2
        write_package(tmp_path, manifest, records)
    else:
        manifest["expected_files"][0]["rows_emitted"] = 2
        write_package(tmp_path, manifest, records)

    with pytest.raises(ValueError, match=location.replace(".", r"\.")):
        load_package(tmp_path)


def test_rejects_missing_manifest(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="manifest.json"):
        load_package(tmp_path)


def test_rejects_mixed_versions(tmp_path: Path) -> None:
    manifest, record = package(tmp_path)
    record["schema_version"] = "1.1"
    write_package(tmp_path, manifest, [record])

    with pytest.raises(ValueError, match=r"movements.jsonl:1.schema_version"):
        load_package(tmp_path)


def test_rejects_false_complete_claim(tmp_path: Path) -> None:
    manifest, record = package(tmp_path)
    manifest["expected_files"][0]["status"] = "missing"
    manifest["expected_files"][0]["sha256"] = None
    write_package(tmp_path, manifest, [record])

    with pytest.raises(ValueError, match=r"manifest.expected_files"):
        load_package(tmp_path)


@pytest.mark.parametrize(
    "section,field",
    [("raw", "date"), ("parsed", "currency"), ("source_identity", "key")],
)
def test_rejects_missing_nullable_required_field(
    tmp_path: Path, section: str, field: str
) -> None:
    manifest, record = package(tmp_path)
    del record[section][field]
    write_package(tmp_path, manifest, [record])

    with pytest.raises(ValueError, match=rf"movements.jsonl:1.{section}.{field}"):
        load_package(tmp_path)
