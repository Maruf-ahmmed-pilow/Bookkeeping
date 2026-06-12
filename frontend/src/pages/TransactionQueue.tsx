import { useEffect, useState } from "react";
import { api, money, type Account, type Transaction } from "../api";

const CONF = (c: number | null) => (c == null ? "" : `${Math.round(c * 100)}%`);

export function TransactionQueue() {
  const [txns, setTxns] = useState<Transaction[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [overrides, setOverrides] = useState<Record<string, string>>({});

  const accountById = (id: string | null) => accounts.find((a) => a.id === id);

  const load = async () => {
    try {
      const [t, a] = await Promise.all([api.transactions(), api.accounts()]);
      setTxns(t);
      setAccounts(a);
    } catch (e) {
      setError(String((e as Error).message));
    }
  };

  useEffect(() => {
    load();
  }, []);

  const run = async (key: string, fn: () => Promise<unknown>) => {
    setBusy(key);
    setError("");
    try {
      await fn();
      await load();
    } catch (e) {
      setError(String((e as Error).message));
    } finally {
      setBusy(null);
    }
  };

  const nonCash = accounts.filter((a) => !a.is_cash && a.is_active);

  return (
    <div>
      <div className="toolbar">
        <h2>Transaction Queue</h2>
        <span className="spacer" />
        <button
          className="action primary"
          disabled={busy !== null}
          onClick={() => run("all", () => api.classifyAll())}
        >
          {busy === "all" ? "Classifying…" : "Classify all new"}
        </button>
        <button className="action" disabled={busy !== null} onClick={load}>
          Refresh
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Description</th>
            <th className="num">Amount</th>
            <th>Suggested account</th>
            <th>Confidence</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {txns.map((t) => {
            const suggested = accountById(t.suggested_account_id);
            const approvable = t.status === "classified" || t.status === "needs_review";
            const chosen = overrides[t.id] ?? t.suggested_account_id ?? "";
            return (
              <tr key={t.id}>
                <td>{t.txn_date}</td>
                <td>
                  {t.description}
                  {t.ai_reasoning && <div className="reasoning">{t.ai_reasoning}</div>}
                </td>
                <td className="num">
                  {t.direction === "outflow" ? "-" : "+"}
                  {money(t.amount)}
                </td>
                <td>
                  {approvable ? (
                    <select
                      value={chosen}
                      onChange={(e) => setOverrides((o) => ({ ...o, [t.id]: e.target.value }))}
                    >
                      <option value="">— choose —</option>
                      {nonCash.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.code} · {a.name}
                        </option>
                      ))}
                    </select>
                  ) : suggested ? (
                    `${suggested.code} · ${suggested.name}`
                  ) : (
                    <span className="muted">—</span>
                  )}
                </td>
                <td>
                  <span
                    className={`conf ${
                      t.confidence == null ? "" : t.confidence >= 0.9 ? "high" : "low"
                    }`}
                  >
                    {CONF(t.confidence)}
                  </span>
                </td>
                <td>
                  <span className={`badge ${t.status}`}>{t.status.replace("_", " ")}</span>
                </td>
                <td style={{ whiteSpace: "nowrap" }}>
                  {t.status === "new" && (
                    <button
                      className="action"
                      disabled={busy !== null}
                      onClick={() => run(t.id, () => api.classify(t.id))}
                    >
                      Classify
                    </button>
                  )}
                  {approvable && (
                    <>
                      <button
                        className="action primary"
                        disabled={busy !== null || !chosen}
                        onClick={() =>
                          run(t.id, () =>
                            api.approve(t.id, {
                              account_id: chosen,
                              reason: "Reviewed in queue",
                            }),
                          )
                        }
                      >
                        Approve & post
                      </button>
                      <button
                        className="action danger"
                        disabled={busy !== null}
                        onClick={() =>
                          run(t.id, () => api.reject(t.id, { reason: "Rejected in queue" }))
                        }
                      >
                        Reject
                      </button>
                    </>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {txns.length === 0 && <p className="muted">No transactions yet. Run the seed script.</p>}
    </div>
  );
}
