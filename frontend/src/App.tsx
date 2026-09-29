import { useState } from "react";
import { Dashboard } from "./pages/Dashboard";
import { Stats } from "./pages/Stats";
import { Submit } from "./pages/Submit";
import { ErrorBoundary } from "./components/ErrorBoundary";

const VIEWS = {
  Submit: {
    Component: Submit,
    label: "Report",
    description: "Send a concern to the right team",
  },
  Dashboard: {
    Component: Dashboard,
    label: "Cases",
    description: "Review and manage submitted cases",
  },
  Stats: {
    Component: Stats,
    label: "Insights",
    description: "Understand service activity at a glance",
  },
} as const;

export function App() {
  const [view, setView] = useState<keyof typeof VIEWS>("Submit");
  const { Component: View, description } = VIEWS[view];

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="header-inner">
          <button
            className="brand"
            type="button"
            onClick={() => setView("Submit")}
            aria-label="Go to report form"
          >
            <span className="brand-mark" aria-hidden="true">C</span>
            <span className="brand-copy">
              <strong>CivicPulse</strong>
              <small>Municipal service desk</small>
            </span>
          </button>

          <nav className="primary-nav" aria-label="Primary navigation">
            {(Object.keys(VIEWS) as (keyof typeof VIEWS)[]).map((key) => (
              <button
                key={key}
                type="button"
                aria-current={key === view ? "page" : undefined}
                onClick={() => setView(key)}
              >
                {VIEWS[key].label}
              </button>
            ))}
          </nav>

          <span className="service-status"><i aria-hidden="true" /> Service online</span>
        </div>
      </header>

      <main className="page-wrap">
        <p className="eyebrow">{description}</p>
        <ErrorBoundary key={view}><View /></ErrorBoundary>
      </main>
    </div>
  );
}
