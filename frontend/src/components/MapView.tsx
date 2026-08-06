import { GeoJSON, MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import type { GeoJSONFeatureCollection } from "../api/client";
import type { SelectedPoi } from "../interfaces/poi";
import { POI_STATUS } from "../const/status";
import { ERROR, LABEL } from "../const/text";
import { default_zoom, GRAZ_COORD } from "../const/map";
import { useState } from "react";
import ResizeHandler from "./ResizeHandler";
import ClickHandler from "./ClickHandler";

interface MapViewProps {
  isochrone: GeoJSONFeatureCollection | null;
  selectedPoi: SelectedPoi | null;
  onMapClick: (latitude: number, longitude: number) => void;
  onClosePoiPopup: () => void;
}

export default function MapView({
  isochrone,
  selectedPoi,
  onMapClick,
  onClosePoiPopup,
}: MapViewProps) {
  const DEFAULT_CENTER: [number, number] = [GRAZ_COORD.lat, GRAZ_COORD.long];
  const DEFAULT_ZOOM = default_zoom;

  const [error, setError] = useState<string | null>(null);

  return (
    <MapContainer
      center={DEFAULT_CENTER}
      zoom={DEFAULT_ZOOM}
      className="map-container"
      scrollWheelZoom
    >
      <ResizeHandler />
      <ClickHandler onMapClick={onMapClick} />

      {error && (
        <calcite-notice
          open
          kind="danger"
          icon
          closable
          oncalciteNoticeClose={() => setError(null)}
        >
          <div slot="message">{error}</div>
        </calcite-notice>
      )}

      {/* OpenStreetMap tile layer */}
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {isochrone && (
        <GeoJSON
          // Re-mount on new data so react-leaflet's GeoJSON layer (which
          // doesn't diff its `data` prop) actually redraws the new shape.
          key={JSON.stringify(isochrone.features.map((f) => f.properties))}
          data={isochrone}
          style={{ color: "#d2691e", weight: 2, fillOpacity: 0.12 }}
        />
      )}

      {selectedPoi && (
        <>
          <Marker position={[selectedPoi.latitude, selectedPoi.longitude]} />
          <Popup
            position={[selectedPoi.latitude, selectedPoi.longitude]}
            eventHandlers={{ remove: onClosePoiPopup }}
          >
            {selectedPoi.status === POI_STATUS.loading && (
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <calcite-loader inline label={LABEL.loading_POI_label} />
                <span>{LABEL.loading_POI}</span>
              </div>
            )}

            {selectedPoi.status === POI_STATUS.ready && (
              <div>
                <strong>{selectedPoi.name ?? LABEL.selected_POI_label_placeholder}</strong>
                {selectedPoi.address && (
                  <div style={{ marginTop: "0.25rem" }}>{selectedPoi.address}</div>
                )}
                <div style={{ marginTop: "0.25rem", fontSize: "0.8em", color: "#666" }}>
                  {selectedPoi.latitude.toFixed(5)}, {selectedPoi.longitude.toFixed(5)}
                </div>
              </div>
            )}

            {selectedPoi.status === POI_STATUS.error && (
              <div>
                {ERROR.point_details}
                <div style={{ marginTop: "0.25rem", fontSize: "0.8em", color: "#666" }}>
                  {selectedPoi.latitude.toFixed(5)}, {selectedPoi.longitude.toFixed(5)}
                </div>
              </div>
            )}
          </Popup>
        </>
      )}
    </MapContainer>
  );
}
