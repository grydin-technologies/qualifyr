"""Per-user API key encryption and resolution.

Keys are stored encrypted (Fernet symmetric) in the user_api_keys table.
Resolution priority: user's own key (DB) > operator key (env var).
"""

from __future__ import annotations

import logging
import os

from cryptography.fernet import Fernet, InvalidToken

from gtm_engine.storage.database import Database

log = logging.getLogger(__name__)

ALLOWED_KEYS = frozenset({"brave", "groq", "gemini", "hunter", "places"})

_ENV_MAP = {
    "brave": "GTM_BRAVE_API_KEY",
    "groq": "GTM_GROQ_API_KEY",
    "gemini": "GTM_GEMINI_API_KEY",
    "hunter": "GTM_HUNTER_API_KEY",
    "places": "GTM_GOOGLE_PLACES_API_KEY",
}


def _fernet() -> Fernet | None:
    key = os.environ.get("GTM_ENCRYPTION_KEY")
    if not key:
        return None
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_key(plaintext: str) -> str:
    f = _fernet()
    if f is None:
        raise RuntimeError("GTM_ENCRYPTION_KEY is not set – cannot encrypt API keys")
    return f.encrypt(plaintext.encode()).decode()


def decrypt_key(ciphertext: str) -> str:
    f = _fernet()
    if f is None:
        raise RuntimeError("GTM_ENCRYPTION_KEY is not set – cannot decrypt API keys")
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        raise ValueError("failed to decrypt API key – encryption key may have changed")


def encryption_available() -> bool:
    return os.environ.get("GTM_ENCRYPTION_KEY") is not None


def resolve_api_key(db: Database, user_id: str | None, key_name: str) -> str | None:
    """Resolve an API key: user DB key first, then operator env var."""
    if user_id and encryption_available():
        encrypted = db.get_user_key(user_id, key_name)
        if encrypted:
            try:
                return decrypt_key(encrypted)
            except (ValueError, RuntimeError):
                log.warning("failed to decrypt user key %s for %s; falling back to env", key_name, user_id)
    return os.environ.get(_ENV_MAP.get(key_name, f"GTM_{key_name.upper()}_API_KEY"))


def resolve_all_keys(db: Database, user_id: str | None) -> dict[str, str | None]:
    """Resolve all API keys at once for a pipeline run."""
    return {name: resolve_api_key(db, user_id, name) for name in ALLOWED_KEYS}
