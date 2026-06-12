"""Unit tests for the rule-based fallback classifier (offline engine)."""

from app.ai.classifier import CoaOption, classify

COA = [
    CoaOption("4000", "Product & Service Revenue", "revenue"),
    CoaOption("5000", "Payroll Expense", "expense"),
    CoaOption("5600", "Software & Subscriptions", "expense"),
    CoaOption("5900", "Other Expenses", "expense"),
]


def test_keyword_match_is_high_confidence():
    result = classify("GUSTO PAYROLL RUN", 8400.0, "outflow", COA)
    assert result.engine == "rule-based"
    assert result.account_code == "5000"
    assert result.confidence >= 0.9


def test_unmatched_outflow_routes_to_other_for_review():
    result = classify("AMZN MKTPLACE US*2A4KD", 264.19, "outflow", COA)
    assert result.account_code == "5900"
    assert result.confidence < 0.9  # below default threshold → human review


def test_inflow_defaults_to_revenue():
    result = classify("STRIPE PAYOUT", 4820.75, "inflow", COA)
    assert result.account_code == "4000"


def test_never_returns_code_outside_chart_of_accounts():
    codes = {o.code for o in COA}
    for desc, direction in [
        ("AWS CLOUD SERVICES", "outflow"),
        ("MYSTERY VENDOR", "outflow"),
        ("CUSTOMER PAYMENT", "inflow"),
    ]:
        assert classify(desc, 100.0, direction, COA).account_code in codes
