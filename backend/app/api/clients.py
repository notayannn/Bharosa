from fastapi import APIRouter, Depends
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
    """
    Creates a client under the given business. RLS (Step 5's
    owner_manage_own_clients policy) rejects this outright if business_id
    doesn't belong to the calling user — no need to double-check that here.
    """
    client = get_supabase_client(user.token)
    result = client.table("clients").insert({
        "business_id": payload.business_id,
        "name": payload.name,
        "contact_channels": payload.contact_channels,
    }).execute()
    return result.data[0]


@router.get("")
def list_clients(business_id: str, user: CurrentUser = Depends(get_current_user)):
    """
    Lists all clients for a business. Also RLS-scoped — even if a caller
    passed a business_id that isn't theirs, this returns an empty list
    rather than another business's clients.
    """
    client = get_supabase_client(user.token)
    result = (
        client.table("clients")
        .select("*")
        .eq("business_id", business_id)
        .execute()
    )
    return result.data