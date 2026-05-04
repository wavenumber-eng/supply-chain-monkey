# Supply Chain Monkey Service Transition Plan

## Purpose

This document captures the planned transition of the supplier provider package
from an embedded workspace package into a standalone deployed internal service.

This is a planning document only. It does **not** mean the migration has
started. The active code now lives in the standalone `supply-chain-monkey` repo.

Target end state:

- standalone flat repo: `supply-chain-monkey`
- deployed FastAPI service
- all vendor credentials stored server-side only
- `appz` applications consume supplier data over HTTP only
- `toolz/supply_chain_monkey` is removed after cutover

## Why This Is Changing

The current package works, but it has structural limits:

- every developer must configure live vendor keys locally
- some providers are business/partner APIs with approval and allowlisting
- LCSC appears to require an approved application flow and may require fixed IP
  allowlisting
- JLC and LCSC integration behavior is increasingly server/infrastructure
  dependent rather than purely package-local
- `lib_cruncher` and future `bom_cruncher` should not directly own supplier
  credentials or vendor-specific logic

The centralization goal is:

- one organization-owned API
- one stable outbound IP / deployment surface
- one cache/rate-limit point
- one place to keep vendor credentials

## Current State

Today `supply_chain_monkey` inside `toolz` provides:

- generic supplier interface
- JLCPCB:
  - scraper-backed MPN search
  - hybrid detail path
    - official API detail by C-number
    - scraper enrichment/fallback
    - explicit legacy scraper option
- LCSC scraper-backed access
- Digikey and Mouser API-backed access
- package-local live provider tests

Current strengths:

- the provider adapter logic is useful and real
- the JLC hybrid model is working well
- test setup is straightforward

Current weaknesses:

- no centralized credential management
- no shared cache
- no shared rate limiting
- no shared provider health/status surface
- app consumers still couple directly to supplier implementation details

## Final Architecture Decision

The final architecture should be:

- standalone repo: `supply-chain-monkey`
- one top-level deployable application
- FastAPI server in that repo
- provider adapters and service runtime in the same repo

`appz` applications should **not** import supplier adapters directly in the end
state. They should call the service over HTTP.

This means the long-term model is:

- `lib_cruncher` -> HTTP -> `supply-chain-monkey`
- `bom_cruncher` -> HTTP -> `supply-chain-monkey`

and **not**:

- `lib_cruncher` -> import `supply_chain_monkey`
- `bom_cruncher` -> import `supply_chain_monkey`

## Why A Standalone Repo

This service should not stay in `toolz` or `appz` long-term because:

- the deployable shape needs to be flat for Appliku
- the service is infrastructure-facing
- the service will own secrets, network policy, caching, and deployment
- apps should consume it over HTTP, not as a Python dependency

It also should not be split into a separate `monkey` + `cruncher` pair for v1.

Reason:

- this service is primarily fetch/search/detail behavior
- it matches the `monkey` naming better than `cruncher`
- the deployable unit should stay simple
- the provider boundary is still moving and should not be fragmented early

## Planned Service Shape

Recommended repo layout:

```text
supply-chain-monkey/
  pyproject.toml
  README.md
  AGENTS.md
  .env.template
  Dockerfile
  src/py/supply_chain_monkey/
    main.py
    settings.py
    auth.py
    cache.py
    models.py
    routers/
      health.py
      providers.py
      search.py
      detail.py
    providers/
      base.py
      jlc.py
      lcsc.py
      digikey.py
      mouser.py
  tests/
  docs/
    adrs/
    plans/
    requirements/
    research/
```

The current `toolz` package can be used as source material, but the deployed
repo should own its final runtime and provider modules directly.

## Runtime Responsibilities

The standalone service should own:

- inbound authentication for internal clients
- provider credential loading
- provider routing
- fallback policy
- caching
- provider health/status reporting
- request logging and observability
- outbound vendor integration behavior

The service should **not** depend on `appz`.

## API Responsibilities

Phase 1 should stay small.

Suggested endpoints:

- `GET /v1/health`
- `GET /v1/providers/status`
- `GET /v1/search?supplier=jlcpcb&mpn=TPS543620RPYR`
- `GET /v1/detail?supplier=jlcpcb&part=C2870085`
- `POST /v1/search/batch`
- `POST /v1/detail/batch`

Optional later:

- `GET /v1/search/all?mpn=...`
- `POST /v1/cache/invalidate`
- `GET /v1/admin/provider-errors`

All responses should normalize around the equivalent of the current
`SupplierPartInfo` model, plus service metadata:

- `source_backend`
- `cached`
- `cache_age_seconds`
- `provider_latency_ms`
- `service_timestamp`

## Provider Strategy

Current recommended provider split:

- JLCPCB search by MPN:
  - scraper-backed initially
  - keep the newer Nuxt-data parser
- JLCPCB detail by C-number:
  - official API by default
  - scraper enrichment/fallback retained
- LCSC:
  - move to official API as soon as the approved account and whitelist are in
    place
- Digikey:
  - official API
- Mouser:
  - official API

Important future direction:

- evaluate whether LCSC official search can replace most JLC search scraping
  because of the shared C-number/component family overlap

## Deployment Plan

Deployment target:

- Appliku
- separate app
- existing DigitalOcean VM initially

Operational requirements:

- stable outbound public IP
- vendor credentials stored on the server only
- application-level auth token for internal callers

If the current VM outbound IP is sufficiently stable, use it first.

If infrastructure churn becomes likely, move to a Reserved IP later.

## Security Model

Server-side only:

- JLC credentials
- LCSC credentials
- Digikey credentials
- Mouser credentials

Client-side:

- one internal bearer token initially

Later options:

- per-client tokens
- service-to-service auth
- Plexus-backed user auth if needed

## Caching Plan

Caching should be part of v1, not a later enhancement.

Reason:

- vendor rate limits are shared at the organization level
- repeated team searches should not repeatedly hit upstream providers

Initial cache store:

- Postgres

Suggested TTLs:

- search results: `12-24h`
- detail responses: `24-72h`
- negative results: `1h`

Possible later addition:

- Redis for hot cache and provider throttling

## Logging And Observability

Phase 1 operational visibility should include:

- request IDs
- provider latency
- cache hit/miss
- provider error counts
- structured logs
- health/ready endpoints

## Migration Sequence

### Phase A: Planning

- finalize service shape
- finalize deployment assumptions
- finalize provider/key ownership model

### Phase B: New Repo Scaffold

- create standalone repo `supply-chain-monkey`
- scaffold FastAPI app, docs, tests, and deployment files
- copy or migrate current provider logic from `toolz/supply_chain_monkey`

### Phase C: First Functional Service

- health endpoint
- provider status endpoint
- JLC search endpoint
- JLC detail endpoint
- server-side credential loading
- basic cache

### Phase D: App Integration

- add service client in `lib_cruncher`
- switch UI/search flow behind a feature flag first
- validate zero local vendor-key requirement for users

### Phase E: Broader Provider Migration

- LCSC official API integration
- Digikey and Mouser through the service
- remove direct supplier imports from app code

### Phase F: Toolz Removal

After the standalone service is stable and apps are using HTTP:

- remove `supply_chain_monkey` from `toolz`
- remove package references from `appz`
- leave a short archival note in the frozen `toolz` path if useful

## Exit Criteria For Removing From Toolz

`toolz/supply_chain_monkey` should only be removed when all of the following are
true:

- standalone `supply-chain-monkey` repo exists
- service is deployed and reachable
- `lib_cruncher` is using the service over HTTP
- no app in active use imports `supply_chain_monkey` directly
- provider credentials are no longer needed on user machines
- basic caching and provider status endpoints are live

## Non-Goals For V1

These should not block the initial service:

- rich admin UI
- user-specific audit dashboards
- perfect provider abstraction across every edge case
- aggressive microservice decomposition
- removal of all scraper fallbacks

## Risks

- LCSC approval and whitelist workflow may take time
- JLC search scraping may still drift until an official search path is proven
- vendor rate limits may be tighter than expected
- mixing too much app-specific policy into the service

## Summary

This package is now considered transitional.

The long-term supported architecture is:

- standalone repo and service: `supply-chain-monkey`
- `appz` apps consume it only over HTTP
- after cutover, remove `supply_chain_monkey` from `toolz`
