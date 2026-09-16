from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import get_current_user, CurrentUser
from app.agents.ledger_agent import create_dispute
from app.agents.dispute_agent import resolve_dispute_case

router = APIRouter()


class DisputeCreate(BaseModel):
    business_id: str
    invoice_id: str
    raised_by: str
    claim_text: str
    claim_amount: float | None = None


@router.post("")
def raise_dispute(payload: DisputeCreate, user: CurrentUser = Depends(get_current_user)):
    """
    Owner logs a client's dispute claim (no client-facing portal in Phase 1,
    so the owner enters it on the client's behalf), then immediately runs
    the Dispute Resolution Agent against it.
    """
    dispute = create_dispute.invoke({
        "invoice_id": payload.invoice_id,
        "raised_by": payload.raised_by,
        "claim_text": payload.claim_text,
        "claim_amount": payload.claim_amount,
    })
    decision = resolve_dispute_case(dispute_id=dispute["id"], business_id=payload.business_id)
    return {"dispute": dispute, "resolution": decision.model_dump()}