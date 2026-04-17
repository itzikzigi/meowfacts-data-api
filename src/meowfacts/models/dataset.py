"""Output contract shapes.

These are the shapes analysts see. Renaming or removing a field here is a
breaking change and requires bumping `Dataset.schema_version` (see CLAUDE.md
"Output contract"). Adding a field is safe.
"""

from datetime import datetime

from pydantic import BaseModel


class FactRecord(BaseModel):
    fact_id: int
    language: str
    text: str
    fetched_at: datetime


class Dataset(BaseModel):
    schema_version: str = "1.0"
    generated_at: datetime
    source: str
    language_count: int
    fact_count: int
    facts: list[FactRecord]
