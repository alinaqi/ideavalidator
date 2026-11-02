"""Human-readable strings for the Palgu device sign-in flow, split out of palgu.py to keep that module
within the functions-per-file limit. Pure formatting; re-exported from palgu for a stable interface.
"""
from __future__ import annotations

from .palgu import PALGU_BILLING, PALGU_WEB


def start_text(start: dict) -> str:
    minutes = round((int(start.get("expires_in") or 600)) / 60)
    code = start.get("user_code", "")
    return (f"Open {PALGU_WEB}/connect?code={code} and approve code {code} (new to Palgu? sign up there). "
            f"The code expires in {minutes} minutes; this run picks up the key once you approve.")


def signed_in_text(s: dict) -> str:
    tail = f" ({s['org']}{', plan ' + s['plan'] if s.get('plan') else ''})" if s.get("org") else ""
    return f"Signed in to Palgu as {s['email']}{tail}. ideavalidator now runs on Palgu."


def status_text(me) -> str:
    if not me:
        return "Palgu: not signed in. Run `palgu login` to sign up or sign in from here."
    acc, org = me.get("account") or {}, me.get("org") or {}
    return (f"Palgu: signed in as {acc.get('email', '?')} ({org.get('name', '?')}, "
            f"plan {org.get('plan', '?')}) · upgrade: {PALGU_BILLING}")
