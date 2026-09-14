"""
Owner approval endpoint -- resolves agent_actions rows where
requires_approval=True (Tier 3 decisions from the Reconciliation Agent or
Dispute Resolution Agent, both of which log their proposed decision as
JSON without applying it).
"""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import get_current_user, CurrentUser
from app.core.supabase_client import get_supabase_client
from app.agents.ledger_agent import _get_admin_client
from app.agents.recon_agent import ReconciliationDecision, apply_settlement
from app.agents.dispute_agent import apply_dispute_action

router = APIRouter()


@router.get("/pending")
def list_pending_approvals(business_id: str, user: CurrentUser = Depends(get_current_user)):
    """Every agent_actions row awaiting an owner's yes/no."""
    client = get_supabase_client(user.token)
    result = (
        client.table("agent_actions")
        .select("*")
        .eq("business_id", business_id)
        .eq("requires_approval", True)
        .is_("approved", "null")
        .execute()
    )
    return result.data


@router.post("/{action_id}/decide")
def decide_approval(action_id: str, approved: bool, user: CurrentUser = Depends(get_current_user)):
    """
    Owner approves or rejects a pending agent decision. On approval, this
    applies whatever the agent proposed -- the agent_actions row stored its
    full decision as JSON precisely so this replay is possible.
    """
    admin_client = _get_admin_client()
    action_result = admin_client.table("agent_actions").select("*").eq("id", action_id).execute()
    if not action_result.data:
        raise HTTPException(status_code=404, detail="Action not found.")
    action = action_result.data[0]

    if approved:
        decision_data = json.loads(action["decision"])
        if action["action_type"] == "reconcile_payment":
            decision = ReconciliationDecision(**decision_data)
            payment_id = action["input_summary"].split("=")[1]  # "payment_id=<id>"
            apply_settlement(payment_id, decision)
        elif action["action_type"] == "resolve_dispute":
            dispute_id = action["input_summary"].split(",")[0].split("=")[1]
            apply_dispute_action(
                dispute_id=dispute_id,
                invoice_id=action["invoice_id"],
                action=decision_data["recommended_action"],
                reasoning=decision_data["reasoning"] + " (owner-approved)",
            )

    admin_client.table("agent_actions").update({
        "approved": approved,
        "resolved_at": datetime.utcnow().isoformat(),
    }).eq("id", action_id).execute()

    return {"action_id": action_id, "approved": approved}