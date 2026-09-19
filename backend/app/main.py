from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response

from app.core.config import settings
from app.api import businesses, clients, invoices, payments, disputes, chatbot, approvals
from app.api import escal as escalation
from app.scheduler import start_scheduler
from app.api import businesses, clients, invoices, payments, disputes, chatbot, approvals, documents
from app.api import escal as escalation
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

app = FastAPI(title="Bharosa API", version="0.1.0")


@app.on_event("startup")
def on_startup():
    start_scheduler()

@app.get("/client")
def serve_client_page():
    return FileResponse("../frontend/client.html")


@app.get("/chat")
def serve_chat_page():
    return FileResponse("../frontend/chat.html")


@app.get("/health")
def health():
    return {"status": "ok"}


#CRUD routes
app.include_router(businesses.router, prefix="/api/businesses", tags=["businesses"])
app.include_router(clients.router, prefix="/api/clients", tags=["clients"])
app.include_router(invoices.router, prefix="/api/invoices", tags=["invoices"])
app.include_router(payments.router, prefix="/api/payments", tags=["payments"])
app.include_router(escalation.router, prefix="/api/escalation", tags=["escalation"])
app.include_router(disputes.router, prefix="/api/disputes", tags=["disputes"])
app.include_router(chatbot.router, prefix="/api/chatbot", tags=["chatbot"])
app.include_router(approvals.router, prefix="/api/approvals", tags=["approvals"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])

@app.get("/js/config.js")
def serve_config():
    js = (
        f'window.__ENV__ = {{'
        f'SUPABASE_URL: "{settings.SUPABASE_URL}", '
        f'SUPABASE_PUBLISHABLE_KEY: "{settings.SUPABASE_PUBLISHABLE_KEY}"'
        f'}};'
    )
    return Response(content=js, media_type="application/javascript")


app.mount("/css", StaticFiles(directory="../frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="../frontend/js"), name="js")


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