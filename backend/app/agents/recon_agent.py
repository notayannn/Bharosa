"""
Reconciliation Agent (spec Section 6.2).

Given an uploaded payment and a client's open invoices, decides which
invoice(s) it settles. Exact-amount matches are handled deterministically --
no LLM call needed. Ambiguous cases (partial payment, one payment covering
multiple invoices, amount mismatched against a claimed discount) go through
an LLM reasoning step that proposes a settlement plan and a confidence score.

Not yet wired into the Orchestrator (that's Day 4) -- for now it's called
directly by the payments upload route right after ingestion extracts the
slip's amount/transaction ID.
"""
import json
from decimal import Decimal

from openai import OpenAI
from pydantic import BaseModel, Field

from app.agents.config import settings
from app.agents.ledger_agent import (
    _get_admin_client,
    get_open_invoices_for_client,
    record_ledger_entry,
    update_invoice_status,
    update_payment,
    log_agent_action,
)

CONFIDENCE_THRESHOLD = 0.9  # per Section 6.2 -- below this, always owner_review
AMOUNT_TOLERANCE = Decimal("0.01")  # float rounding slack for exact-match comparison

_llm_client = OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)


class SettlementLine(BaseModel):
    invoice_id: str
    amount_applied: float


class ReconciliationDecision(BaseModel):
    """
    Schema-validated output -- the LLM's free-text reasoning never reaches
    the Orchestrator directly, only this structured decision does (the
    'no agent returns free text as final output' rule in Section 6).
    """
    settlement_plan: list[SettlementLine] = Field(default_factory=list)
    confidence: float
    requires_owner_review: bool
    reasoning: str


def reconcile_payment(payment_id: str, business_id: str) -> ReconciliationDecision:
    payment = _get_payment(payment_id)
    client_id = payment["client_id"]
    open_invoices = get_open_invoices_for_client.invoke({"client_id": client_id})

    if not open_invoices:
        decision = ReconciliationDecision(
            settlement_plan=[],
            confidence=1.0,
            requires_owner_review=True,
            reasoning="No open invoices found for this client -- can't reconcile automatically.",
        )
    else:
        exact_match = _find_exact_match(payment, open_invoices)
        if exact_match is not None:
            decision = ReconciliationDecision(
                settlement_plan=[SettlementLine(invoice_id=exact_match["id"], amount_applied=payment["amount"])],
                confidence=1.0,
                requires_owner_review=False,
                reasoning=f"Exact amount match against invoice {exact_match['id']} -- no LLM reasoning needed.",
            )
        else:
            decision = _reason_ambiguous_case(payment, open_invoices)

    _apply_decision(payment_id, business_id, decision)
    return decision


def _find_exact_match(payment: dict, open_invoices: list[dict]) -> dict | None:
    if payment.get("amount") is None:
        return None
    candidates = [
        inv for inv in open_invoices
        if abs(Decimal(str(inv["amount"])) - Decimal(str(payment["amount"]))) <= AMOUNT_TOLERANCE
    ]
    # Two invoices with the same amount is itself an ambiguous case, not a
    # clean match -- only count it as exact if exactly one candidate matches.
    return candidates[0] if len(candidates) == 1 else None


def _reason_ambiguous_case(payment: dict, open_invoices: list[dict]) -> ReconciliationDecision:
    prompt = (
        "You are the Reconciliation Agent for a B2B invoicing ledger. "
        "A payment was uploaded that doesn't match exactly one open invoice. "
        "Propose how to apply it and how confident you are.\n\n"
        f"Payment: amount={payment.get('amount')}, "
        f"transaction_id={payment.get('transaction_id')}\n\n"
        f"Open invoices for this client: {json.dumps(open_invoices, default=str)}\n\n"
        "Respond with ONLY a JSON object matching this shape, nothing else:\n"
        '{"settlement_plan": [{"invoice_id": "...", "amount_applied": 0.0}], '
        '"confidence": 0.0, "requires_owner_review": true, "reasoning": "..."}'
    )

    response = _llm_client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    raw = response.choices[0].message.content.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        parsed = json.loads(raw)
        decision = ReconciliationDecision(**parsed)
    except (json.JSONDecodeError, TypeError, ValueError):
        # LLM returned something we can't validate -- fail safe to owner
        # review rather than silently guessing at a settlement.
        decision = ReconciliationDecision(
            settlement_plan=[], confidence=0.0, requires_owner_review=True,
            reasoning="Reconciliation Agent couldn't produce a valid settlement plan; routed to owner review.",
        )

    if decision.confidence < CONFIDENCE_THRESHOLD:
        decision.requires_owner_review = True

    return decision


def apply_settlement(payment_id: str, decision: ReconciliationDecision) -> None:
    """
    Actually commits a settlement -- called either automatically (exact
    match, no review needed) or from the approval endpoint once an owner
    approves an ambiguous-case recommendation.
    """
    for line in decision.settlement_plan:
        record_ledger_entry.invoke({
            "invoice_id": line.invoice_id,
            "entry_type": "payment_received",
            "amount": line.amount_applied,
            "actor": "agent",
            "agent_name": "reconciliation_agent",
            "reasoning_summary": decision.reasoning,
        })
        update_invoice_status.invoke({"invoice_id": line.invoice_id, "new_status": "paid"})

    settled_invoice_id = decision.settlement_plan[0].invoice_id if decision.settlement_plan else None
    update_payment.invoke({
        "payment_id": payment_id,
        "invoice_id": settled_invoice_id,
        "verified": True,
        "verified_by": "agent",
    })


def _apply_decision(payment_id: str, business_id: str, decision: ReconciliationDecision) -> None:
    if not decision.requires_owner_review:
        apply_settlement(payment_id, decision)

    log_agent_action.invoke({
        "agent_name": "reconciliation_agent",
        "action_type": "reconcile_payment",
        "invoice_id": decision.settlement_plan[0].invoice_id if decision.settlement_plan else None,
        "business_id": business_id,
        "input_summary": f"payment_id={payment_id}",
        "decision": decision.model_dump_json(),
        "confidence": decision.confidence,
        "requires_approval": decision.requires_owner_review,
    })


def _get_payment(payment_id: str) -> dict:
    client = _get_admin_client()
    result = client.table("payments").select("*").eq("id", payment_id).execute()
    if not result.data:
        raise ValueError(f"Payment {payment_id} not found.")
    return result.data[0]