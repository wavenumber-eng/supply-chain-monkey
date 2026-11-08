# Supplier account data API review — 2026-11-02

This began as a read-only investigation of customer-held component stock, past
component purchases, PCB order history, and MPN-to-C-code search for future SCM
API and CLI work. It compares the downloaded JLC SDK bundles with the current
`production` SCM baseline (`2f755cd`). A subsequent authenticated stock check
is recorded below; order access remains unverified.

## Evidence and limits

- The downloaded `8800702540738781184-overseas-openapi-sdk-java-1.0.6.jar` is
  the latest stable business SDK among the five supplied archives. It has 146
  classes versus 93 in SCM's checked-in Java 1.0 SDK. The April and August
  snapshots have no request URI or client method absent from the final 1.0.6
  JAR. The downloaded Core SDK is byte-identical to SCM's checked-in core JAR;
  these files show no signing change. The Java business target moved from Java 8
  to Java 17; SCM's Python HTTP client does not load the JAR.
- SDK operations and request fields below were checked using `jar` and `javap`
  against those local artifacts. The anonymous website search probes used no
  account credentials. No authenticated supplier endpoint was called during
  the original 2026-11-02 review.
- [JLC's public API overview](https://api.jlcpcb.com/) describes PCB ordering
  and tracking and component pricing/stock. Its detailed API list did not expose
  endpoint definitions anonymously during this review. SDK presence alone does
  not prove this account's API entitlements or the semantics of a live response.

## JLC OpenAPI changes

| Need | Confirmed signed OpenAPI method and path in Java 1.0.6 | SCM today |
| --- | --- | --- |
| Customer/private component stock | `getPrivateComponentLibrary`, `POST /overseas/openapi/component/getPrivateComponentLibrary` | Direct HTTP method exists but is not exposed through SCM and requests only `{}` once. |
| Public component library feed | `getComponentLibraryList`, `POST /overseas/openapi/component/getComponentLibraryList` | Direct HTTP method exists. This is a paginated feed, not MPN search. |
| Component detail by C-code | `getComponentDetailByCode`, `POST /overseas/openapi/component/getComponentDetailByCode` | Direct HTTP method and JLC detail adapter exist. |
| PCB order list | `pagePcbOrderInfo`, `POST /overseas/openapi/pcb/pagePcbOrderInfo` | No SCM operation. Absent from checked-in Java 1.0 SDK. |
| Batch/order list by type | `pageBatchInfoByOrderType`, `POST /overseas/openapi/pcb/pageBatchInfoByOrderType` | No SCM operation. |
| PCB batch detail | `getOrderDetailByBatchNumV2`, `POST /overseas/openapi/pcb/v2/order/detail` | No SCM operation. The older `getOrderDetailByBatchNum` method also remains. |

`CustomerPrivateStockListRequest` has `currentPage` and `pageSize` fields,
defaulting to 1 and 30. Its response carries a list but no documented total or
cursor in the Java model. Stock rows carry `componentCode`, model,
specification, brand, and separate `jlcpcbParts`, `globalSourcingParts`,
`consignedParts`, and `idleStock` counts. SCM's current
`JLCOpenAPIClient.get_private_component_library()` sends `{}` and expects one
list. It may see only the first 30 rows; this needs a real authorized response
check, including the end-of-pages behavior. Do not add these counts together
without verifying their meanings and overlap.

`pagePcbOrderInfo` requests include `pageNum`, `pageSize`, `batchNum`,
`orderAccessId`, `createTimeStart`, and `createTimeEnd`. Its response model
contains `list`, `total`, and `pages`; entries include order and batch codes,
status, Gerber name, tracking number, and fee information. The v2 detail model
contains board/stencil order entries, shipping/payment information, and address
fields. Default SCM responses should select the operational fields needed for
history and leave address/payment data out unless explicitly required.

The supplied business SDKs have no component purchase-order history method.
They contain a TDP order-list method, but that is a separate 3D-printing order
surface. This is an SDK coverage finding, not proof that JLC has no other
private or future purchase-history API.

## JLC arbitrary component search

The official Java 1.0.6 component client has four methods: public feed,
library feed, private stock, and C-code detail. None accepts an MPN or keyword
search request. [JLC's search help article](https://jlcpcb.com/help/article/instruction-on-searching-jlcpcb-electronic-components)
describes website search, a separate surface.

The current JLC parts-page JavaScript uses the website route
`POST https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList/v2`.
An anonymous `CL10A106KQ8NNNC` probe returned application code 200, one result,
and `C95839`. It also worked with SCM's existing search request body unchanged.
The returned row retains the fields SCM converts: C-code, MPN, stock, prices,
and URL suffix. SCM's existing website route, at
`/api/overseas-smt-component-order-platform/v1/overseasSmtComponentOrder/componentSearch/selectSmtComponentList`,
returned HTTP 200 with application code 500 and
`java.lang.IllegalArgumentException: argument "content" is null` for that MPN.
Changing the URL appears to repair this *one* search probe, but both routes are
website APIs with no official OpenAPI stability promise. SCM's existing LCSC
C-code resolution remains a useful fallback until an official search path is
configured and validated.

JLConE 1.0.73 is an Electron shell around remotely loaded JLCPCB pages. Its
bundled `app.asar` opens `/user-center/` and has no component-search, inventory,
or order route implementation. Its cookie-sharing bridge serves the website
session; it is not JLC's signed OpenAPI. Current website JavaScript reveals:

On 2026-11-02, after the user signed in to JLConE, its local profile reported
`isLoggedIn: true`. Static inspection of the installed app's `app.asar` found
that its `http-request` IPC handler can read cookies from Electron's
`persist:shared` session and copy an `XSRF-TOKEN` cookie into the
`x-xsrf-token` request header. The handler accepts requests from the app's
local renderer, not arbitrary remote web pages or an external SCM process.
The active app holds its cookie database open, so this investigation did not
extract or replay any session secret. Anonymous calls to the inventory and
parts-order website routes both returned HTTP 200 with application code 460
(`automatically logged out`), consistent with those routes requiring a website
session. A live authenticated response is still needed to verify account
coverage, record IDs, paging, and response semantics. Copying desktop cookies
to the SCM VM would couple the service to a personal website session and its
expiry; it is suitable only as a short-lived local research probe, not the
primary service authentication design.

| Website UI need | Private route under `/api/overseas-smt-component-order-platform` | Observed UI request |
| --- | --- | --- |
| My inventory | `GET /v1/overseasSmtComponentOrder/myLibrary/getCustomerComponentStock` | `pageNum`, `pageSize`, `keyWord`, `inStock`; defaults 1, 30, empty keyword, null stock filter. |
| Parts purchase history | `POST /v1/overseasSmtComponentOrder/presaleOrder/selectPresaleOrderList` | `pageNum`, `pageSize`, `keyword`, optional `orderType`, `orderStatus`, `actionRequired`; defaults 1 and 25. |

Both UI responses are treated as `list` plus `total`. The inventory UI renders
`privateStockCount`, `idleStockCount`, `overseasStockCount`, and
`postStockCount`. The order-history UI labels `orderType=1` as JLC parts and
`orderType=2` as global sourcing, with `stockList`, `buyList`,
`overseasShopList`, and `idleOrderList` groups. This establishes a website
purchase-history screen, but neither full historical coverage nor access via
signed OpenAPI credentials. No authenticated request was made. The page
implementation is in JLC's public
[inventory](https://jlcpcb.com/user-center/user-center-static/js/8b68317e76dc5d90872a.js),
[order-history](https://jlcpcb.com/user-center/user-center-static/js/dd7a22d783d741b4acfb.js),
and [API declaration](https://jlcpcb.com/user-center/user-center-static/js/b32401e4da6db82cedd7.js)
bundles. These are leads for documentation review, not recommended server-side
SCM integrations.

## Other supplier coverage

| Supplier | Past component orders | Customer-held inventory | SCM gap |
| --- | --- | --- | --- |
| LCSC | [Official API list](https://www.lcsc.com/agent/list?urlKey=list) has search/detail, **only for orders created through its API**. | No account-held inventory endpoint found; catalog stock is available. | SCM uses unofficial website JSON. An official adapter needs partner credentials and current signed-request format. |
| DigiKey | [OrderStatus v4](https://developer.digikey.com/products/order-status/orderstatus/searchorders) lists orders by date with line items and pagination; sales-order detail is also documented. | [SupplyChain](https://developer.digikey.com/products/supplychain/supplychain) offers bonded inventory at authorized locations, requiring three-legged OAuth. | SCM uses two-legged OAuth for product search and has no account ID setting. Two-legged order search requires `X-DIGIKEY-Account-Id`. |
| Mouser | The checked-in V1 Swagger defines order history by date and order detail with line items. | No customer-held inventory API found; search stock is Mouser's catalog availability. | SCM implements only product search/detail; order-history entitlement of the existing key is unknown. |

**LCSC official API access:** [LCSC offers a reviewed, free partner
application](https://www.lcsc.com/agent/). Its current API list includes
`GET /rest/api/agent/product/v1/keywordsearch` for MPN, LCSC part number,
manufacturer, or category. This is the strongest supported candidate for
MPN-to-C-code resolution. An LCSC C-code match alone does not establish JLC
assembly-library availability or customer-held stock. Confirm candidates with
JLC C-code detail and exact MPN matching before presenting them as JLC-orderable.
The [current authentication guide](https://www.lcsc.com/agent/authentication?urlKey=authentication)
uses signed headers and SHA-256; the older `/docs/` SHA-1 example must not be
used as the current contract. Reference search limits are 60/minute and
1,000/day; actual limits depend on the approved account. The
[application](https://www.lcsc.com/agent/apply) asks for business details.
No registration was submitted.

**DigiKey details:** `SearchOrders` accepts a date range, `Shared`,
`PageNumber`, and `PageSize` up to 25. Its [current OrderStatus v4
Swagger](https://developer.digikey.com/node/2288/oas-download) says
`X-DIGIKEY-Account-Id` is required with two-legged OAuth. The existing SCM
DigiKey product adapter does not supply it. Bonded inventory is a different
account-owned stock concept from supplier catalog availability and needs an
additional OAuth authorization flow.

**Mouser details:** The checked-in V1 Swagger has `ByDateRange` and
`ByDateFilter` list routes and sales/web order detail. Its list routes do not
declare pagination. The current account's access to those APIs has not been
tested; do not infer that a product-search key also has order access.

## Recommended SCM sequence

1. Confirm account entitlements and obtain redacted live examples for JLC
   private stock pages, PCB order pages/detail, and any component purchase
   history the website docs expose. Confirm date formats, maximum page sizes,
   and whether private stock quantities overlap.
2. Add read-only, resource-specific SCM operations for customer-held stock,
   order lists, and order detail. Keep supplier catalog stock and your own
   physical inventory distinct from supplier-held customer stock. Normalize
   supplier, order kind, identifiers, dates/status, line items, quantities,
   and paging; retain limited provider detail when needed.
3. Author the new HTTP/JSON shapes in TypeSpec first, then regenerate Python
   and Rust contracts and extend both clients/CLI. The existing single SCM
   bearer token grants all authenticated operations; scope or otherwise
   restrict access before exposing account order data to automated tools.
4. Apply for LCSC partner API access for supported C-code search. Keep the
   website JLC search route behind a replaceable adapter and test its fallback
   behavior. Treat ordering/checkout as separate future write operations.

No implementation change or authenticated account test was made in the original
2026-11-02 review.

## Authenticated stock check — 2026-11-07

With credentials loaded into the local process environment, SCM's existing
signed JLC HTTP client successfully called `getPrivateComponentLibrary` using
`currentPage` and `pageSize`. Only response structure, row counts, and
identifier comparisons were printed; no credentials or inventory rows were
recorded. The response `data` was a list whose rows contained `componentCode`,
`componentModel`, `componentSpecification`, `componentBrandEn`, and the four
stock buckets documented above. The sampled bucket values were integers.

Page requests advanced through distinct rows. A request beyond the last page
repeated the final nonempty page instead of returning an empty list. The
response envelope had `code`, `success`, `message`, and `data`, with no total
count or next-page marker. Therefore a stock walker must detect a repeated
page and stop; an empty-page-only termination rule would loop indefinitely.
This observation establishes access and paging behavior for this account at
the time of the check, but does not establish the meaning or overlap of the
four stock buckets or snapshot consistency. PCB order access is examined
separately below.

A bounded walk with the SDK default page size found no missing or repeated
`componentCode` values, blank `componentModel` values, noninteger balances, or
negative balances. Some library rows reported zero in all four buckets, so
membership in this feed is not evidence of positive stock. At least one model
appeared under multiple C-codes; an MPN lookup must allow multiple records.
These observations are account-specific samples, not universal JLC guarantees.

JLC's [parts sourcing instructions](https://jlcpcb.com/help/article/pcba-parts-sourcing-instruction)
distinguish public JLC parts, global sourcing, customer pre-orders, and
consignment. Its [own-parts guidance](https://jlcpcb.com/help/article/how-to-use-my-own-parts-for-pcb-assembly-order)
also says the allowed combinations depend on source. These documents support
keeping the four SDK buckets separate; they do not establish an exact mapping
from every SDK field to ownership or build-available quantity. `idleStock`
remains especially unclear. No bucket should be summed or labeled "available
to build" without an account UI comparison or JLC confirmation.

## Authenticated PCB order check — 2026-11-07

The same signing credentials reached `pagePcbOrderInfo` and
`getOrderDetailByBatchNumV2`. For the order list, `createTimeStart` and
`createTimeEnd` are required in practice. Date-only strings failed validation;
`yyyy-MM-dd HH:mm:ss` was accepted. A bounded recent range and a prior
calendar-year range both returned order rows. The list `data` contained
`list`, `total`, `pages`, `pageNum`, and `pageSize`; a batch-detail response
contained PCB items plus shipping, address, and payment fields. The latter
must be filtered before any SCM response is built.

Sampled list rows had populated `batchNum`, `orderAccessId`, and `orderCode`.
Multiple rows shared one batch number, while sampled `orderAccessId` values
were distinct. A detail request for that shared batch returned the matching
PCB items, each with its own `orderAccessId`. This supports using the board
item's `orderAccessId` as a candidate list-row identity and `batchNum` as a
separate detail reference. It does not prove identifier stability across all
order types or over time. The sampled list and detail shapes did not establish
a placed-at timestamp, currency, or as-built component list. The API's date
filter timezone and whether it covers every website-placed historical order
also remain unverified; a known website order is needed for that comparison.

No order numbers, inventory rows, addresses, payment fields, or credentials
were recorded in this research note. No SCM account endpoint was implemented.

## Next research decisions

The immediate user goal is viewing purchased or pre-ordered parts held in
JLC's My Parts Lib through SCM. PCB order history is useful research, but is
not required for that inventory view.

1. Compare one known C-code and its four displayed stock categories in the
   account UI with the signed stock response. Keep raw source-bucket names
   until JLC confirms their exact meaning and any overlap.
2. Compare one known historical website-placed PCB batch, ideally containing
   multiple board items, with the signed list and detail responses. Confirm
   order-history coverage, timestamp timezone, and stable row identifiers.
3. Implement the JLC inventory slice independently of order history. Its
   authenticated source, response shape, and end-of-pages behavior are now
   established enough to build a bounded read-only adapter and contract.
