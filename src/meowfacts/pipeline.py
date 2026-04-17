from pathlib import Path

from .config import Settings
from .extract.client import MeowFactsClient
from .load.writer import DatasetWriter
from .models.dataset import FactRecord
from .transform.transformer import FactsTransformer
from .utils.logger import Logger


class Pipeline:
    """Orchestrates Extract → Transform → Load.

    Sequences the stages but implements none of them. Fails soft on per-language
    errors (logs and skips); if discovery itself fails, proceeds with an empty
    language list and writes an empty dataset — the caller decides what to do.
    Swap any stage (different writer for Parquet, different transformer) without
    touching this file.
    """

    def __init__(self, settings: Settings | None = None):
        self.logger = Logger(__name__)
        self._settings = settings or Settings()
        self._client = MeowFactsClient(self._settings)
        self._transformer = FactsTransformer()
        self._writer = DatasetWriter()

    def run(self, languages: list[str] | None, output_path: str | Path) -> None:
        if languages is None:
            languages = self._discover_languages()
        records = self._collect_records(languages)
        dataset = self._transformer.build_dataset(records, source=self._settings.base_url)
        self._writer.write(dataset, output_path)

    def _discover_languages(self) -> list[str]:
        try:
            options = self._client.get_options()
        except Exception as exc:
            self.logger.error("Failed to discover languages, API may be unavailable: %s", exc)
            return []
        languages = options.get_languages()
        self.logger.info("Discovered %d languages: %s", len(languages), languages)
        return languages

    def _collect_records(self, languages: list[str]) -> list[FactRecord]:
        all_records: list[FactRecord] = []
        for lang in languages:
            try:
                response = self._client.get_facts(lang, self._settings.facts_per_request)
                records = self._transformer.to_records(response, lang)
                all_records.extend(records)
                self.logger.info("Fetched %d facts for language '%s'", len(records), lang)
            except Exception as exc:
                self.logger.warning("Skipping language '%s': %s", lang, exc)
        return all_records
