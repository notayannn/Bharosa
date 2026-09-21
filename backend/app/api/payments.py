import os
import tempfile
import uuid

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException

from app.core.auth import get_current_user, CurrentUser
from app.core.supabase_client import get_supabase_client
from app.ingestion.router import extract, UnsupportedFileType
from app.integrations.storage import upload_slip
from app.agents.ledger_agent import create_pending_payment
from app.agents.orchestrator import run_reconciliation_flow

router = APIRouter()


@router.post("/upload")
async def upload_payment_slip(
    business_id: str = Form(...),
    client_id: str = Form(...),
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
):
    """
    Owner uploads a photographed payment slip for one of their clients.
    Runs OCR extraction, uploads the slip to Supabase Storage (so it
    survives regardless of host/redeploys), creates the pending payments
    row, then hands off to the Reconciliation Agent via the Orchestrator.
    """
    client = get_supabase_client(user.token)
    business = client.table("businesses").select("id").eq("id", business_id).execute()
    if not business.data:
        raise HTTPException(status_code=404, detail="Business not found for this user.")

    file_bytes = await file.read()
    ext = os.path.splitext(file.filename or "")[1] or ".jpg"

    # OCR needs an actual file on disk to read -- /tmp is safe scratch
    # space on every host (ephemeral is fine here, we only need it for
    # the few seconds Tesseract runs), separate from permanent storage.
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        extracted = extract(tmp_path)
    except UnsupportedFileType as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        os.remove(tmp_path)

    slip_url = upload_slip(file_bytes, file.filename or f"{uuid.uuid4()}.jpg")

    payment = create_pending_payment.invoke({
        "client_id": client_id,
        "amount": extracted.amount,
        "transaction_id": extracted.transaction_id,
        "slip_url": slip_url,
    })

    flow_result = run_reconciliation_flow(payment_id=payment["id"], business_id=business_id)
    decision = flow_result["decision"]

    return {
        "payment": payment,
        "extracted": {
            "amount": extracted.amount,
            "transaction_id": extracted.transaction_id,
            "confidence": extracted.confidence,
        },
        "reconciliation": decision.model_dump(),
    }