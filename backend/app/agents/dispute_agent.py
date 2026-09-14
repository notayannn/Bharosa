"""
Dispute Resolution Agent (spec Section 6.4) -- simplified version.

Given a client's dispute claim, judges plausibility using the invoice's
ledger history and the claim details directly (no pgvector/RAG -- cut for
demo time, per the Day 4 scope decision). Tier 2 (auto-resolve) below the
Rs. 10,000 threshold at high confidence; Tier 3 (owner review) above it,
or whenever confidence is low, regardless of amount.
"""
import json
from decimal import Decimal

from openai import OpenAI
from pydantic import BaseModel

from app.agents.config import settings
from app.agents.ledger_agent import (
    get_dispute,
    get_invoice,
    get_invoice_ledger,
    resolve_dispute,
    update_invoice_status,
    record_ledger_entry,
    log_agent_action,
)

CONFIDENCE_THRESHOLD = 0.9
TIER3_AMOUNT_THRESHOLD = Decimal("10000")  # Rs. 10,000 per spec

_llm_client = OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)


class DisputeDecision(BaseModel):
    is_plausible: bool
    recommended_action: str  # dismiss_dispute | write_off | adjust_invoice | escalate_to_owner
    confidence: float
    requires_owner_review: bool
    reasoning: str


def resolve_dispute_case(dispute_id: str, business_id: str) -> DisputeDecision:
    dispute = get_dispute.invoke({"dispute_id": dispute_id})
    invoice = get_invoice.invoke({"invoice_id": dispute["invoice_id"]})
    ledger_history = get_invoice_ledger.invoke({"invoice_id": dispute["invoice_id"]})

    decision = _judge(dispute, invoice, ledger_history)

    invoice_amount = Decimal(str(invoice.get("amount", 0)))
    if invoice_amount > TIER3_AMOUNT_THRESHOLD or decision.confidence < CONFIDENCE_THRESHOLD:
        decision.requires_owner_review = True

    _apply_dispute_decision(dispute_id, business_id, decision)
    return decision


def _judge(dispute: dict, invoice: dict, ledger_history: list[dict]) -> DisputeDecision:
    prompt = (
        "You are the Dispute Resolution Agent for a B2B invoicing ledger. "
        "A client has disputed an invoice. Judge whether the dispute is "
        "plausible given the ledger history, and recommend an action.\n\n"
        f"Dispute claim: {json.dumps(dispute, default=str)}\n\n"
        f"Invoice: {json.dumps(invoice, default=str)}\n\n"
        f"Ledger history for this invoice: {json.dumps(ledger_history, default=str)}\n\n"
        "Respond with ONLY a JSON object matching this shape, nothing else:\n"
        '{"is_plausible": true, "recommended_action": "dismiss_dispute", '
        '"confidence": 0.0, "requires_owner_review": true, "reasoning": "..."}\n'
        "recommended_action must be one of: dismiss_dispute, write_off, "
        "adjust_invoice, escalate_to_owner."
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
        return DisputeDecision(**parsed)
    except (json.JSONDecodeError, TypeError, ValueError):
        return DisputeDecision(
            is_plausible=False,
            recommended_action="escalate_to_owner",
            confidence=0.0,
            requires_owner_review=True,
            reasoning="Dispute Agent couldn't produce a valid judgment; routed to owner review.",
        )


def apply_dispute_action(dispute_id: str, invoice_id: str, action: str, reasoning: str) -> None:
    """
    Actually applies a dispute resolution -- called automatically (Tier 2)
    or from the approval endpoint once an owner approves a Tier 3 case.
    """
    if action == "dismiss_dispute":
        resolve_dispute.invoke({
            "dispute_id": dispute_id, "status": "dismissed",
            "resolution": reasoning, "resolved_by": "agent",
        })
    elif action == "write_off":
        update_invoice_status.invoke({"invoice_id": invoice_id, "new_status": "written_off"})
        record_ledger_entry.invoke({
            "invoice_id": invoice_id, "entry_type": "write_off", "amount": None,
            "actor": "agent", "agent_name": "dispute_agent", "reasoning_summary": reasoning,
        })
        resolve_dispute.invoke({
            "dispute_id": dispute_id, "status": "resolved",
            "resolution": reasoning, "resolved_by": "agent",
        })
    elif action == "adjust_invoice":
        record_ledger_entry.invoke({
            "invoice_id": invoice_id, "entry_type": "dispute_adjustment", "amount": None,
            "actor": "agent", "agent_name": "dispute_agent", "reasoning_summary": reasoning,
        })
        resolve_dispute.invoke({
            "dispute_id": dispute_id, "status": "resolved",
            "resolution": reasoning, "resolved_by": "agent",
        })
    # "escalate_to_owner" applies nothing -- terminal state for
    # requires_owner_review, no further DB write needed beyond the log.


def _apply_dispute_decision(dispute_id: str, business_id: str, decision: DisputeDecision) -> None:
    dispute = get_dispute.invoke({"dispute_id": dispute_id})

    if not decision.requires_owner_review:
        apply_dispute_action(dispute_id, dispute["invoice_id"], decision.recommended_action, decision.reasoning)

    log_agent_action.invoke({
        "agent_name": "dispute_agent",
        "action_type": "resolve_dispute",
        "invoice_id": dispute["invoice_id"],
        "business_id": business_id,
        "input_summary": f"dispute_id={dispute_id}, recommended_action={decision.recommended_action}",
        "decision": decision.model_dump_json(),
        "confidence": decision.confidence,
        "requires_approval": decision.requires_owner_review,
    })