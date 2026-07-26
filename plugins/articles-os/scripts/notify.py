#!/usr/bin/env python3
"""notify() 추상화 백엔드 디스패처. 메시지는 stdin으로 받는다.

Usage:
    echo "메시지" | python3 notify.py <data-path>
    python3 notify.py <data-path> --test        # 테스트 메시지 발송

동작:
    <data-path>/config/notify.yaml 의 backend 를 읽고,
    - none  → 아무것도 안 하고 exit 0
    - slack → ~/.articles-os/registry.json 에서 <data-path>의 install_id 를 찾아
              ~/.articles-os/secrets.json[install_id]["slack_webhook_url"] 로 POST

exit code: 0 성공(또는 backend none), 1 실패
"""
import json
import os
import re
import sys
import urllib.request
import urllib.error

HOME_DIR = os.path.expanduser("~/.articles-os")
REGISTRY = os.path.join(HOME_DIR, "registry.json")
SECRETS = os.path.join(HOME_DIR, "secrets.json")
TIMEOUT = 15


def die(msg):
    print(f"notify.py error: {msg}", file=sys.stderr)
    sys.exit(1)


def read_backend(data_path):
    conf = os.path.join(data_path, "config", "notify.yaml")
    if not os.path.exists(conf):
        die(f"notify.yaml not found: {conf}")
    with open(conf, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^\s*backend\s*:\s*([\w-]+)", line)
            if m:
                return m.group(1).lower()
    die("no 'backend:' key in notify.yaml")


def find_install_id(data_path):
    if not os.path.exists(REGISTRY):
        die(f"registry not found: {REGISTRY}")
    with open(REGISTRY, encoding="utf-8") as f:
        installs = json.load(f).get("installs", [])
    target = os.path.realpath(os.path.expanduser(data_path))
    for ins in installs:
        if os.path.realpath(os.path.expanduser(ins.get("path", ""))) == target:
            return ins["install_id"]
    die(f"no install registered for path: {data_path}")


def read_webhook(install_id):
    if not os.path.exists(SECRETS):
        die(f"secrets not found: {SECRETS} (run notify-config)")
    with open(SECRETS, encoding="utf-8") as f:
        secrets = json.load(f)
    url = secrets.get(install_id, {}).get("slack_webhook_url")
    if not url:
        die(f"no slack_webhook_url for install '{install_id}' (run notify-config)")
    return url


def main():
    if len(sys.argv) < 2:
        die("usage: notify.py <data-path> [--test]")
    data_path = sys.argv[1]
    is_test = "--test" in sys.argv[2:]

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

    webhook = read_webhook(find_install_id(data_path))
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
