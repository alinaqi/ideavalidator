"""Palgu device-code sign-in (RFC 8628), ported from mixture-of-models. Pure logic only — the network
calls live in palgu_run. Sign up / sign in once and ideavalidator runs on a single Palgu key instead of
your own GEMINI_API_KEY + council provider keys. The key is only ever sent to api.palgu.ai.
"""
from __future__ import annotations

CLIENT_ID = "ideavalidator"
CLIENT_VERSION = "0.1.0"
PALGU_ORIGIN = "https://api.palgu.ai"
PALGU_V1 = PALGU_ORIGIN + "/v1"
PALGU_WEB = "https://www.palgu.ai"
PALGU_BILLING = PALGU_WEB + "/billing"
_DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"

HELP = ("/palgu login: sign up or sign in to Palgu and run ideavalidator on its key · "
        "/palgu status: who is signed in, on which plan · /palgu upgrade: plans and billing")

_STOPS = {
    "expired_token": "the code expired: run `palgu login` again",
    "access_denied": "sign-in was denied on the web",
    "invalid_grant": "the code is unknown or was already used: run `palgu login` again",
}


def is_palgu(url: str) -> bool:
    u = str(url or "")
    return u == PALGU_ORIGIN or u.startswith(PALGU_ORIGIN + "/")


def parse_arg(arg: str) -> str:
    word = str(arg or "").strip().lower()
    return word if word in ("login", "status", "upgrade") else "help"


def device_name(host: str) -> str:
    clean = "".join(c for c in str(host or "") if c >= " " and c not in "<>\x7f").strip()
    return ("Claude Code on " + clean if clean else "Claude Code")[:64]


def new_install_id(random) -> str:
    hx = lambda n: "".join("0123456789abcdef"[int(random() * 16)] for _ in range(n))
    variant = "0123456789abcdef"[(int(random() * 16) & 0x3) | 0x8]
    return f"{hx(8)}-{hx(4)}-4{hx(3)}-{variant}{hx(3)}-{hx(12)}"


def platform_tag(sys_platform: str) -> str:
    tag = str(sys_platform or "").lower()
    if tag.startswith("darwin"):
        return "darwin"
    return "win32" if tag.startswith("win") else "linux"


def device_body(name: str, install_id: str, platform: str) -> dict:
    device = {"name": name, "platform": platform_tag(platform),
              "client_version": CLIENT_VERSION, "install_id": install_id}
    return {"client_id": CLIENT_ID, "device": device}


def token_body(device_code: str) -> dict:
    return {"grant_type": _DEVICE_GRANT, "client_id": CLIENT_ID, "device_code": device_code}


def _signed_in(body: dict) -> dict:
    acc, org = body.get("account") or {}, body.get("org") or {}
    return {"state": "ok", "key": body.get("access_token"), "email": acc.get("email", ""),
            "org": org.get("name", ""), "plan": org.get("plan", "")}


def token_step(res: dict, interval: int) -> dict:
    """One answer from POST /auth/token: keep waiting, stop with a reason, or the minted key."""
    body = res.get("body") or {}
    if res.get("ok"):
        key = body.get("access_token")
        return _signed_in(body) if isinstance(key, str) and key else {"state": "stop", "reason": "Palgu answered without a key"}
    err = body.get("error")
    if err == "authorization_pending":
        return {"state": "wait", "interval": interval}
    if err == "slow_down":
        return {"state": "wait", "interval": interval + 5}
    return {"state": "stop", "reason": _STOPS.get(err, f"Palgu answered {res.get('status')}")}
