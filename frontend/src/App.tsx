// From now on, from now on...

import {useRef, useState} from "react";

import {api, type GeoJSONFeatureCollection, type IsochroneMode} from "./api/client";
import MapView from "./components/MapView";
import { ToggleButton } from "./components/ToggleButton";
import type {SelectedPoi} from "./interfaces/poi";
import {POI_STATUS} from "./const/status";
import { LABEL, SITE_HEADING, SITE_SUBTITLE } from "./const/text";
import { AMENITIES, COMMUTE_MODE } from "./const/map";
import {Amenities} from "./interfaces/amenties";

export default function App() {
  const [selectedPoi, setSelectedPoi] = useState<SelectedPoi | null>(null);
  const latestPoiRequestId = useRef(0);

  const [isochroneMode, setIsochroneMode] = useState<IsochroneMode>("walk");
  const [isochroneRangeMinutes, setIsochroneRangeMinutes] = useState("15");
  const [isochrone, setIsochrone] = useState<GeoJSONFeatureCollection | null>(null);
  const [isochroneLoading, setIsochroneLoading] = useState(false);
  const latestIsochroneRequestId = useRef(0);


  const [amenities, setAmenities] = useState<Amenities | null>(null);
  const latestAmenitiesRequestId = useRef(0);

  async function fetchIsochroneFor(
    latitude: number,
    longitude: number,
    isochroneMode: IsochroneMode,
  ) {
    // Guard against out-of-order responses the same way handleMapClick
    // does — relevant here too since isochrone lookups can be slow
    // (Geoapify sometimes computes them asynchronously and this polls for
    // the result), so an earlier click's isochrone could otherwise finish
    // after a later one and overwrite it on screen.
    const requestId = ++latestIsochroneRequestId.current;

    setIsochroneLoading(true);
    setIsochrone(null); // clear the previous shape immediately, not just on success
    setAmenities(null);

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
    } finally {
      if (latestIsochroneRequestId.current === requestId) setIsochroneLoading(false);
    }
  }

  async function fetchAmenitiesForIsochrone(amenity: string, isochrone?: GeoJSONFeatureCollection) {
    const requestId = ++latestAmenitiesRequestId.current;

    try {
      if(!isochrone) {
        if(amenities) {
          setAmenities(null);
        }
        return;
      }
      const result = await api.getAmenities(isochrone, amenity);
      if (latestAmenitiesRequestId.current !== requestId) return;

      setAmenities((prev) => {
        const next = { ...prev };
        // If the user toggled it off, we could remove it,
        // but usually, we want to keep existing ones and add/update the current one.
        // To strictly follow the ToggleButton state, we check the result.
        // If result is empty or we want to remove it, we'd handle it here.
        // For now, we merge the results.
        next[amenity] = result;
        return next;
      });
    } catch (err) {
      if (latestAmenitiesRequestId.current !== requestId) return;
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
    void fetchIsochroneFor(latitude, longitude, isochroneMode);

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
      <div className="grid-container" style={{ margin: 0 }}>
        <calcite-tile
          className="panel-title"
          heading={SITE_HEADING}
          description={SITE_SUBTITLE}
        ></calcite-tile>

        {!selectedPoi && (
          <calcite-tile
            className="panel-info"
            heading={LABEL.section.how_to_use_title}
            description={LABEL.section.how_to_use_description}
          ></calcite-tile>
        )}

        {selectedPoi && (
          <calcite-tile
            className="panel-info"
            heading={selectedPoi?.name ?? LABEL.section.selected_POI_label_placeholder}
            description={selectedPoi?.address ?? ""}
          ></calcite-tile>
        )}

        <div
          className="panel-commute"
        >
          <calcite-label style={{ maxWidth: 160 }}>
            {LABEL.input.mode_of_commute}
            <calcite-select
              value={isochroneMode}
              label={""}
              oncalciteSelectChange={(e) => {
                return setIsochroneMode(
                  (e.target as unknown as HTMLSelectElement).value as IsochroneMode,
                );
              }}
            >
              <calcite-option value={COMMUTE_MODE.walk}>Walk</calcite-option>
              <calcite-option value={COMMUTE_MODE.bicycle}>Bicycle</calcite-option>
              <calcite-option value={COMMUTE_MODE.drive}>Drive</calcite-option>
              <calcite-option value={COMMUTE_MODE.transit}>Public transit</calcite-option>
            </calcite-select>
          </calcite-label>
          <calcite-label style={{ maxWidth: 120 }}>
            {LABEL.input.range_of_commute}
            <calcite-input
              type="number"
              value={isochroneRangeMinutes}
              oncalciteInputInput={(e) =>
                setIsochroneRangeMinutes((e.target as unknown as HTMLInputElement).value)
              }
            />
          </calcite-label>
          {selectedPoi && (
            <calcite-button
              appearance="outline"
              loading={isochroneLoading}
              onClick={() =>
                fetchIsochroneFor(selectedPoi.latitude, selectedPoi.longitude, isochroneMode)
              }
            >
              {LABEL.button.update_isochron}
            </calcite-button>
          )}
        </div>

        <div
          className="panel-amenities"
        >
          {isochrone && (
            <ToggleButton
              label={LABEL.button.shops}
              selected={!!amenities?.shops}
              onToggle={(isSelected) => {
                if (isSelected) {
                  fetchAmenitiesForIsochrone(AMENITIES.shops, isochrone);
                } else {
                  setAmenities((prev) => {
                    if (!prev) return null;
                    const next = { ...prev };
                    delete next[AMENITIES.shops];
                    return Object.keys(next).length > 0 ? next : null;
                  });
                }
              }}
            />
          )}

          {isochrone && (
            <ToggleButton
              label={LABEL.button.doctors}
              selected={!!amenities?.doctors}
              onToggle={(isSelected) => {
                if (isSelected) {
                  fetchAmenitiesForIsochrone(AMENITIES.doctors, isochrone);
                } else {
                  setAmenities((prev) => {
                    if (!prev) return null;
                    const next = { ...prev };
                    delete next[AMENITIES.doctors];
                    return Object.keys(next).length > 0 ? next : null;
                  });
                }
              }}
            />
          )}

          {isochrone && (
            <ToggleButton
              label={LABEL.button.schools}
              selected={!!amenities?.schools}
              onToggle={(isSelected) => {
                if (isSelected) {
                  fetchAmenitiesForIsochrone(AMENITIES.schools, isochrone);
                } else {
                  setAmenities((prev) => {
                    if (!prev) return null;
                    const next = { ...prev };
                    delete next[AMENITIES.schools];
                    return Object.keys(next).length > 0 ? next : null;
                  });
                }
              }}
            />
          )}

          {isochrone && (
            <ToggleButton
              label={LABEL.button.restaurants}
              selected={!!amenities?.restaurants}
              onToggle={(isSelected) => {
                if (isSelected) {
                  fetchAmenitiesForIsochrone(AMENITIES.restaurants, isochrone);
                } else {
                  setAmenities((prev) => {
                    if (!prev) return null;
                    const next = { ...prev };
                    delete next[AMENITIES.restaurants];
                    return Object.keys(next).length > 0 ? next : null;
                  });
                }
              }}
            />
          )}
        </div>

        <calcite-panel className="panel-map">
          <MapView
            isochrone={isochrone}
            amenities={amenities}
            selectedPoi={selectedPoi}
            onMapClick={handleMapClick}
            onClosePoiPopup={() => {
              setSelectedPoi(null);
              setIsochrone(null);
            }}
          />
        </calcite-panel>
      </div>
    </calcite-shell>
  );
}
