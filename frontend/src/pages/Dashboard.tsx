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
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let stale = false;
    listComplaints({ page, page_size: PAGE_SIZE, ...filters })
      .then((response) => {
        if (stale) return;
        setData(response);
        setError("");
      })
      .catch((requestError: Error) => {
        if (!stale) setError(requestError.message);
      });
    return () => { stale = true; };
  }, [page, filters, reload]);

  async function advance(id: string, status: Status) {
    try {
      await setStatus(id, status);
      setReload((value) => value + 1);
    } catch (requestError) {
      setError((requestError as Error).message);
    }
  }

  const filter = (key: keyof typeof filters, options: readonly string[]) => (
    <label className="filter-control" key={key}>
      <span>{key}</span>
      <select
        aria-label={key}
        value={filters[key]}
        onChange={(event) => {
          setPage(1);
          setFilters({ ...filters, [key]: event.target.value });
        }}
      >
        <option value="">All {key}</option>
        {options.map((option) => <option key={option}>{option}</option>)}
      </select>
    </label>
  );

  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <section className="data-page">
      <div className="data-page-heading">
        <div>
          <p className="section-kicker">Operations</p>
          <h2>Cases</h2>
          <p>Review incoming reports and update their progress.</p>
        </div>
        <span className="case-total">{data?.total ?? 0} reports</span>
      </div>

      <div className="filters" aria-label="Case filters">
        {filter("category", CATEGORIES)}
        {filter("priority", PRIORITIES)}
        {filter("status", STATUSES)}
      </div>

      {error && <p role="alert" className="err server-error">{error}</p>}
      {!data && !error ? <p className="loading-copy">Loading cases...</p> : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Summary</th><th>Location</th><th>Category</th><th>Priority</th><th>Status</th><th>Triaged by</th></tr>
            </thead>
            <tbody>
              {data?.items.map((complaint) => (
                <tr key={complaint.id}>
                  <td title={complaint.text}>{complaint.ai_summary ?? complaint.text.slice(0, 80)}</td>
                  <td>{complaint.location}</td>
                  <td><span className="table-tag">{complaint.category}</span></td>
                  <td><span className={`priority-tag priority-${complaint.priority}`}>{complaint.priority}</span></td>
                  <td>
                    <select aria-label="status" value={complaint.status} onChange={(event) => advance(complaint.id, event.target.value as Status)}>
                      {STATUSES.map((status) => <option key={status}>{status}</option>)}
                    </select>
                  </td>
                  <td><code>{complaint.triaged_by}</code></td>
                </tr>
              ))}
              {data?.items.length === 0 && <tr><td colSpan={6} className="empty-cell">No complaints match these filters.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      <div className="pagination" aria-label="Pagination">
        <button type="button" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
        <span>Page {page} of {pages} ({data?.total ?? 0} total)</span>
        <button type="button" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</button>
      </div>
    </section>
  );
}
