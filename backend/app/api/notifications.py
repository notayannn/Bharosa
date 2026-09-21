from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user, CurrentUser
from app.integrations.resend_email import send_email

router = APIRouter()


class TestEmailRequest(BaseModel):
    to: str


@router.post("/test-email")
def send_test_email(payload: TestEmailRequest, user: CurrentUser = Depends(get_current_user)):
    try:
        result = send_email(
            to=payload.to,
            subject="Bharosa — test email",
            html_body="<p>If you're reading this, Resend is wired up correctly.</p>",
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Email send failed: {e}")
    return {"sent": True, "resend_id": result.get("id")}