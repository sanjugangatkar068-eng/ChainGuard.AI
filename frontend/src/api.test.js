import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "./api";

describe("api client", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("POSTs analyze requests as JSON", async () => {
    fetch.mockResolvedValue({ ok: true, json: async () => ({ ok: 1 }) });

    const result = await api.analyze({ disruption_id: 7, suppliers: [] });

    expect(result).toEqual({ ok: 1 });
    const [url, options] = fetch.mock.calls[0];
    expect(url).toContain("/api/analyze");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({ disruption_id: 7, suppliers: [] });
  });

  it("GETs list endpoints with the limit query", async () => {
    fetch.mockResolvedValue({ ok: true, json: async () => ({ items: [] }) });

    await api.alerts(5);

    expect(fetch.mock.calls[0][0]).toContain("/api/alerts?limit=5");
  });

  it("surfaces the server's detail message on failure", async () => {
    fetch.mockResolvedValue({
      ok: false,
      statusText: "Bad Request",
      json: async () => ({ detail: "Approval already decided" }),
    });

    await expect(api.decide(1, { decision: "approve" })).rejects.toThrow(
      "Approval already decided"
    );
  });
});
