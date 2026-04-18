import json
from datetime import datetime, timezone
from pathlib import Path

from meowfacts.load.writer import DatasetWriter
from meowfacts.models.dataset import Dataset, FactRecord


def _sample_dataset() -> Dataset:
    now = datetime.now(timezone.utc)
    return Dataset(
        generated_at=now,
        source="http://src",
        language_count=1,
        fact_count=1,
        facts=[FactRecord(fact_id=1, language="eng", text="meow", fetched_at=now)],
    )


def test_write_produces_valid_roundtrippable_json(tmp_path: Path):
    out = tmp_path / "dataset.json"
    DatasetWriter().write(_sample_dataset(), out)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == "1.0"
    assert loaded["facts"][0]["text"] == "meow"
    assert loaded["facts"][0]["fact_id"] == 1


def test_write_creates_missing_parent_dirs(tmp_path: Path):
    out = tmp_path / "nested" / "deep" / "dataset.json"
    DatasetWriter().write(_sample_dataset(), out)
    assert out.exists()


def test_write_leaves_no_tmp_files_on_success(tmp_path: Path):
    DatasetWriter().write(_sample_dataset(), tmp_path / "out.json")
    stray = [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
    assert stray == []


def test_write_preserves_unicode_text(tmp_path: Path):
    now = datetime.now(timezone.utc)
    dataset = Dataset(
        generated_at=now, source="http://src", language_count=1, fact_count=1,
        facts=[FactRecord(fact_id=1, language="esp", text="adiós 🐈", fetched_at=now)],
    )
    out = tmp_path / "out.json"
    DatasetWriter().write(dataset, out)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["facts"][0]["text"] == "adiós 🐈"
