import { useEffect, useState } from "react";
import { api, money, type BalanceSheet, type ProfitAndLoss, type ReportLine } from "../api";

function LineTable({ rows }: { rows: ReportLine[] }) {
  if (rows.length === 0) return <p className="muted">No posted entries.</p>;
  return (
    <table>
      <tbody>
        {rows.map((r) => (
          <tr key={r.code}>
            <td>
              <span className="muted">{r.code}</span> {r.name}
            </td>
            <td className="num">{money(r.amount)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function Reports() {
  const [pl, setPl] = useState<ProfitAndLoss | null>(null);
  const [bs, setBs] = useState<BalanceSheet | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.profitAndLoss(), api.balanceSheet()])
      .then(([p, b]) => {
        setPl(p);
        setBs(b);
      })
      .catch((e) => setError(String((e as Error).message)));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!pl || !bs) return <p className="muted">Loading…</p>;

  return (
    <div className="report-grid">
      <div className="report">
        <h3>Profit &amp; Loss</h3>
        <h4 className="muted">Revenue</h4>
        <LineTable rows={pl.revenue} />
        <h4 className="muted">Expenses</h4>
        <LineTable rows={pl.expenses} />
        <table>
          <tbody>
            <tr className="total">
              <td>Total Revenue</td>
              <td className="num">{money(pl.total_revenue)}</td>
            </tr>
            <tr className="total">
              <td>Total Expenses</td>
              <td className="num">{money(pl.total_expenses)}</td>
            </tr>
            <tr className="total">
              <td>Net Income</td>
              <td className="num">{money(pl.net_income)}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="report">
        <h3>
          Balance Sheet{" "}
          <span className={bs.balanced ? "conf high" : "conf low"} style={{ fontSize: 12 }}>
            {bs.balanced ? "✓ balanced" : "⚠ out of balance"}
          </span>
        </h3>
        <h4 className="muted">Assets</h4>
        <LineTable rows={bs.assets} />
        <h4 className="muted">Liabilities</h4>
        <LineTable rows={bs.liabilities} />
        <h4 className="muted">Equity</h4>
        <LineTable rows={bs.equity} />
        <table>
          <tbody>
            <tr className="total">
              <td>Total Assets</td>
              <td className="num">{money(bs.total_assets)}</td>
            </tr>
            <tr className="total">
              <td>Liabilities + Equity</td>
              <td className="num">{money(bs.total_liabilities + bs.total_equity)}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
