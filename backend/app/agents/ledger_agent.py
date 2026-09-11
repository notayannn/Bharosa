from datetime import date

from langchain_core.tools import tool
from supabase import create_client, Client

from agents.config import settings

_admin_client: Client | None = None


def _get_admin_client() -> Client:
    """
    Supabase client authenticated with the SECRET key — bypasses RLS.
    Reserved for agent-internal operations acting on behalf of the system.
    Never expose this client via a user-facing API route directly.
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
    their invoices, oldest first. This is what the Dispute Resolution
    Agent (Day 5) will read to judge whether a client's claim is plausible.
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
    paid or written off — the working set the Escalation Agent (Day 5)
    will scan on its reminder schedule.
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
def record_ledger_entry(
    invoice_id: str,
    entry_type: str,
    amount: float | None,
    actor: str,
    agent_name: str | None,
    reasoning_summary: str,
) -> dict:
    """
    Append a new entry to an invoice's ledger. This is the ONLY correct way
    for any agent to record a payment, adjustment, or event — ledger_entries
    is append-only and is the system's source of truth; it is never edited
    or deleted after the fact.
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
    Updates an invoice's status. Per the Orchestrator design (Day 4), this
    should ONLY ever be called by the Orchestrator itself — kept here as
    the underlying DB operation the Orchestrator's state machine calls into,
    not something the Reconciliation/Dispute agents call directly.
    """
    client = _get_admin_client()
    result = (
        client.table("invoices").update({"status": new_status}).eq("id", invoice_id).execute()
    )
    return result.data[0]