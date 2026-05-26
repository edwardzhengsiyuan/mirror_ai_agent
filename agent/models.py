"""Model constants for LLM configuration.

The authoritative model catalog lives in config/llm_routes.json. Keep this
module as a compatibility shim for older imports.
"""

try:
    from .llm_config import available_models, default_model

    DEFAULT_MODEL = default_model()
    AVAILABLE_MODELS = available_models()
except Exception:
    DEFAULT_MODEL = "gemini-3.1-pro-preview"
    AVAILABLE_MODELS = [DEFAULT_MODEL]
