import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import { GeoJSONFeatureCollection } from "../api/client";
import { default_zoom, GRAZ_COORD } from "../const/map";
import { useState } from "react";
import { CalciteLoader, CalciteNotice } from "@esri/calcite-components-react";
import ResizeHandler from "./ResizeHandler";
import { SelectedPoi } from "../interfaces/poi";
import ClickHandler from "./ClickHandler";
import { ERROR, LABEL } from "../const/text";
import {POI_STATUS} from "../const/status";

interface MapViewProps {
  bufferFeature?: GeoJSON.Feature | null;
  features?: GeoJSONFeatureCollection | null;
  selectedPoi: SelectedPoi | null;
  onMapClick: (latitude: number, longitude: number) => void;
  onClosePoiPopup: () => void;
}

export default function MapView({ onClosePoiPopup, onMapClick, selectedPoi }: MapViewProps) {
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
        <CalciteNotice open kind="danger" icon closable onCalciteNoticeClose={() => setError(null)}>
          <div slot="message">{error}</div>
        </CalciteNotice>
      )}

      {/* OpenStreetMap tile layer */}
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {selectedPoi && (
        <>
          <Marker position={[selectedPoi.latitude, selectedPoi.longitude]} />
          <Popup
            position={[selectedPoi.latitude, selectedPoi.longitude]}
            eventHandlers={{ remove: onClosePoiPopup }}
          >
            {selectedPoi.status === POI_STATUS.loading && (
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <CalciteLoader inline label={LABEL.loading_POI_label} />
                <span>{LABEL.loading_POI}</span>
              </div>
            )}

            {selectedPoi.status === POI_STATUS.ready && (
              <div>
                <strong>{selectedPoi.name ?? "Selected point"}</strong>
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
