import L, { CircleMarker } from "leaflet";

export function createDotMarker(latlng: L.LatLng, color: string): CircleMarker {
  return L.circleMarker(latlng, {
    radius: 6,
    color: color,
    fillColor: color,
    fillOpacity: 0.8,
    weight: 1,
  });
}
