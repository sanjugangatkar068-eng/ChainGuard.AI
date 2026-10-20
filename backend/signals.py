"""Lightweight external signal ingestion for the Disruption Sensing Agent.

Fetches RSS/Atom feeds, extracts headlines, and returns them as plain dicts.
Feed URLs come from the SIGNAL_FEEDS environment variable (comma-separated);
if none are set a small default set is used. If every feed is unreachable the
function returns a built-in offline sample so demos never come back empty.
"""

import os
import xml.etree.ElementTree as ET
from html import unescape

import httpx

ATOM = "{http://www.w3.org/2005/Atom}"

DEFAULT_FEEDS = [
    "https://news.google.com/rss/search?q=supply+chain+disruption+OR+port+closure+OR+tariff",
    "https://news.google.com/rss/search?q=port+congestion+OR+shipping+OR+freight",
]

SAMPLE_SIGNALS = [
    {
        "title": "Red Sea diversions continue as carriers reroute around Cape",
        "summary": "Major carriers extend Cape of Good Hope routings, adding transit time.",
        "link": "",
        "published": None,
        "source": "sample",
    },
    {
        "title": "Port congestion builds on the US West Coast",
        "summary": "Container backlog and vessel queues grow at major gateways.",
        "link": "",
        "published": None,
        "source": "sample",
    },
]


def configured_feeds():
    raw = (os.getenv("SIGNAL_FEEDS", "") or "").strip()
    if raw:
        return [url.strip() for url in raw.split(",") if url.strip()]
    return DEFAULT_FEEDS


def _text(node, tag):
    found = node.find(tag)
    if found is not None and found.text:
        return unescape(found.text.strip())
    return ""


def _atom_link(node):
    link = node.find(f"{ATOM}link")
    if link is not None:
        return link.get("href", "")
    return ""


def parse_feed(xml_text, source="", limit=10):
    """Parse an RSS 2.0 or Atom document into a list of signal dicts."""
    root = ET.fromstring(xml_text)

    entries = root.findall(".//item")
    is_atom = False
    if not entries:
        entries = root.findall(f".//{ATOM}entry")
        is_atom = True

    signals = []
    for entry in entries[:limit]:
        if is_atom:
            title = _text(entry, f"{ATOM}title")
            link = _atom_link(entry)
            published = _text(entry, f"{ATOM}updated") or _text(entry, f"{ATOM}published")
            summary = _text(entry, f"{ATOM}summary")
        else:
            title = _text(entry, "title")
            link = _text(entry, "link")
            published = _text(entry, "pubDate")
            summary = _text(entry, "description")

        if not title:
            continue

        signals.append({
            "title": title,
            "summary": summary,
            "link": link,
            "published": published or None,
            "source": source,
        })
    return signals


def fetch_signals(feeds=None, limit=10, timeout=8.0):
    """Fetch and parse all feeds. Never raises; falls back to sample data."""
    feeds = feeds if feeds is not None else configured_feeds()
    collected = []

    for url in feeds:
        if len(collected) >= limit:
            break
        try:
            response = httpx.get(url, timeout=timeout, follow_redirects=True,
                                 headers={"User-Agent": "ChainGuardAI/1.1"})
            response.raise_for_status()
            collected.extend(
                parse_feed(response.text, source=url, limit=limit - len(collected))
            )
        except (httpx.HTTPError, ET.ParseError, ValueError):
            continue

    if not collected:
        return SAMPLE_SIGNALS[:limit]
    return collected[:limit]
