#!/usr/bin/env python3
"""알림 백엔드별 상수 테이블 (stdlib only).

백엔드를 추가할 때 이 파일만 고치면 save_secret·check_notify_complete·notify가 함께 따라온다.

필드:
    secret_key: secrets.json에서 웹훅 URL을 담는 키
    payload_field: POST 본문에서 메시지 텍스트가 들어가는 필드
    url_prefixes: 저장 시 허용하는 URL 접두사
    user_agent: 요청에 실을 User-Agent
    max_chars: 백엔드가 받는 텍스트 상한 (None이면 상한 없음)
"""

NONE = "none"

PLUGIN_URL = "https://github.com/yoouyeon/claude-plugin"
PLUGIN_VERSION = "0.2.1"  # .claude-plugin/plugin.json의 version과 맞춘다

BACKENDS = {
    "slack": {
        "secret_key": "slack_webhook_url",
        "url_prefixes": ("https://hooks.slack.com/",),
        "payload_field": "text",
        "user_agent": f"articles-os ({PLUGIN_URL}, {PLUGIN_VERSION})",
        "max_chars": None,
    },
    "discord": {
        "secret_key": "discord_webhook_url",
        # discordapp.com은 구 도메인이지만 아직 발급된 웹훅이 남아 있어 함께 받는다.
        "url_prefixes": (
            "https://discord.com/api/webhooks/",
            "https://discordapp.com/api/webhooks/",
        ),
        "payload_field": "content",
        # Discord는 유효한 User-Agent가 없는 요청을 Cloudflare 단계에서 막는다(에러 1010).
        # 형식은 문서가 지정한 "DiscordBot ($url, $versionNumber)"를 따른다.
        "user_agent": f"DiscordBot ({PLUGIN_URL}, {PLUGIN_VERSION})",
        "max_chars": 2000,
    },
}

# secrets.json에 웹훅이 실릴 수 있는 모든 키. 삭제·교체 때 훑는다.
SECRET_KEYS = tuple(spec["secret_key"] for spec in BACKENDS.values())

# config.yaml의 notify.backend가 가질 수 있는 값.
CHOICES = sorted(BACKENDS) + [NONE]
