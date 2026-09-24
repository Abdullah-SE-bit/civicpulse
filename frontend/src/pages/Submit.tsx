import { useState } from "react";
import { ApiError, createComplaint, type Complaint } from "../api/client";
import { validateComplaint } from "../api/validate";

export function Submit() {
  const [form, setForm] = useState({ text: "", location: "", reporter_contact: "" });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [serverError, setServerError] = useState("");
  const [result, setResult] = useState<Complaint | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setServerError("");
    setResult(null);
    const errs = validateComplaint(form);
    setErrors(errs);
    if (Object.keys(errs).length) return;
    setLoading(true);
    try {
      setResult(await createComplaint({ ...form, reporter_contact: form.reporter_contact.trim() || undefined }));
      setForm({ text: "", location: "", reporter_contact: "" });
    } catch (err) {
      setServerError(
        err instanceof ApiError && err.status === 429
          ? `Too many submissions. Retry after ${err.retryAfter ?? "a moment"} seconds.`
          : (err as Error).message,
      );
    } finally {
      setLoading(false);
    }
  }

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [k]: e.target.value });

  return (
    <section>
      <h2>Report a problem</h2>
      <form onSubmit={onSubmit} noValidate>
        <label>
          Complaint
          <textarea value={form.text} onChange={set("text")} rows={5} maxLength={2000} />
        </label>
        {errors.text && <p role="alert" className="err">{errors.text}</p>}
        <label>
          Location
          <input value={form.location} onChange={set("location")} maxLength={200} />
        </label>
        {errors.location && <p role="alert" className="err">{errors.location}</p>}
        <label>
          Contact (optional)
          <input value={form.reporter_contact} onChange={set("reporter_contact")} />
        </label>
        <button disabled={loading}>{loading ? "Triaging your complaint… this can take a few seconds" : "Submit"}</button>
      </form>
      {serverError && <p role="alert" className="err">{serverError}</p>}
      {result && (
        <div className="card" aria-live="polite">
          <h3>Received</h3>
          <p>Category: <b>{result.category}</b> · Priority: <b>{result.priority}</b></p>
          <p>Summary: {result.ai_summary ?? "—"}</p>
          <p>Triaged by: <code>{result.triaged_by}</code></p>
        </div>
      )}
    </section>
  );
}
