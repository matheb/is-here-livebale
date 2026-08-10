import { GeoJSONFeatureCollection } from "../api/client";

export interface Amenities {
  shops?: GeoJSONFeatureCollection;
  restaurants?: GeoJSONFeatureCollection;
  doctors?: GeoJSONFeatureCollection;
  schools?: GeoJSONFeatureCollection;
}