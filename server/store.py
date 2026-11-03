"""Disk-backed run store so a hosted agent can read a validation across sessions. Runs are keyed by Palgu
**account** (a non-reversible hash of the account email) under IV_STORE, so get_status / get_report /
list_runs work in a brand-new session with the same account. Each run is a dir with a meta.json.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path


def account_id(email) -> str:
    return hashlib.sha256((email or "anon").encode()).hexdigest()[:16]


@dataclass(frozen=True)
class RunRef:
    account_id: str
    run_id: str


class RunStore:
    def __init__(self, root) -> None:
        self.root = Path(root)

    def path(self, ref: RunRef) -> Path:
        return self.root / ref.account_id / ref.run_id

    def _write(self, ref: RunRef, meta: dict) -> None:
        d = self.path(ref)
        d.mkdir(parents=True, exist_ok=True)
        (d / "meta.json").write_text(json.dumps(meta))

    def create(self, account: str, slug: str) -> tuple:
        ref = RunRef(account, uuid.uuid4().hex[:12])
        meta = {"run_id": ref.run_id, "slug": slug, "state": "pending",
                "stages": [], "cancel": False, "created": time.time()}
        self._write(ref, meta)
        return ref, meta

    def get(self, ref: RunRef) -> dict | None:
        p = self.path(ref) / "meta.json"
        return json.loads(p.read_text()) if p.exists() else None

    def list(self, account: str) -> list:
        base = self.root / account
        metas = [json.loads(m.read_text()) for m in base.glob("*/meta.json")] if base.exists() else []
        return sorted(metas, key=lambda m: m.get("created", 0), reverse=True)

    def update(self, ref: RunRef, fields: dict) -> dict | None:
        meta = self.get(ref)
        if meta is None:
            return None
        meta.update(fields)
        self._write(ref, meta)
        return meta

    def record_stage(self, ref: RunRef, step: dict) -> None:
        meta = self.get(ref)
        if meta is not None:
            meta["stages"].append(step)
            self._write(ref, meta)
