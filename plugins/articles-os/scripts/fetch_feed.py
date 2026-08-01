#!/usr/bin/env python3
"""RSS/Atom/RDF 피드 fetch + 파싱 (stdlib only).

소스를 병렬로 가져온다. 입력 채널은 둘이지만 출력 계약은 하나다 — **항상 배열**이다.

Usage:
    python3 fetch_feed.py <feed-url> [--source-name NAME]   # 소스 하나 (URL에 특수문자가 섞여도 안전)
    python3 fetch_feed.py [--max-workers N]                 # stdin의 소스 목록

stdin (인자를 주지 않은 경우):
    {"sources": [{"name": "...", "url": "..."}, ...]} 또는 그 배열
    (`manage_config.py sources list` 출력을 그대로 받는다)

stdout (JSON 배열, 입력 순서 유지):
    성공: {"ok": true, "source_name": "...", "source_url": "...", "feed_title": "...",
           "entries": [{"title": "...", "url": "...", "summary": "...",
                        "published_at": "ISO8601 UTC | null"}]}
    실패: {"ok": false, "source_name": "...", "source_url": "...", "error": "..."}

fetch 실패 시 내부적으로 1회 재시도한다(호출자는 재시도를 신경 쓰지 않는다).
source_name/source_url은 성공·실패 응답 모두에 항상 포함된다(source_url은 피드 URL과 동일).

개별 소스가 실패해도 종료 코드는 0이다. 부분 성공을 허용하며, `apply_collection_results.py`가 성공분만 반영하고 실패는 상태 카운터에 적는다.
exit 1은 입력 자체를 읽지 못한 경우뿐이며, 그때만 stdout이 배열이 아니라 `{"ok": false, "error": "..."}` 객체 하나다.
"""
import argparse
import html
import http.client
import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import NoReturn

TIMEOUT = 30
MAX_BYTES = 30 * 1024 * 1024  # 병적으로 큰 응답을 막는 절대 상한
UA = "articles-os/0.1 (RSS reader)"
SUMMARY_MAX = 300
MAX_ATTEMPTS = 2  # 최초 시도 + 1회 재시도
MAX_WORKERS = 8   # 동시 fetch 상한


def fail(msg, source_name=None, source_url=None) -> NoReturn:
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
    except (TypeError, ValueError):
        pass
    # ISO 8601 (Atom)
    try:
        s2 = re.sub(r"Z$", "+00:00", s)
        dt = datetime.fromisoformat(s2)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
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
    try:
        # Request() 생성도 try 안에 둔다 — 지원하지 않는 URL 형식이면 여기서 ValueError가 난다.
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        })
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = resp.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} for {url}")
    # OSError는 URLError·타임아웃·소켓 오류를, ValueError는 지원하지 않는 URL 형식을 포괄한다.
    except (OSError, ValueError, http.client.HTTPException) as e:
        raise RuntimeError(f"fetch error for {url}: {e}")

    if len(data) > MAX_BYTES:
        raise RuntimeError(f"response exceeded {MAX_BYTES} bytes for {url}")

    try:
        feed_title, entries = parse_feed(data)
    # ParseError는 SyntaxError 계열이라 ValueError로 잡히지 않는다.
    except (ET.ParseError, ValueError, TypeError) as e:
        raise RuntimeError(f"parse error for {url}: {e}")

    return feed_title, entries


def fetch_source(url, source_name):
    """소스 하나를 재시도까지 포함해 가져온다. 예외를 올리지 않고 결과 dict를 돌려준다."""
    last_error = None
    for _ in range(MAX_ATTEMPTS):
        try:
            feed_title, entries = fetch_and_parse_once(url)
            return {
                "ok": True,
                "source_name": source_name,
                "source_url": url,
                "feed_title": strip_html(feed_title),
                "entries": entries,
            }
        except RuntimeError as e:
            last_error = str(e)
    return {"ok": False, "source_name": source_name, "source_url": url, "error": last_error}


def error_result(url, source_name, exc):
    return {
        "ok": False,
        "source_name": source_name,
        "source_url": url,
        "error": f"{type(exc).__name__}: {exc}",
    }


def read_sources_from_stdin():
    """`manage_config.py sources list` 출력({"sources": [...]})이나 그 배열을 그대로 받는다."""
    try:
        doc = json.load(sys.stdin)
    except ValueError as e:
        fail(f"invalid stdin JSON: {e}")
    if isinstance(doc, dict):
        if doc.get("ok") is False:
            fail(doc.get("error") or "source list unavailable")
        doc = doc.get("sources")
    if not isinstance(doc, list):
        fail("stdin must be {\"sources\": [...]} or a JSON array")
    sources = []
    for item in doc:
        if not isinstance(item, dict) or not item.get("url"):
            fail("each source needs a url")
        sources.append((item["url"], item.get("name")))
    return sources


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("feed_url", nargs="?", default=None)
    parser.add_argument("--source-name", default=None)
    parser.add_argument("--max-workers", type=int, default=MAX_WORKERS)
    args = parser.parse_args()

    if args.feed_url:
        sources = [(args.feed_url, args.source_name)]
    else:
        sources = read_sources_from_stdin()

    # submit + future.exception()으로 받는다. pool.map은 예외를 그대로 올려 한 소스의 예기치 못한
    # 오류가 나머지 소스까지 죽이는데, 여기서는 그 소스만 실패로 적고 나머지를 살려야 한다.
    workers = max(1, min(args.max_workers, len(sources))) if sources else 1
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(fetch_source, url, name) for url, name in sources]
        results = [
            fut.result() if fut.exception() is None else error_result(url, name, fut.exception())
            for (url, name), fut in zip(sources, futures)
        ]
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
