"""
Thin wrapper around the Telegram Bot HTTP API.
"""
import requests
import config

API_BASE = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


def send_message(text: str):
    """Telegram caps messages at 4096 chars; split long text into chunks."""
    chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)] or [""]
    for chunk in chunks:
        resp = requests.post(
            f"{API_BASE}/sendMessage",
            data={"chat_id": config.TELEGRAM_CHAT_ID, "text": chunk},
            timeout=20,
        )
        if not resp.ok:
            print(f"[telegram] sendMessage failed: {resp.status_code} {resp.text}")


def send_document(filepath: str, caption: str = ""):
    with open(filepath, "rb") as f:
        resp = requests.post(
            f"{API_BASE}/sendDocument",
            data={"chat_id": config.TELEGRAM_CHAT_ID, "caption": caption},
            files={"document": f},
            timeout=60,
        )
    if not resp.ok:
        print(f"[telegram] sendDocument failed: {resp.status_code} {resp.text}")


def send_photo(filepath: str, caption: str = ""):
    with open(filepath, "rb") as f:
        resp = requests.post(
            f"{API_BASE}/sendPhoto",
            data={"chat_id": config.TELEGRAM_CHAT_ID, "caption": caption},
            files={"photo": f},
            timeout=60,
        )
    if not resp.ok:
        print(f"[telegram] sendPhoto failed: {resp.status_code} {resp.text}")
