from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user, CurrentUser
from app.core.supabase_client import get_supabase_client

router = APIRouter()


class ClientCreate(BaseModel):
    business_id: str
    name: str
    contact_channels: dict = {}


@router.post("")
def create_client(payload: ClientCreate, user: CurrentUser = Depends(get_current_user)):

    client = get_supabase_client(user.token)
    result = client.table("clients").insert({
        "business_id": payload.business_id,
        "name": payload.name,
        "contact_channels": payload.contact_channels,
    }).execute()
    return result.data[0]

class ClientUpdate(BaseModel):
    name: str | None = None
    contact_channels: dict | None = None


@router.patch("/{client_id}")
def update_client(client_id: str, payload: ClientUpdate, user: CurrentUser = Depends(get_current_user)):
    """
    Updates a client's name and/or contact info. RLS scopes this to the
    caller's own business the same way every other route here does.
    """
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update.")

    client = get_supabase_client(user.token)
    result = client.table("clients").update(updates).eq("id", client_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Client not found.")
    return result.data[0]

@router.get("")
def list_clients(business_id: str, user: CurrentUser = Depends(get_current_user)):

    client = get_supabase_client(user.token)
    result = (
        client.table("clients")
        .select("*")
        .eq("business_id", business_id)
        .execute()
    )
    return result.data