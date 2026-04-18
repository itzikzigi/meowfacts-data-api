from datetime import datetime, timezone

from meowfacts.models.api import ApiFactResponse
from meowfacts.models.dataset import FactRecord
from meowfacts.transform.transformer import FactsTransformer


def _rec(fact_id: int, language: str) -> FactRecord:
    return FactRecord(
        fact_id=fact_id,
        language=language,
        text="t",
        fetched_at=datetime.now(timezone.utc),
    )


def test_to_records_assigns_positional_ids_starting_at_one():
    response = ApiFactResponse(data=["first", "second", "third"])
    records = FactsTransformer().to_records(response, language="eng")
    assert [r.fact_id for r in records] == [1, 2, 3]


def test_to_records_propagates_language_and_text():
    response = ApiFactResponse(data=["hola", "adiós"])
    records = FactsTransformer().to_records(response, language="esp")
    assert [r.language for r in records] == ["esp", "esp"]
    assert [r.text for r in records] == ["hola", "adiós"]


def test_to_records_uses_utc_fetched_at():
    record = FactsTransformer().to_records(ApiFactResponse(data=["x"]), "eng")[0]
    assert record.fetched_at.tzinfo is timezone.utc


def test_to_records_handles_empty_response():
    assert FactsTransformer().to_records(ApiFactResponse(data=[]), "eng") == []


def test_build_dataset_counts_distinct_languages_and_total_facts():
    records = [
        _rec(1, "eng"), _rec(2, "eng"), _rec(3, "eng"),
        _rec(1, "esp"), _rec(2, "esp"),
    ]
    dataset = FactsTransformer().build_dataset(records, source="http://src")
    assert dataset.fact_count == 5
    assert dataset.language_count == 2
    assert dataset.source == "http://src"
    assert dataset.schema_version == "1.0"


def test_build_dataset_handles_empty_records():
    dataset = FactsTransformer().build_dataset([], source="http://src")
    assert dataset.fact_count == 0
    assert dataset.language_count == 0
    assert dataset.facts == []
