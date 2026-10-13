from __future__ import annotations

import hashlib
import hmac


def hash_order_access_key(access_key: str) -> str:
    return hashlib.sha256(access_key.encode()).hexdigest()


def valid_order_access_key(access_key: str | None, stored_hash: str | None) -> bool:
    if not access_key or not stored_hash:
        return False
    return hmac.compare_digest(hash_order_access_key(access_key), stored_hash)
