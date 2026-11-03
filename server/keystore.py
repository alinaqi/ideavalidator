"""Per-session Palgu key + account store for the hosted MCP server (bring-your-own-Palgu). Holds the
minted key and the resolved account id (hash of the Palgu email) keyed by MCP session id; never logs the
key. In-memory for v0.1. `settings_for` builds a pipeline Settings on a key.
"""
from __future__ import annotations

from pathlib import Path

from pipeline.config import Settings


class KeyStore:
    def __init__(self) -> None:
        self._keys: dict[str, str] = {}
        self._accounts: dict[str, str] = {}

    def set(self, session_id: str, key: str) -> None:
        self._keys[session_id] = key

    def get(self, session_id: str) -> str | None:
        return self._keys.get(session_id)

    def has(self, session_id: str) -> bool:
        return bool(self._keys.get(session_id))

    def clear(self, session_id: str) -> None:
        self._keys.pop(session_id, None)
        self._accounts.pop(session_id, None)

    def set_account(self, session_id: str, account: str) -> None:
        self._accounts[session_id] = account

    def account(self, session_id: str) -> str:
        return self._accounts.get(session_id, "")


def settings_for(key: str, root) -> Settings:
    return Settings._palgu(key, {}, Path(root))
