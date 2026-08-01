#!/usr/bin/env python3
"""알림 연결(notify-config) 완료 여부 확인 (stdlib only).

Usage:
    python3 check_notify_complete.py <plugin-data-dir>

동작:
    notify.backend를 설정한 적이 없으면 미완료.
    backend가 none이면 시크릿 존재 여부와 무관하게 완료.
    웹훅 백엔드(slack·discord)면 <plugin-data-dir>/secrets.json에 그 백엔드의 웹훅 키가 있어야 완료.
    그 밖의 값이면 손으로 편집된 config.yaml이므로 미완료로 본다.

stdout (JSON):
    {"complete": true, "backend": "..."}
    {"complete": false, "backend": "...", "reason": "..."}

exit code: 0 판정 완료(complete 값으로 구분), 1 판정 불가(인자 오류·config.yaml 읽기 실패)
"""
import json
import os
import sys

import manage_config
import notify_backends
import save_secret


def report(complete, backend=None, reason=None):
    out = {"complete": complete}
    if backend is not None:
        out["backend"] = backend
    if reason:
        out["reason"] = reason
    print(json.dumps(out, ensure_ascii=False))


def main():
    if len(sys.argv) != 2:
        report(False, reason="usage: check_notify_complete.py <plugin-data-dir>")
        sys.exit(1)

    try:
        config = manage_config.load_config(manage_config.config_path())
    except OSError as e:
        report(False, reason=f"cannot read config.yaml: {type(e).__name__}")
        sys.exit(1)

    if not config["backend_set"]:
        report(False, reason="notify backend not configured")
        return

    backend = config["backend"]
    if backend == notify_backends.NONE:
        report(True, backend)
        return

    spec = notify_backends.BACKENDS.get(backend)
    if spec is None:
        report(False, backend, "unknown backend")
        return

    secrets = save_secret.load_secrets(os.path.join(sys.argv[1], "secrets.json"))
    if secrets.get(spec["secret_key"]):
        report(True, backend)
        return
    report(False, backend, "webhook not saved")


if __name__ == "__main__":
    main()
