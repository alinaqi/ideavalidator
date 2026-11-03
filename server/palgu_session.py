"""Palgu device-code sign-in for a hosted MCP session (bring-your-own-Palgu). `login_async` starts the
device flow, returns the approve-at-palgu.ai URL + code immediately, and polls for approval on a
background thread, storing the minted key in the per-session key store. Reuses the pure logic in
`pipeline.palgu` and the injectable HTTP in `pipeline.palgu_run`, so the poll is unit-testable.
"""
from __future__ import annotations

import random
import socket
import sys
import threading
import time
from dataclasses import dataclass

from pipeline import palgu, palgu_run, palgu_text
from .keystore import KeyStore


@dataclass
class DeviceLogin:
    keystore: KeyStore
    http: object = None
    sleep: object = None

    def _client(self):
        return self.http or palgu_run._Http()

    def start(self) -> dict:
        body = palgu.device_body(palgu.device_name(socket.gethostname()),
                                 palgu.new_install_id(random.random), sys.platform)
        return (self._client().post("/auth/device/code", body).get("body")) or {}

    def poll(self, session_id: str, start: dict) -> bool:
        http, sleep = self._client(), (self.sleep or time.sleep)
        interval, waited, deadline = int(start.get("interval") or 5), 0, int(start.get("expires_in") or 600)
        while waited < deadline:
            step = palgu.token_step(http.post("/auth/token", palgu.token_body(start["device_code"])), interval)
            if step["state"] == "ok":
                self.keystore.set(session_id, step["key"])
                return True
            if step["state"] == "stop":
                return False
            interval = step["interval"]; sleep(interval); waited += interval
        return False

    def login_async(self, session_id: str) -> dict:
        start = self.start()
        if not start.get("device_code"):
            return {"ok": False, "text": "Palgu sign-in could not start; try again.", "thread": None}
        thread = threading.Thread(target=self.poll, args=(session_id, start), daemon=True)
        thread.start()
        return {"ok": True, "text": palgu_text.start_text(start), "thread": thread}

    def status(self, session_id: str) -> str:
        key = self.keystore.get(session_id)
        if not key:
            return palgu_text.status_text(None)
        res = self._client().get("/me", key)
        return palgu_text.status_text(res.get("body") if res.get("ok") else None)
