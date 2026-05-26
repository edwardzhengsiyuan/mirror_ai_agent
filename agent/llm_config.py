"""LLM provider and per-node routing configuration."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any, Dict

from .models import DEFAULT_MODEL

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
DEFAULT_ROUTE_CONFIG = os.path.join(REPO_ROOT, "config", "llm_routes.json")


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=4)
def load_llm_routes(path: str | None = None) -> Dict[str, Any]:
    config_path = path or os.environ.get("LLM_ROUTE_CONFIG") or DEFAULT_ROUTE_CONFIG
    if not os.path.exists(config_path):
        return {}
    return _load_json(config_path)


def reset_llm_routes_cache() -> None:
    load_llm_routes.cache_clear()


def resolve_llm_settings(node: str, requested_model: str | None = None) -> Dict[str, str | None]:
    """Resolve provider credentials and model for an LLM node."""
    if os.environ.get("LLM_ROUTING_ENABLED", "1").lower() in ("0", "false", "no"):
        model_name = requested_model or os.environ.get("LLM_MODEL") or DEFAULT_MODEL
        return {
            "provider": "legacy",
            "model": model_name,
            "api_base": os.environ.get("LLM_API_BASE") or os.environ.get("OPENAI_API_BASE"),
            "api_key": os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY"),
            "authorization_scheme": "Bearer",
        }

    routes = load_llm_routes()
    default_route = routes.get("default", {}) if isinstance(routes.get("default"), dict) else {}
    node_routes = routes.get("nodes", {}) if isinstance(routes.get("nodes"), dict) else {}
    node_route = node_routes.get(node, {}) if isinstance(node_routes.get(node), dict) else {}

    provider_name = node_route.get("provider") or default_route.get("provider")
    providers = routes.get("providers", {}) if isinstance(routes.get("providers"), dict) else {}
    provider = providers.get(provider_name, {}) if isinstance(providers.get(provider_name), dict) else {}

    model_name = (
        node_route.get("model")
        or default_route.get("model")
        or requested_model
        or os.environ.get("LLM_MODEL")
        or DEFAULT_MODEL
    )

    api_base = None
    api_base_env = provider.get("api_base_env")
    if api_base_env:
        api_base = os.environ.get(str(api_base_env))
    api_base = api_base or provider.get("api_base") or provider.get("default_api_base")

    api_key = None
    api_key_env = provider.get("api_key_env")
    if api_key_env:
        api_key = os.environ.get(str(api_key_env))
    api_key = api_key or provider.get("api_key")

    if not api_base:
        api_base = os.environ.get("LLM_API_BASE") or os.environ.get("OPENAI_API_BASE")
    if not api_key:
        api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")

    return {
        "provider": str(provider_name or "legacy"),
        "model": str(model_name),
        "api_base": str(api_base) if api_base else None,
        "api_key": str(api_key) if api_key else None,
        "authorization_scheme": str(provider.get("authorization_scheme") or "Bearer"),
    }
