"""Transaction Classification Agent (F2 / FR-TRAN-1).

Maps a financial transaction to a Chart of Accounts category and produces a
confidence score. Uses the Claude API when ANTHROPIC_API_KEY is set, and falls
back to a deterministic rule-based classifier so the platform runs offline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic import BaseModel, Field

from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class CoaOption:
    code: str
    name: str
    account_type: str


@dataclass
class ClassificationOutput:
    account_code: str
    confidence: float
    reasoning: str
    engine: str  # "claude" | "rule-based"


class _LLMClassification(BaseModel):
    """Schema Claude is constrained to return (structured output)."""

    account_code: str = Field(description="The exact COA code from the provided list")
    confidence: float = Field(
        description="Confidence between 0 and 1 that this is the correct category"
    )
    reasoning: str = Field(description="One or two sentences explaining the choice")


SYSTEM_PROMPT = (
    "You are the Transaction Classification Agent in an enterprise bookkeeping "
    "platform. Given a bank transaction, choose the single best matching account "
    "from the provided Chart of Accounts. Use the transaction description, the "
    "direction (inflow = money received, outflow = money spent), and standard "
    "double-entry accounting conventions.\n\n"
    "Rules:\n"
    "- Outflows are normally expenses, asset purchases, or liability payments.\n"
    "- Inflows are normally revenue or liability/loan proceeds.\n"
    "- Never pick the cash/bank account itself — that is the other side of the entry.\n"
    "- Return account_code exactly as it appears in the list.\n"
    "- Set a low confidence (< 0.9) when the description is ambiguous, abbreviated, "
    "or the vendor is unfamiliar, so a human reviews it."
)


def _coa_block(coa: list[CoaOption]) -> str:
    return "\n".join(f"  {o.code}  {o.name}  [{o.account_type}]" for o in coa)


# Force structured output via a single-tool tool_choice. The model is required to
# call this tool, and its arguments are validated against _LLMClassification.
CLASSIFY_TOOL = {
    "name": "classify_transaction",
    "description": "Record the chosen Chart of Accounts category for the transaction.",
    "input_schema": _LLMClassification.model_json_schema(),
}


def _classify_with_claude(
    description: str, amount: float, direction: str, coa: list[CoaOption]
) -> ClassificationOutput:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    user = (
        f"Chart of Accounts (non-cash categories you may choose from):\n"
        f"{_coa_block(coa)}\n\n"
        f"Transaction:\n"
        f"  Description: {description}\n"
        f"  Amount: {amount:.2f}\n"
        f"  Direction: {direction}\n\n"
        f"Classify it."
    )
    response = client.messages.create(
        model=settings.ai_model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user}],
        tools=[CLASSIFY_TOOL],
        tool_choice={"type": "tool", "name": CLASSIFY_TOOL["name"]},
    )
    tool_use = next((b for b in response.content if b.type == "tool_use"), None)
    if tool_use is None:
        raise ValueError("Claude returned no classification tool call")
    parsed = _LLMClassification.model_validate(tool_use.input)

    valid_codes = {o.code for o in coa}
    if parsed.account_code not in valid_codes:
        # Model picked something outside the COA — force human review.
        return ClassificationOutput(
            account_code=parsed.account_code,
            confidence=min(parsed.confidence, 0.5),
            reasoning=f"(unverified code) {parsed.reasoning}",
            engine="claude",
        )
    return ClassificationOutput(
        account_code=parsed.account_code,
        confidence=max(0.0, min(1.0, parsed.confidence)),
        reasoning=parsed.reasoning,
        engine="claude",
    )


# Keyword heuristics for the offline fallback engine.
_RULES: list[tuple[tuple[str, ...], str]] = [
    (("payroll", "gusto", "adp", "paychex", "salary", "wages"), "5000"),
    (("rent", "lease", "landlord"), "5100"),
    (("electric", "water", "utility", "internet", "comcast", "verizon"), "5200"),
    (("insurance",), "5300"),
    (("google ads", "facebook ads", "marketing", "mailchimp", "hubspot"), "5400"),
    (("uber", "lyft", "airline", "hotel", "flight", "travel"), "5500"),
    (("aws", "amazon web", "google cloud", "azure", "github", "saas", "software"), "5600"),
    (("legal", "law", "accountant", "consult", "advisory"), "5700"),
]


def _classify_with_rules(
    description: str, amount: float, direction: str, coa: list[CoaOption]
) -> ClassificationOutput:
    codes = {o.code for o in coa}
    desc = description.lower()
    if direction == "inflow":
        code = "4000" if "4000" in codes else next(iter(codes))
        return ClassificationOutput(
            account_code=code,
            confidence=0.7,
            reasoning="Inflow defaulted to revenue by rule-based engine.",
            engine="rule-based",
        )
    for keywords, code in _RULES:
        if code in codes and any(k in desc for k in keywords):
            return ClassificationOutput(
                account_code=code,
                confidence=0.95,
                reasoning=f"Matched keyword rule for account {code}.",
                engine="rule-based",
            )
    fallback = "5900" if "5900" in codes else next(iter(codes))
    return ClassificationOutput(
        account_code=fallback,
        confidence=0.4,
        reasoning="No keyword rule matched; routed to Other Expenses for review.",
        engine="rule-based",
    )


def classify(
    description: str, amount: float, direction: str, coa: list[CoaOption]
) -> ClassificationOutput:
    """Classify a transaction, preferring Claude and falling back to rules.

    When an API key is configured the Claude classifier is attempted first. Any
    failure is logged and degraded to the deterministic rule-based engine so that
    transaction intake is never blocked by an AI outage. The failure detail is
    recorded in the application log — never surfaced in the user-facing
    ``reasoning`` field.
    """
    if not settings.anthropic_api_key:
        return _classify_with_rules(description, amount, direction, coa)

    try:
        return _classify_with_claude(description, amount, direction, coa)
    except Exception:  # noqa: BLE001 — resilience boundary: degrade, never block intake
        logger.warning(
            "Claude classification failed; falling back to rule-based engine "
            "(description=%r, direction=%s)",
            description,
            direction,
            exc_info=True,
        )
        return _classify_with_rules(description, amount, direction, coa)
