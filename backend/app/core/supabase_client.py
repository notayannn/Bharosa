from supabase import create_client, Client

from app.core.config import settings


def get_supabase_client(user_jwt: str) -> Client:
    """
    Returns a Supabase client authenticated AS the calling user (using their
    own JWT, not the secret key). This means every query automatically goes
    through RLS as that specific user — the database enforces business_id
    scoping, not application code.
    """
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_PUBLISHABLE_KEY)
    client.postgrest.auth(user_jwt)
    return client