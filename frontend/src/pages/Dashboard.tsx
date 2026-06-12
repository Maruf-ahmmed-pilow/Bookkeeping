import { useEffect, useState } from "react";
import { api, money, type DashboardMetrics } from "../api";

export function Dashboard({ onGoToQueue }: { onGoToQueue: () => void }) {
  const [m, setM] = useState<DashboardMetrics | null>(null);
  const [error, setError] = useState("");

  const load = () =>
    api
      .dashboard()
      .then(setM)
      .catch((e) => setError(String(e.message ?? e)));

  useEffect(() => {
    load();
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!m) return <p className="muted">Loading…</p>;

  return (
    <div>
      <div className="cards">
        <div className="card">
          <div className="label">Total Revenue</div>
          <div className="value green">{money(m.total_revenue)}</div>
        </div>
        <div className="card">
          <div className="label">Total Expenses</div>
          <div className="value red">{money(m.total_expenses)}</div>
        </div>
        <div className="card">
          <div className="label">Net Income</div>
          <div className={`value ${m.net_income >= 0 ? "green" : "red"}`}>
            {money(m.net_income)}
          </div>
        </div>
        <div className="card">
          <div className="label">Cash on Hand</div>
          <div className="value">{money(m.cash_on_hand)}</div>
        </div>
        <div className="card">
          <div className="label">Pending Review</div>
          <div className={`value ${m.pending_review ? "amber" : ""}`}>{m.pending_review}</div>
        </div>
        <div className="card">
          <div className="label">Posted Transactions</div>
          <div className="value">{m.posted_transactions}</div>
        </div>
      </div>

      <p style={{ marginTop: 24 }} className="muted">
        Figures are computed from posted general-ledger entries only. Classify and approve
        transactions in the{" "}
        <a onClick={onGoToQueue} style={{ color: "var(--accent)", cursor: "pointer" }}>
          Transaction Queue
        </a>{" "}
        to see them flow into reports.
      </p>
    </div>
  );
}
