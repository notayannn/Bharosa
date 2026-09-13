from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response

from app.core.config import settings
from app.api import businesses, clients, invoices
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.api import businesses, clients, invoices, payments

app = FastAPI(title="Bharosa API", version="0.1.0")

app.include_router(payments.router, prefix="/api/payments", tags=["payments"])


@app.get("/health")
def health():
    return {"status": "ok"}


# CRUD routes
app.include_router(businesses.router, prefix="/api/businesses", tags=["businesses"])
app.include_router(clients.router, prefix="/api/clients", tags=["clients"])
app.include_router(invoices.router, prefix="/api/invoices", tags=["invoices"])


@app.get("/js/config.js")
def serve_config():
    """
    Generates a tiny JS file at request time from backend env vars, so the
    frontend never hardcodes secrets and .env stays the single source of
    truth. Only exposes the PUBLISHABLE key — same one that was always
    safe to expose client-side — never the secret key.

    Defined BEFORE the /js static mount below so this specific route wins
    over the general static file handler for the same path.
    """
    js = (
        f'window.__ENV__ = {{'
        f'SUPABASE_URL: "{settings.SUPABASE_URL}", '
        f'SUPABASE_PUBLISHABLE_KEY: "{settings.SUPABASE_PUBLISHABLE_KEY}"'
        f'}};'
    )
    return Response(content=js, media_type="application/javascript")


# Serve the frontend's CSS/JS as static assets
app.mount("/css", StaticFiles(directory="../frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="../frontend/js"), name="js")


# Serve each HTML page directly — explicit routes rather than a blanket
# static mount, so clean URLs work (e.g. /dashboard instead of /dashboard.html)
@app.get("/")
def serve_index():
    return FileResponse("../frontend/index.html")


@app.get("/dashboard")
def serve_dashboard():
    return FileResponse("../frontend/dashboard.html")


@app.get("/clients")
def serve_clients_page():
    return FileResponse("../frontend/clients.html")


@app.get("/invoice")
def serve_invoice_page():
    return FileResponse("../frontend/invoice.html")