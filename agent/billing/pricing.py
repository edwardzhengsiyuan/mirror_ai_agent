"""Endpoint pricing table (in credits).

Loaded from ``config/pricing.json`` at startup. Each endpoint has a base
price; specific request shapes (e.g. ``include_star_gong=true``) can override
the base via the ``variants`` block.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, Optional, Tuple


DEFAULT_PRICING_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "config",
    "pricing.json",
)


def _variant_key(endpoint: str, params: Iterable[Tuple[str, Any]]) -> str:
    """Build a deterministic variant lookup key.

    ``params`` may be empty. Order does not matter — keys are sorted for
    deterministic lookup. Boolean values are normalized to lowercase
    ``true``/``false`` so JSON ``True`` and string ``"true"`` collide.
    """
    if not params:
        return endpoint
    parts = []
    for name, value in sorted(params, key=lambda x: x[0]):
        if isinstance(value, bool):
            value_str = "true" if value else "false"
        else:
            value_str = str(value).lower()
        parts.append(f"{name}={value_str}")
    return f"{endpoint}?{'&'.join(parts)}"


class Pricing:
    def __init__(
        self,
        default_credits: int,
        endpoints: Dict[str, int],
        variants: Optional[Dict[str, int]] = None,
    ) -> None:
        self.default_credits = int(default_credits)
        self.endpoints = {k: int(v) for k, v in endpoints.items()}
        self.variants = {k: int(v) for k, v in (variants or {}).items()}

    @classmethod
    def load(cls, path: Optional[str] = None) -> "Pricing":
        path = path or DEFAULT_PRICING_PATH
        if not os.path.exists(path):
            return cls(default_credits=50, endpoints={}, variants={})
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            default_credits=int(data.get("default_credits", 50)),
            endpoints=data.get("endpoints", {}) or {},
            variants=data.get("variants", {}) or {},
        )

    def cost(
        self,
        endpoint: str,
        variant_params: Optional[Iterable[Tuple[str, Any]]] = None,
    ) -> int:
        """Resolve the price for an endpoint call.

        Lookup precedence:
        1. ``variants`` exact match for ``endpoint?param=val[&...]``.
        2. ``endpoints`` entry for the bare endpoint.
        3. ``default_credits``.
        """
        if variant_params:
            key = _variant_key(endpoint, variant_params)
            if key in self.variants:
                return self.variants[key]
        if endpoint in self.endpoints:
            return self.endpoints[endpoint]
        return self.default_credits

    def as_dict(self) -> Dict[str, Any]:
        return {
            "default_credits": self.default_credits,
            "endpoints": dict(self.endpoints),
            "variants": dict(self.variants),
        }
