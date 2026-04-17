from datetime import datetime, timezone

from ..models.api import ApiFactResponse
from ..models.dataset import Dataset, FactRecord


class FactsTransformer:
    """Transform stage: shape raw API responses into output-contract objects.

    Pure composition — no network, no disk. Swap this class to change the
    output contract without touching extract or load.

    Fact IDs mirror the upstream API's behavior: 1-based positional indexes
    within each language response. They are NOT stable across runs — the
    upstream API makes no such promise, so we don't invent one.
    """

    def to_records(self, response: ApiFactResponse, language: str) -> list[FactRecord]:
        fetched_at = datetime.now(timezone.utc)
        return [
            FactRecord(
                fact_id=idx + 1,
                language=language,
                text=text,
                fetched_at=fetched_at,
            )
            for idx, text in enumerate(response.data)
        ]

    def build_dataset(self, records: list[FactRecord], source: str) -> Dataset:
        return Dataset(
            generated_at=datetime.now(timezone.utc),
            source=source,
            language_count=len({r.language for r in records}),
            fact_count=len(records),
            facts=records,
        )
