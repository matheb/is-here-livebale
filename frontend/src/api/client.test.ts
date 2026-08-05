import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "./client";

describe("api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches sample features from the spatial endpoint", async () => {
    const mockResponse = { type: "FeatureCollection", features: [] };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await api.getSampleFeatures();

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/spatial/sample"),
      expect.any(Object),
    );
    expect(result).toEqual(mockResponse);
  });

  it("throws when the backend responds with an error status", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({}) }),
    );

    await expect(api.getSampleFeatures()).rejects.toThrow(/status 500/);
  });

  it("posts POI requests with just lat/lon, no distance", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ type: "Feature", geometry: {}, properties: {} }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await api.getPoi(47.07, 15.44);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/spatial/poi");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ latitude: 47.07, longitude: 15.44 });
  });

  it("posts buffer requests with the expected body", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ type: "Feature", geometry: {}, properties: {} }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await api.bufferPoint(47.07, 15.44, 500);

    const [, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({
      latitude: 47.07,
      longitude: 15.44,
      distance_meters: 500,
    });
  });

  it("posts isochrone requests with mode and range_minutes", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ type: "FeatureCollection", features: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await api.getIsochrone(47.07, 15.44, "transit", 20);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/spatial/isochrone");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({
      latitude: 47.07,
      longitude: 15.44,
      mode: "transit",
      range_minutes: 20,
    });
  });
});
