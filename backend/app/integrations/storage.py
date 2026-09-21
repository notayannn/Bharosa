"""
Supabase Storage integration for uploaded payment slips. Replaces local
disk writes, which don't survive across most serverless/ephemeral hosts
and tie storage behavior to whichever host you deploy to.
"""
import uuid

from app.agents.ledger_agent import _get_admin_client

_BUCKET = "payment-slips"


def upload_slip(file_bytes: bytes, original_filename: str) -> str:
    """
    Uploads slip bytes to Supabase Storage and returns a public URL.
    Filename is UUID-prefixed to avoid collisions between clients.
    """
    ext = original_filename.rsplit(".", 1)[-1] if "." in original_filename else "jpg"
    storage_path = f"{uuid.uuid4()}.{ext}"

    client = _get_admin_client()
    client.storage.from_(_BUCKET).upload(
        storage_path, file_bytes, {"content-type": f"image/{ext}"}
    )
    return client.storage.from_(_BUCKET).get_public_url(storage_path)