const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

export interface GeoJSONFeatureCollection {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    geometry: GeoJSON.Geometry;
    properties: Record<string, unknown>;
  }>;
}


export interface GeoJSONFeature {
  type: "Feature";
  geometry: GeoJSON.Geometry;
  properties: Record<string, unknown>;
}

export interface GeocodeResult {
  display_name: string;
  latitude: number;
  longitude: number;
}

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
  get_poi: (latitude: number, longitude: number) => {
    console.log("lat", latitude);
    console.log("long", longitude);

    return request<{
      type: string;
      geometry: GeoJSON.Geometry;
      properties: Record<string, unknown>;
    }>("/spatial/poi", {
      method: "POST",
      body: JSON.stringify({
        latitude,
        longitude,
      }),
    });
  },

  geocode: (query: string) =>
    request<GeocodeResult[]>(`/external/geocode?q=${encodeURIComponent(query)}`),
};
