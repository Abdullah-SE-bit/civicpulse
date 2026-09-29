import { useEffect, useState } from "react";
import { getStats, type Stats as StatsData } from "../api/client";

function Counts({ title, counts }: { title: string; counts: Record<string, number> }) {
  return (
    <article className="stat-card">
      <h3>{title}</h3>
      <dl>
        {Object.entries(counts).map(([key, value]) => (
          <div key={key}><dt>{key}</dt><dd>{value}</dd></div>
        ))}
      </dl>
    </article>
  );
}

export function Stats() {
  const [state, setState] = useState<{ stats: StatsData; cache: string | null } | null>(null);
  const [error, setError] = useState("");

  const load = () => getStats()
    .then((response) => { setState(response); setError(""); })
    .catch((requestError) => setError(requestError.message));

  useEffect(() => { load(); }, []);

  return (
    <section className="data-page">
      <div className="data-page-heading">
        <div>
          <p className="section-kicker">Service overview</p>
          <h2>Insights</h2>
          <p>A compact view of incoming reports and triage activity.</p>
        </div>
        <button className="quiet-button" type="button" onClick={load}>Refresh data</button>
      </div>

      {error && <p role="alert" className="err server-error">{error}</p>}
      {!state && !error && <p className="loading-copy">Loading service activity...</p>}
      {state && (
        <>
          <div className="overview-card">
            <span>Total: reports</span>
            <strong>{state.stats.total}</strong>
            <p>Cache status: <code>{state.cache ?? "unknown"}</code></p>
          </div>
          <div className="stats-grid">
            <Counts title="By category" counts={state.stats.by_category} />
            <Counts title="By priority" counts={state.stats.by_priority} />
          </div>
        </>
      )}
    </section>
  );
}
