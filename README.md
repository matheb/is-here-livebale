# Spatial App — FastAPI + React
 
A starter full-stack project:
 
- **Backend**: FastAPI, handles spatial data (GeoPandas/Shapely) and proxies a
  configurable third-party API (defaults to OpenStreetMap Nominatim for geocoding).
- **Frontend**: React + Vite + TypeScript, map built with **Leaflet** on
  **OpenStreetMap** tiles, UI built with **Esri's Calcite Design System**
  (`@esri/calcite-components-react`).
```
project/
├── backend/          FastAPI app, tests, ruff config
└── frontend/          Vite + React app, vitest, eslint config
```
 
## Prerequisites
 
- Python 3.11+
- Node.js 20+
## Backend
 
```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env             # adjust EXTERNAL_API_BASE_URL / KEY as needed
 
uvicorn app.main:app --reload    # hot reload dev server on http://localhost:8000
```
 
- Interactive API docs: http://localhost:8000/docs
- Run tests: `pytest`
- Run linter: `ruff check .` (auto-fix: `ruff check . --fix`)
### Endpoints
 
| Method | Path                  | Description                                   |
| ------ | --------------------- | ---------------------------------------------- |
| GET    | `/health`              | Liveness/health check                         |
| GET    | `/spatial/sample`      | Sample GeoJSON FeatureCollection               |
| POST   | `/spatial/poi`         | Return a chosen lat/lon point as GeoJSON, enriched with name/address via reverse geocoding |
| POST   | `/spatial/buffer`      | Buffer a lat/lon point by meters → GeoJSON     |
| POST   | `/spatial/isochrone`   | Reachable-area polygon around a point (drive/walk/bicycle/transit) via the configured isochrone provider |
| GET    | `/external/geocode`    | Proxies a geocode lookup to the 3rd-party API  |
 
Point the backend at any other third-party API by changing
`EXTERNAL_API_BASE_URL` / `EXTERNAL_API_KEY` in `backend/.env` — the
`ExternalAPIClient` in `app/services/external_api.py` is the single place
that knows how to talk to it.
 
## Frontend
 
```bash
cd frontend
npm install
cp .env.example .env             # VITE_API_BASE_URL, defaults to /api (proxied to backend)
 
npm run dev                      # hot reload dev server on http://localhost:5173
```
 
- Run tests: `npm run test`
- Run linter: `npm run lint` (auto-fix: `npm run lint:fix`)
- Format: `npm run format`
- Build: `npm run build`
The Vite dev server proxies `/api/*` to `http://localhost:8000` (see
`vite.config.ts`), so make sure the backend is running too.
 
## Git
 
This repo is already initialized with an initial commit and a root
`.gitignore` covering both the Python and Node toolchains. A GitHub Actions
workflow (`.github/workflows/ci.yml`) runs lint + tests for both apps on
every push/PR.
 
## Troubleshooting
 
**`Cannot read properties of undefined (reading 'loading')` (or similar) from a
Calcite component:** this means `@esri/calcite-components` and
`@esri/calcite-components-react` resolved to mismatched versions. The React
wrapper package bundles its own compatible version of the components package
internally — do **not** add `@esri/calcite-components` as a separate direct
dependency in `package.json`. If you hit this, delete `node_modules` and the
lockfile and reinstall:
```bash
rm -rf node_modules package-lock.json
npm install
```
 
## Switching to a different geocoder
 
The public Nominatim instance (the default) is rate-limited and will 403
requests it suspects are from a regular app rather than sparse manual
lookups — not something to build on beyond local testing. `ExternalAPIClient`
(`app/services/external_api.py`) supports two ways to authenticate, covering
most providers via config alone:
 
- **Bearer header** (default): `Authorization: Bearer <EXTERNAL_API_KEY>`
- **Query-string key**: set `EXTERNAL_API_KEY_PARAM_NAME` (e.g. `key`) and
  the key is sent as `?<name>=<EXTERNAL_API_KEY>` instead
**Nominatim-compatible providers** (e.g. LocationIQ, which mirrors
Nominatim's `/search` and `/reverse` endpoints and `format=json` response
shape) need **no code changes** — just update `.env`:
```bash
EXTERNAL_API_BASE_URL=https://us1.locationiq.com/v1
EXTERNAL_API_KEY=your_locationiq_token
EXTERNAL_API_KEY_PARAM_NAME=key
```
See the commented example in `.env.example`.
 
**Providers with a different API shape** (Google, Mapbox, Geoapify's own
format, etc.) need the request/response handling updated too, since they
don't share Nominatim's `/search`/`/reverse` + `format=json` contract:
1. `ExternalAPIClient.geocode()` / `.reverse_geocode()` — update the path
   and query params to match the provider's API.
2. `app/api/routes/external.py` (`geocode`) and
   `app/api/routes/spatial.py` (`get_poi`) — update how the response is
   parsed (e.g. `item["lat"]`/`item["lon"]` → whatever fields that
   provider returns) and mapped onto `GeocodeResult` / the POI's
   `name`/`address` properties.
**The isochrone provider is configured independently** of the geocoding
provider above (`ISOCHRONE_API_*` settings vs `EXTERNAL_API_*`) — see
`ExternalAPIClient`'s `provider="geocoding"|"isochrone"` parameter, which
selects which config block to use. This matters because they're commonly
different vendors (e.g. LocationIQ for geocoding, Geoapify for
isochrones, as set up in this project) with separate base URLs, keys, and
auth styles.
 
## Logging
 
Every call to a third-party API flows through `ExternalAPIClient.get()`
(`app/services/external_api.py`), which logs consistently regardless of
which route/method is calling it:
 
| Level | What it logs |
|---|---|
| `DEBUG` | The exact request as httpx will actually send it: method, full URL with query string, and headers (API key **redacted** wherever it appears — query param or header) |
| `INFO` | Successful responses, with status code and timing |
| `WARNING` | Non-2xx responses, including the **response body** (the actual reason a request was rejected — invalid key, bad param, quota, etc.) |
| `ERROR` | Network-level failures (timeout, connection refused, DNS) |
 
The request is built explicitly via `client.build_request()` before being
logged and sent, so what you see in the log is the literal request on the
wire — not an approximation reconstructed from the base URL/path/params
separately.
 
Routes add their own business-context log line on top (e.g. "Reverse
geocode failed for (lat, lon): ..." in `/spatial/poi`), so a failure shows
both *what* went wrong at the HTTP level and *which* request in the app
triggered it.
 
Control verbosity via `LOG_LEVEL` in `.env` (`DEBUG`/`INFO`/`WARNING`/
`ERROR`) — `DEBUG` is especially useful when diagnosing a new third-party
API integration, since it shows the exact outgoing request. Logging is
configured once at startup in `app/logging_config.py`; without this,
FastAPI/uvicorn don't configure Python's root logger, so `INFO`/`DEBUG`
calls would otherwise be silently dropped.
 
## Click-to-select POI & isochrones
 
Click anywhere on the map to drop a marker at that point and fetch its
details via `POST /spatial/poi` — the popup shows a Calcite loader while
the reverse-geocode lookup is in flight, then the resolved name/address
(or a graceful "couldn't load details" message if the lookup fails).
Click the popup's close button to clear the selection. See
`frontend/src/components/MapView.tsx` (`ClickHandler`) and
`frontend/src/App.tsx` (`handleMapClick`) for the implementation.
 
The same click also fetches an isochrone (reachable-area polygon) around
that point via `POST /spatial/isochrone`, drawn as a second, distinctly
colored shape on the map. This runs **in parallel** with the POI lookup —
neither blocks on the other — via `fetchIsochroneFor()` in `App.tsx`, with
its own loading state and out-of-order-response guard (relevant since
isochrone lookups can take a few seconds, sometimes longer if the provider
computes it asynchronously — see below). Mode (drive/walk/bicycle/transit)
and range (minutes) are adjustable in the toolbar; changing them and
clicking "Update isochrone" recomputes for the currently selected point
without needing to click the map again.
 
### Handling async isochrone providers (Geoapify's 202 pattern)
 
Geoapify's Isoline API sometimes computes isochrones asynchronously: a
`202` response means "still computing," with an `id` to poll for the
result rather than an immediate `200`. `ExternalAPIClient.get_isochrone()`
(`app/services/external_api.py`) handles this transparently — polling
automatically (every 2s, up to 10 attempts by default) until the result
is ready, or raising `TimeoutError` if it never completes. Callers (the
`/spatial/isochrone` route) always just get back the final GeoJSON, or a
clean error — the polling detail is fully encapsulated in the client.
 
## Notes on the design system
 
Calcite components are web components; `defineCustomElements` is called
once in `src/main.tsx` to register them, and
`@esri/calcite-components-react` provides typed React wrappers
(`CalciteShell`, `CalciteButton`, `CalciteInput`, etc.) used in `App.tsx`.
Swap in more Calcite components as the UI grows — see the
[Calcite Design System docs](https://developers.arcgis.com/calcite-design-system/).
 
