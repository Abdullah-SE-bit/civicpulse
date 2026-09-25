import { useEffect, useState } from "react";
import { getStats, type Stats as StatsData } from "../api/client";

function Counts({ title, counts }: { title: string; counts: Record<string, number> }) {
  return (
    <div className="card">
      <h3>{title}</h3>
      <ul>{Object.entries(counts).map(([k, v]) => <li key={k}>{k}: <b>{v}</b></li>)}</ul>
    </div>
  );
}

export function Stats() {
  const [state, setState] = useState<{ stats: StatsData; cache: string | null } | null>(null);
  const [error, setError] = useState("");

  const load = () => getStats().then((s) => { setState(s); setError(""); }).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  return (
    <section>
      <h2>Stats</h2>
      <button onClick={load}>Refresh</button>
      {error && <p role="alert" className="err">{error}</p>}
      {state && (
        <>
          <p>Total: <b>{state.stats.total}</b> · Cache: <code>{state.cache ?? "unknown"}</code></p>
          <Counts title="By category" counts={state.stats.by_category} />
          <Counts title="By priority" counts={state.stats.by_priority} />
        </>
      )}
    </section>
  );
}
