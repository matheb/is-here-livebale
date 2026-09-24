# Project Overview
- **Name:** IsHereLiveable
- **Description:** It is a starter full-stack project, whose aim is to analyze the location and infrastructure of a prospective home, with an emphasis of accessibility and mobility aspects
 
  - **Backend**: FastAPI, handles spatial data (GeoPandas/Shapely) and proxies a
    configurable third-party API (defaults to OpenStreetMap Nominatim for geocoding).
  - **Frontend**: React + Vite + TypeScript, map built with **Leaflet** on
    **OpenStreetMap** tiles, UI built with **Esri's Calcite Design System**