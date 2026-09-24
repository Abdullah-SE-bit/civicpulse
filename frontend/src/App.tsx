import { useState } from "react";
import { Dashboard } from "./pages/Dashboard";
import { Stats } from "./pages/Stats";
import { Submit } from "./pages/Submit";
import { ErrorBoundary } from "./components/ErrorBoundary";

const VIEWS = { Submit, Dashboard, Stats } as const;

export function App() {
  const [view, setView] = useState<keyof typeof VIEWS>("Submit");
  const View = VIEWS[view];
  return (
    <main>
      <h1>CivicPulse</h1>
      <nav>
        {(Object.keys(VIEWS) as (keyof typeof VIEWS)[]).map((v) => (
          <button key={v} aria-current={v === view} onClick={() => setView(v)}>{v}</button>
        ))}
      </nav>
      <ErrorBoundary key={view}><View /></ErrorBoundary>
    </main>
  );
}
