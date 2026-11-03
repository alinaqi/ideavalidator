"""Per-session Palgu key store for the hosted MCP server (bring-your-own-Palgu). The caller signs in to
their own Palgu inside the session; we hold the minted key keyed by the MCP session id and never log it.
In-memory for v0.1 (a restart drops sessions). `settings_for` builds a pipeline Settings on that key.
"""
from __future__ import annotations

from pathlib import Path

from pipeline.config import Settings


class KeyStore:
    def __init__(self) -> None:
        self._keys: dict[str, str] = {}

    def set(self, session_id: str, key: str) -> None:
        self._keys[session_id] = key

    def get(self, session_id: str) -> str | None:
        return self._keys.get(session_id)

    def has(self, session_id: str) -> bool:
        return bool(self._keys.get(session_id))

    def clear(self, session_id: str) -> None:
        self._keys.pop(session_id, None)


def settings_for(key: str, root) -> Settings:
    return Settings._palgu(key, {}, Path(root))
