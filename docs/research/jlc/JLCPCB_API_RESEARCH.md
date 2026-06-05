# JLCPCB API Research

**Updated:** 2026-03-23  
**Status:** Live probing completed; official component detail API confirmed

## Summary

JLCPCB now exposes a real authenticated component API on:

- `https://open.jlcpcb.com`

The current official component surface is enough to stop scraping for
component-detail lookup by C-number.

What is confirmed live:

- public component feed:
  - `POST /overseas/openapi/component/getComponentInfos`
- private component library feed:
  - `POST /overseas/openapi/component/getPrivateComponentLibrary`
- component detail by C-number:
  - `POST /overseas/openapi/component/getComponentDetailByCode`

What is still not proven:

- official MPN / keyword search

So the recommended split is now:

- use official API for `get_part_details(Cxxxx)`
- keep scraper for `search_by_mpn(...)` until an official search route is found

## Authentication

All API requests use:

- HTTPS
- `POST`
- `Content-Type: application/json`
- UTF-8
- `Authorization: JOP ...`

Signature format from the docs:

```text
<HTTP Method>\n
<Request Path>\n
<Timestamp>\n
<Nonce>\n
<Request Body>\n
```

Signature algorithm:

- HMAC-SHA256
- Base64 output

Current local env fields used for probing:

- `JLCPCB_APP_ID`
- `JLCPCB_ACCESS_KEY`
- `JLCPCB_SECRET_KEY`

Tokenization keys are separate from request signing:

- `JLCPCB_TOKENIZATION_PUBLIC_KEY_PATH`
- `JLCPCB_TOKENIZATION_PRIVATE_KEY_PATH`

Those are RSA privacy/tokenization keys, not the HMAC signing secret.

## Official Component APIs

### 1. Public Component Feed

Endpoint:

```text
POST /overseas/openapi/component/getComponentInfos
```

Observed behavior:

- works with valid auth
- returns public library parts
- SDK wraps this endpoint
- request field `lastKey` is accepted for pagination
- extra search-ish fields like `lcscPart`, `mfrPart`, `componentCode` were ignored in live probes

Conclusion:

- this is a paginated feed/list endpoint
- not a true search endpoint

Representative response fields:

- `lcscPart`
- `mfrPart`
- `manufacturer`
- `firstCategory`
- `secondCategory`
- `stock`
- `price`
- `datasheet`

### 2. Private Component Library Feed

Endpoint:

```text
POST /overseas/openapi/component/getPrivateComponentLibrary
```

Observed behavior:

- works with valid auth
- returns authenticated private/library inventory rows
- extra search-ish fields were ignored in live probes

Representative response fields:

- `componentModel`
- `componentSpecification`
- `componentCode`
- `jlcpcbParts`
- `globalSourcingParts`
- `consignedParts`
- `idleStock`

Conclusion:

- real endpoint
- list/feed style, not proven as a search endpoint

### 3. Component Detail by C-number

Endpoint:

```text
POST /overseas/openapi/component/getComponentDetailByCode
```

This endpoint was found by live route probing and is real.

Correct request shape:

```json
{"componentCodes":["C2040"]}
```

Important:

- `componentCodes` must be an array
- scalar forms like `"C2040"` failed with a generic business error
- guesses like `componentCode`, `lcscPart`, and `cNumber` were not accepted

Live probes succeeded for:

- `C2040`
- `C2870085`

Representative response fields:

- `componentCode`
- `componentModel`
- `componentSpecification`
- `firstTypeName`
- `secondTypeName`
- `libraryType`
- `description`
- `datasheetUrl`
- `solderJointCount`
- `priceRanges`
- `stockCount`
- `parameters`
- `assemblyComponentFlag`
- `eccnCode`
- `rohsFlag`
- `dataManualUrl`

Conclusion:

- this is the official replacement for scraper-based C-number detail lookup

## SDK Analysis

JARs in this folder:

- `8633429564758577152-jlc-openapi-sdk-core-java-1.0.0.jar`
- `8642398160330141696-overseas-openapi-sdk-java-1.0.jar`
- `8642398872531484672-overseas-openapi-sdk-java-1.0.jar`
- `8642399738286297088-overseas-openapi-sdk-java-1.0.jar`

Important observations:

- the three overseas JARs are byte-identical
- core JAR metadata is from March 2025
- overseas JAR metadata is from August 2025
- the SDK is stale relative to the current docs/API list

The overseas SDK only exposes one component client method:

- `ComponentApiClient.getComponentInfo(...)`

Mapped URI:

- `/overseas/openapi/component/getComponentInfos`

The shipped request object only exposes:

- `lastKey`

So the SDK does **not** currently expose:

- `getPrivateComponentLibrary`
- `getComponentDetailByCode`

Conclusion:

- do not treat the Java SDK as authoritative for current component coverage
- treat the docs + live HTTP probing as authoritative

## Relationship To The Existing Scraper

Current scraper:

- search page:
  - `https://jlcpcb.com/parts/componentSearch?searchTxt=<mpn>`
- detail page:
  - `https://jlcpcb.com/partdetail/<C-code>`

The search/detail pages are Nuxt/SSR-backed and contain structured page data,
including fields like:

- `componentCode`
- `componentModelEn`
- `componentBrandEn`
- `lcscComponentId`
- `urlSuffix`

This strongly suggests the website is backed by an internal structured data
service, but the page HTML did not directly reveal the same public
`open.jlcpcb.com` routes.

Current best interpretation:

- scraper is using website SSR/internal backend data
- public Open Platform API is separate

## Recommended Implementation Direction

Short term:

- switch JLC `get_part_details()` to:
  - `getComponentDetailByCode`
- keep JLC `search_by_mpn()` on the scraper path

Medium term:

- optionally build a local searchable cache/index from `getComponentInfos`
- then use scraper only as fallback or retire it if official search emerges

## Files In This Directory

- `JLCPCB_API_RESEARCH.md`
- `8633429564758577152-jlc-openapi-sdk-core-java-1.0.0.jar`
- `8642398160330141696-overseas-openapi-sdk-java-1.0.jar`
- `8642398872531484672-overseas-openapi-sdk-java-1.0.jar`
- `8642399738286297088-overseas-openapi-sdk-java-1.0.jar`

## Next Steps

1. Implement an official JLC client path for:
   - `getComponentDetailByCode`
2. Keep scraper-based MPN search in place for now
3. Continue route discovery only if we want:
   - official MPN search
   - official filtering on the public/private feed endpoints
