from datetime import date

from langchain_core.tools import tool
from supabase import create_client, Client

from app.agents.config import settings

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
    method: str = "manual_slip",
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
    invoice it settles (or that it can't decide confidently and needs
    owner review, in which case invoice_id stays null and verified stays
    false).
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
    Writes an audit row to agent_actions -- every autonomous decision any
    agent makes gets logged here (Section 12), regardless of which other
    table (if any) it also wrote to.
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