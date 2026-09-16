from abc import ABC, abstractmethod
from decimal import Decimal
from enum import Enum


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    FAILED = "failed"


class PaymentProvider(ABC):

    @abstractmethod
    def create_payment_request(self, invoice_id: str, amount: Decimal) -> dict:

        raise NotImplementedError

    @abstractmethod
    def get_status(self, payment_reference: str) -> PaymentStatus:
        raise NotImplementedError

    @abstractmethod
    def verify_webhook(self, payload: bytes, headers: dict) -> bool:

        raise NotImplementedError