import {
  CalciteInput,
  CalciteLabel,
  CalciteNavigation,
  CalciteNavigationLogo,
  CalciteShell,
} from "@esri/calcite-components-react";
import { useRef, useState } from "react";
import MapView from "./components/MapView";
import { LABEL, SITE_HEADING, SITE_SUBTITLE } from "./const/text";
import { SelectedPoi } from "./interfaces/poi";
import { api } from "./api/client";
import { POI_STATUS } from "./const/status";

export default function App() {
  const [selectedPoi, setSelectedPoi] = useState<SelectedPoi | null>(null);
  const latestPoiRequestId = useRef(0);

  async function handleMapClick(latitude: number, longitude: number) {
    // Guard against out-of-order responses: if the user clicks a second
    // point before the first lookup resolves, ignore the stale response.
    const requestId = ++latestPoiRequestId.current;

    // Show a marker at the clicked point immediately, in a loading state,
    // while the POI lookup (with reverse-geocoded name/address) resolves.
    setSelectedPoi({ latitude, longitude, status: POI_STATUS.loading, name: null, address: null });

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
    <CalciteShell className="app-shell">
      <CalciteNavigation slot="header">
        <CalciteNavigationLogo slot="logo" heading={SITE_HEADING} description={SITE_SUBTITLE} />
      </CalciteNavigation>

      <div style={{ padding: "0.75rem 1rem", display: "flex", gap: "0.75rem", alignItems: "end" }}>
        <CalciteLabel style={{ maxWidth: 200 }}>
          {LABEL.buffer}
          <CalciteInput type="text" />
        </CalciteLabel>
      </div>

      <MapView
        selectedPoi={selectedPoi}
        onMapClick={handleMapClick}
        onClosePoiPopup={() => setSelectedPoi(null)}
      />
    </CalciteShell>
  );
}
