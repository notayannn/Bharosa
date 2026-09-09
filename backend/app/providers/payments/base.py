from abc import ABC, abstractmethod
from decimal import Decimal
from enum import Enum


class PaymentStatus(str, Enum):
    PENDING = "pending"       # request created, no payment seen yet
    SUBMITTED = "submitted"   # payer claims they've paid (slip uploaded / manual mark)
    VERIFIED = "verified"     # confirmed — triggers Reconciliation Agent
    FAILED = "failed"


class PaymentProvider(ABC):
    """
    Every payment method (manual, JazzCash, Safepay, etc.) implements this
    same interface. The Reconciliation Agent and API routes only ever talk
    to this interface — never to a specific provider's SDK directly — so
    swapping or adding providers later never touches agent/orchestrator code.
    """

    @abstractmethod
    def create_payment_request(self, invoice_id: str, amount: Decimal) -> dict:
        """
        Called when an invoice is issued (or a client wants to pay).
        Returns a dict describing how the payer should proceed — for a real
        gateway this would include a hosted checkout URL; for manual, just
        instructions.
        """
        raise NotImplementedError

    @abstractmethod
    def get_status(self, payment_reference: str) -> PaymentStatus:
        """Look up the current status of a payment by its reference/id."""
        raise NotImplementedError

    @abstractmethod
    def verify_webhook(self, payload: bytes, headers: dict) -> bool:
        """
        Verify an inbound webhook's signature before trusting it.
        Manual provider has no webhooks, so it always returns False —
        callers should never expect this to be hit for ManualPaymentProvider.
        """
        raise NotImplementedError