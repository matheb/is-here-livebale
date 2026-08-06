import {useRef, useState} from "react";

import {api, type GeoJSONFeatureCollection, type IsochroneMode} from "./api/client";
import MapView from "./components/MapView";
import type {SelectedPoi} from "./interfaces/poi";
import {POI_STATUS} from "./const/status";
import {SITE_HEADING, SITE_SUBTITLE} from "./const/text";

export default function App() {
  const [selectedPoi, setSelectedPoi] = useState<SelectedPoi | null>(null);
  const latestPoiRequestId = useRef(0);

  const [isochroneMode, setIsochroneMode] = useState<IsochroneMode>("walk");
  const [isochroneRangeMinutes, setIsochroneRangeMinutes] = useState("15");
  const [isochrone, setIsochrone] = useState<GeoJSONFeatureCollection | null>(null);
  const [isochroneLoading, setIsochroneLoading] = useState(false);
  const latestIsochroneRequestId = useRef(0);

  async function fetchIsochroneFor(latitude: number, longitude: number) {
    // Guard against out-of-order responses the same way handleMapClick
    // does — relevant here too since isochrone lookups can be slow
    // (Geoapify sometimes computes them asynchronously and this polls for
    // the result), so an earlier click's isochrone could otherwise finish
    // after a later one and overwrite it on screen.
    const requestId = ++latestIsochroneRequestId.current;

    setIsochroneLoading(true);
    setIsochrone(null); // clear the previous shape immediately, not just on success

    try {
      const result = await api.getIsochrone(
        latitude,
        longitude,
        isochroneMode,
        Number(isochroneRangeMinutes),
      );
      if (latestIsochroneRequestId.current !== requestId) return;
      setIsochrone(result);
    } catch (err) {
      if (latestIsochroneRequestId.current !== requestId) return;
      // setError(err instanceof Error ? err.message : String(err));
    } finally {
      if (latestIsochroneRequestId.current === requestId) setIsochroneLoading(false);
    }
  }

  async function handleMapClick(latitude: number, longitude: number) {
    // Guard against out-of-order responses: if the user clicks a second
    // point before the first lookup resolves, ignore the stale response.
    const requestId = ++latestPoiRequestId.current;

    // Show a marker at the clicked point immediately, in a loading state,
    // while the POI lookup (with reverse-geocoded name/address) resolves.

    setSelectedPoi({ latitude, longitude, status: POI_STATUS.loading, name: null, address: null });

    // Fetch the isochrone in parallel — it's a separate concern from the
    // POI lookup and shouldn't block on it, or vice versa.
    void fetchIsochroneFor(latitude, longitude);

    try {
      const poi = await api.getPoi(latitude, longitude);
      if (latestPoiRequestId.current !== requestId) return;
      setSelectedPoi({
        latitude,
        longitude,
        status: POI_STATUS.ready,
        name: (poi.properties?.name as string | null) ?? null,
        address: (poi.properties?.address as string | null) ?? null,
      });
    } catch {
      if (latestPoiRequestId.current !== requestId) return;
      setSelectedPoi({ latitude, longitude, status: POI_STATUS.error, name: null, address: null });
    }
  }

  return (
    <calcite-shell className="app-shell">
      <calcite-navigation slot="header">
        <calcite-navigation-logo slot="logo" heading={SITE_HEADING} description={SITE_SUBTITLE} />
        <calcite-action slot="content-end" icon="map" text="Map" />
      </calcite-navigation>

      <div
        style={{
          padding: "0.75rem 1rem",
          display: "flex",
          gap: "0.75rem",
          alignItems: "end",
          flexWrap: "wrap",
        }}
      >
        <calcite-label style={{ maxWidth: 160 }}>
          Isochrone mode
          <calcite-select
            value={isochroneMode}
            label={"PLACEHOLDER LABEL"}
            onChange={(e) =>
              setIsochroneMode((e.target as unknown as HTMLSelectElement).value as IsochroneMode)
            }
          >
            <calcite-option value="walk">Walk</calcite-option>
            <calcite-option value="bicycle">Bicycle</calcite-option>
            <calcite-option value="drive">Drive</calcite-option>
            <calcite-option value="transit">Public transit</calcite-option>
          </calcite-select>
        </calcite-label>
        <calcite-label style={{ maxWidth: 120 }}>
          Range (min)
          <calcite-input
            type="number"
            value={isochroneRangeMinutes}
            onInput={(e) =>
              setIsochroneRangeMinutes((e.target as unknown as HTMLInputElement).value)
            }
          />
        </calcite-label>

        {selectedPoi && (
          <calcite-button
            appearance="outline"
            loading={isochroneLoading}
            onClick={() => fetchIsochroneFor(selectedPoi.latitude, selectedPoi.longitude)}
          >
            Update isochrone
          </calcite-button>
        )}
      </div>

      <MapView
        isochrone={isochrone}
        selectedPoi={selectedPoi}
        onMapClick={handleMapClick}
        onClosePoiPopup={() => {
          setSelectedPoi(null);
          setIsochrone(null);
        }}
      />
    </calcite-shell>
  );
}
