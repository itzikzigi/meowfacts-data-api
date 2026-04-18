import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from meowfacts.cli import already_fetched_today


def test_returns_false_when_file_missing(tmp_path: Path):
    assert already_fetched_today(tmp_path / "does-not-exist.json") is False


def test_returns_true_when_generated_today(tmp_path: Path):
    path = tmp_path / "out.json"
    path.write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat()}))
    assert already_fetched_today(path) is True


def test_returns_false_when_generated_yesterday(tmp_path: Path):
    path = tmp_path / "out.json"
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    path.write_text(json.dumps({"generated_at": yesterday.isoformat()}))
    assert already_fetched_today(path) is False


def test_returns_false_when_json_is_malformed(tmp_path: Path):
    path = tmp_path / "out.json"
    path.write_text("{not valid json")
    assert already_fetched_today(path) is False


def test_returns_false_when_generated_at_field_missing(tmp_path: Path):
    path = tmp_path / "out.json"
    path.write_text(json.dumps({"other": "stuff"}))
    assert already_fetched_today(path) is False
