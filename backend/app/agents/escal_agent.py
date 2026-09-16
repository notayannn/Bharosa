from datetime import date
from app.agents.ledger_agent import (
    get_overdue_invoices,
    get_upcoming_invoices,
    record_reminder,
    log_agent_action,
)

_CHANNEL = "email"


def run_escalation_check(business_id: str) -> list[dict]:
    """
    Checks every invoice for this business against the reminder rules and
    fires (simulated) reminders for anything due.
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
        "requires_approval": False,
    })

    return reminder