import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_OUTPUT = Path("output/meowfacts.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch all meowfacts and write to JSON.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--languages", nargs="+", default=None)
    parser.add_argument("--force", action="store_true", help="Re-fetch even if output is already up to date.")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args()


def already_fetched_today(output_path: Path) -> bool:
    """True only if the existing file parses cleanly and its `generated_at`
    is today (UTC). Any read/parse failure is treated as "not fetched" so a
    corrupted file doesn't block a re-run — the next write will replace it."""
    if not output_path.exists():
        return False
    try:
        data = json.loads(output_path.read_text(encoding="utf-8"))
        generated_at = datetime.fromisoformat(data["generated_at"])
        return generated_at.date() == datetime.now(timezone.utc).date()
    except Exception:
        return False
