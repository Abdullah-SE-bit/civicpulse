// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, getStats, setStatus } from "../src/api/client";
import { Dashboard } from "../src/pages/Dashboard";
import { Stats } from "../src/pages/Stats";
import { Submit } from "../src/pages/Submit";

const complaint = {
  id: "c1", text: "Burst water main on Street 12", location: "Street 12", reporter_contact: null,
  category: "water", priority: "high", status: "open", ai_summary: "Burst main flooding Street 12",
  triaged_by: "rules:fallback", triage_latency_ms: 12, created_at: "2026-09-24T00:00:00Z", updated_at: "2026-09-24T00:00:00Z",
};

function mockFetch(status: number, body: unknown, headers: Record<string, string> = {}) {
  const fn = vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status, headers }));
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("Submit", () => {
  it("shows field errors and does not call the server when input is invalid", async () => {
    const fetchFn = mockFetch(201, complaint);
    render(<Submit />);
    await userEvent.click(screen.getByRole("button", { name: "Submit" }));
    expect(screen.getByText(/Complaint must be 10–2000/)).toBeTruthy();
    expect(screen.getByText(/Location must be 3–200/)).toBeTruthy();
    expect(fetchFn).not.toHaveBeenCalled();
  });

  it("renders category, priority, summary and provider from the server response", async () => {
    mockFetch(201, complaint);
    render(<Submit />);
    await userEvent.type(screen.getByLabelText("Complaint"), "Burst water main on Street 12");
    await userEvent.type(screen.getByLabelText("Location"), "Street 12");
    await userEvent.click(screen.getByRole("button", { name: "Submit" }));
    expect(await screen.findByText("Burst main flooding Street 12", { exact: false })).toBeTruthy();
    expect(screen.getByText("rules:fallback")).toBeTruthy();
    expect(screen.getByText("water")).toBeTruthy();
  });
});

describe("Dashboard", () => {
  it("surfaces the server's 409 message verbatim on an invalid transition", async () => {
    const msg = "Invalid transition: resolved -> open";
    const fetchFn = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [{ ...complaint, status: "resolved" }], total: 1, page: 1, page_size: 20 })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: msg }), { status: 409 }));
    vi.stubGlobal("fetch", fetchFn);
    render(<Dashboard />);
    const select = await screen.findByDisplayValue("resolved");
    await userEvent.selectOptions(select, "open");
    expect((await screen.findByRole("alert")).textContent).toBe(msg);
  });

  it("lists complaints with the total", async () => {
    mockFetch(200, { items: [complaint], total: 1, page: 1, page_size: 20 });
    render(<Dashboard />);
    expect(await screen.findByText("Burst main flooding Street 12")).toBeTruthy();
    expect(screen.getByText(/Page 1 of 1 \(1 total\)/)).toBeTruthy();
  });
});

describe("Stats", () => {
  it("shows aggregates and the X-Cache state", async () => {
    mockFetch(200, { total: 3, by_category: { water: 2, roads: 1 }, by_priority: { high: 3 } }, { "X-Cache": "HIT" });
    render(<Stats />);
    await waitFor(() => expect(screen.getByText("HIT")).toBeTruthy());
    expect(screen.getByText(/Total:/)).toBeTruthy();
  });
});

describe("api client", () => {
  it("turns a FastAPI validation error list into a readable message", async () => {
    mockFetch(400, { detail: [{ loc: ["body", "text"], msg: "String should have at least 10 characters" }] });
    await expect(getStats()).rejects.toThrow("text: String should have at least 10 characters");
  });

  it("keeps Retry-After on a 429", async () => {
    mockFetch(429, { detail: "rate limited" }, { "Retry-After": "30" });
    const err = await setStatus("c1", "open").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.retryAfter).toBe("30");
  });
});
