#!/usr/bin/env python3
"""알림 연결(notify-config) 완료 여부 확인 (stdlib only).

Usage:
    python3 check_notify_complete.py <data-path> <plugin-data-dir>

동작:
    backend가 none이면 시크릿 존재 여부와 무관하게 완료로 판정한다(notify-config는
    none 전환 시 기존 시크릿을 지우지 않으므로 남아있을 수 있으나 무의미).
    backend가 slack이면 <plugin-data-dir>/secrets.json에 slack_webhook_url이
    저장돼 있어야 완료로 판정한다.

config.yaml 파싱은 manage_config.load_config, secrets.json 존재 확인은
save_secret.load_secrets를 그대로 재사용한다(중복 구현 금지 — docs/conventions.md).

stdout (JSON):
    {"complete": true, "backend": "..."}
    {"complete": false, "backend": "slack", "reason": "webhook not saved"}
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import manage_config  # noqa: E402
import save_secret  # noqa: E402


def main():
    if len(sys.argv) != 3:
        print(json.dumps({"complete": False, "reason": "usage: check_notify_complete.py <data-path> <plugin-data-dir>"}, ensure_ascii=False))
        sys.exit(1)

    data_path, plugin_data_dir = sys.argv[1], sys.argv[2]

    config = manage_config.load_config(manage_config.config_path(data_path))
    backend = config["backend"]

    if backend != "slack":
        print(json.dumps({"complete": True, "backend": backend}, ensure_ascii=False))
        return

    secrets = save_secret.load_secrets(os.path.join(plugin_data_dir, "secrets.json"))
    if secrets.get("slack_webhook_url"):
        print(json.dumps({"complete": True, "backend": "slack"}, ensure_ascii=False))
        return

    print(json.dumps({"complete": False, "backend": "slack", "reason": "webhook not saved"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
