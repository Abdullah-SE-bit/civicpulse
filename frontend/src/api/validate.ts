import type { NewComplaint } from "./client";

// Mirrors the server's length rules for fast feedback only; the server stays the authority.
export function validateComplaint(c: NewComplaint): Record<string, string> {
  const errors: Record<string, string> = {};
  const text = c.text.trim().length;
  const loc = c.location.trim().length;
  if (text < 10 || text > 2000) errors.text = "Complaint must be 10–2000 characters.";
  if (loc < 3 || loc > 200) errors.location = "Location must be 3–200 characters.";
  return errors;
}
