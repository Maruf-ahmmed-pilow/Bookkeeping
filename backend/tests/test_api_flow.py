"""End-to-end API tests for the intake → classify → approve → report flow."""


def test_health_reports_rule_based_engine_without_key(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["ai_engine"] == "rule-based"


def test_classify_all_sets_status_and_confidence(client):
    classified = client.post("/api/transactions/classify-all").json()["classified"]
    assert classified == 4

    statuses = {t["description"]: t["status"] for t in client.get("/api/transactions").json()}
    # Clear vendors classify; ambiguous Amazon charge is escalated for review.
    assert statuses["GUSTO PAYROLL RUN"] == "classified"
    assert statuses["AMZN MKTPLACE US*2A4KD"] == "needs_review"


def test_approve_posts_balanced_journal_and_balance_sheet_balances(client):
    client.post("/api/transactions/classify-all")
    txns = client.get("/api/transactions").json()

    # Approve every classified/needs_review item using its suggested account.
    for t in txns:
        if t["status"] in ("classified", "needs_review"):
            res = client.post(
                f"/api/transactions/{t['id']}/approve",
                json={"account_id": t["suggested_account_id"], "reason": "test"},
            )
            assert res.status_code == 200
            assert res.json()["status"] == "posted"

    bs = client.get("/api/reports/balance-sheet").json()
    assert bs["balanced"] is True

    pl = client.get("/api/reports/profit-and-loss").json()
    assert pl["net_income"] == round(pl["total_revenue"] - pl["total_expenses"], 2)


def test_cannot_approve_with_cash_account(client):
    client.post("/api/transactions/classify-all")
    txn = client.get("/api/transactions").json()[0]
    accounts = client.get("/api/accounts").json()
    cash = next(a for a in accounts if a["is_cash"])

    res = client.post(
        f"/api/transactions/{txn['id']}/approve",
        json={"account_id": cash["id"]},
    )
    assert res.status_code == 422


def test_reject_moves_transaction_out_of_queue(client):
    client.post("/api/transactions/classify-all")
    txn = client.get("/api/transactions").json()[0]
    res = client.post(f"/api/transactions/{txn['id']}/reject", json={"reason": "duplicate"})
    assert res.status_code == 200
    assert res.json()["status"] == "rejected"


def test_classify_missing_transaction_returns_404(client):
    res = client.post("/api/transactions/00000000-0000-0000-0000-000000000000/classify")
    assert res.status_code == 404
