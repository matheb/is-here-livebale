import "@esri/calcite-components/dist/calcite/calcite.css";
import "leaflet/dist/leaflet.css";
import "./index.css";

import { defineCustomElements } from "@esri/calcite-components/dist/loader";
import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";

// Registers the Calcite web components (Esri's design system) for use
// throughout the app, e.g. <calcite-shell>, <calcite-button>, etc.
defineCustomElements(window);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
