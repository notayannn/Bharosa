import os
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from app.core.auth import get_current_user, CurrentUser
from app.core.supabase_client import get_supabase_client
from app.ingestion.router import extract, UnsupportedFileType
from app.agents.ledger_agent import create_pending_payment
from app.agents.orchestrator import run_reconciliation_flow

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "slips")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_payment_slip(
    business_id: str = Form(...),
    client_id: str = Form(...),
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
):

    client = get_supabase_client(user.token)
    business = client.table("businesses").select("id").eq("id", business_id).execute()
    if not business.data:
        raise HTTPException(status_code=404, detail="Business not found for this user.")

    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    saved_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{ext}")
    with open(saved_path, "wb") as f:
        f.write(await file.read())

    try:
        extracted = extract(saved_path)
    except UnsupportedFileType as e:
        raise HTTPException(status_code=400, detail=str(e))

    payment = create_pending_payment.invoke({
        "client_id": client_id,
        "amount": extracted.amount,
        "transaction_id": extracted.transaction_id,
        "slip_url": saved_path,
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