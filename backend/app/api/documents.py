from fastapi import APIRouter, Depends, HTTPException, Response

from app.core.auth import get_current_user, CurrentUser
from app.core.supabase_client import get_supabase_client
from app.documents.pdf_builder import (
    build_invoice_html, build_receipt_html, build_statement_html, render_pdf,
)

router = APIRouter()


@router.get("/invoice/{invoice_id}")
def get_invoice_pdf(invoice_id: str, user: CurrentUser = Depends(get_current_user)):
    client = get_supabase_client(user.token)
    invoice_result = client.table("invoices").select("*").eq("id", invoice_id).execute()
    if not invoice_result.data:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    invoice = invoice_result.data[0]

    client_result = client.table("clients").select("*").eq("id", invoice["client_id"]).execute()
    business_result = client.table("businesses").select("*").eq("id", invoice["business_id"]).execute()
    if not client_result.data or not business_result.data:
        raise HTTPException(status_code=404, detail="Related client or business not found.")

    html = build_invoice_html(invoice, client_result.data[0], business_result.data[0])
    pdf_bytes = render_pdf(html)
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="invoice-{invoice_id[:8]}.pdf"'},
    )


@router.get("/receipt/{invoice_id}")
def get_receipt_pdf(invoice_id: str, user: CurrentUser = Depends(get_current_user)):
    client = get_supabase_client(user.token)
    invoice_result = client.table("invoices").select("*").eq("id", invoice_id).execute()
    if not invoice_result.data:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    invoice = invoice_result.data[0]

    if invoice["status"] != "paid":
        raise HTTPException(status_code=400, detail="Receipt is only available for fully paid invoices.")

    client_result = client.table("clients").select("*").eq("id", invoice["client_id"]).execute()
    business_result = client.table("businesses").select("*").eq("id", invoice["business_id"]).execute()
    payments_result = (
        client.table("ledger_entries")
        .select("*")
        .eq("invoice_id", invoice_id)
        .eq("entry_type", "payment_received")
        .order("created_at")
        .execute()
    )

    html = build_receipt_html(invoice, client_result.data[0], business_result.data[0], payments_result.data)
    pdf_bytes = render_pdf(html)
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="receipt-{invoice_id[:8]}.pdf"'},
    )


@router.get("/statement/{client_id}")
def get_statement_pdf(client_id: str, user: CurrentUser = Depends(get_current_user)):
    client = get_supabase_client(user.token)
    client_result = client.table("clients").select("*").eq("id", client_id).execute()
    if not client_result.data:
        raise HTTPException(status_code=404, detail="Client not found.")
    client_row = client_result.data[0]

    business_result = client.table("businesses").select("*").eq("id", client_row["business_id"]).execute()
    invoices_result = client.table("invoices").select("*").eq("client_id", client_id).order("issue_date").execute()

    invoice_ids = [inv["id"] for inv in invoices_result.data]
    ledger_data = []
    if invoice_ids:
        ledger_result = (
            client.table("ledger_entries").select("*").in_("invoice_id", invoice_ids).order("created_at").execute()
        )
        ledger_data = ledger_result.data

    html = build_statement_html(client_row, business_result.data[0], invoices_result.data, ledger_data)
    pdf_bytes = render_pdf(html)
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="statement-{client_id[:8]}.pdf"'},
    )