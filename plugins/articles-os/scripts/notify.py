#!/usr/bin/env python3
"""notify() 추상화 백엔드 디스패처. 메시지는 stdin으로 받는다.

Usage:
    echo "메시지" | python3 notify.py <data-path> <plugin-data-dir>
    python3 notify.py <data-path> <plugin-data-dir> --test   # 테스트 메시지 발송

동작:
    <data-path>/config.yaml 의 notify.backend 를 읽고,
    - none  → 아무것도 안 하고 exit 0
    - slack → <plugin-data-dir>/secrets.json 의 slack_webhook_url 로 POST

<plugin-data-dir>는 호출자(SKILL.md)가 `${CLAUDE_PLUGIN_DATA}` 플레이스홀더를 그대로
넘긴 값이어야 한다 — 스크립트 내부에서 `os.environ`으로 다시 읽지 않는 이유는
save_secret.py 참고(다른 플러그인의 hook이 남긴 값과 섞일 수 있음을 실측 확인).

exit code: 0 성공(또는 backend none), 1 실패
"""
import json
import os
import re
import sys
import urllib.request
import urllib.error

TIMEOUT = 15


def die(msg):
    print(f"notify.py error: {msg}", file=sys.stderr)
    sys.exit(1)


def read_backend(data_path):
    conf = os.path.join(data_path, "config.yaml")
    if not os.path.exists(conf):
        die(f"config.yaml not found: {conf}")
    in_notify = False
    with open(conf, encoding="utf-8") as f:
        for line in f:
            if re.match(r"^notify:\s*$", line):
                in_notify = True
                continue
            if in_notify:
                m = re.match(r"^\s*backend\s*:\s*([\w-]+)", line)
                if m:
                    return m.group(1).lower()
    die("no notify.backend key in config.yaml")


def read_webhook(plugin_data_dir):
    secrets_file = os.path.join(plugin_data_dir, "secrets.json")
    if not os.path.exists(secrets_file):
        die(f"secrets not found: {secrets_file} (run notify-config)")
    with open(secrets_file, encoding="utf-8") as f:
        secrets = json.load(f)
    url = secrets.get("slack_webhook_url")
    if not url:
        die("no slack_webhook_url configured (run notify-config)")
    return url


def main():
    if len(sys.argv) < 3:
        die("usage: notify.py <data-path> <plugin-data-dir> [--test]")
    data_path = sys.argv[1]
    plugin_data_dir = sys.argv[2]
    is_test = "--test" in sys.argv[3:]

    backend = read_backend(data_path)
    if backend == "none":
        print("backend=none, skipped")
        return
    if backend != "slack":
        die(f"unknown backend: {backend}")

    if is_test:
        text = "✅ articles-os 테스트 알림입니다. 알림 연결이 정상 동작합니다."
    else:
        text = sys.stdin.read().strip()
    if not text:
        die("empty message (pipe text via stdin, or use --test)")

    webhook = read_webhook(plugin_data_dir)
    body = json.dumps({"text": text}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        webhook, data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            if resp.status != 200:
                die(f"slack returned HTTP {resp.status}")
    except urllib.error.HTTPError as e:
        die(f"slack webhook HTTP {e.code}: {e.read().decode(errors='replace')[:200]}")
    except Exception as e:
        die(f"slack webhook error: {e}")
    print("sent")


if __name__ == "__main__":
    main()
