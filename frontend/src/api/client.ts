const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

export interface GeoJSONFeatureCollection {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    geometry: GeoJSON.Geometry;
    properties: Record<string, unknown>;
  }>;
}

export interface GeocodeResult {
  display_name: string;
  latitude: number;
  longitude: number;
}

export type IsochroneMode = "drive" | "walk" | "bicycle" | "transit";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    throw new Error(`Request to ${path} failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  getSampleFeatures: () => request<GeoJSONFeatureCollection>("/spatial/sample"),

  getPoi: (latitude: number, longitude: number) =>
    request<{ type: string; geometry: GeoJSON.Geometry; properties: Record<string, unknown> }>(
      "/spatial/poi",
      {
        method: "POST",
        body: JSON.stringify({ latitude, longitude }),
      },
    ),

  bufferPoint: (latitude: number, longitude: number, distanceMeters: number) =>
    request<{ type: string; geometry: GeoJSON.Geometry; properties: Record<string, unknown> }>(
      "/spatial/buffer",
      {
        method: "POST",
        body: JSON.stringify({
          latitude,
          longitude,
          distance_meters: distanceMeters,
        }),
      },
    ),

  geocode: (query: string) =>
    request<GeocodeResult[]>(`/external/geocode?q=${encodeURIComponent(query)}`),

  getIsochrone: (latitude: number, longitude: number, mode: IsochroneMode, rangeMinutes: number) =>
    request<GeoJSONFeatureCollection>("/spatial/isochrone", {
      method: "POST",
      body: JSON.stringify({
        latitude,
        longitude,
        mode,
        range_minutes: rangeMinutes,
      }),
    }),
};

