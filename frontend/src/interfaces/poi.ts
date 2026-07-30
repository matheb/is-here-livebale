export type PoiStatus = "loading" | "ready" | "error";

export interface SelectedPoi {
  latitude: number;
  longitude: number;
  status: PoiStatus;
  name: string | null;
  address: string | null;
}

