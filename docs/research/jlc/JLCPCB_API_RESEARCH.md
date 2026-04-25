# JLCPCB API Research

**Updated:** 2026-04-25
**Status:** Live probing reconfirmed against live server. See divergences from
the 2026-04-25 PDF doc bundle below.

## Summary

JLCPCB exposes an authenticated component API on:

- `https://open.jlcpcb.com`

Confirmed live on 2026-04-25:

- `POST /overseas/openapi/component/getComponentDetailByCode`
- `POST /overseas/openapi/component/getComponentInfos`         (legacy name, still works, richest row shape)
- `POST /overseas/openapi/component/getComponentLibraryList`   (newer name, sparse rows)
- `POST /overseas/openapi/component/getPrivateComponentLibrary`

Still not present:

- official MPN / keyword search

The 2026-04-25 PDF bundle in this folder describes intended request/response
shapes. The live server diverges from those PDFs in several places. The
recorded shapes below are what the server actually returned during probing
on 2026-04-25; current implementation in `scm/server/providers/jlc_openapi.py`
matches the live server, not the PDFs.

## Authentication

All API requests use:

- HTTPS
- `POST`
- `Content-Type: application/json`
- UTF-8
- `Authorization: JOP appid="...",accesskey="...",nonce="...",timestamp="...",signature="..."`

Signature input:

```
<HTTP Method>\n
<Request Path>\n
<Timestamp>\n
<Nonce>\n
<Request Body>\n
```

Algorithm: HMAC-SHA256, output base64.

Env fields used by `JLCOpenAPIClient`:

- `JLCPCB_APP_ID`
- `JLCPCB_ACCESS_KEY`
- `JLCPCB_SECRET_KEY`

Tokenization keys (`JLCPCB_TOKENIZATION_PUBLIC_KEY_PATH`,
`JLCPCB_TOKENIZATION_PRIVATE_KEY_PATH`) are RSA privacy/tokenization keys,
unrelated to request signing.

## Common response envelope

All four `open.jlcpcb.com` endpoints return:

```json
{
  "success": true,
  "code": 200,
  "message": null,
  "data": ...
}
```

Note: the field is `success`, not `successful`. The 2026-04-25 PDF for
`getComponentLibraryList` shows `successful` — the live server uses
`success`. Our client at `_post()` checks `success == True` and that is
correct.

## Endpoints

### 1. `getComponentDetailByCode`

Endpoint:

```
POST /overseas/openapi/component/getComponentDetailByCode
```

Request body (live-confirmed):

```json
{"componentCodes": ["C2040", "C2870085"]}
```

- `componentCodes` must be an array; scalar fails.
- Up to 1000 codes per request (per PDF).

Response shape (live-confirmed 2026-04-25):

- `data` is **a list of detail rows directly**.
- The PDF claims `data.componentDetailResponseVOList[]`. The live server does
  not wrap it; current code unwrapping `data` as a list is correct.

Row fields (live):

- `componentCode`
- `componentModel`
- `componentSpecification`
- `firstTypeName`
- `secondTypeName`
- `libraryType`
- `description`
- `datasheetUrl`
- `solderJointCount`
- `priceRanges` (array of `{startQuantity, endQuantity, unitPrice}`)
- `stockCount`
- `parameters` (array of `{parameterName, parameterValue}`)
- `assemblyComponentFlag`
- `eccnCode`
- `rohsFlag`
- `dataManualUrl`               (present live, absent from new PDF)
- `dataManualOfficialLink`      (present live, absent from new PDF)
- `dataManualFileAccessId`      (present live, absent from new PDF)

The `dataManualUrl` fallback in `jlc.py:241` is meaningful — keep it.

### 2. `getComponentInfos` (legacy name, still live)

Endpoint:

```
POST /overseas/openapi/component/getComponentInfos
```

Not in the 2026-04-25 PDF bundle but **live-confirmed working**.

Request body:

```json
{}
```

or with pagination:

```json
{"lastKey": "<opaque key from previous response>"}
```

Response:

```
data.componentInfos = [ {row}, ... ]
data.lastKey = "..."
```

Row fields (live):

- `lcscPart`         (the JLC C-code, despite the name)
- `firstCategory`
- `secondCategory`
- `mfrPart`
- `solderJoint`
- `manufacturer`
- `libraryType`
- `description`
- `datasheet`
- `price`            (string, e.g. `"1-9:0.804724,10-29:0.585827,..."`)
- `stock`
- `package`

This is the richest list-style row shape JLC exposes, and it is the basis
for the local MPN index proposed in ADR-010.

Probe returned 1000 rows per page in a single call.

### 3. `getComponentLibraryList` (new name in 2026-04-25 PDFs)

Endpoint:

```
POST /overseas/openapi/component/getComponentLibraryList
```

Request body:

```json
{"pageSize": 30, "lastKey": "<optional>"}
```

Response:

```
data.componentLibraryInfoVOS = [ {row}, ... ]
data.lastKey = "..."
```

Row fields (live, sparse):

- `componentModel`
- `componentSpecification`
- `componentCode`

Useful as a fast catalog enumeration when only model/code/package are
needed. **Not** a replacement for `getComponentInfos` for MPN-search
indexing; the 3-field row is too thin.

Note: probe sent `pageSize: 30` and got back 1000 rows. Either the server
ignores `pageSize`, or `pageSize` is interpreted differently from the
PDF description. Treat the returned page size as authoritative and use
`lastKey` to advance.

### 4. `getPrivateComponentLibrary`

Endpoint:

```
POST /overseas/openapi/component/getPrivateComponentLibrary
```

Request body — server is permissive:

- `{}` works (defaults to ~30 rows).
- `{"pageNum": 1, "pageSize": 10}` also works (returns 10 rows).

Response shape (live-confirmed):

- `data` is **a list of rows directly**.
- The PDF claims `data.list[]` plus `pageNum`/`pageSize`/`total` siblings.
  The live server returns a flat list. Current code unwrapping `data` as
  a list is correct.

Row fields (live):

- `componentModel`
- `componentSpecification`
- `componentCode`
- `jlcpcbParts`
- `globalSourcingParts`
- `consignedParts`
- `idleStock`

Recommendation: pass `{"pageNum": 1, "pageSize": N}` explicitly even though
`{}` works today. The PDFs declare those fields required, and the server
may tighten validation later.

## Divergences: PDF docs vs. live server (2026-04-25)

| | 2026-04-25 PDF | Live server |
|---|---|---|
| top-level success field | `successful` (list endpoint) | `success` (all endpoints) |
| `getComponentDetailByCode` `data` | `{componentDetailResponseVOList:[...]}` | list directly |
| `getPrivateComponentLibrary` `data` | `{list:[...], pageNum, pageSize, total}` | list directly |
| `getPrivateComponentLibrary` body | `pageNum`+`pageSize` required | `{}` accepted, defaults to 30 rows |
| `getComponentInfos` (legacy) | not documented | works, richest row shape |
| detail row datasheet fields | `datasheetUrl` only | `datasheetUrl` + `dataManualUrl` + `dataManualOfficialLink` + `dataManualFileAccessId` |

The PDFs appear to describe a future or aspirational shape. Implementation
follows the live server.

## SDK status

JARs in this folder (March/August 2025):

- `8633429564758577152-jlc-openapi-sdk-core-java-1.0.0.jar`
- `8642398160330141696-overseas-openapi-sdk-java-1.0.jar`
- `8642398872531484672-overseas-openapi-sdk-java-1.0.jar`
- `8642399738286297088-overseas-openapi-sdk-java-1.0.jar`

The three overseas JARs are byte-identical and only expose
`ComponentApiClient.getComponentInfo(...)` mapped to `/getComponentInfos`.
They lag both the docs and the live API. Treat live HTTP probing as
authoritative.

## Relationship to the existing scraper

Current scraper paths in `jlc_scraper.py`:

- `https://jlcpcb.com/parts/componentSearch?searchTxt=<mpn>` (search HTML)
- `https://jlcpcb.com/partdetail/<C-code>` (detail HTML)

The HTML pages are Nuxt/SSR-backed; the public OpenAPI on `open.jlcpcb.com`
is a separate surface and does not expose a keyword search route.

The MPN-search path currently borrows the LCSC API to verify candidate
C-codes scraped from the JLC search HTML (`jlc_scraper.py:402-422`). This
is the LCSC-borrow that ADR-010 proposes to remove by indexing
`getComponentInfos` locally.

## Recommended implementation direction

Short term (no code change required):

- Current `jlc_openapi.py` matches the live server. No urgent fixes.
- Document the divergence between PDFs and live server (this file).

Medium term:

- Per ADR-010, build a local JLC index from `getComponentInfos` and use
  it to resolve MPN -> C-code, replacing the LCSC verification block in
  the scraper.
- Continue using `getComponentDetailByCode` for authoritative current
  stock/price after an index hit.

Future:

- If JLC retires `getComponentInfos`, fall back to `getComponentLibraryList`
  for catalog enumeration plus per-row `getComponentDetailByCode` to
  reconstitute the richer fields.
- Continue to monitor for an official keyword/MPN search endpoint.

## Files in this directory

- `JLCPCB_API_RESEARCH.md` (this file)
- `Component information interface 2026-04-25.pdf`            (legacy `api.jlcpcb.com/demo/component/info` multipart endpoint)
- `Get Component list 2026-04-25.pdf`                          (`getComponentLibraryList`)
- `Query Component Detail Data Interface 2026-04-25.pdf`       (`getComponentDetailByCode`)
- `Query Private Component Library Interface 2026-04-25.pdf`   (`getPrivateComponentLibrary`)
- `8633429564758577152-jlc-openapi-sdk-core-java-1.0.0.jar`
- `8642398160330141696-overseas-openapi-sdk-java-1.0.jar`
- `8642398872531484672-overseas-openapi-sdk-java-1.0.jar`
- `8642399738286297088-overseas-openapi-sdk-java-1.0.jar`

## Probe artifact

The 2026-04-25 probe script lives at `temp/probe_jlc_2026_04_25.py` and
can be re-run to confirm shapes after future API changes.
