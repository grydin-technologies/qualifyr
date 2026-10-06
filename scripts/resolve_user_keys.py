"""Resolve a user's encrypted API keys from Supabase and write them to $GITHUB_ENV.

Called by gather-leads.yml before the campaign run so the engine picks up
the user's own keys instead of (absent) repo-level secrets.

Usage: python scripts/resolve_user_keys.py <user_id>
"""

from __future__ import annotations

import os
import sys

from gtm_engine.api.keys import ALLOWED_KEYS, _ENV_MAP, decrypt_key, encryption_available
from gtm_engine.storage.database import Database


def main() -> None:
    user_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not user_id:
        print("no user_id provided – skipping key resolution")
        return

    if not encryption_available():
        print("GTM_ENCRYPTION_KEY not set – cannot decrypt user keys")
        sys.exit(1)

    db_url = os.environ.get("GTM_DATABASE_URL")
    if not db_url:
        print("GTM_DATABASE_URL not set")
        sys.exit(1)

    db = Database(db_url)
    github_env = os.environ.get("GITHUB_ENV")
    resolved = 0

    for key_name in ALLOWED_KEYS:
        encrypted = db.get_user_key(user_id, key_name)
        if not encrypted:
            continue
        try:
            plaintext = decrypt_key(encrypted)
        except (ValueError, RuntimeError) as exc:
            print(f"warning: could not decrypt {key_name}: {exc}")
            continue

        env_var = _ENV_MAP.get(key_name, f"GTM_{key_name.upper()}_API_KEY")
        if github_env:
            with open(github_env, "a") as f:
                f.write(f"{env_var}={plaintext}\n")
        else:
            os.environ[env_var] = plaintext
        resolved += 1
        print(f"resolved {key_name} -> {env_var}")

    db.close()
    print(f"resolved {resolved}/{len(ALLOWED_KEYS)} keys for user {user_id[:8]}...")


if __name__ == "__main__":
    main()
