"""
Escalation Agent (spec Section 6.3).

Decides when and through which channel to follow up on an invoice.
Tier 1 -- fully autonomous, no owner approval needed, since no financial
amount is being changed, only communication.

Sends REAL messages now via Resend (email) and Green API (WhatsApp),
picked per-client based on what's in contact_channels.primary: an "@" in
the value is treated as an email, otherwise as a WhatsApp number. This is
a heuristic, not a real field distinction -- contact_channels only stores
one loose "primary" value in the current client form.
"""
from datetime import date

from app.agents.ledger_agent import (
    get_overdue_invoices,
    get_upcoming_invoices,
    get_client,
    record_reminder,
    log_agent_action,
)
from app.integrations.resend_email import send_email
from app.integrations.green_api import send_whatsapp_message


def _build_message(invoice: dict, template_id: str) -> tuple[str, str]:
    """Returns (subject, body) for a given template."""
    amount = f"{invoice['currency']} {invoice['amount']}"
    if template_id == "pre_due_reminder":
        return (
            "Upcoming invoice due soon",
            f"Hi, this is a reminder that an invoice for {amount} is due on {invoice['due_date']}.",
        )
    if template_id == "overdue_reminder_1d":
        return (
            "Invoice overdue",
            f"Your invoice for {amount} was due on {invoice['due_date']} and is now overdue. Please arrange payment when you can.",
        )
    return (
        "Invoice significantly overdue",
        f"Your invoice for {amount}, due {invoice['due_date']}, remains unpaid a week past due. Please get in touch to resolve this.",
    )


def run_escalation_check(business_id: str) -> list[dict]:
    """
    Checks every invoice for this business against the reminder rules and
    sends real reminders for anything due. Meant to be called periodically
    by APScheduler, or manually via a "send reminders now" button.
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
    client = get_client.invoke({"client_id": invoice["client_id"]})
    contact = (client.get("contact_channels") or {}).get("primary", "")
    subject, body = _build_message(invoice, template_id)

    channel = "email" if "@" in contact else "whatsapp"
    status = "failed"
    error_detail = None

    if not contact:
        channel = "none"
        error_detail = "No contact info on file for this client."
    else:
        try:
            if channel == "email":
                send_email(to=contact, subject=subject, html_body=f"<p>{body}</p>")
            else:
                send_whatsapp_message(phone=contact, message=f"{subject}\n\n{body}")
            status = "sent"
        except Exception as e:
            error_detail = str(e)

    reminder = record_reminder.invoke({
        "invoice_id": invoice["id"],
        "channel": channel,
        "template_used": template_id,
        "response_status": status if status == "sent" else f"failed: {error_detail}",
    })

    log_agent_action.invoke({
        "agent_name": "escalation_agent",
        "action_type": "send_reminder",
        "invoice_id": invoice["id"],
        "business_id": business_id,
        "input_summary": f"template={template_id}, channel={channel}, contact={contact or 'none'}",
        "decision": f"{'Sent' if status == 'sent' else 'Failed to send'} {template_id} via {channel}",
        "confidence": 1.0,
        "requires_approval": False,  # Tier 1 -- fully autonomous
    })

    return reminder