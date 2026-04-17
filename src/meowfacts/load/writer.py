import json
import os
import tempfile
from pathlib import Path

from ..models.dataset import Dataset
from ..utils.logger import Logger


class DatasetWriter:
    """Load stage: serialize a Dataset to JSON on disk, atomically."""

    def __init__(self):
        self.logger = Logger(__name__)

    def write(self, dataset: Dataset, output_path: str | Path) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = json.dumps(dataset.model_dump(mode="json"), indent=2, ensure_ascii=False)
        self._atomic_write(path, data)
        self.logger.info("Wrote %d facts to %s", dataset.fact_count, path)

    def _atomic_write(self, path: Path, data: str) -> None:
        """Write via temp file + rename so a crash mid-write never leaves a
        half-written JSON that downstream BI tools would happily parse."""
        fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
