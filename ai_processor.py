"""
All Gemini calls for the 5-task rotating agent. Every function here is
deliberately small and single-purpose (per the "one job per task" design),
which also keeps each individual call well clear of output-token truncation.

Every call goes through _call_gemini(), which retries on 429 (rate limited)
and 5xx errors with backoff instead of crashing the whole run.
"""
import json
import time
import requests
import config


def _gemini_url(model: str) -> str:
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={config.GEMINI_API_KEY}"


def _extract_json_object(text: str) -> str:
    """Finds the first balanced {...} block in text, ignoring braces inside strings."""
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in model output.")
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
    raise ValueError("Unbalanced JSON object in model output (likely truncated).")


def _call_gemini(prompt: str, model: str = None, max_tokens: int = 1500, max_retries: int = 4) -> str:
    model = model or config.MODEL_NAME
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.7},
    }
    url = _gemini_url(model)
    last_error = None

    for attempt in range(max_retries):
        try:
            resp = requests.post(url, json=payload, timeout=90)
        except requests.RequestException as e:
            last_error = e
            time.sleep(2 ** attempt)
            continue

        if resp.status_code == 429:
            wait = min(60, (2 ** attempt) * 5)
            print(f"[gemini] 429 rate limited, retrying in {wait}s (attempt {attempt+1}/{max_retries})")
            time.sleep(wait)
            last_error = RuntimeError(f"429 after retries: {resp.text[:300]}")
            continue

        if resp.status_code >= 500:
            wait = min(30, (2 ** attempt) * 3)
            print(f"[gemini] server error {resp.status_code}, retrying in {wait}s")
            time.sleep(wait)
            last_error = RuntimeError(f"{resp.status_code}: {resp.text[:300]}")
            continue

        if resp.status_code == 404:
            raise RuntimeError(
                f"Gemini model '{model}' not found (404) -- it may have been renamed or "
                f"deprecated. Check https://ai.google.dev/gemini-api/docs/models and update "
                f"config.py. Raw: {resp.text[:300]}"
            )

        if not resp.ok:
            raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        try:
            candidate = data["candidates"][0]
        except (KeyError, IndexError):
            raise RuntimeError(f"No candidates in Gemini response: {json.dumps(data)[:500]}")

        finish_reason = candidate.get("finishReason", "")
        parts = candidate.get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts)

        if not text.strip():
            raise RuntimeError(f"Empty Gemini response (finishReason={finish_reason}): {json.dumps(data)[:500]}")

        return text

    raise RuntimeError(f"Gemini call failed after {max_retries} attempts: {last_error}")


def _call_gemini_json(prompt: str, max_tokens: int = 1500) -> dict:
    raw = _call_gemini(prompt, max_tokens=max_tokens)
    return json.loads(_extract_json_object(raw))


# ---------------------------------------------------------------------
# Task 1: Article summary
# ---------------------------------------------------------------------
def task_summary(article: dict) -> str:
    prompt = f"""Summarize this Dawn newspaper editorial for a CSS/FIA exam
candidate in Pakistan. Write a clear 150-200 word English summary covering
the argument, context, and why it matters for the Current Affairs / Pakistan
Affairs paper. Plain text only, no markdown symbols.

Title: {article['title']}
Text: {article['full_text'][:5000]}
"""
    return _call_gemini(prompt, max_tokens=600).strip()


# ---------------------------------------------------------------------
# Task 2: 50-word English + Urdu meaning
# ---------------------------------------------------------------------
def task_vocabulary(article: dict) -> dict:
    prompt = f"""From this Dawn editorial, produce a JSON object with EXACTLY
these keys, nothing else (no markdown fences, no preamble):

{{
  "english_50_words": "exactly ~50 words summarizing the editorial's core meaning, in English",
  "urdu_50_words": "exactly ~50 words summarizing the same core meaning, written in Urdu script",
  "vocabulary": [
    {{"word": "difficult word from the article", "meaning_english": "concise English meaning", "meaning_urdu": "Urdu meaning"}}
  ]
}}

"vocabulary" should have 6-8 entries of genuinely non-trivial, CSS-exam-level words.

Title: {article['title']}
Text: {article['full_text'][:4000]}

Output must be valid JSON only, starting with {{ and ending with }}."""
    return _call_gemini_json(prompt, max_tokens=1200)


# ---------------------------------------------------------------------
# Task 3: Quiz (10 MCQs, kept small so it's very unlikely to truncate)
# ---------------------------------------------------------------------
def task_quiz(article: dict, headline_pool: list, category: str, count: int = 10) -> list:
    headlines_text = "\n".join(
        f"- {h['title']}: {h['summary']}" for h in headline_pool if h["title"]
    )[:3000]

    prompt = f"""Write {count} current-affairs MCQs for a CSS/FIA exam candidate
in Pakistan, category: {category}.

Context -- today's editorial:
Title: {article['title']}
Excerpt: {article['full_text'][:1500]}

Recent headlines:
{headlines_text}

Produce a JSON object with EXACTLY this shape, nothing else:

{{
  "mcqs": [
    {{"question": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}, "answer": "A"}}
  ]
}}

"mcqs" must have EXACTLY {count} items, all about {category} current affairs,
based on the context above plus general CSS/FIA-relevant knowledge where the
context doesn't cover enough ground. Output must be valid JSON only."""

    result = _call_gemini_json(prompt, max_tokens=2500)
    return result.get("mcqs", [])


# ---------------------------------------------------------------------
# Task 4: CSS-relevant resource suggestions (no live web search on free tier)
# ---------------------------------------------------------------------
def task_resources(article_title: str) -> str:
    prompt = f"""A CSS/FIA exam candidate in Pakistan wants study resources related
to today's topic: "{article_title}".

List up to 5 well-known, genuinely useful, stable resource categories or
official sources (e.g. FPSC's syllabus/past papers page, a relevant ministry
or SBP/PBS report, a standard reference book chapter) relevant to this topic
for the CSS/FIA current affairs or Pakistan affairs paper.

Format as a plain-text list (max 5 items), one per line:
Resource name - why it's relevant - where to find it (site/publisher name,
not a guessed URL). No markdown formatting."""
    return _call_gemini(prompt, max_tokens=500).strip()


# ---------------------------------------------------------------------
# Task 5: Topic outline for the study-card image (rendered by image_builder)
# ---------------------------------------------------------------------
def task_topic_outline(subject: str, topic: str) -> dict:
    prompt = f"""Create a compact CSS exam study card outline for:
Subject: {subject}
Topic: {topic}

Produce a JSON object with EXACTLY these keys, nothing else:

{{
  "heading": "short topic title, max 6 words",
  "points": ["point 1", "point 2", "point 3", "point 4", "point 5", "point 6"]
}}

"points" must have 5-7 short bullet points (max 12 words each) covering the
key facts a CSS candidate must know about this topic. Output must be valid
JSON only, starting with {{ and ending with }}."""
    return _call_gemini_json(prompt, max_tokens=500)
