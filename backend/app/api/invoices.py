from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import get_current_user, CurrentUser
from app.core.supabase_client import get_supabase_client

router = APIRouter()


class InvoiceCreate(BaseModel):
    business_id: str
    client_id: str
    amount: float
    currency: str = "PKR"
    issue_date: date
    due_date: date


@router.post("")
def create_invoice(payload: InvoiceCreate, user: CurrentUser = Depends(get_current_user)):
    """
    Issues a new invoice. Also writes the corresponding ledger_entries row
    in the same call — an invoice existing without a matching ledger entry
    would violate the append-only ledger being the source of truth
    (Section 12 of the spec), so these two writes always happen together.
    """
    client = get_supabase_client(user.token)

    invoice_result = client.table("invoices").insert({
        "business_id": payload.business_id,
        "client_id": payload.client_id,
        "amount": payload.amount,
        "currency": payload.currency,
        "issue_date": payload.issue_date.isoformat(),
        "due_date": payload.due_date.isoformat(),
        "status": "issued",
    }).execute()

    invoice = invoice_result.data[0]

    client.table("ledger_entries").insert({
        "invoice_id": invoice["id"],
        "entry_type": "invoice_issued",
        "amount": payload.amount,
        "actor": "owner",
        "reasoning_summary": "Invoice issued by business owner.",
    }).execute()

    return invoice


@router.get("")
def list_invoices(business_id: str, user: CurrentUser = Depends(get_current_user)):
    client = get_supabase_client(user.token)
    result = (
        client.table("invoices")
        .select("*")
        .eq("business_id", business_id)
        .execute()
    )
    return result.data