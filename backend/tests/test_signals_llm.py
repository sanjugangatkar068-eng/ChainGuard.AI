import httpx
import pytest
from fastapi.testclient import TestClient

import main
import signals
from agents import (
    classify_signal,
    explanation_agent,
    run_supply_chain_agents,
    signal_ingestion_agent,
)
from models import ScenarioRequest

client = TestClient(main.app)

RSS_SAMPLE = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item>
    <title>Carriers reroute around the Cape after canal closure</title>
    <link>https://example.com/a</link>
    <pubDate>Mon, 20 Oct 2026 10:00:00 GMT</pubDate>
    <description>Shipping lines extend diversions.</description>
  </item>
  <item>
    <title>New tariffs announced on imported goods</title>
    <link>https://example.com/b</link>
    <description>Duties rise next quarter.</description>
  </item>
</channel></rss>"""

ATOM_SAMPLE = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Storm disrupts port operations</title>
    <link href="https://example.com/c"/>
    <updated>2026-10-20T09:00:00Z</updated>
    <summary>High winds close terminals.</summary>
  </entry>
</feed>"""


# --- feed parsing ---------------------------------------------------------

def test_parse_rss_feed():
    items = signals.parse_feed(RSS_SAMPLE, source="test")
    assert len(items) == 2
    assert items[0]["title"].startswith("Carriers reroute")
    assert items[0]["link"] == "https://example.com/a"
    assert items[0]["source"] == "test"


def test_parse_atom_feed():
    items = signals.parse_feed(ATOM_SAMPLE, source="atom")
    assert len(items) == 1
    assert items[0]["title"] == "Storm disrupts port operations"
    assert items[0]["link"] == "https://example.com/c"


def test_fetch_signals_falls_back_to_sample(monkeypatch):
    def boom(*args, **kwargs):
        raise httpx.ConnectError("no network")

    monkeypatch.setattr(signals.httpx, "get", boom)
    result = signals.fetch_signals(feeds=["https://unreachable.example/feed"])
    assert result
    assert all(item["source"] == "sample" for item in result)


# --- classification -------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("Strait closure halts container traffic", "port_closure"),
    ("Tariffs raised on steel imports", "tariff_change"),
    ("Hurricane closes terminals", "weather"),
    ("Supplier factory fire", "supplier_outage"),
    ("Something unrelated entirely", "other"),
])
def test_classify_signal(text, expected):
    assert classify_signal(text) == expected


def test_signal_ingestion_agent_marks_offline_sample():
    out = signal_ingestion_agent(signals.SAMPLE_SIGNALS)
    assert out["count"] == len(signals.SAMPLE_SIGNALS)
    assert out["data_source"] == "Offline sample"
    assert all("disruption_type" in s for s in out["signals"])


# --- explanation agent ----------------------------------------------------

def test_explanation_falls_back_to_rules_without_llm():
    result = run_supply_chain_agents(None, ScenarioRequest())
    assert result["explanation"]["reasoning_source"] == "rules"
    assert isinstance(result["explanation"]["explanation"], str)
    assert result["explanation"]["explanation"]


def test_explanation_agent_direct():
    result = run_supply_chain_agents(None, ScenarioRequest())
    out = explanation_agent(result)
    assert out["reasoning_source"] == "rules"


# --- signals endpoint -----------------------------------------------------

def test_signals_endpoint(monkeypatch):
    monkeypatch.setattr(
        main, "fetch_signals",
        lambda limit=10: [{"title": "Port closure in the canal",
                           "summary": "", "link": "", "published": None,
                           "source": "test"}],
    )
    body = client.get("/api/signals?limit=5").json()
    assert body["count"] == 1
    assert body["signals"][0]["disruption_type"] == "port_closure"


def test_analyze_includes_explanation():
    did = client.post("/api/disruptions", json={
        "title": "Red Sea reroute", "disruption_type": "port_closure",
        "location": "Suez Canal", "severity": "critical", "delay_days": 14,
    }).json()["id"]
    body = client.post("/api/analyze", json={"disruption_id": did}).json()
    assert body["explanation"]["reasoning_source"] == "rules"
    assert "critical" in body["explanation"]["explanation"].lower()
