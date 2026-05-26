"""LLM provider and per-node routing configuration."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any, Dict

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
DEFAULT_ROUTE_CONFIG = os.path.join(REPO_ROOT, "config", "llm_routes.json")
FALLBACK_DEFAULT_MODEL = "gemini-3-pro-preview"


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=4)
def load_llm_routes(path: str | None = None) -> Dict[str, Any]:
    config_path = path or os.environ.get("LLM_ROUTE_CONFIG") or DEFAULT_ROUTE_CONFIG
    if not os.path.isabs(config_path):
        config_path = os.path.join(REPO_ROOT, config_path)
    if not os.path.exists(config_path):
        return {}
    return _load_json(config_path)


def reset_llm_routes_cache() -> None:
    load_llm_routes.cache_clear()


def available_models() -> list[str]:
    routes = load_llm_routes()
    models = routes.get("models", [])
    if isinstance(models, list):
        ids = []
        for item in models:
            if isinstance(item, dict) and item.get("id"):
                ids.append(str(item["id"]))
            elif isinstance(item, str):
                ids.append(item)
        if ids:
            return ids
    return [FALLBACK_DEFAULT_MODEL]


def default_model() -> str:
    routes = load_llm_routes()
    default_route = routes.get("default", {}) if isinstance(routes.get("default"), dict) else {}
    model = default_route.get("model") or os.environ.get("LLM_MODEL") or FALLBACK_DEFAULT_MODEL
    model_name = str(model)
    if model_name not in available_models():
        return FALLBACK_DEFAULT_MODEL
    return model_name


def configurable_nodes() -> list[str]:
    routes = load_llm_routes()
    nodes = routes.get("configurable_nodes", [])
    if isinstance(nodes, list):
        return [str(node) for node in nodes if node]
    node_routes = routes.get("nodes", {}) if isinstance(routes.get("nodes"), dict) else {}
    return sorted(str(node) for node in node_routes)


def validate_model(model: str | None) -> bool:
    return not model or model in available_models()


def _provider_for_model(routes: Dict[str, Any], model: str) -> str | None:
    model_catalog = routes.get("models", []) if isinstance(routes.get("models"), list) else []
    for item in model_catalog:
        if isinstance(item, dict) and item.get("id") == model and item.get("provider"):
            return str(item.get("provider"))
    return None


def resolve_llm_settings(
    node: str,
    requested_model: str | None = None,
    node_model_overrides: Dict[str, str] | None = None,
) -> Dict[str, str | None]:
    """Resolve provider credentials and model for an LLM node."""
    if os.environ.get("LLM_ROUTING_ENABLED", "1").lower() in ("0", "false", "no"):
        model_name = requested_model or os.environ.get("LLM_MODEL") or default_model()
        return {
            "provider": "legacy",
            "model": model_name,
            "api_base": os.environ.get("LLM_API_BASE") or os.environ.get("OPENAI_API_BASE"),
            "api_key": os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY"),
            "authorization_scheme": "Bearer",
        }

    routes = load_llm_routes()
    default_route = routes.get("default", {}) if isinstance(routes.get("default"), dict) else {}
    node_name = str(node or "").upper()
    node_routes = routes.get("nodes", {}) if isinstance(routes.get("nodes"), dict) else {}
    node_route = node_routes.get(node_name, {}) if isinstance(node_routes.get(node_name), dict) else {}
    override_model = None
    if isinstance(node_model_overrides, dict):
        for key, value in node_model_overrides.items():
            if str(key).upper() == node_name and value:
                override_model = str(value)
                break

    model_name = str(
        override_model
        or node_route.get("model")
        or requested_model
        or default_route.get("model")
        or os.environ.get("LLM_MODEL")
        or FALLBACK_DEFAULT_MODEL
    )
    if not validate_model(model_name):
        model_name = default_model()

    provider_name = node_route.get("provider") or default_route.get("provider")
    provider_name = _provider_for_model(routes, model_name) or provider_name
    providers = routes.get("providers", {}) if isinstance(routes.get("providers"), dict) else {}
    provider = providers.get(provider_name, {}) if isinstance(providers.get(provider_name), dict) else {}

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
