from datetime import date, timedelta, datetime

from langchain_core.tools import tool
from supabase import create_client, Client

from app.agents.config import settings

_admin_client: Client | None = None


def _get_admin_client() -> Client:
    """
    Supabase client authenticated with the SECRET key — bypasses RLS.
    """
    global _admin_client
    if _admin_client is None:
        _admin_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)
    return _admin_client


@tool
def get_invoice(invoice_id: str) -> dict:
    """Fetch a single invoice by its ID, including current status and amount."""
    client = _get_admin_client()
    result = client.table("invoices").select("*").eq("id", invoice_id).execute()
    if not result.data:
        return {"error": f"Invoice {invoice_id} not found."}
    return result.data[0]


@tool
def get_client_ledger(client_id: str) -> list[dict]:
    """
    Fetch the full ledger history for a client — every entry across all
    their invoices, oldest first.
    """
    client = _get_admin_client()
    invoices = client.table("invoices").select("id").eq("client_id", client_id).execute()
    invoice_ids = [inv["id"] for inv in invoices.data]
    if not invoice_ids:
        return []
    entries = (
        client.table("ledger_entries")
        .select("*")
        .in_("invoice_id", invoice_ids)
        .order("created_at")
        .execute()
    )
    return entries.data


@tool
def get_overdue_invoices(business_id: str) -> list[dict]:
    """
    Fetch every invoice for a business past its due_date and not yet fully
    paid or written off.
    """
    client = _get_admin_client()
    today = date.today().isoformat()
    result = (
        client.table("invoices")
        .select("*")
        .eq("business_id", business_id)
        .lt("due_date", today)
        .not_.in_("status", ["paid", "written_off"])
        .execute()
    )
    return result.data


@tool
def get_upcoming_invoices(business_id: str) -> list[dict]:
    """
    Fetch invoices for a business due in exactly 3 days and not yet paid --
    the pre-due nudge window the Escalation Agent checks on its schedule.
    """
    client = _get_admin_client()
    target_date = (date.today() + timedelta(days=3)).isoformat()
    result = (
        client.table("invoices")
        .select("*")
        .eq("business_id", business_id)
        .eq("due_date", target_date)
        .not_.in_("status", ["paid", "written_off"])
        .execute()
    )
    return result.data


@tool
def record_ledger_entry(
    invoice_id: str,
    entry_type: str,
    amount: float | None,
    actor: str,
    agent_name: str | None,
    reasoning_summary: str,
) -> dict:
    """
    Append a new entry to an invoice's ledger.
    """
    client = _get_admin_client()
    result = client.table("ledger_entries").insert({
        "invoice_id": invoice_id,
        "entry_type": entry_type,
        "amount": amount,
        "actor": actor,
        "agent_name": agent_name,
        "reasoning_summary": reasoning_summary,
    }).execute()
    return result.data[0]


@tool
def update_invoice_status(invoice_id: str, new_status: str) -> dict:
    """
    Updates an invoice's status.
    """
    client = _get_admin_client()
    result = (
        client.table("invoices").update({"status": new_status}).eq("id", invoice_id).execute()
    )
    return result.data[0]


@tool
def get_open_invoices_for_client(client_id: str) -> list[dict]:
    """
    Fetch every invoice for a client that isn't fully paid or written off --
    the candidate set the Reconciliation Agent checks an uploaded payment
    against.
    """
    client = _get_admin_client()
    result = (
        client.table("invoices")
        .select("*")
        .eq("client_id", client_id)
        .not_.in_("status", ["paid", "written_off"])
        .order("due_date")
        .execute()
    )
    return result.data


@tool
def create_pending_payment(
    client_id: str,
    amount: float | None,
    transaction_id: str | None,
    slip_url: str | None,
    method: str = "bank_transfer",
) -> dict:
    """
    Creates the initial payments row right after a slip is uploaded, before
    reconciliation has run. invoice_id starts null -- filled in once the
    Reconciliation Agent (or owner review) decides which invoice this
    payment settles.
    """
    client = _get_admin_client()
    result = client.table("payments").insert({
        "client_id": client_id,
        "amount": amount,
        "transaction_id": transaction_id,
        "slip_url": slip_url,
        "method": method,
        "verified": False,
    }).execute()
    return result.data[0]


@tool
def update_payment(payment_id: str, invoice_id: str | None, verified: bool, verified_by: str) -> dict:
    """
    Updates a payment row once the Reconciliation Agent has decided which
    invoice it settles.
    """
    client = _get_admin_client()
    result = (
        client.table("payments")
        .update({"invoice_id": invoice_id, "verified": verified, "verified_by": verified_by})
        .eq("id", payment_id)
        .execute()
    )
    return result.data[0]


@tool
def record_reminder(invoice_id: str, channel: str, template_used: str, response_status: str) -> dict:
    """
    Logs a reminder as sent.
    """
    client = _get_admin_client()
    result = client.table("reminders").insert({
        "invoice_id": invoice_id,
        "channel": channel,
        "template_used": template_used,
        "response_status": response_status,
        "sent_at": datetime.utcnow().isoformat(),
    }).execute()
    return result.data[0]


@tool
def list_all_business_ids() -> list[str]:
    """Returns every business's id -- used by the scheduler to loop through all businesses."""
    client = _get_admin_client()
    result = client.table("businesses").select("id").execute()
    return [row["id"] for row in result.data]


@tool
def log_agent_action(
    agent_name: str,
    action_type: str,
    invoice_id: str | None,
    business_id: str | None,
    input_summary: str,
    decision: str,
    confidence: float | None,
    requires_approval: bool,
) -> dict:
    """
    Record an agent decision or audit step into the agent_actions log table.
    """
    client = _get_admin_client()
    result = client.table("agent_actions").insert({
        "agent_name": agent_name,
        "action_type": action_type,
        "invoice_id": invoice_id,
        "business_id": business_id,
        "input_summary": input_summary,
        "decision": decision,
        "confidence": confidence,
        "requires_approval": requires_approval,
    }).execute()
    return result.data[0]


@tool
def get_dispute(dispute_id: str) -> dict:
    """Fetch a single dispute by its ID."""
    client = _get_admin_client()
    result = client.table("disputes").select("*").eq("id", dispute_id).execute()
    if not result.data:
        return {"error": f"Dispute {dispute_id} not found."}
    return result.data[0]


@tool
def create_dispute(invoice_id: str, raised_by: str, claim_text: str, claim_amount: float | None) -> dict:
    """Logs a new dispute claim against an invoice, status starts 'open'."""
    client = _get_admin_client()
    result = client.table("disputes").insert({
        "invoice_id": invoice_id,
        "raised_by": raised_by,
        "claim_text": claim_text,
        "claim_amount": claim_amount,
        "status": "open",
    }).execute()
    return result.data[0]


@tool
def list_clients(business_id: str) -> list[dict]:
    """List all clients for a business, with their id and name -- use this to look up a client's id before calling any tool that needs client_id."""
    client = _get_admin_client()
    result = client.table("clients").select("id, name").eq("business_id", business_id).execute()
    return result.data


@tool
def resolve_dispute(dispute_id: str, status: str, resolution_summary: str) -> dict:
    """Updates a dispute's status and resolution once judged, by agent or owner."""
    client = _get_admin_client()
    result = (
        client.table("disputes")
        .update({"status": status, "resolution_summary": resolution_summary})
        .eq("id", dispute_id)
        .execute()
    )
    return result.data[0]

@tool
def get_client(client_id: str) -> dict:
    """Fetch a single client's details, including contact_channels, by ID."""
    client = _get_admin_client()
    result = client.table("clients").select("*").eq("id", client_id).execute()
    if not result.data:
        return {"error": f"Client {client_id} not found."}
    return result.data[0]


@tool
def get_invoice_ledger(invoice_id: str) -> list[dict]:
    """Fetch ledger entries for a single invoice, oldest first."""
    client = _get_admin_client()
    result = (
        client.table("ledger_entries")
        .select("*")
        .eq("invoice_id", invoice_id)
        .order("created_at")
        .execute()
    )
    return result.data