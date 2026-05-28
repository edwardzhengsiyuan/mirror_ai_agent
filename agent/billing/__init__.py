"""Billing module: credit balances, API keys, per-endpoint charging.

Public entry point is :class:`BillingService`. The Flask-facing helpers live
in :mod:`agent.billing.middleware`.
"""

from .errors import (
    BillingError,
    DailyLimitExceededError,
    InsufficientFundsError,
    UnknownUserError,
    UnknownApiKeyError,
    DuplicateRequestError,
    InflightLimitError,
    RateLimitError,
)
from .pricing import Pricing
from .service import BillingService, ChargeReceipt
from .store import BillingStore, EmailAlreadyRegisteredError
from .stripe_gateway import (
    StripeGateway,
    StripeNotConfiguredError,
    StripeSignatureError,
    TopupPack,
    TopupPackConfig,
    load_pack_config,
)

__all__ = [
    "BillingService",
    "BillingStore",
    "ChargeReceipt",
    "Pricing",
    "StripeGateway",
    "StripeNotConfiguredError",
    "StripeSignatureError",
    "TopupPack",
    "TopupPackConfig",
    "load_pack_config",
    "BillingError",
    "DailyLimitExceededError",
    "InsufficientFundsError",
    "UnknownUserError",
    "UnknownApiKeyError",
    "DuplicateRequestError",
    "InflightLimitError",
    "RateLimitError",
    "EmailAlreadyRegisteredError",
]
