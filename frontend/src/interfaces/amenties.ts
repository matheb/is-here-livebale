import { GeoJSONFeatureCollection } from "../api/client";

export interface Amenities {
  shops?: GeoJSONFeatureCollection;
  restaurants?: GeoJSONFeatureCollection;
  doctors?: GeoJSONFeatureCollection;
  schools?: GeoJSONFeatureCollection;
}

export interface AmenityCache {
  [cacheKey: string]: {
    [amenityType: string]: GeoJSONFeatureCollection;
  };
}

export interface ActiveAmenities {
  [amenityType: string]: boolean;
}
