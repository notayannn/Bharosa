from fastapi import APIRouter, Depends

from app.core.auth import get_current_user, CurrentUser
from app.integrations.green_api import get_qr_code, get_instance_state

router = APIRouter()


@router.get("/status")
def whatsapp_status(user: CurrentUser = Depends(get_current_user)):
    state = get_instance_state()
    return {"state": state, "connected": state == "authorized"}


@router.get("/qr")
def whatsapp_qr(user: CurrentUser = Depends(get_current_user)):
    return get_qr_code()