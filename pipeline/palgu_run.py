"""Palgu device sign-in over the network + CLI glue. Writes the minted key to the repo .env as
PALGU_API_KEY (gitignored, mode 600). HTTP is injectable so the login loop is testable without a network.
"""
from __future__ import annotations

import json
import random
import socket
import time
import urllib.request
from pathlib import Path

from . import palgu
from .config import load_env


class _Http:
    def post(self, path: str, body: dict) -> dict:
        data = json.dumps(body).encode()
        req = urllib.request.Request(palgu.PALGU_ORIGIN + path, data=data, method="POST",
                                     headers={"content-type": "application/json"})
        return self._send(req)

    def get(self, path: str, key: str) -> dict:
        req = urllib.request.Request(palgu.PALGU_ORIGIN + path,
                                     headers={"authorization": "Bearer " + key})
        return self._send(req)

    def _send(self, req) -> dict:
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return {"ok": resp.status < 400, "status": resp.status, "body": json.loads(resp.read().decode())}
        except Exception as exc:
            code = getattr(exc, "code", 0)
            body = {}
            try:
                body = json.loads(exc.read().decode())  # type: ignore[attr-defined]
            except Exception:
                pass
            return {"ok": False, "status": code, "body": body}


def write_key(root: Path, key: str) -> None:
    path = root / ".env"
    lines = [ln for ln in (path.read_text().splitlines() if path.exists() else [])
             if not ln.startswith("PALGU_API_KEY=")]
    lines.append(f"PALGU_API_KEY={key}")
    path.write_text("\n".join(lines) + "\n")
    path.chmod(0o600)


def login(root: Path, http=None, sleep=None) -> int:
    http, sleep = http or _Http(), sleep or time.sleep
    body = palgu.device_body(palgu.device_name(socket.gethostname()), palgu.new_install_id(random.random))
    start = (http.post("/auth/device/code", body).get("body")) or {}
    if not start.get("device_code"):
        print("Palgu sign-in could not start; paste PALGU_API_KEY into .env instead.")
        return 1
    print(palgu.start_text(start))
    interval, waited, deadline = int(start.get("interval") or 5), 0, int(start.get("expires_in") or 600)
    while waited < deadline:
        step = palgu.token_step(http.post("/auth/token", palgu.token_body(start["device_code"])), interval)
        if step["state"] == "ok":
            write_key(root, step["key"]); print(palgu.signed_in_text(step)); return 0
        if step["state"] == "stop":
            print("Palgu: " + step["reason"]); return 1
        interval = step["interval"]; sleep(interval); waited += interval
    print("Palgu sign-in timed out.")
    return 1


def status(root: Path, http=None) -> int:
    key = load_env(root / ".env").get("PALGU_API_KEY")
    if not key:
        print(palgu.status_text(None)); return 0
    res = (http or _Http()).get("/me", key)
    print(palgu.status_text(res.get("body") if res.get("ok") else None))
    return 0


def run_palgu_cmd(args, root: Path) -> int:
    action = palgu.parse_arg(getattr(args, "action", ""))
    if action == "login":
        return login(root)
    if action == "status":
        return status(root)
    if action == "upgrade":
        print("Palgu plans and billing: " + palgu.PALGU_BILLING); return 0
    print(palgu.HELP)
    return 0
