#!/usr/bin/env python3
"""RSS/Atom/RDF 피드 fetch + 파싱 (stdlib only).

Usage:
    python3 fetch_feed.py <feed-url> [--source-name NAME]

fetch 실패 시 내부적으로 1회 재시도한다(호출자는 재시도를 신경 쓰지 않는다).
source_name/source_url은 성공·실패 응답 모두에 항상 포함된다(source_url은 <feed-url>과 동일).

stdout (JSON):
    성공: {"ok": true, "source_name": "...", "source_url": "...", "feed_title": "...",
           "entries": [{"title": "...", "url": "...", "summary": "...",
                        "published_at": "ISO8601 UTC | null"}]}
    실패: {"ok": false, "source_name": "...", "source_url": "...", "error": "..."}  (exit code 1)
"""
import argparse
import html
import json
import re
import sys
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

TIMEOUT = 30
MAX_BYTES = 10 * 1024 * 1024
UA = "articles-os/0.1 (RSS reader)"
SUMMARY_MAX = 300
MAX_ATTEMPTS = 2  # 최초 시도 + 1회 재시도


def fail(msg, source_name=None, source_url=None):
    print(json.dumps(
        {"ok": False, "source_name": source_name, "source_url": source_url, "error": msg},
        ensure_ascii=False,
    ))
    sys.exit(1)


def strip_html(s):
    if not s:
        return ""
    s = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    # RFC 822 (RSS pubDate)
    try:
        dt = parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        pass
    # ISO 8601 (Atom)
    try:
        s2 = re.sub(r"Z$", "+00:00", s)
        dt = datetime.fromisoformat(s2)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return None


def local(tag):
    return tag.rsplit("}", 1)[-1].lower() if isinstance(tag, str) else ""


def child_text(elem, names):
    for c in elem:
        if local(c.tag) in names and c.text:
            return c.text
    return None


def entry_link(elem):
    fallback = None
    for c in elem:
        if local(c.tag) != "link":
            continue
        href = c.get("href")
        if href:  # Atom
            rel = c.get("rel", "alternate")
            if rel == "alternate":
                return href.strip()
            fallback = fallback or href.strip()
        elif c.text:  # RSS
            return c.text.strip()
    return fallback


def parse_feed(data):
    root = ET.fromstring(data)
    rtag = local(root.tag)
    feed_title = None
    items = []

    if rtag == "rss":
        channel = next((c for c in root if local(c.tag) == "channel"), None)
        if channel is None:
            raise ValueError("rss without channel")
        feed_title = child_text(channel, {"title"})
        items = [c for c in channel if local(c.tag) == "item"]
    elif rtag == "feed":  # Atom
        feed_title = child_text(root, {"title"})
        items = [c for c in root if local(c.tag) == "entry"]
    elif rtag == "rdf":  # RSS 1.0
        for c in root:
            if local(c.tag) == "channel":
                feed_title = child_text(c, {"title"})
        items = [c for c in root if local(c.tag) == "item"]
    else:
        raise ValueError(f"unknown feed root element: <{rtag}>")

    entries = []
    for it in items:
        url = entry_link(it)
        title = strip_html(child_text(it, {"title"}))
        if not url or not title:
            continue
        desc = child_text(it, {"description", "summary"}) or child_text(it, {"encoded", "content"})
        date_raw = (
            child_text(it, {"pubdate", "published"})
            or child_text(it, {"updated", "date"})
        )
        entries.append({
            "title": title,
            "url": url,
            "summary": strip_html(desc)[:SUMMARY_MAX],
            "published_at": parse_date(date_raw),
        })
    return feed_title, entries


def fetch_and_parse_once(url):
    """한 번의 fetch+파싱 시도. 성공 시 (feed_title, entries), 실패 시 에러 메시지를 raise."""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = resp.read(MAX_BYTES)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} for {url}")
    except Exception as e:
        raise RuntimeError(f"fetch error for {url}: {e}")

    try:
        feed_title, entries = parse_feed(data)
    except Exception as e:
        raise RuntimeError(f"parse error for {url}: {e}")

    return feed_title, entries


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("feed_url")
    parser.add_argument("--source-name", default=None)
    args = parser.parse_args()

    url = args.feed_url
    source_name = args.source_name
    source_url = url

    last_error = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            feed_title, entries = fetch_and_parse_once(url)
            last_error = None
            break
        except RuntimeError as e:
            last_error = str(e)

    if last_error is not None:
        fail(last_error, source_name, source_url)

    print(json.dumps(
        {
            "ok": True,
            "source_name": source_name,
            "source_url": source_url,
            "feed_title": strip_html(feed_title),
            "entries": entries,
        },
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
