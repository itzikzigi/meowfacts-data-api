# meowfacts-data-api

A scheduled Python pipeline that extracts every cat fact in every supported language from the public [meowfacts API](https://github.com/wh-iterabb-it/meowfacts) and writes them to a single JSON file for use in BI tools or downstream pipelines.

## Requirements

- Python 3.10+
- Dependencies: `pydantic>=2.0`, `requests>=2.31.0`, `urllib3>=2.0`

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Fetch all languages, write to ./output/meowfacts.json
python main.py

# Custom output path
python main.py --output /tmp/facts.json

# Fetch a subset of languages
python main.py --languages eng-us esp-es por-br

# Verbose logging (DEBUG level)
python main.py -v
```

## Project layout

```
meowfacts-data-api/
├── main.py                 # CLI entry point
├── requirements.txt
└── meowfacts/
    ├── config.py           # Settings (base URL, timeouts, retries)
    ├── models.py           # Pydantic models: ApiFactResponse, FactRecord, Dataset
    ├── client.py           # HTTP client with retry/backoff
    ├── collector.py        # Orchestrates language discovery and fact fetching
    └── writer.py           # Atomic JSON writer
```

## Output format

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-04-17T09:00:00Z",
  "source": "https://meowfacts.herokuapp.com",
  "language_count": 15,
  "fact_count": 1283,
  "facts": [
    {
      "fact_id": 1,
      "language": "eng-us",
      "text": "...",
      "fetched_at": "2026-04-17T09:00:01Z"
    }
  ]
}
```

Analysts key off `(fact_id, language)`. Adding fields is safe; renaming or removing fields is a breaking change and requires bumping `schema_version`.

## Supported languages

Languages are discovered automatically at runtime via the `/options` endpoint. As of April 2026 the API returns 15 variants:

| Code | Language |
|---|---|
| `ben-in` | Bengali (India) |
| `ces-cz` | Czech |
| `eng-us` | English (United States) |
| `esp-es` | Spanish (Spain) |
| `esp-mx` | Spanish (Mexico) |
| `fil-tl` | Filipino / Tagalog |
| `fra-fr` | French (France) |
| `ger-de` | German |
| `ita-it` | Italian |
| `kor-ko` | Korean |
| `por-br` | Portuguese (Brazil) |
| `rus-ru` | Russian |
| `ukr-ua` | Ukrainian |
| `urd-ud` | Urdu |
| `zho-tw` | Chinese (Taiwan) |

New locales published by the upstream API will appear automatically without any code changes.

## Error handling

| Scenario | Behaviour |
|---|---|
| Transient HTTP error (5xx, 429) | Retried up to 3 times with exponential backoff |
| Single language fetch fails after retries | Skipped with a `WARNING` log; remaining languages continue |
| `/options` endpoint unreachable (API totally down) | `ERROR` logged; produces an empty dataset (`fact_count: 0`); exits 0 |
| `--languages` passed and API is down | Skips discovery; each language is still attempted individually |
| Unexpected failure (disk full, bad path, etc.) | `CRITICAL` logged with full traceback; exits 1 |

## Running on a schedule

The pipeline is stateless — each run produces a full snapshot. Drop it into any scheduler:

**Cron (daily at 09:00):**
```cron
0 9 * * * cd /path/to/meowfacts-data-api && python main.py
```

**GitHub Actions:**
```yaml
on:
  schedule:
    - cron: "0 9 * * *"
jobs:
  fetch:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: python main.py --output output/meowfacts.json
      - uses: actions/upload-artifact@v4
        with:
          name: meowfacts
          path: output/meowfacts.json
```

## Configuration

Settings are loaded from a `.env` file in the project root (or from real environment variables). Copy the example and edit as needed:

```bash
cp .env.example .env
```

| Env var | Default | Description |
|---|---|---|
| `BASE_URL` | `https://meowfacts.herokuapp.com` | Upstream API base URL |
| `TIMEOUT_SECONDS` | `10` | Per-request timeout (seconds) |
| `MAX_RETRIES` | `3` | Max retry attempts per request |
| `BACKOFF_FACTOR` | `0.5` | Exponential backoff multiplier |
| `RETRY_ON_STATUSES` | `[429,500,502,503,504]` | HTTP status codes that trigger a retry |
| `FACTS_PER_REQUEST` | `9999` | Max facts requested per language (effectively "all") |

Environment variables take precedence over `.env` values. The `.env` file is optional — all settings have defaults.
