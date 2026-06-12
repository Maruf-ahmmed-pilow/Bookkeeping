import { useEffect, useState } from "react";
import { api } from "./api";
import { Dashboard } from "./pages/Dashboard";
import { TransactionQueue } from "./pages/TransactionQueue";
import { Reports } from "./pages/Reports";

type Tab = "dashboard" | "queue" | "reports";

export function App() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [engine, setEngine] = useState<string>("");

  useEffect(() => {
    api
      .health()
      .then((h) => setEngine(String(h.ai_engine)))
      .catch(() => setEngine("offline"));
  }, []);

  const engineLabel = engine || "…";
  const engineOnline = engine && engine !== "offline";

  return (
    <>
      <header>
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            ▦
          </span>
          <div>
            <h1>Bookkeeping AI Control Tower</h1>
            <span className="sub">Northwind Trading Co. · USD</span>
          </div>
        </div>
        <span className={`engine ${engineOnline ? "engine--ok" : "engine--off"}`}>
          <span className="engine-dot" aria-hidden="true" />
          AI engine: <strong>{engineLabel}</strong>
        </span>
      </header>
      <nav aria-label="Primary">
        <button className={tab === "dashboard" ? "active" : ""} onClick={() => setTab("dashboard")}>
          Dashboard
        </button>
        <button className={tab === "queue" ? "active" : ""} onClick={() => setTab("queue")}>
          Transaction Queue
        </button>
        <button className={tab === "reports" ? "active" : ""} onClick={() => setTab("reports")}>
          Financial Reports
        </button>
      </nav>
      <main>
        {tab === "dashboard" && <Dashboard onGoToQueue={() => setTab("queue")} />}
        {tab === "queue" && <TransactionQueue />}
        {tab === "reports" && <Reports />}
      </main>
      <footer>
        Core MVP · intake → AI classification → human review → ledger → reports. Figures derive from
        posted double-entry journal lines only.
      </footer>
    </>
  );
}
