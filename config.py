"""
Central config. Secrets come from environment variables injected by GitHub
Actions from repo secrets (Settings -> Secrets -> Actions). Never hardcode
real tokens/keys here.
"""
import os

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "6345421988")

# IMPORTANT: gemini-2.0-flash was deprecated by Google on 2026-06-01 -- do
# not use it. gemini-2.5-flash-lite has a much higher free daily-request
# quota than full gemini-2.5-flash, which matters a lot here because this
# agent runs every 30 minutes (48 times/day). Everything routine uses the
# lite model; nothing needs the heavier model at this call volume.
# If Google renames/retires these again, check current free-tier names at
# https://ai.google.dev/gemini-api/docs/models before swapping in.
MODEL_NAME = "gemini-2.5-flash-lite"

OUTPUT_DIR = "output"

# --- Task rotation -----------------------------------------------------
# One task runs every 30 minutes, cycling through this fixed order. A full
# cycle takes 2.5 hours, so each task individually runs about 9-10 times a
# day -- comfortably inside free-tier quota even on a restricted account.
TASKS = ["summary", "vocabulary", "quiz", "resources", "topic_image"]

# Dawn RSS feeds (official, stable, don't break when Dawn changes site HTML)
DAWN_EDITORIAL_FEED = "https://www.dawn.com/feeds/editorial"
DAWN_HOME_FEED = "https://www.dawn.com/feeds/home"
DAWN_PAKISTAN_FEED = "https://www.dawn.com/feeds/pakistan"
DAWN_WORLD_FEED = "https://www.dawn.com/feeds/world"
