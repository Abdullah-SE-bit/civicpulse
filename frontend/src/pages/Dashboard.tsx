import { useEffect, useState } from "react";
import {
  CATEGORIES, PRIORITIES, STATUSES, listComplaints, setStatus,
  type ComplaintPage, type Status,
} from "../api/client";

const PAGE_SIZE = 20;

export function Dashboard() {
  const [filters, setFilters] = useState({ category: "", priority: "", status: "" });
  const [page, setPage] = useState(1);
  const [data, setData] = useState<ComplaintPage | null>(null);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0); // bump to refetch after a status change

  useEffect(() => {
    let stale = false; // ignore a slow response that arrives after the filters changed
    listComplaints({ page, page_size: PAGE_SIZE, ...filters })
      .then((d) => {
        if (stale) return;
        setData(d);
        setError("");
      })
      .catch((e: Error) => {
        if (!stale) setError(e.message);
      });
    return () => {
      stale = true;
    };
  }, [page, filters, reload]);

  // The server owns the state machine; on an invalid transition we show its 409 message verbatim.
  async function advance(id: string, status: Status) {
    try {
      await setStatus(id, status);
      setReload((n) => n + 1);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const filter = (k: keyof typeof filters, options: readonly string[]) => (
    <select
      aria-label={k}
      value={filters[k]}
      onChange={(e) => {
        setPage(1);
        setFilters({ ...filters, [k]: e.target.value });
      }}
    >
      <option value="">all {k}</option>
      {options.map((o) => <option key={o}>{o}</option>)}
    </select>
  );

  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <section>
      <h2>Dashboard</h2>
      <div className="filters">
        {filter("category", CATEGORIES)}
        {filter("priority", PRIORITIES)}
        {filter("status", STATUSES)}
      </div>
      {error && <p role="alert" className="err">{error}</p>}
      {!data && !error ? <p>Loading…</p> : (
        <table>
          <thead>
            <tr><th>Summary</th><th>Location</th><th>Category</th><th>Priority</th><th>Status</th><th>Triaged by</th></tr>
          </thead>
          <tbody>
            {data?.items.map((c) => (
              <tr key={c.id}>
                <td title={c.text}>{c.ai_summary ?? c.text.slice(0, 80)}</td>
                <td>{c.location}</td>
                <td>{c.category}</td>
                <td>{c.priority}</td>
                <td>
                  <select aria-label="status" value={c.status} onChange={(e) => advance(c.id, e.target.value as Status)}>
                    {STATUSES.map((s) => <option key={s}>{s}</option>)}
                  </select>
                </td>
                <td><code>{c.triaged_by}</code></td>
              </tr>
            ))}
            {data?.items.length === 0 && <tr><td colSpan={6}>No complaints match.</td></tr>}
          </tbody>
        </table>
      )}
      <p>
        <button disabled={page <= 1} onClick={() => setPage(page - 1)}>Prev</button>{" "}
        Page {page} of {pages} ({data?.total ?? 0} total){" "}
        <button disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</button>
      </p>
    </section>
  );
}
