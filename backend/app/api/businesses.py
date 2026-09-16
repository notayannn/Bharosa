from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user, CurrentUser
from app.core.supabase_client import get_supabase_client

router = APIRouter()


class BusinessCreate(BaseModel):
    name: str


@router.post("")
def create_business(payload: BusinessCreate, user: CurrentUser = Depends(get_current_user)):

    client = get_supabase_client(user.token)
    result = client.table("businesses").insert({
        "name": payload.name,
        "owner_user_id": user.id,
    }).execute()
    return result.data[0]


@router.get("/me")
def get_my_business(user: CurrentUser = Depends(get_current_user)):
    """
    Returns the calling user's own business — RLS guarantees this can only
    ever return their own row, never anyone else's
    """
    client = get_supabase_client(user.token)
    result = client.table("businesses").select("*").execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="No business found for this user.")
    return result.data[0]