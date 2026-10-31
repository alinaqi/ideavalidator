from types import SimpleNamespace as NS

from pipeline.images import generate_hero


class _FakeImgClient:
    def __init__(self, data=b"PNGDATA", boom=False):
        self._data = data; self._boom = boom
        self.models = self

    def generate_content(self, **kw):
        if self._boom:
            raise RuntimeError("no image model")
        part = NS(inline_data=NS(data=self._data, mime_type="image/png"), text=None)
        return NS(candidates=[NS(content=NS(parts=[part]))])


def test_generate_hero_returns_bytes():
    assert generate_hero("a clean security dashboard", client=_FakeImgClient()) == b"PNGDATA"


def test_generate_hero_graceful_on_error():
    assert generate_hero("x", client=_FakeImgClient(boom=True)) is None
