"""
Escalation Agent (spec Section 6.3).

Decides when and through which channel to follow up on an invoice.
Tier 1 -- fully autonomous, no owner approval needed, since no financial
amount is being changed, only communication.

DEMO NOTE: nothing is actually sent. This writes a `reminders` row exactly
as if a message went out (channel, template, timestamp) so the dashboard's
activity feed and "reminders sent" story work end-to-end, without wiring a
real email/SMS/WhatsApp provider. Swap the channel logic for a real
provider call in Phase 2.
"""
from datetime import date

from app.agents.ledger_agent import (
    get_overdue_invoices,
    get_upcoming_invoices,
    record_reminder,
    log_agent_action,
)

# Rule-based baseline per Section 6.3: -3 days (pre-due nudge), +1 and +7
# days overdue. Channel effectiveness modulation (WhatsApp vs email based
# on client history) is a Phase 2 refinement -- Phase 1 always uses email.
_CHANNEL = "email"


def run_escalation_check(business_id: str) -> list[dict]:
    """
    Checks every invoice for this business against the reminder rules and
    fires (simulated) reminders for anything due. Meant to be called
    periodically by APScheduler, or manually via a "send reminders now"
    button for demo purposes.
    """
    sent = []

    for invoice in get_upcoming_invoices.invoke({"business_id": business_id}):
        sent.append(_fire_reminder(invoice, template_id="pre_due_reminder", business_id=business_id))

    for invoice in get_overdue_invoices.invoke({"business_id": business_id}):
        days_overdue = (date.today() - date.fromisoformat(invoice["due_date"])).days
        if days_overdue in (1, 7):
            template_id = f"overdue_reminder_{days_overdue}d"
            sent.append(_fire_reminder(invoice, template_id=template_id, business_id=business_id))

    return sent


def _fire_reminder(invoice: dict, template_id: str, business_id: str) -> dict:
    reminder = record_reminder.invoke({
        "invoice_id": invoice["id"],
        "channel": _CHANNEL,
        "template_used": template_id,
        "response_status": "simulated_sent",
    })

    log_agent_action.invoke({
        "agent_name": "escalation_agent",
        "action_type": "send_reminder",
        "invoice_id": invoice["id"],
        "business_id": business_id,
        "input_summary": f"template={template_id}, channel={_CHANNEL}",
        "decision": f"Sent (simulated) {template_id} via {_CHANNEL}",
        "confidence": 1.0,
        "requires_approval": False,  # Tier 1 -- fully autonomous
    })

    return reminder