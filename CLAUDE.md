# CLAUDE.md

Guidance for Claude when working on this repository.

## What this project does

A small, scheduled-friendly Python pipeline that extracts **every cat fact in every
supported language** from the public [meowfacts API](https://github.com/wh-iterabb-it/meowfacts)
and writes them to a single JSON file that analysts can load into BI tools.

It is intentionally designed to be run **daily** (e.g. via cron / Airflow / GitHub
Actions). Each run produces a fresh snapshot; the output shape is stable so that
downstream consumers can rely on it.

## How to run it

```bash
pip install -r requirements.txt
python src/main.py                                # writes ./output/meowfacts.json
python src/main.py --output /tmp/facts.json       # custom path
python src/main.py --languages eng esp            # subset (default: all)
```

Run from the project root. Python adds `src/` (the script's directory) to
`sys.path`, which is how `import meowfacts` resolves.

## Project layout

```
meowfacts_pipeline/
├── requirements.txt
├── output/                     # produced by main.py; gitignored artifact.
└── src/
    ├── main.py                 # Entry point. Only `main()` and the `__main__` guard — no helpers.
    └── meowfacts/              # the package. Structured as ETL — every stage lives in its own folder.
        ├── pipeline.py         # Pipeline class — orchestrates E → T → L. Implements no stage itself.
        ├── cli.py              # parse_args(), already_fetched_today(), DEFAULT_OUTPUT — entry-point helpers.
        ├── config.py           # Settings object (base URL, timeouts, retries). Pydantic.
        ├── extract/            # E: pull raw data from external sources.
        │   └── client.py       # MeowFactsClient — HTTP with retry/backoff. Returns wire shapes.
        ├── transform/          # T: shape raw data into output-contract objects. Pure, no I/O.
        │   └── transformer.py  # FactsTransformer — record & dataset assembly from wire shapes.
        ├── load/               # L: persist output-contract objects.
        │   └── writer.py       # DatasetWriter — atomic JSON write.
        ├── models/             # One file per data group. Never mix unrelated shapes.
        │   ├── api.py          # ApiFactResponse, ApiOptionsResponse — wire shapes only.
        │   ├── dataset.py      # FactRecord, Dataset — output contract shapes only.
        │   └── config.py       # Settings-adjacent models, if they grow out of config.py.
        └── utils/              # Shared code. Anything used in 2+ places lives here.
            └── logger.py       # Logger class — shared, configurable logging client.
```

Rules:

- `src/` contains only `main.py` at the top level. Any other file must live
  inside a subdirectory (a package or a topic folder) — never loose in `src/`.
- `main.py` contains only `main()` and the `__main__` guard. It wires things
  together and nothing else. Arg parsing, freshness checks, and any other
  helper belong in a sibling module under `meowfacts/` (see `cli.py`).

Together these keep the entry point obvious and force new code to declare
which concern it belongs to.

## Design principles to preserve

1. **≤150 lines per file.** If a file grows past that, split it.
2. **One class per file** where OOP is used. Functions are fine for pure helpers.
3. **Group connected files into folders.** If two files serve the same concern
   (e.g. several model groups, several writers, several clients), put them in a
   folder named after the concern. A folder is cheaper than a long flat list and
   tells a new developer where to look.
4. **Models are a folder, split by data group.** Never put unrelated shapes in
   one file — an API response and a config struct do not belong together. Name
   each file after the group it holds (`api.py`, `dataset.py`, `config.py`), so
   new contributors can find the right model without reading every file.
5. **Pydantic for every boundary** — API responses, config, and the output schema
   all go through Pydantic models. Never pass around raw dicts across module
   boundaries.
6. **Shared code lives in `utils/`, with one source of truth.** If the same
   helper, formatter, constant, or client is needed in two places, lift it into
   `utils/` and import it. No copy-paste. If you find duplication during a
   change, fix it in the same PR.
7. **Shared services are class-based clients in `utils/`, held as instance
   attributes.** A "client" here means a small class that wraps a shared
   resource (logger, HTTP session, metrics client, feature-flag client, cache,
   etc.) and is instantiated on each object that uses it — typically assigned
   to `self.<name>` in `__init__`. Process-wide configuration lives on the
   class (e.g. a `configure()` classmethod, called once from `main.py`), not on
   the instance. The logger is the canonical example:

   ```python
   # meowfacts/utils/logger.py
   class Logger:
       @classmethod
       def configure(cls, verbose: bool = False) -> None: ...   # call once, in main.py
       def info(self, msg, *args, **kwargs) -> None: ...
       # debug / warning / error / critical ...

   # meowfacts/client.py
   class MeowFactsClient:
       def __init__(self, settings):
           self.logger = Logger(__name__)
           ...
           self.logger.info("ready")
   ```

   The same shape applies to any future shared service: one `configure()` on
   the class, everywhere else imports the class and stores an instance on
   `self`. No module-level globals, no direct use of `logging` (or any other
   raw stdlib resource) in feature code.
8. **Stage responsibilities are strict, and the pipeline never implements a
   stage.** The code is laid out as ETL and the boundaries must be respected:
   - `extract/client.py` only talks to the API and returns parsed wire shapes.
     It knows nothing about `FactRecord` or `Dataset`.
   - `transform/transformer.py` only shapes wire data into output-contract
     objects (record & dataset assembly). It does no network and no disk I/O.
   - `load/writer.py` only persists a `Dataset` that is already fully built.
     It doesn't compute fields, doesn't call the API.
   - `pipeline.py` sequences E → T → L. It must not do the work of any stage
     itself; if a step grows logic, that logic belongs in the stage, not here.

   Don't let these leak. A new stage file (e.g. another extractor, a Parquet
   writer) goes in the matching folder — never flat in `meowfacts/`.
9. **Fail loud on config, fail soft on data.** A bad language code should skip
   that language with a logged warning; a missing env var or unreachable API
   should raise.
10. **No hardcoded language lists in code.** Languages are discovered at runtime
    via the `/options` endpoint so new locales appear automatically.

## Documentation style

Docs are for humans reading the code for the first time. The goal is: a new
developer can open a file and understand *why* something exists and *when* to
use it, without having to trace every call site.

Rules:

- **Document non-obvious things only.** If the name and signature already tell
  the full story (`def language_codes() -> list[str]`), skip the docstring.
  Adding `"""Return language codes."""` is noise.
- **Classes almost always deserve a short docstring.** A class is an API surface
  — say what it owns, what it does *not* own, and how it's meant to be used
  (e.g. "singleton — import `get_logger`, don't instantiate directly").
- **Hard functions deserve a docstring.** "Hard" means: non-trivial logic,
  a non-obvious invariant, a surprising side effect, or a subtle contract with
  the caller. Explain the *why*, not the *what*.
- **Keep it short.** 1–4 lines is the sweet spot. If you need more, the code
  is probably doing too much — split it instead of writing an essay.
- **No decorative docstrings.** Don't restate the function name. Don't list
  every parameter if the types already make it clear. Don't write "Args / Returns /
  Raises" boilerplate unless at least one of those sections carries information
  the signature doesn't.
- **Write for the next developer, not for a doc generator.** Plain sentences,
  no marketing tone.

## Output contract (do not break without bumping `schema_version`)

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-04-17T09:00:00Z",
  "source": "https://meowfacts.herokuapp.com",
  "language_count": 13,
  "fact_count": 312,
  "facts": [
    {
      "fact_id": 1,
      "language": "eng",
      "text": "...",
      "fetched_at": "2026-04-17T09:00:01Z"
    }
  ]
}
```

`fact_id` is a 1-based positional index within each language response,
mirroring the upstream API. It is **not** stable across runs — the upstream
API doesn't promise stability, so we don't either. Don't invent guarantees
(content hashes, dedup, normalization) for problems the upstream itself
doesn't solve; let the pipeline mirror upstream semantics.

Adding fields is safe; renaming, removing, or changing the type/semantics of
a field is a breaking change and needs `schema_version` bumped.

## Testing

Tests live in `tests/` (flat layout, one file per module under test) and run
with `pytest` from the project root. `pytest.ini` puts `src/` on `pythonpath`,
so tests import the package the same way `main.py` does.

What to test and what to skip:

- **Test what has logic.** Transform (pure), pipeline orchestration
  (fail-soft + branch paths), writer (atomic rename, unicode), client response
  parsing, CLI freshness check (error-swallowing).
- **Don't test pydantic models themselves** — they're declarative, so you'd be
  re-testing pydantic. Test them indirectly via the code that builds them.
- **Don't test the Logger wrapper** — it's a one-line delegation to stdlib.
- **Don't hit the network.** Client tests mock `_session`; pipeline tests mock
  `_client` and `_writer` but keep the real transformer (pure = safe to run).
- **Don't reassert what types already guarantee.** If a function returns
  `list[FactRecord]`, a test that checks `isinstance(x, list)` is noise.

Run: `python -m pytest` or just `pytest`.

## Scaling notes (when this gets bigger)

- **More sources?** Add a sibling package (e.g. `dogfacts/`) with its own
  `extract / transform / load / pipeline` layout. Promote truly shared pieces
  (retry config, logger, HTTP session) into a `common/` package at that point,
  not before.
- **Bigger volume?** Add a new writer under `load/` (e.g. `jsonl_writer.py` or
  `parquet_writer.py`) — the `FactRecord` model is already row-shaped for JSONL.
  The pipeline swaps writers in one line; transform and extract don't care.
- **Incremental loads?** Today every run is a full snapshot. For incremental,
  add a `since` param to `Pipeline.run` and persist a watermark — likely a new
  file under `load/`. Don't retrofit this until a real requirement lands.

## What NOT to do

- Don't add a database layer. This produces a file; storage is someone else's
  problem.
- Don't add async/await unless request volume actually justifies it — the API
  has a few hundred facts total and a sequential run finishes in seconds.
- Don't reach past the public interface of a module (e.g. importing
  `_private_helper` from `client.py`). If you need it, it isn't private.
