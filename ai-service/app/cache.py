"""Tenant-isolated, cryptographic response cache for Project Atlas.

Guarantees zero cross-client leakage by partitioning cache keys on:
- client_id
- client's entitled report fingerprint
- normalized query text
"""

import hashlib
import time
from typing import Any


class ResponseCache:
    def __init__(self, max_entries: int = 1000, ttl_seconds: int = 3600):
        self._max_entries = max_entries
        self._ttl_seconds = ttl_seconds
        self._cache: dict[str, dict[str, Any]] = {}

    def _make_key(self, client_id: str, question: str, allowed_reports: set[str]) -> str:
        normalized_q = " ".join(question.strip().lower().split())
        entitlements_hash = ",".join(sorted(allowed_reports))
        payload = f"{client_id}:{entitlements_hash}:{normalized_q}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, client_id: str, question: str, allowed_reports: set[str]) -> dict[str, Any] | None:
        key = self._make_key(client_id, question, allowed_reports)
        entry = self._cache.get(key)
        if not entry:
            return None
        if time.time() > entry["expires_at"]:
            self._cache.pop(key, None)
            return None
        return entry["data"]

    def set(self, client_id: str, question: str, allowed_reports: set[str], data: dict[str, Any]) -> None:
        # Never cache empty, escalated, or error answers
        if not data or data.get("escalation_reason") or not data.get("answer"):
            return
        if len(self._cache) >= self._max_entries:
            # Evict oldest entry (simple FIFO / LRU approximation)
            oldest_key = next(iter(self._cache))
            self._cache.pop(oldest_key, None)
        key = self._make_key(client_id, question, allowed_reports)
        self._cache[key] = {
            "expires_at": time.time() + self._ttl_seconds,
            "data": dict(data),
        }

    def clear(self) -> None:
        self._cache.clear()

    def size(self) -> int:
        return len(self._cache)


response_cache = ResponseCache()
