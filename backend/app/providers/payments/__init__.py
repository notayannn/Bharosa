from app.core.config import settings
from app.providers.payments.base import PaymentProvider, PaymentStatus
from app.providers.payments.manual import ManualPaymentProvider

__all__ = ["PaymentProvider", "PaymentStatus", "get_payment_provider"]

_PROVIDERS = {
    "manual": ManualPaymentProvider,
}


def get_payment_provider() -> PaymentProvider:
    provider_cls = _PROVIDERS.get(settings.PAYMENT_PROVIDER)
    if provider_cls is None:
        raise ValueError(f"Unknown PAYMENT_PROVIDER: {settings.PAYMENT_PROVIDER}")
    return provider_cls()