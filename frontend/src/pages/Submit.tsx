import { useState } from "react";
import { ApiError, createComplaint, type Complaint } from "../api/client";
import { validateComplaint } from "../api/validate";

type FormState = { text: string; location: string; reporter_contact: string };

const EMPTY_FORM: FormState = { text: "", location: "", reporter_contact: "" };

export function Submit() {
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [serverError, setServerError] = useState("");
  const [result, setResult] = useState<Complaint | null>(null);

  const set = (key: keyof FormState) => (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    setForm((current) => ({ ...current, [key]: event.target.value }));
    if (errors[key]) setErrors((current) => ({ ...current, [key]: "" }));
  };

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setServerError("");
    setResult(null);

    const nextErrors = validateComplaint(form);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setLoading(true);
    try {
      setResult(await createComplaint({
        ...form,
        reporter_contact: form.reporter_contact.trim() || undefined,
      }));
      setForm(EMPTY_FORM);
    } catch (error) {
      setServerError(
        error instanceof ApiError && error.status === 429
          ? `Too many submissions. Retry after ${error.retryAfter ?? "a moment"} seconds.`
          : (error as Error).message,
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="report-layout">
      <div className="report-intro">
        <span className="section-kicker">New service request</span>
        <h1>Tell us what needs attention.</h1>
        <p>
          Share a clear description and location. CivicPulse routes the report to the
          appropriate team and gives it an initial priority.
        </p>
        <div className="report-note">
          <span className="note-icon" aria-hidden="true">↗</span>
          <span><strong>A few useful details go a long way.</strong> Include landmarks, timings, or anything that helps a team find the issue.</span>
        </div>
      </div>

      <div className="form-panel">
        <div className="panel-heading">
          <div>
            <h2>Report a problem</h2>
            <p>Fields marked with an asterisk are required.</p>
          </div>
          <span className="step-indicator">01 / 01</span>
        </div>

        <form onSubmit={onSubmit} noValidate>
          <div className="field-group">
            <label htmlFor="complaint-text">Complaint <span aria-hidden="true">*</span></label>
            <p id="complaint-help" className="field-help">Describe the issue in 10 to 2,000 characters.</p>
            <textarea
              id="complaint-text"
              value={form.text}
              onChange={set("text")}
              rows={6}
              maxLength={2000}
              placeholder="For example: The streetlight outside the library has been out for two nights."
              aria-label="Complaint"
              aria-invalid={Boolean(errors.text)}
              aria-describedby="complaint-help complaint-error"
            />
            <div className="field-footer">
              {errors.text ? <p id="complaint-error" role="alert" className="err">{errors.text}</p> : <span />}
              <span className="character-count">{form.text.length}/2000</span>
            </div>
          </div>

          <div className="field-group">
            <label htmlFor="complaint-location">Location <span aria-hidden="true">*</span></label>
            <p id="location-help" className="field-help">A street, neighborhood, landmark, or address.</p>
            <input
              id="complaint-location"
              value={form.location}
              onChange={set("location")}
              maxLength={200}
              placeholder="e.g. Main Street, beside Central Library"
              aria-label="Location"
              aria-invalid={Boolean(errors.location)}
              aria-describedby="location-help location-error"
            />
            {errors.location && <p id="location-error" role="alert" className="err">{errors.location}</p>}
          </div>

          <div className="field-group">
            <label htmlFor="reporter-contact">Contact <em>(optional)</em></label>
            <p id="contact-help" className="field-help">Leave an email or phone number only if you want a follow-up.</p>
            <input
              id="reporter-contact"
              value={form.reporter_contact}
              onChange={set("reporter_contact")}
              placeholder="you@example.com"
              aria-describedby="contact-help"
            />
          </div>

          <button className="primary-button" disabled={loading} aria-label={loading ? "Submitting report" : "Submit"}>
            {loading ? <><span className="spinner" aria-hidden="true" /> Triaging your complaint...</> : <>Submit report <span aria-hidden="true">→</span></>}
          </button>
        </form>

        {serverError && <p role="alert" className="err server-error">{serverError}</p>}
        {result && (
          <div className="result-card" aria-live="polite">
            <div className="result-icon" aria-hidden="true">✓</div>
            <div>
              <p className="section-kicker">Report received</p>
              <h3>It is now in the queue.</h3>
              <p className="result-meta"><strong>{result.category}</strong><span>•</span><strong>{result.priority} priority</strong></p>
              <p className="result-summary">{result.ai_summary ?? "Your report has been recorded and will be reviewed by the relevant team."}</p>
              <p className="result-footer">Triaged by <code>{result.triaged_by}</code></p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
