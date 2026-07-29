#!/usr/bin/env python3
"""notify() 추상화 백엔드 디스패처. 메시지는 stdin으로 받는다.

Usage:
    echo "메시지" | python3 notify.py <plugin-data-dir>
    python3 notify.py <plugin-data-dir> --test   # 테스트 메시지 발송

동작:
    고정 경로의 config.yaml 에서 notify.backend 를 읽고,
    - none  → 아무것도 안 하고 exit 0
    - slack → <plugin-data-dir>/secrets.json 의 slack_webhook_url 로 POST

<plugin-data-dir>는 호출자(SKILL.md)가 `${CLAUDE_PLUGIN_DATA}` 플레이스홀더를 그대로 넘긴 값이어야 한다.

exit code: 0 성공(또는 backend none), 1 실패, 2 인자 오류(argparse)
"""
import argparse
import http.client
import json
import os
import sys
import urllib.error
import urllib.request
from typing import NoReturn

import manage_config
import paths

TIMEOUT = 15


def die(msg) -> NoReturn:
    print(f"notify.py error: {msg}", file=sys.stderr)
    sys.exit(1)


def read_backend():
    """config.yaml의 notify.backend. 파싱은 manage_config에 위임한다(파서 중복 방지)."""
    conf = paths.config_path()
    if not os.path.exists(conf):
        die(f"config.yaml not found: {conf}")
    try:
        config = manage_config.load_config(conf)
    except OSError as e:
        die(f"cannot read config.yaml: {type(e).__name__}: {e}")
    if not config["backend_set"]:
        die("no notify.backend key in config.yaml")
    return config["backend"]


def read_webhook(plugin_data_dir):
    secrets_file = os.path.join(plugin_data_dir, "secrets.json")
    if not os.path.exists(secrets_file):
        die(f"secrets not found: {secrets_file} (run notify-config)")
    try:
        with open(secrets_file, encoding="utf-8") as f:
            secrets = json.load(f)
    except (OSError, ValueError) as e:
        # 메시지에 파일 내용은 넣지 않는다 — 웹훅 URL이 노출될 수 있다.
        die(f"cannot read secrets.json: {type(e).__name__}")
    if not isinstance(secrets, dict):
        die("secrets.json is not a JSON object (run notify-config)")
    url = secrets.get("slack_webhook_url")
    if not url:
        die("no slack_webhook_url configured (run notify-config)")
    return url


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("plugin_data_dir")
    parser.add_argument("--test", action="store_true", help="테스트 메시지 발송")
    args = parser.parse_args()

    backend = read_backend()
    if backend == "none":
        print("backend=none, skipped")
        return
    if backend != "slack":
        die(f"unknown backend: {backend}")

    if args.test:
        text = "✅ articles-os 테스트 알림입니다. 알림 연결이 정상 동작합니다."
    else:
        text = sys.stdin.read().strip()
    if not text:
        die("empty message (pipe text via stdin, or use --test)")

    webhook = read_webhook(args.plugin_data_dir)
    body = json.dumps({"text": text}, ensure_ascii=False).encode("utf-8")
    try:
        # Request() 생성자가 URL 형식을 검증하므로 try 안에 둔다.
        req = urllib.request.Request(
            webhook, data=body, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            if resp.status != 200:
                die(f"slack returned HTTP {resp.status}")
    except urllib.error.HTTPError as e:
        die(f"slack webhook HTTP {e.code}: {e.read().decode(errors='replace')[:200]}")
    except (OSError, http.client.HTTPException, ValueError) as e:
        # OSError: URLError·타임아웃·연결 끊김 / HTTPException: 깨진 응답 (OSError 아님)
        # ValueError: secrets.json이 손으로 편집돼 URL 형식이 깨진 경우
        die(f"slack webhook error: {type(e).__name__}: {e}")
    print("sent")


if __name__ == "__main__":
    main()
