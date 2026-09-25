import { describe, expect, it } from "vitest";
import { validateComplaint } from "../src/api/validate";

describe("validateComplaint", () => {
  it("accepts a valid complaint", () => {
    expect(validateComplaint({ text: "Burst water main on Street 12", location: "Street 12" })).toEqual({});
  });
  it("rejects short text and location", () => {
    expect(Object.keys(validateComplaint({ text: "short", location: "ab" })).sort()).toEqual(["location", "text"]);
  });
  it("rejects text over 2000 chars", () => {
    expect(validateComplaint({ text: "x".repeat(2001), location: "Street 12" }).text).toBeDefined();
  });
});
