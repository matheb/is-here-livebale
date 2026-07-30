import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ type: "FeatureCollection", features: [] }),
    }),
  );
});

describe("App", () => {
  it("renders the app heading", () => {
    render(<App />);
    expect(screen.getByText("Spatial App")).toBeInTheDocument();
  });

  it("renders the buffer control button", () => {
    render(<App />);
    expect(screen.getByText("Buffer point around Graz")).toBeInTheDocument();
  });
});
