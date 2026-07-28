#!/usr/bin/env python3
"""데이터 폴더 경로(userConfig) 설정 여부 확인 (stdlib only).

Usage:
    python3 check_data_path.py "<value>"

<value>는 스킬이 `${user_config.data_path}`로 읽은 그대로의 문자열을 전달한다 —
비어있거나, 치환되지 않아 플레이스홀더가 그대로 남아있거나(예: 문자열에 "${" 포함),
공백만 있는 경우를 "미설정"으로 판정한다.

stdout (JSON):
    설정됨:   {"configured": true, "path": "<정규화된 절대경로>"}
    미설정:   {"configured": false}
"""
import json
import os
import sys


def main():
    value = sys.argv[1] if len(sys.argv) > 1 else ""
    value = value.strip()

    if not value or "${" in value:
        print(json.dumps({"configured": False}, ensure_ascii=False))
        return

    print(json.dumps({"configured": True, "path": os.path.realpath(os.path.expanduser(value))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
