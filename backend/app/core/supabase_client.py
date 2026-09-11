from supabase import create_client, Client

from app.core.config import settings


def get_supabase_client(user_jwt: str) -> Client:
    """
    Returns a Supabase client authenticated AS the calling user (using their
    own JWT, not the secret key). This means every query automatically goes
    through RLS as that specific user — the database enforces business_id
    scoping, not application code. This is the client every CRUD route uses.

    Never use the secret-key client for routes a regular user calls — that
    bypasses RLS entirely and would let any authenticated user see/edit any
    business's data. The secret key is reserved for backend-only admin
    operations (e.g. the Orchestrator writing agent_actions across the
    system), which we'll build separately later.
    """
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_PUBLISHABLE_KEY)
    client.postgrest.auth(user_jwt)
    return client