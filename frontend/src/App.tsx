// From now on, from now on...

import { useRef, useState } from "react";

import { api, type GeoJSONFeatureCollection, type IsochroneMode } from "./api/client";
import MapView from "./components/MapView";
import { ToggleButton } from "./components/ToggleButton";
import type { SelectedPoi } from "./interfaces/poi";
import { POI_STATUS } from "./const/status";
import { LABEL, SITE_HEADING, SITE_SUBTITLE } from "./const/text";
import { AMENITIES, COMMUTE_MODE } from "./const/map";
import { type ActiveAmenities, Amenities, type AmenityCache } from "./interfaces/amenties";

export default function App() {
  const [selectedPoi, setSelectedPoi] = useState<SelectedPoi | null>(null);
  const latestPoiRequestId = useRef(0);

  const [isochroneMode, setIsochroneMode] = useState<IsochroneMode>("walk");
  const [isochroneRangeMinutes, setIsochroneRangeMinutes] = useState("15");
  const [isochrone, setIsochrone] = useState<GeoJSONFeatureCollection | null>(null);
  const [isochroneLoading, setIsochroneLoading] = useState(false);
  const latestIsochroneRequestId = useRef(0);

  const [amenityCache, setAmenityCache] = useState<AmenityCache>({});
  const [activeAmenities, setActiveAmenities] = useState<ActiveAmenities>({});
  const [amenitiesLoading, setAmenitiesLoading] = useState<ActiveAmenities>({});
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
      if (!isochrone || !selectedPoi) {
        return;
      }

      const cacheKey = `${selectedPoi.latitude},${selectedPoi.longitude},${isochroneMode},${isochroneRangeMinutes}`;

      if (amenityCache[cacheKey]?.[amenity]) {
        setActiveAmenities((prev) => ({ ...prev, [amenity]: true }));
        return;
      }

      setAmenitiesLoading((prev) => ({ ...prev, [amenity]: true }));

      const result = await api.getAmenities(isochrone, amenity);
      if (latestAmenitiesRequestId.current !== requestId) return;

      // Only set as active if we actually received data (features array is not empty)
      if (result && result.features && result.features.length > 0) {
        setAmenityCache((prev) => {
          const next = { ...prev };
          if (!next[cacheKey]) {
            next[cacheKey] = {};
          }
          next[cacheKey][amenity] = result;
          return next;
        });

        setActiveAmenities((prev) => ({ ...prev, [amenity]: true }));
      } else {
        // No data found for this amenity type in this area
        setActiveAmenities((prev) => ({ ...prev, [amenity]: false }));
      }
    } catch (err) {
      if (latestAmenitiesRequestId.current !== requestId) return;
      // Ensure that if fetch fails (timeout, network error, etc.), it's not marked as active
      setActiveAmenities((prev) => ({ ...prev, [amenity]: false }));
    } finally {
      if (latestAmenitiesRequestId.current === requestId) {
        setAmenitiesLoading((prev) => ({ ...prev, [amenity]: false }));
      }
    }
  }

  async function handleMapClick(latitude: number, longitude: number) {
    // Guard against out-of-order responses: if the user clicks a second
    // point before the first lookup resolves, ignore the stale response.
    const requestId = ++latestPoiRequestId.current;

    // Show a marker at the clicked point immediately, in a loading state,
    // while the POI lookup (with reverse-geocoded name/address) resolves.
    setSelectedPoi({ latitude, longitude, status: POI_STATUS.loading, name: null, address: null });
    setActiveAmenities({});
    setAmenitiesLoading({});

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

  function getActiveAmenitiesForMap(): Amenities | null {
    if (!selectedPoi) return null;

    const cacheKey = `${selectedPoi.latitude},${selectedPoi.longitude},${isochroneMode},${isochroneRangeMinutes}`;

    return Object.entries(activeAmenities)
      .filter(([_, active]) => active)
      .reduce((acc, [type, _]) => {
        const data = amenityCache[cacheKey]?.[type];
        if (data) acc[type] = data;
        return acc;
      }, {} as Amenities);
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
          <div
            className="panel-info-wrapper panel-info-default"
            style={{ gridArea: "panel-info", margin: "1rem" }}
          >
            <calcite-icon icon="information" style={{ color: "#005e95", fontSize: "large" }} />
            <calcite-tile
              className="panel-info-tile"
              heading={LABEL.section.how_to_use_title}
              description={LABEL.section.how_to_use_description}
            ></calcite-tile>
          </div>
        )}

        {selectedPoi && (
          <div
            className="panel-info-wrapper panel-info-selected"
            style={{ gridArea: "panel-info", margin: "1rem" }}
          >
            <calcite-icon icon="home" style={{ color: "darkgreen" }} />
            <calcite-tile
              className="panel-info-tile"
              heading={selectedPoi?.name ?? LABEL.section.selected_POI_label_placeholder}
              description={selectedPoi?.address ?? ""}
            ></calcite-tile>
          </div>
        )}

        <div className="panel-commute">
          <calcite-label className="panel-commute-label">
            {LABEL.input.mode_of_commute}
            <calcite-select
              value={isochroneMode}
              label={""}
              oncalciteSelectChange={(e) => {
                const newValue = (e.target as unknown as HTMLSelectElement).value as IsochroneMode;
                setIsochroneMode(newValue);
                setActiveAmenities({});
              }}
            >
              <calcite-option value={COMMUTE_MODE.walk}>Walk</calcite-option>
              <calcite-option value={COMMUTE_MODE.bicycle}>Bicycle</calcite-option>
              <calcite-option value={COMMUTE_MODE.drive}>Drive</calcite-option>
              <calcite-option value={COMMUTE_MODE.transit}>Public transit</calcite-option>
            </calcite-select>
          </calcite-label>
          <calcite-label className="panel-commute-label-small">
            {LABEL.input.range_of_commute}
            <calcite-input
              type="number"
              value={isochroneRangeMinutes}
              oncalciteInputInput={(e) => {
                const newValue = (e.target as unknown as HTMLInputElement).value;
                setIsochroneRangeMinutes(newValue);
                setActiveAmenities({});
              }}
            />
          </calcite-label>
          {selectedPoi && (
            <calcite-label className="panel-commute-label">
              <span className="label-hidden-text">{LABEL.button.update_isochron}</span>
              <calcite-button
                className="panel-commute-button"
                appearance="outline"
                loading={isochroneLoading}
                onClick={() =>
                  fetchIsochroneFor(selectedPoi.latitude, selectedPoi.longitude, isochroneMode)
                }
              >
                {LABEL.button.update_isochron}
              </calcite-button>
            </calcite-label>
          )}
        </div>

        <div className="panel-amenities">
          {isochrone && (
            <calcite-label className="panel-amenities-label">
              <span className="label-hidden-text">{LABEL.button.shops}</span>
              <ToggleButton
                label={LABEL.button.shops}
                selected={activeAmenities[AMENITIES.shops] ?? false}
                loading={amenitiesLoading[AMENITIES.shops]}
                onToggle={(isSelected) => {
                  if (isSelected) {
                    fetchAmenitiesForIsochrone(AMENITIES.shops, isochrone);
                  } else {
                    setActiveAmenities((prev) => ({ ...prev, [AMENITIES.shops]: false }));
                  }
                }}
              />
            </calcite-label>
          )}

          {isochrone && (
            <calcite-label className="panel-amenities-label">
              <span className="label-hidden-text">{LABEL.button.doctors}</span>
              <ToggleButton
                label={LABEL.button.doctors}
                selected={activeAmenities[AMENITIES.doctors] ?? false}
                loading={amenitiesLoading[AMENITIES.doctors]}
                onToggle={(isSelected) => {
                  if (isSelected) {
                    fetchAmenitiesForIsochrone(AMENITIES.doctors, isochrone);
                  } else {
                    setActiveAmenities((prev) => ({ ...prev, [AMENITIES.doctors]: false }));
                  }
                }}
              />
            </calcite-label>
          )}

          {isochrone && (
            <calcite-label className="panel-amenities-label">
              <span className="label-hidden-text">{LABEL.button.schools}</span>
              <ToggleButton
                label={LABEL.button.schools}
                selected={activeAmenities[AMENITIES.schools] ?? false}
                loading={amenitiesLoading[AMENITIES.schools]}
                onToggle={(isSelected) => {
                  if (isSelected) {
                    fetchAmenitiesForIsochrone(AMENITIES.schools, isochrone);
                  } else {
                    setActiveAmenities((prev) => ({ ...prev, [AMENITIES.schools]: false }));
                  }
                }}
              />
            </calcite-label>
          )}

          {isochrone && (
            <calcite-label className="panel-amenities-label">
              <span className="label-hidden-text">{LABEL.button.restaurants}</span>
              <ToggleButton
                label={LABEL.button.restaurants}
                selected={activeAmenities[AMENITIES.restaurants] ?? false}
                loading={amenitiesLoading[AMENITIES.restaurants]}
                onToggle={(isSelected) => {
                  if (isSelected) {
                    fetchAmenitiesForIsochrone(AMENITIES.restaurants, isochrone);
                  } else {
                    setActiveAmenities((prev) => ({ ...prev, [AMENITIES.restaurants]: false }));
                  }
                }}
              />
            </calcite-label>
          )}
        </div>InputInput={(e) => {
                const newValue = (e.target as unknown as HTMLInputElement).value;
                setIsochroneRangeMinutes(newValue);
                setActiveAmenities({});
              }}
            />
          </calcite-label>
          {selectedPoi && (
            <calcite-label style={{ maxWidth: 160, fontWeight: "bold" }}>
              <span style={{ display: "block", visibility: "hidden" }}>{LABEL.button.update_isochron}</span>
              <calcite-button
                appearance="outline"
                loading={isochroneLoading}
                style={{ height: "32px", width: "auto", minWidth: "120px" }}
                onClick={() =>
                  fetchIsochroneFor(selectedPoi.latitude, selectedPoi.longitude, isochroneMode)
                }
              >
                {LABEL.button.update_isochron}
              </calcite-button>
            </calcite-label>
          )}
        </div>

        <div className="panel-amenities" style={{ display: "flex", alignItems: "flex-end", gap: "0.75rem", height: "auto" }}>
          {isochrone && (
            <calcite-label style={{ fontWeight: "bold" }}>
              <span style={{ display: "block", visibility: "hidden" }}>{LABEL.button.shops}</span>
              <ToggleButton
                label={LABEL.button.shops}
                selected={activeAmenities[AMENITIES.shops] ?? false}
                loading={amenitiesLoading[AMENITIES.shops]}
                onToggle={(isSelected) => {
                  if (isSelected) {
                    fetchAmenitiesForIsochrone(AMENITIES.shops, isochrone);
                  } else {
                    setActiveAmenities((prev) => ({ ...prev, [AMENITIES.shops]: false }));
                  }
                }}
              />
            </calcite-label>
          )}

          {isochrone && (
            <calcite-label style={{ fontWeight: "bold" }}>
              <span style={{ display: "block", visibility: "hidden" }}>{LABEL.button.doctors}</span>
              <ToggleButton
                label={LABEL.button.doctors}
                selected={activeAmenities[AMENITIES.doctors] ?? false}
                loading={amenitiesLoading[AMENITIES.doctors]}
                onToggle={(isSelected) => {
                  if (isSelected) {
                    fetchAmenitiesForIsochrone(AMENITIES.doctors, isochrone);
                  } else {
                    setActiveAmenities((prev) => ({ ...prev, [AMENITIES.doctors]: false }));
                  }
                }}
              />
            </calcite-label>
          )}

          {isochrone && (
            <calcite-label style={{ fontWeight: "bold" }}>
              <span style={{ display: "block", visibility: "hidden" }}>{LABEL.button.schools}</span>
              <ToggleButton
                label={LABEL.button.schools}
                selected={activeAmenities[AMENITIES.schools] ?? false}
                loading={amenitiesLoading[AMENITIES.schools]}
                onToggle={(isSelected) => {
                  if (isSelected) {
                    fetchAmenitiesForIsochrone(AMENITIES.schools, isochrone);
                  } else {
                    setActiveAmenities((prev) => ({ ...prev, [AMENITIES.schools]: false }));
                  }
                }}
              />
            </calcite-label>
          )}

          {isochrone && (
            <calcite-label style={{ fontWeight: "bold" }}>
              <span style={{ display: "block", visibility: "hidden" }}>{LABEL.button.restaurants}</span>
              <ToggleButton
                label={LABEL.button.restaurants}
                selected={activeAmenities[AMENITIES.restaurants] ?? false}
                loading={amenitiesLoading[AMENITIES.restaurants]}
                onToggle={(isSelected) => {
                  if (isSelected) {
                    fetchAmenitiesForIsochrone(AMENITIES.restaurants, isochrone);
                  } else {
                    setActiveAmenities((prev) => ({ ...prev, [AMENITIES.restaurants]: false }));
                  }
                }}
              />
            </calcite-label>
          )}
        </div>

        <calcite-panel className="panel-map">
          <MapView
            isochrone={isochrone}
            amenities={getActiveAmenitiesForMap()}
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
