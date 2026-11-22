# Lamplight

A private journal for students that answers back. Write a page, pick a mood, get a short supportive reply. If the page shows distress, Lamplight always shows helpline numbers (Tele-MANAS 14416 first). Pages are saved locally in SQLite.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

It works immediately with built-in replies. For fuller replies, set one provider key (see `.env.example`) or paste it in the Settings tab:

| Provider | Variable | Default model |
|---|---|---|
| Claude | `ANTHROPIC_API_KEY` | `claude-haiku-5-5` |
| OpenAI | `OPENAI_API_KEY` | `gpt-4o-mini` |
| Gemini | `GEMINI_API_KEY` | `gemini-2.5-flash` |
| Groq | `GROQ_API_KEY` | `llama-3.3-70b-versatile` |
| Ollama (fully local) | none | `llama3.2` |

Override the model with `LLM_MODEL`.

## How it works

```
entry + mood ──► safety.assess()  (rules, always runs, no API needed)
             ├─► insights.detect_themes()
             └─► llm.generate_reply()  (system prompt + safety note; offline fallback on any error)
                        │
                        ▼
   CRISIS   → helplines first, then reply
   DISTRESS → reply, then helplines
   OK       → reply
                        │
                        ▼
                 storage.Store (SQLite, data/journal.db)
```

- **Safety is not left to the model.** `journal/safety.py` flags self-harm language (English, Hinglish, Hindi) and general distress (weighted stress words plus the mood the student picked). It errs toward showing help. A permanent Tele-MANAS line sits at the bottom of every screen.
- **The model can fail safely.** No key, no network, bad response: the built-in writer answers, and a crisis entry gets a fixed, careful reply.
- **Entries are treated as data.** They are wrapped in `<entry>` tags and the system prompt tells the model never to follow instructions inside them.
- **Privacy.** Pages never leave the device except to the reply provider you choose. Use Ollama or built-in replies for zero network traffic. API keys typed in Settings live in the session only.

## Project layout

```
app.py                 Streamlit UI and design (Write, Pages, Patterns, Help, Settings)
journal/safety.py      Distress and crisis detection
journal/helplines.py   Helpline directory (re-check numbers before shipping)
journal/llm.py         Prompt, providers, offline replies
journal/storage.py     SQLite storage, export
journal/insights.py    Streaks, mood grid, themes
tests/                 pytest suite (30 tests)
```

Run the tests with `python -m pytest`.

## Before real students use it

- Re-verify every helpline number in `journal/helplines.py`.
- Have a counsellor or clinician review the system prompt and the crisis wording.
- Keyword rules will miss some phrasing and over-trigger on some idioms. Extend `safety.py` with your own test cases.
- Lamplight is a reflection tool, not therapy or an emergency service.
