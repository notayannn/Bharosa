from fastapi import APIRouter, Depends

from app.core.auth import get_current_user, CurrentUser
from app.agents.escal_agent import run_escalation_check

router = APIRouter()


@router.post("/run")
def trigger_escalation_check(business_id: str, user: CurrentUser = Depends(get_current_user)):
    """
    Manual trigger for the demo's "send reminders now" button -- runs the
    same check the scheduler runs periodically, immediately, for one business.
    """
    sent = run_escalation_check(business_id)
    return {"reminders_sent": sent}