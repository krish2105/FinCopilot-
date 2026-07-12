from src.agents.classifier import classify, heuristic_route
from src.providers.router import ProviderRouter


def test_heuristic_relationship():
    assert heuristic_route("Which companies share this risk?").route == "relationship"
    assert heuristic_route("What do Apple and Microsoft have in common?").route == "relationship"


def test_heuristic_multi_hop():
    assert heuristic_route("How did revenue trend over time?").route == "multi_hop"


def test_heuristic_simple():
    assert heuristic_route("What was Apple's net revenue?").route == "simple"


def test_classify_stub_uses_heuristic(settings):
    router = ProviderRouter(settings)  # stub mode
    d = classify(router, "Which companies share competition risk?")
    assert d.route == "relationship"
