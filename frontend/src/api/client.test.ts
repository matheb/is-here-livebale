import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "./client";

describe("api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
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
    expect(JSON.parse(init.body)).toEqual({ lat: 47.07, long: 15.44 });
  });

});
