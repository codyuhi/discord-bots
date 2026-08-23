#!/usr/bin/env python3
"""
Utility script to send a test message/embed to the SnakeCode test Discord channel via webhook.
Usage:
    python scripts/test_webhook.py
"""

import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "weekly-boysnight-poll", ".env"))

WEBHOOK_URL = os.getenv(
    "SNAKECODE_TEST_WEBHOOK_URL",
    "https://discord.com/api/webhooks/1540942878115631146/L7TL3U8HVgrcZKO36l7CU__Kh39Kke4KiOfUcIzjASeLBrasukpXuOePUevavdzhGXlK",
)


def send_test_webhook(content="🎮 Bot test message sent successfully to #bot-tests!"):
    payload = {
        "content": content,
        "embeds": [
            {
                "title": "✅ Test Notification",
                "description": "This is a test message from the discord-bots repository.",
                "color": 0x5865F2,
                "fields": [
                    {"name": "Server", "value": "SnakeCode", "inline": True},
                    {"name": "Channel", "value": "#bot-tests", "inline": True},
                ],
            }
        ],
    }

    req = urllib.request.Request(
        WEBHOOK_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "DiscordBot-TestScript"},
    )

    try:
        import ssl
        try:
            import certifi
            ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            ssl_ctx = ssl.create_default_context()

        with urllib.request.urlopen(req, context=ssl_ctx) as response:
            if response.status in (200, 204):
                print(f"SUCCESS: Webhook payload delivered to {WEBHOOK_URL} (Status: {response.status})")
                return True
            else:
                print(f"WARNING: Received status code {response.status}")
                return False
    except Exception as e:
        print(f"ERROR sending webhook: {e}")
        return False


if __name__ == "__main__":
    send_test_webhook()
