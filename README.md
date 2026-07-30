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

| Method | Path                | Description                                   |
| ------ |---------------------| ---------------------------------------------- |
| GET    | `/health`           | Liveness/health check                         |
| GET    | `/spatial/sample`   | Sample GeoJSON FeatureCollection               |
| GET    | `/spatial/poi`      | Sample GeoJSON FeatureCollection               |
| POST   | `/spatial/buffer`   | Buffer a lat/lon point by meters → GeoJSON     |
| GET    | `/external/geocode` | Proxies a geocode lookup to the 3rd-party API  |

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

## Notes on the design system

Calcite components are web components; `defineCustomElements` is called
once in `src/main.tsx` to register them, and
`@esri/calcite-components-react` provides typed React wrappers
(`CalciteShell`, `CalciteButton`, `CalciteInput`, etc.) used in `App.tsx`.
Swap in more Calcite components as the UI grows — see the
[Calcite Design System docs](https://developers.arcgis.com/calcite-design-system/).
