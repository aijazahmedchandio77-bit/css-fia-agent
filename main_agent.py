"""
Runs every 30 minutes (scheduled by .github/workflows/agent.yml). Each run
does exactly ONE job, cycling through config.TASKS in order:

  slot 0: article summary
  slot 1: 50-word English + Urdu meaning + vocabulary
  slot 2: 10-question quiz (category alternates Pakistan/International)
  slot 3: CSS-relevant resource suggestions
  slot 4: CSS subject topic study-card image

A full cycle takes 2.5 hours, so each task individually runs ~9-10 times a
day -- deliberately light on the Gemini free-tier quota.

The task for "now" is picked purely from the current UTC time (no external
state needed), so this stays simple and never gets out of sync.
"""
import datetime
import traceback
import fetch_article
import ai_processor
import image_builder
import telegram_bot
import config
from topics import pick_topic


def _current_slot() -> int:
    """0-4, cycling every 30 minutes through the 5 tasks."""
    now = datetime.datetime.utcnow()
    half_hour_index = now.hour * 2 + (1 if now.minute >= 30 else 0)
    return half_hour_index % len(config.TASKS)


def run_summary(article: dict):
    print("Task: article summary")
    summary = ai_processor.task_summary(article)
    telegram_bot.send_message(
        f"📄 Article Summary\n{article['title']}\n{article['link']}\n\n{summary}"
    )


def run_vocabulary(article: dict):
    print("Task: 50-word meaning + vocabulary")
    result = ai_processor.task_vocabulary(article)
    telegram_bot.send_message(
        f"🇬🇧 50-word meaning (English)\n{result.get('english_50_words','')}"
    )
    telegram_bot.send_message(
        f"🇵🇰 50-word meaning (Urdu)\n{result.get('urdu_50_words','')}"
    )
    vocab = result.get("vocabulary", [])
    if vocab:
        lines = "\n".join(f"- {v['word']}: {v['meaning_english']} | Urdu: {v['meaning_urdu']}" for v in vocab)
        telegram_bot.send_message(f"📚 Vocabulary\n{lines}")


def run_quiz(article: dict, headline_pool: list, slot_counter: int):
    category = "Pakistan" if slot_counter % 2 == 0 else "International"
    print(f"Task: quiz ({category})")
    mcqs = ai_processor.task_quiz(article, headline_pool, category, count=10)
    if not mcqs:
        telegram_bot.send_message("⚠️ Quiz generation returned no questions this run.")
        return
    lines = [f"📝 Quiz — {category} Current Affairs ({len(mcqs)} questions)\n"]
    answers = []
    for idx, mcq in enumerate(mcqs, start=1):
        lines.append(f"{idx}. {mcq['question']}")
        for key in ["A", "B", "C", "D"]:
            lines.append(f"   {key}) {mcq.get('options', {}).get(key, '')}")
        answers.append(f"{idx}-{mcq.get('answer','?')}")
    lines.append("\nAnswer key: " + "  ".join(answers))
    telegram_bot.send_message("\n".join(lines))


def run_resources(article: dict):
    print("Task: CSS-relevant resources")
    resources = ai_processor.task_resources(article["title"])
    telegram_bot.send_message(f"🔎 CSS-relevant resource suggestions\n{resources}")


def run_topic_image():
    print("Task: topic study-card image")
    now = datetime.datetime.utcnow()
    day_index = now.timetuple().tm_yday
    slot_index = now.hour * 2 + (1 if now.minute >= 30 else 0)
    subject, topic = pick_topic(day_index, slot_index)
    outline = ai_processor.task_topic_outline(subject, topic)
    image_path = image_builder.build_topic_card(subject, topic, outline)
    telegram_bot.send_photo(image_path, caption=f"🖼️ {subject}: {topic}")


def run():
    slot = _current_slot()
    task_name = config.TASKS[slot]
    print(f"Running slot {slot}: {task_name}")

    # Topic image doesn't need the Dawn article at all -- skip fetching it
    # to save an HTTP call when it's not needed.
    if task_name == "topic_image":
        run_topic_image()
        return

    article = fetch_article.get_latest_editorial()

    if task_name == "summary":
        run_summary(article)
    elif task_name == "vocabulary":
        run_vocabulary(article)
    elif task_name == "quiz":
        headline_pool = fetch_article.get_headline_pool()
        run_quiz(article, headline_pool, slot)
    elif task_name == "resources":
        run_resources(article)
    else:
        raise RuntimeError(f"Unknown task: {task_name}")


if __name__ == "__main__":
    try:
        run()
        print("Done.")
    except Exception:
        err = traceback.format_exc()
        print(err)
        try:
            telegram_bot.send_message(f"⚠️ Agent run failed:\n{err[-1200:]}")
        except Exception:
            pass
        raise
