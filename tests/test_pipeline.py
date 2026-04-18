from pathlib import Path
from unittest.mock import MagicMock

from meowfacts.models.api import ApiFactResponse
from meowfacts.pipeline import Pipeline


def _pipeline_with_mocked_io() -> Pipeline:
    """Pipeline with mocked extract/load stages and the real transformer —
    transformer is pure, so keeping it real lets tests verify end-to-end shape
    while still controlling external calls."""
    p = Pipeline()
    p._client = MagicMock()
    p._writer = MagicMock()
    return p


def test_explicit_languages_skips_discovery(tmp_path: Path):
    p = _pipeline_with_mocked_io()
    p._client.get_facts.return_value = ApiFactResponse(data=["a", "b"])
    p.run(languages=["eng"], output_path=tmp_path / "out.json")
    p._client.get_options.assert_not_called()
    dataset = p._writer.write.call_args.args[0]
    assert dataset.fact_count == 2
    assert dataset.language_count == 1


def test_no_languages_triggers_discovery(tmp_path: Path):
    p = _pipeline_with_mocked_io()
    options = MagicMock()
    options.get_languages.return_value = ["eng"]
    p._client.get_options.return_value = options
    p._client.get_facts.return_value = ApiFactResponse(data=["a"])
    p.run(languages=None, output_path=tmp_path / "out.json")
    p._client.get_options.assert_called_once()


def test_failing_language_is_skipped_and_others_continue(tmp_path: Path):
    p = _pipeline_with_mocked_io()
    p._client.get_facts.side_effect = [
        RuntimeError("boom"),
        ApiFactResponse(data=["ok1", "ok2"]),
    ]
    p.run(languages=["broken", "eng"], output_path=tmp_path / "out.json")
    dataset = p._writer.write.call_args.args[0]
    assert dataset.fact_count == 2
    assert dataset.language_count == 1


def test_discovery_failure_skips_write(tmp_path: Path):
    """If discovery fails we collect zero records — the writer must NOT be
    called, otherwise an empty snapshot dated today would block the next run's
    freshness check from retrying."""
    p = _pipeline_with_mocked_io()
    p._client.get_options.side_effect = RuntimeError("network down")
    p.run(languages=None, output_path=tmp_path / "out.json")
    p._client.get_facts.assert_not_called()
    p._writer.write.assert_not_called()


def test_all_languages_failing_skips_write(tmp_path: Path):
    p = _pipeline_with_mocked_io()
    p._client.get_facts.side_effect = RuntimeError("boom")
    p.run(languages=["eng", "esp"], output_path=tmp_path / "out.json")
    p._writer.write.assert_not_called()
