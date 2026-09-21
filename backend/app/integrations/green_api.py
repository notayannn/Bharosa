"""
Green API integration -- WhatsApp messaging via a real linked WhatsApp
number (not Meta's official Business API). See green-api.com docs.
"""
import requests

from app.core.config import settings

_BASE_URL = f"https://api.green-api.com/waInstance{settings.GREENAPI_INSTANCE_ID}"


def get_qr_code() -> dict:
    """
    Fetches the QR code needed to link a WhatsApp number to this instance.
    Returns {"status": "needs_scan", "qr_base64": "..."} or
    {"status": "already_linked"} if a number is already connected.
    """
    url = f"{_BASE_URL}/qr/{settings.GREENAPI_TOKEN_ID}"
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    data = response.json()

    if data.get("type") == "alreadyLogged":
        return {"status": "already_linked"}
    if data.get("type") == "qrCode" and data.get("message"):
        return {"status": "needs_scan", "qr_base64": data["message"]}
    return {"status": "error", "detail": data}


def get_instance_state() -> str:
    """Returns the raw instance state string, e.g. 'authorized' or 'notAuthorized'."""
    url = f"{_BASE_URL}/getStateInstance/{settings.GREENAPI_TOKEN_ID}"
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return response.json().get("stateInstance", "unknown")

def send_whatsapp_message(phone: str, message: str) -> dict:
    """
    Sends a WhatsApp text message via the linked number. `phone` should be
    digits only with country code, no + or spaces (e.g. "923001234567").
    """
    digits_only = "".join(ch for ch in phone if ch.isdigit())
    chat_id = f"{digits_only}@c.us"

    url = f"{_BASE_URL}/sendMessage/{settings.GREENAPI_TOKEN_ID}"
    response = requests.post(url, json={"chatId": chat_id, "message": message}, timeout=15)
    response.raise_for_status()
    return response.json()