# How Altium Designer Talks to Supplier APIs

**Date:** 2026-04-25
**Source:** Decompiled Altium Designer 25.8.1 .NET assemblies at
`C:\Users\EliHughes\OneDrive - Wavenumber LLC\altium_research\25.8.1\.net_decompiled`
**Status:** Reference / informational only. Findings derived from a static
read of decompiled C# source. Not for re-use — see "Implications" below.

## TL;DR

Altium Designer's supplier search (Components panel, ActiveBOM, Manufacturer
Parts, the "Order" / supplier-solutions UI) does NOT use Nexar/Octopart for
data, and does NOT authenticate via an Altium 365 OAuth token. Instead it
calls a private Altium-hosted backend named **Ciiva** (Altium-owned since
2014) that aggregates distributor pricing, stock, datasheets, lifecycle,
and parametric data server-side.

## What was hypothesized

We assumed Altium would use Nexar (Octopart) and pass the user's Altium 365
credentials. That was wrong on both counts.

## Hostnames found in the decompiled tree

| Host | Purpose | File |
|---|---|---|
| `https://api3.ciiva.com/api` | Default JSON RPC backend (parts, suppliers, prices, stock, datasheets, manufacturers, exchange rates) | `Altium.Ciiva\DefaultConnectionParameters.cs:7` |
| `https://api.ciiva.com/api` | Older constant referenced by `CiivaConnectionParameters` | `Altium.Edp.PartSource.Altium\Altium.Edp.PartSource.Altium.SearchManager\CiivaConnectionParameters.cs:7,13` |
| Workspace-resolved `CiivaApi` URL | A365 tenant override returned by the portal settings — typically `<tenant>/api` | `Altium.Edp.SupplyChain.AltiumPartProvider\PortalConnectionParametersProvider.cs:146`: `portal.GetPRT_GlobalServiceUrl("CiivaApi")` |
| `https://octopart-clicks.com/click/altium` | Click-tracking redirector for "Buy" button navigation. **Not a data API call.** | `Altium.SupplyChain.Views\OctopartApi.cs:9,61`, also duplicated in `Altium.BOM.Common\OctopartApi.cs` |

`DXP\Hosts.cs` whitelists `.altium.com`, `.ciiva.com`, `.octopart.com` for
the embedded WebView.

### Negative findings

A full-tree search for the following turned up zero supplier-data hits:

- `api.nexar.com`, `nexar.com`
- `api.octopart.com` (other than the click-tracking redirector above)
- `api.mouser.com`, `developer.mouser`
- `api.digikey.com`, `developer.digikey`
- `api.arrow.com`, `supplyframe`, `oemsecrets`, `siliconexpert`
- GraphQL string literals
- Class names like `OctopartClient`, `NexarClient`

SiliconExpert appears only as a backend-provider flag on Altium's own
PartCatalog server (`PartExtraData/Providers/se/settings`) — Altium's
server queries SiliconExpert on the user's behalf; the desktop client does
not.

## Authentication model

Two tiers, both proprietary. **No `Authorization: Bearer` is ever
constructed in the supplier path.**

### Anonymous baseline

Hard-coded ServiceStack basic-auth credentials embedded in the binary:

```csharp
// Altium.Ciiva\DefaultConnectionParameters.cs
public static readonly Uri    Uri      = new Uri("https://api3.ciiva.com/api");
public static readonly string UserName = "0a7d3822-90a7-4b34-b7f5-733c1b9fdf57";
public static readonly string Password = "MBnwv3WKQEel9E1rOwkU";
```

Yes — these are literal hard-coded credentials in the desktop binary that
guarantee anonymous users can still hit `api3.ciiva.com`.

### Live-session upgrade

When the user signs into Altium 365, the desktop pushes the A365 IDS
session ID into the Ciiva client as a `globalids` provider credential:

```csharp
// Altium.Ciiva\CiivaClient.cs:392-402
public void EnableLiveSession(string liveSessionId) {
    Credentials newCredentials = new Credentials {
        UserName = liveSessionId,
        Password = string.Empty,
        Provider = "globalids"
    };
    credentialsHolder.ChangeCredentials(newCredentials, isSetLiveSessionByMethod);
}
```

Sourced from the running A365 portal connection, not a token exchange:

```csharp
// Altium.Edp.SupplyChain.AltiumPartProvider\PortalConnectionParametersProvider.cs:142-156
IPortal portal  = GlobalVars.Portal;
string url      = portal.GetPRT_GlobalServiceUrl("CiivaApi");
string user     = portal.GetPRT_Setting("CiivaUserName");
string password = portal.GetPRT_Setting("CiivaPassword");
```

`CiivaPartProvider.SetLiveSession(...)` and
`CiivaSearchManager.SetLiveSession(...)` propagate that session ID into
every search call. Transport: ServiceStack basic-auth + `ss-pid` session
cookie (cached via `CiivaClient.GetCiivaAPISessionID`, ~line 463).

## Architecture: aggregator-as-proxy

All distributor pricing, stock, datasheets, lifecycle, parametric
attributes, alternates, and MPN search go through one Altium-hosted
backend. Method roster on `Altium.Ciiva\CiivaClient.cs:160-280`:

- `GetManufacturerComponentsByPartNumber`
- `GetMultipleManufacturerComponentsByPartNumberForAltium`
- `GetPricingForSupplierComponentById`
- `GetStockForSupplierComponentById`
- `GetSupplierComponentsByManufacturerComponentId`
- `GetAllSuppliers`
- `GetAllManufacturers`
- `GetExchangeRates`
- `GetPartNumberSuggestion`
- `GetSubscriptionStatus`

Distributor names (`DigiKey`, `Mouser`, `Arrow`, etc.) are returned as
data fields, not API targets — see normalization table at
`Altium.Edp.SupplyChain.Contracts\SupplierConstants.cs:42-45`.

## ActiveBOM specifically

ActiveBOM has no supplier client of its own.
`Altium.ActiveBOM.Solutions\PrioritySolutionsFactory.cs` consumes
already-fetched `PartChoice` / `SupplierPart` / `PartSource` records. The
underlying fetch is delegated:

```
Altium.Edp.SupplyChain.AltiumPartProvider\CiivaPartProvider
  -> CiivaSearchManager
  -> CiivaClient   (api3.ciiva.com)
```

`ActiveBomPartExtraDataProvider.cs` separately calls Altium's PartCatalog
REST service for health/lifecycle/extra parameters via relative paths
(`ManufacturerParts`, `PartLifecycles`, `PartExtraData/Providers/se/settings`).
Base URL is the workspace's PartCatalog server (the same A365 tenant) —
again, not a third-party host.

## Where parametrics, lifecycle, and datasheets come from

All of it: Ciiva (`api3.ciiva.com` for anonymous use, or the user's A365
tenant's `CiivaApi` proxy when signed in) plus Altium's PartCatalog
service for paid extras like SiliconExpert lifecycle / availability data.
Datasheet URLs are fields inside Ciiva DTOs (`AltiumManufacturerComponent`),
not retrieved from a third-party API directly.

The only outbound non-Altium URL the desktop client ever generates for
supplier data is the Octopart click-tracking redirect, used purely for
"Order" / "Buy" button navigation in the UI.

## Implications for `supply-chain-monkey`

- **Ciiva is not a public API.** No developer portal, no docs, no
  published terms. The hard-coded basic-auth credentials are intended
  for the Altium Designer client; using them from a non-Altium app is at
  minimum a TOS issue and carries real legal risk. Do not use.
- **Altium's architecture validates the aggregator-as-proxy model** —
  they pay the integration cost once, server-side, and ship the desktop
  one API. That is exactly what Nexar/Octopart sells to non-Altium
  customers.
- **No re-use is available.** You cannot borrow Altium's auth or
  endpoint. The legitimate aggregator path stands: **TrustedParts (free,
  authorized distributors only) + Nexar (paid, if lifecycle/parametrics
  in one API are needed)**.
- **Octopart appears in Altium only as a click-tracking redirect** for
  "Buy" buttons. That is unrelated to data integration and provides no
  evidence about Octopart/Nexar's data API itself.

## Reproducing the search

The decompiled tree is large. The relevant assemblies are:

- `Altium.Ciiva` — the actual Ciiva HTTP client
- `Altium.Edp.PartSource.Altium` — search-manager wrapper
- `Altium.Edp.SupplyChain.AltiumPartProvider` — A365 portal connection wiring
- `Altium.Edp.SupplyChain.Contracts` — distributor name constants
- `Altium.SupplyChain.Views` — UI plus the Octopart click redirector
- `Altium.ActiveBOM` and `Altium.ActiveBOM.Solutions` — ActiveBOM consumers

A grep for `https://` and for the class names `CiivaClient`,
`CiivaSearchManager`, `CiivaPartProvider`,
`PortalConnectionParametersProvider` is the fastest way to retrace the
findings.
