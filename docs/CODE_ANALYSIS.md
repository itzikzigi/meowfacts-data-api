# meowfacts — Code Analysis

A read-through of the `meowfacts` API source, written for consumers who need to
understand what the service actually returns and how stable those returns are
before building a pipeline on top of it.

Scope: the upstream Node/Express service that lives at
`../projects/meowfacts/` (sibling directory on disk, separate repo:
[wh-iterabb-it/meowfacts](https://github.com/wh-iterabb-it/meowfacts)). This
document is written from the perspective of the data pipeline in *this*
repo, which consumes that API.

---

## 1. What this service is

A tiny Express app that serves cat facts over HTTP. There is **no database**.
All facts live in JavaScript source files, one per locale, under
[src/models/localizations/](../../projects/meowfacts/src/models/localizations/). The server reads
them into memory at startup and serves them from arrays.

Entry point: [src/app.js](../../projects/meowfacts/src/app.js). Three routes:

| Route      | Purpose                                             |
| ---------- | --------------------------------------------------- |
| `GET /`    | Return one or more cat facts                        |
| `GET /options` | List every supported language with metadata     |
| `GET /health`  | Uptime, version, request counter                |

CORS is wide open (`*`) and restricted to `GET` — see [app.js:29-37](../../projects/meowfacts/src/app.js#L29-L37).

---

## 2. How a fact is identified

This is the important part for anyone planning to key off facts.

### 2.1 There is no "real" ID

Facts are stored as plain JS arrays inside each locale file, for example
[eng-us.js](../../projects/meowfacts/src/models/localizations/eng-us.js#L1). The "ID" you pass via
`?id=` is **just the 1-based index into that array** — see
[facts.js:32-40](../../projects/meowfacts/src/models/facts.js#L32-L40):

```js
function getSingle(ID = null, lang = "eng-us") {
  const facts = getLanguageFacts(lang);
  if (ID) {
    const id = ID - 1;          // <-- ID is array index + 1
    return facts[id];
  }
  return facts[Math.floor(Math.random() * facts.length)];
}
```

Consequences you need to internalize:

- **The ID is positional, not intrinsic.** There is no field on a fact. The
  "ID" exists only because of array order.
- **ID 1 in `eng-us` and ID 1 in `ben-in` are unrelated strings** that happen
  to share the same array index. They may translate the same source fact in
  most locales (the tests verify ID 1 and ID 3 translate consistently across
  several languages) but this is a convention enforced only by whoever edits
  the files — not by the code.
- **ID ranges differ per language.** `getLanguages()` in
  [facts.js:62-87](../../projects/meowfacts/src/models/facts.js#L62-L87) exposes a `fact_count` per
  locale. English has ~93 facts; other locales have fewer. A valid ID in
  `eng-us` may be out of bounds in `ben-in`.

### 2.2 Can a fact change?

Yes. Silently. There is nothing in the code preventing it.

Because the ID is array position, **any of the following changes the meaning
of an ID**:

1. **Editing the string at that index.** A contributor fixes a typo in
   `eng-us.js` at index 5 → fact ID 6 now has different text, same ID.
2. **Inserting a fact in the middle of the array.** Every ID from that point
   onward shifts by one. The old "ID 42" is now "ID 43".
3. **Deleting a fact.** Same shift, in the other direction. The old "ID 42"
   is gone and a *different* fact now answers to ID 42.
4. **Re-ordering for any reason.** The indexing is implicit; there is no
   guard.

There is no version field on facts, no last-modified timestamp, no hash, no
content-addressed ID. The only way to detect a change is to fetch and compare
text yourself.

The API version in [package.json](../../projects/meowfacts/package.json#L3) (`0.4.14`) and
`/health`'s `version` field track the **service** version, not the data. A
fact text can change without any version bump.

### 2.3 ID stability in practice

Looking at the commit history of the locale files would tell you how often
this actually happens, but from a contract standpoint **treat `(lang, id)`
as an unstable key**. The text is the source of truth.

For a daily snapshot pipeline, the safest primary key in the output is:

- `(language, fact_id, text_hash)` if you want to detect in-place edits, or
- `(language, text)` if you are willing to treat edits as new facts.

Either works; don't trust `(language, fact_id)` alone.

---

## 3. Endpoint behaviour in detail

### 3.1 `GET /`

Defined at [app.js:65-80](../../projects/meowfacts/src/app.js#L65-L80). Query params, processed in
this priority order:

1. `count=N` present → return N **randomly sampled** facts (no replacement).
   The sample uses `Array.sort(() => 0.5 - Math.random())` — see
   [facts.js:49-55](../../projects/meowfacts/src/models/facts.js#L49-L55). Non-deterministic.
2. `id=N` present → return the fact at 1-based index N.
3. Neither → return one **random** fact.

`lang` is orthogonal and combines with any of the above.

**The random path is non-reproducible.** Two back-to-back calls with no `id`
will almost always return different facts. If your pipeline wants every fact,
you must iterate `id=1..fact_count` explicitly — which is what a sensible
collector should do, and what the `/options` endpoint exists to make
possible.

### 3.2 Response shape

Every `/` response is:

```json
{ "data": ["<string>", "<string>", ...] }
```

The `data` array holds **raw strings**, not objects. No `id`, no `lang`, no
`fetched_at` — the server does not echo back what you asked for. The
consumer has to remember its own request context to build a proper record.

### 3.3 `GET /options`

[app.js:86-88](../../projects/meowfacts/src/app.js#L86-L88) → [facts.js:62-87](../../projects/meowfacts/src/models/facts.js#L62-L87).
Returns one object per locale:

```json
{
  "lang": [
    {
      "locale_code": "us",
      "iso_code": "eng",
      "full_code": "eng-us",
      "local_name": "United States",
      "english_name": "english",
      "full_name": "english (United States)",
      "fact_count": 93
    }
  ]
}
```

`full_code` is the canonical identifier (`eng-us`, `ben-in`, etc.) and is
what you should send to `lang=`. `iso_code` (`eng`, `ben`) also works but is
ambiguous when multiple locales share one ISO (e.g. `esp-es` vs `esp-mx`);
the ambiguous case is resolved by `defaultLanguages` — see
[defaultLanguages.js](../../projects/meowfacts/src/models/localizations/defaultLanguages.js), which
currently maps bare `esp` → `esp-es`.

`fact_count` is authoritative for that locale at the moment of the call —
it's literally `facts.length` on the in-memory array. **Use this to bound
your iteration over IDs.** Don't hardcode.

### 3.4 `GET /health`

[app.js:94-105](../../projects/meowfacts/src/app.js#L94-L105). Returns `{uptime, version, requests}`.
The request counter resets on process restart (Heroku dyno spin-down). Useful
for liveness, not for any data correctness claim.

---

## 4. Validation middleware — caveats

[src/middleware.js](../../projects/meowfacts/src/middleware.js) has three middlewares: language,
count, and ID validation. A few of them are buggy in ways that affect
consumers:

- **`invalidCountMiddleware`** at [middleware.js:73-89](../../projects/meowfacts/src/middleware.js#L73-L89)
  checks `request.query.count == undefined` *while count is also truthy* —
  this condition can never be true, so the middleware is effectively a
  no-op. Invalid counts are not actually rejected by it; they just pass
  through to [facts.js:49](../../projects/meowfacts/src/models/facts.js#L49) and get handled by
  `Array.slice` semantics (negative/huge values silently degrade to
  whatever `slice` does).
- **`invalidIDMiddleware`** at [middleware.js:91-108](../../projects/meowfacts/src/middleware.js#L91-L108)
  forgets to `return` after calling `next()`, so in some branches the
  handler runs twice. Also uses `validateCount` (not a dedicated ID
  validator) to range-check. An out-of-range `id` will generally return
  `undefined` from [facts.js:36](../../projects/meowfacts/src/models/facts.js#L36) and the server
  will send `{"data":[null]}`.
- **`invalidLanguageMiddleware`** at [middleware.js:51-64](../../projects/meowfacts/src/middleware.js#L51-L64)
  works correctly. Unknown `lang` → 400 with the valid list. Known `lang`
  or no `lang` → passes through; `getLanguageFacts` falls back to `eng-us`
  if it doesn't match anything, so this is belt-and-suspenders.

**Practical implication:** don't trust the server to reject bad input
consistently. Validate on the client side before sending, and be defensive
about `null`/`undefined` strings in `data[]`.

---

## 5. Supported languages (as of this reading)

Discovered dynamically at startup by
[localizations/index.js:15-27](../../projects/meowfacts/src/models/localizations/index.js#L15-L27),
which barrel-imports every `.js` file in the folder except `index.js` and
`defaultLanguages.js`. Current set:

`ben-in`, `ces-cz`, `eng-us`, `esp-es`, `esp-mx`, `fil-tl`, `fra-fr`,
`ger-de`, `ita-it`, `kor-ko`, `por-br`, `rus-ru`, `ukr-ua`, `urd-ud`,
`zho-tw`.

New locales appear just by adding a file — which is why any consumer should
discover languages via `/options` rather than hardcoding a list.

---

## 6. Things to know when consuming this API

Short checklist for the pipeline:

1. **Call `/options` first.** It gives you both the full set of `full_code`
   values and the `fact_count` per locale. Everything else flows from there.
2. **Iterate IDs 1..fact_count per language.** Don't use `count=` for
   snapshotting — the sampling is random and may return duplicates if you
   repeat. `id=` is deterministic (for the current state of the file).
3. **Treat `(language, id)` as unstable.** If you need to detect changes
   between snapshots, store the text (or a hash of it) as well.
4. **Expect `null`s in `data[]` for out-of-range IDs.** Filter them at
   ingestion; don't let them into the output file.
5. **Expect the source to change silently.** Version bumps in `/health`
   don't track fact content. If you care about change tracking, do it
   yourself.
6. **Rate limit politely.** There is no rate limit enforced in the code, but
   this is someone else's Heroku dyno. Sequential requests with a small
   delay are fine; parallel floods are rude.
7. **`ben` in the ISO code maps to `ben-in`** and similar for most single-ISO
   locales. For Spanish, bare `esp` resolves to `esp-es` via
   `defaultLanguages`. Prefer sending the full code to avoid surprises.

---

## 7. One-line summary

The API is a read-only Express wrapper over a set of hand-maintained
JavaScript string arrays. IDs are array positions, not identifiers, and the
underlying text can change at any time with no signalling. Build your
pipeline assuming the text is the truth and the ID is a convenience.
