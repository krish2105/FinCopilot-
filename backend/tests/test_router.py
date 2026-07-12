import pytest
from pydantic import BaseModel

from src.config.settings import Settings
from src.providers.base import LLMResponse, Provider, ProviderError, RateLimitError
from src.providers.router import ProviderRouter


class Rec(BaseModel):
    a: int
    b: str


class FakeProvider(Provider):
    def __init__(self, name, model, behavior):
        self.name = name
        self.model = model
        self.behavior = behavior
        self.calls = 0

    def complete(self, messages, json_mode=False):
        self.calls += 1
        if self.behavior == "rate":
            raise RateLimitError(self.model)
        if self.behavior == "error":
            raise ProviderError(self.model)
        if self.behavior == "json":
            return LLMResponse('{"a": 1, "b": "x"}', self.name, self.model)
        if self.behavior == "badjson":
            return LLMResponse("not json", self.name, self.model)
        return LLMResponse("hello world", self.name, self.model)


@pytest.fixture
def live_router(monkeypatch):
    monkeypatch.setattr("src.providers.router.time.sleep", lambda s: None)

    def _make(providers):
        r = ProviderRouter(Settings(gemini_api_key="x"))  # live mode
        r.providers = providers
        r.mode = "live"
        return r

    return _make


def test_falls_through_on_rate_limit(live_router):
    p1 = FakeProvider("gemini", "flash-lite", "rate")
    p2 = FakeProvider("groq", "llama", "ok")
    r = live_router([p1, p2])
    trace = []
    out = r.text("hi", trace=trace)
    assert out == "hello world"
    assert trace[-1]["provider"] == "groq"


def test_all_fail_raises(live_router):
    r = live_router([FakeProvider("a", "m", "rate"), FakeProvider("b", "m", "error")])
    with pytest.raises(ProviderError):
        r.text("hi")


def test_structured_parses_json(live_router):
    r = live_router([FakeProvider("gemini", "flash", "json")])
    obj = r.structured("give me a rec", Rec)
    assert obj.a == 1 and obj.b == "x"


def test_structured_falls_through_bad_json_then_stub(live_router):
    r = live_router([FakeProvider("a", "m", "badjson")])
    obj = r.structured("x", Rec, stub=lambda: Rec(a=9, b="stub"))
    assert obj.b == "stub"


def test_cache_hit(live_router):
    p = FakeProvider("gemini", "flash", "ok")
    r = live_router([p])
    r.text("same prompt")
    r.text("same prompt")
    assert p.calls == 1  # second served from cache


def test_stub_mode_uses_stub_builder():
    r = ProviderRouter(Settings(fincopilot_offline_mode=True))
    assert r.mode == "stub"
    obj = r.structured("x", Rec, stub=lambda: Rec(a=7, b="s"))
    assert obj.a == 7
    assert r.text("hello", stub_text="canned") == "canned"
