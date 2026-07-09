# CSS/FIA Rotating Prep Agent (5 tasks, every 30 minutes)

One focused job every 30 minutes, cycling through 5 tasks, delivered to
Telegram. Built entirely on free services: GitHub Actions, Google Gemini
free tier, Telegram bot.

## How the rotation works

A single scheduled job fires every 30 minutes. Each run does **one** task,
picked purely from the current time (no external state needed) — so a full
cycle takes 2.5 hours, and each task runs about 9-10 times per day:

| Slot | Task | What it sends |
|---|---|---|
| 1 | **Article summary** | 150-200 word English summary of today's Dawn editorial |
| 2 | **50-word meaning** | 50-word gist in English, 50-word gist in Urdu, plus 6-8 vocabulary words with Urdu meanings |
| 3 | **Quiz** | 10 MCQs with an answer key (alternates Pakistan / International each time it runs) |
| 4 | **CSS resources** | Suggested study resource categories relevant to today's topic |
| 5 | **Topic image** | A designed study-card PNG covering a CSS/FIA syllabus topic (rotates through Pakistan Affairs, Current Affairs, International Relations, Islamic Studies, English Grammar, etc.) |

This design keeps Gemini API usage light and predictable: ~48 calls/day
total across all 5 task types combined, all on `gemini-2.5-flash-lite`,
which has a materially higher free daily quota than full Flash.

## What was fixed from earlier versions

1. **Model name**: `gemini-2.0-flash` was deprecated by Google on
   **June 1, 2026** — that's why nothing worked before. Now using
   `gemini-2.5-flash-lite`.
2. **"Article unavailable" bug**: the old scraper looked for one specific
   CSS class on Dawn's article pages, which doesn't reliably exist. The new
   `fetch_article.py` grabs all paragraph text, trims Dawn's standard
   trailing boilerplate, retries failed requests, and falls back to the
   page's meta description if paragraph scraping comes up short — so you
   get a real article body, not just a 1-2 line RSS teaser.
3. **Truncated JSON crashes**: every task's AI call is now small and
   single-purpose (10 MCQs, not 50; one summary; one vocab set), which
   keeps responses well under the output token limit.
4. **Retry with backoff**: a `429` (rate limited) or server error now waits
   and retries automatically instead of killing the run.
5. **Image generation without a paid API**: Gemini's image generation
   (Nano Banana) is a paid feature, so Task 5 instead renders a clean
   study-card PNG locally using `matplotlib` (which ships its own font, so
   it works on a bare GitHub runner with zero extra setup) — no image API
   quota consumed at all.

---

## Step-by-step setup

### Step 1 — Free Gemini API key
https://aistudio.google.com/app/apikey → sign in → **Create API Key** → copy it.

### Step 2 — Telegram bot
Message **@BotFather** → `/newbot` → follow prompts → copy the token.
Send your bot any message first (e.g. "hi") so it's allowed to message you back.

### Step 3 — GitHub repo
New repository (Public, for unlimited free Actions minutes) → leave
README/.gitignore/license off.

### Step 4 — Upload these files
`config.py`, `fetch_article.py`, `ai_processor.py`, `image_builder.py`,
`topics.py`, `telegram_bot.py`, `main_agent.py`, `requirements.txt`, `README.md`
via **Add file → Upload files → Commit changes**.

### Step 5 — Create the workflow file
Browser drag-and-drop often fails on the hidden `.github` folder, so create
it directly:
1. **Add file → Create new file**
2. Filename: `.github/workflows/agent.yml`
3. Paste in that file's contents
4. **Commit changes**

### Step 6 — Add secrets
`Settings → Secrets and variables → Actions → New repository secret`:

| Name | Value |
|---|---|
| `GEMINI_API_KEY` | key from Step 1 |
| `TELEGRAM_BOT_TOKEN` | token from Step 2 |
| `TELEGRAM_CHAT_ID` | `6345421988` |

### Step 7 — Enable Actions, then test manually
**Actions** tab → enable if prompted → click **"CSS/FIA Rotating Agent (every 30 min)"**
→ **Run workflow** → **Run workflow**. Wait a minute, refresh, click the run
to watch logs. Check Telegram — you'll get whichever task matches the
current time slot. Run it manually a few times to see different task types.

### Step 8 — Done
Once one manual run succeeds, you're finished — it fires every 30 minutes,
forever, from GitHub's own servers.

---

## Troubleshooting

- **"Gemini model not found (404)"**: Google renamed/retired the model.
  Open `config.py`, update `MODEL_NAME` to whatever's current at
  https://ai.google.dev/gemini-api/docs/models.
- **429 errors repeating**: your account's quota may be tighter than usual.
  Tell me your numbers from AI Studio and I'll widen the spacing (e.g. every
  45-60 min instead of 30) to fit.
- **Still see short/generic summaries**: check the workflow log for which
  `source` the article came from (`full_article`, `rss_summary_fallback`,
  or `title_only_fallback`) — printed by `fetch_article.py`. If it's
  consistently falling back, Dawn's page structure may have changed again;
  send me a run log and I'll adjust the scraper.
- **GitHub pauses scheduled workflows after 60 days of zero repo activity**
  — a small commit or manual run every couple of months keeps it alive.

## File overview

- `config.py` — secrets, model name, task rotation order
- `fetch_article.py` — resilient Dawn RSS + article-body fetcher
- `ai_processor.py` — the 5 task functions, all Gemini calls with retry/backoff
- `image_builder.py` — renders the Task 5 study-card PNG with matplotlib
- `topics.py` — rotating pool of CSS/FIA syllabus topics for Task 5
- `telegram_bot.py` — send text / document / photo to Telegram
- `main_agent.py` — single entry point; picks the task for "now" and runs it
- `.github/workflows/agent.yml` — the every-30-minutes schedule
