from decimal import Decimal

from app.providers.payments.base import PaymentProvider, PaymentStatus


class ManualPaymentProvider(PaymentProvider):
    """
    Phase 1 default. No real money movement, no gateway account needed.
    The client (or owner, on the client's behalf) uploads a payment slip;
    the Reconciliation Agent matches it against the open invoice via OCR +
    fuzzy matching, not via a gateway callback.

    Status transitions happen by direct calls from the API layer:
      - a slip upload -> mark_submitted()
      - Reconciliation Agent confirms match -> mark_verified() (done at the
        DB layer via the `payments` table, not inside this class — this
        class has no DB access by design, keeping it a pure interface
        implementation that's trivial to test in isolation)
    """

    def create_payment_request(self, invoice_id: str, amount: Decimal) -> dict:
        return {
            "provider": "manual",
            "invoice_id": invoice_id,
            "amount": str(amount),
            "instructions": (
                "Pay via bank transfer or your usual method, then upload a "
                "photo of the payment slip/receipt in the client portal."
            ),
        }

    def get_status(self, payment_reference: str) -> PaymentStatus:
        # Manual provider doesn't track status itself — the `payments` table
        # row (verified boolean) is the actual source of truth. This method
        # exists to satisfy the interface for callers that don't care which
        # provider they're talking to; real implementation queries the DB
        # via the calling service layer, not here.
        raise NotImplementedError(
            "Query the `payments` table directly for manual payment status."
        )

    def verify_webhook(self, payload: bytes, headers: dict) -> bool:
        return False  # no webhooks for manual payments