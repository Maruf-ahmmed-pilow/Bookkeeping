export interface Account {
  id: string;
  code: string;
  name: string;
  account_type: string;
  is_cash: boolean;
  is_active: boolean;
}

export interface Transaction {
  id: string;
  txn_date: string;
  description: string;
  amount: number;
  direction: "inflow" | "outflow";
  status: string;
  source_system: string;
  confidence: number | null;
  ai_reasoning: string | null;
  suggested_account_id: string | null;
  bank_account_id: string;
  created_at: string;
}

export interface ClassifyResult {
  transaction_id: string;
  account_code: string;
  account_name: string;
  confidence: number;
  reasoning: string;
  engine: string;
  status: string;
}

export interface ReportLine {
  code: string;
  name: string;
  amount: number;
}

export interface ProfitAndLoss {
  revenue: ReportLine[];
  expenses: ReportLine[];
  total_revenue: number;
  total_expenses: number;
  net_income: number;
}

export interface BalanceSheet {
  assets: ReportLine[];
  liabilities: ReportLine[];
  equity: ReportLine[];
  total_assets: number;
  total_liabilities: number;
  total_equity: number;
  balanced: boolean;
}

export interface DashboardMetrics {
  total_revenue: number;
  total_expenses: number;
  net_income: number;
  cash_on_hand: number;
  pending_review: number;
  posted_transactions: number;
}

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => http<Record<string, unknown>>("/api/health"),
  accounts: () => http<Account[]>("/api/accounts"),
  transactions: (status?: string) =>
    http<Transaction[]>(`/api/transactions${status ? `?status=${status}` : ""}`),
  classify: (id: string) =>
    http<ClassifyResult>(`/api/transactions/${id}/classify`, { method: "POST" }),
  classifyAll: () =>
    http<{ classified: number }>("/api/transactions/classify-all", { method: "POST" }),
  approve: (id: string, body: { account_id?: string; reason?: string; actor?: string }) =>
    http<Transaction>(`/api/transactions/${id}/approve`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  reject: (id: string, body: { reason?: string; actor?: string }) =>
    http<Transaction>(`/api/transactions/${id}/reject`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  dashboard: () => http<DashboardMetrics>("/api/reports/dashboard"),
  profitAndLoss: () => http<ProfitAndLoss>("/api/reports/profit-and-loss"),
  balanceSheet: () => http<BalanceSheet>("/api/reports/balance-sheet"),
};

export const money = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD" });
