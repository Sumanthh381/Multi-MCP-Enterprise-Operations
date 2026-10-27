import pytest

from enterprise.orchestrator import asset_query, plan


@pytest.mark.parametrize(
    "message,intent",
    [
        ("response efficiency for Compressor 202", "efficiency"),
        ("highest priority alarm on Motor 501", "priority"),
        ("flood analysis", "flood"),
        ("show trends", "trend"),
        ("stale alarms", "rationalization"),
        ("recurring alarms", "correlation"),
        ("summarize", "summary"),
    ],
)
def test_intents(message, intent):
    assert plan(message) == intent


def test_asset_resolution_and_context():
    assert asset_query("investigate Boiler Feed Pump 102 now") == "Boiler Feed Pump 102"
    assert asset_query("show BFP-101") == "BFP-101"
    assert asset_query("what about its trend?", "Compressor 201") == "Compressor 201"
    assert asset_query("hello") is None
