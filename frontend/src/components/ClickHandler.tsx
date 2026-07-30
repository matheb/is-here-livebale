import {useMapEvents} from "react-leaflet";

/** Reports map clicks up to the parent so it can fetch a POI at that point. */
export default function ClickHandler({ onMapClick }: { onMapClick: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(event) {
      onMapClick(event.latlng.lat, event.latlng.lng);
    },
  });
  return null;
}
