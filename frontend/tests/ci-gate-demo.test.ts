import { expect, it } from "vitest";

// DELIBERATELY FAILING (demo of the CI gate, issue about rubric I). Removed in the "fix" commit. Never merge this.
it("ci gate demo: this test fails on purpose", () => {
  expect(1 + 1).toBe(3);
});
