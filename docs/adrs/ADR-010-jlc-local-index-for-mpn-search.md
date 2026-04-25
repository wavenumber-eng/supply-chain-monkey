# ADR-010: Local JLC Index for MPN Search

## Status

Proposed (deferred — current system works; revisit when ready)

## Context

JLCPCB does not expose a keyword/MPN search endpoint. The 2026-04-25 PDF doc
bundle (`docs/research/jlc/`) confirms this: the four documented surfaces are
`getComponentDetailByCode`, `getComponentLibraryList`, `getComponentInfos`, and
`getPrivateComponentLibrary`. None take an MPN, keyword, or `searchTxt`.

The current MPN search path in `jlc_scraper.py` works like this:

1. Fetch `https://jlcpcb.com/parts/componentSearch?searchTxt=<mpn>`.
2. Try to parse the structured Nuxt payload from the page.
3. If that fails, regex C-codes out of the HTML and verify each one against
   the **LCSC** detail API (`jlc_scraper.py:402-422`), falling back to the JLC
   detail scraper when LCSC misses.

The system works today. Borrowing LCSC for verification was an expedient that
predates the docs we now have. Downsides we want to retire eventually:

- LCSC and JLC stock/price can diverge. We currently return LCSC data
  labeled as JLC data.
- It couples the JLC provider to the LCSC API for reasons unrelated to
  LCSC's own role.
- It only works when JLC's HTML happens to leak a C-code we can verify.

Live probing on 2026-04-25 (see `JLCPCB_API_RESEARCH.md`) confirmed two
candidate enumeration endpoints we could feed a local index from:

- `getComponentInfos` (legacy name, still live, NOT in the 2026-04-25 PDFs)
  — rich rows: `lcscPart`, `mfrPart`, `manufacturer`, `description`,
  `datasheet`, `package`, `stock`, `price`, etc.
- `getComponentLibraryList` (new name, in the PDFs)
  — sparse rows: `componentModel`, `componentCode`, `componentSpecification`.

There is also a data-quality unknown that has to be resolved before
committing to either source: in the PDF example for `getComponentInfos`,
the row for C2727 shows `mfrPart: "TO-220,TO-220-3"` while the actual
manufacturer part number (per the row's own datasheet URL) is
`MBR20200CTG`. If `mfrPart` does not reliably contain the MPN across the
catalog, the "rich row" advantage of `getComponentInfos` evaporates and
the documented `getComponentLibraryList` path (whose `componentModel`
field is consistent with `getComponentDetailByCode.componentModel`)
becomes the better choice.

## Decision

### 1. Prototype offline before changing the request path

The current scraper + LCSC borrow stays as the primary search path. The
indexer work is built as a standalone offline pipeline that does not
touch `search_by_mpn` until it is proven.

### 2. Resolve the `mfrPart` data-quality question first

Probe a representative sample of rows from `getComponentInfos` and compare
each row's `mfrPart` to the same C-code's `componentModel` from
`getComponentDetailByCode`. Recommended sample: at least 100 rows spanning
multiple `firstCategory` values.

Pass criteria for `getComponentInfos` to be the index source:

- `mfrPart` matches `componentModel` (after normalization) for the
  large majority of sampled rows.

If it fails, prefer `getComponentLibraryList` + `getComponentDetailByCode`
as the index source on the grounds that `componentModel` is consistent and
the endpoint is documented.

### 3. Build the chosen pipeline as an offline experiment

Whichever endpoint wins the data-quality test:

- Walk the catalog with `lastKey` pagination.
- Write rows to a local store. SQLite with an FTS5 index on the MPN field
  + description is the leading candidate; flat JSON-lines is the fallback
  if SQLite adds operational friction on Appliku.
- If using `getComponentLibraryList`, optionally enrich a slice with
  `getComponentDetailByCode` (batch up to 1000) to add description /
  manufacturer / category fields.

This pipeline lives outside the request path. Acceptable form factors:
a script under `temp/`, a CLI module under `scm.tools`, or similar. Not
wired into the FastAPI app yet.

### 4. Decision gate before promoting to primary

Before touching `search_by_mpn`, measure on the offline prototype:

- Full-walk wall time and HTTP call count.
- Total catalog row count.
- MPN match rate against a known set of test parts (the existing
  scraper's known-good MPN set is a good starting point).

If those numbers look good, write a follow-up ADR (or revise this one to
"Accepted") that covers:

- Final storage location and refresh cadence.
- Removal of the LCSC verification block at `jlc_scraper.py:402-422`.
- Stateful service implications — the service is stateless today, and an
  on-disk index changes that. May motivate a separate ADR on storage
  location (Appliku managed disk vs. external object store).

### 5. Stock and price freshness (when promoted)

The index is a discovery layer, not a stock layer. After a hit, always call
`getComponentDetailByCode` to get current stock/price/lifecycle before
returning to the client. The index `stock` field is advisory.

## Consequences

- No code changes today. Current system continues to work unchanged.
- We preserve the option to remove the LCSC borrow without committing to
  an endpoint choice ahead of evidence.
- When promoted, JLC search returns authoritative JLC data, not LCSC
  stand-ins.
- Adds an indexer process and a small persistent store at promotion time.
  Up to now the service has been stateless; this is a real change.
- If we end up choosing `getComponentInfos` as the source we accept the
  risk that JLC may retire it in favor of `getComponentLibraryList`.
  Mitigation: the indexer is small and easy to retarget if the row shape
  changes.
