"""Optional AI-generated imagery for HTML/PDF reports (Gemini image models).

Best-effort: returns None on any failure so a report never breaks for lack of an image. Charts are
drawn as deterministic inline SVG elsewhere; this is only for a cover/hero illustration."""
from __future__ import annotations

IMAGE_MODELS = ("gemini-3-pro-image-preview", "nano-banana-pro-preview", "gemini-2.5-flash-image")


def _parts(response):
    for cand in getattr(response, "candidates", None) or []:
        yield from getattr(getattr(cand, "content", None), "parts", None) or []


def _extract(response) -> bytes | None:
    for part in _parts(response):
        blob = getattr(getattr(part, "inline_data", None), "data", None)
        if blob:
            return blob
    return None


def _try_model(api, model: str, prompt: str) -> bytes | None:
    try:
        return _extract(api.models.generate_content(model=model, contents=prompt))
    except Exception:
        return None


def _client(settings):
    from google import genai

    return genai.Client(api_key=settings.api_key)


def generate_hero(prompt: str, client=None, settings=None) -> bytes | None:
    """Return PNG bytes for a hero image, or None. Pass a client (tests) or settings (real use)."""
    api = client or (_client(settings) if settings else None)
    if api is None:
        return None
    full = (f"A clean, modern, abstract editorial illustration for a business report about: {prompt}. "
            "Muted professional palette, no text, no logos, 16:9.")
    for model in IMAGE_MODELS:
        blob = _try_model(api, model, full)
        if blob:
            return blob
    return None
