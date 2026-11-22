"""Lamplight: a private journal that answers back.

Run with:  streamlit run app.py
"""
from __future__ import annotations

import html
import os
from datetime import date, datetime
from pathlib import Path

import streamlit as st

from journal import helplines, insights
from journal.llm import DEFAULT_MODELS, PROVIDERS, generate_reply, resolve_config
from journal.safety import Level, assess
from journal.storage import Store

ROOT = Path(__file__).parent
DB_PATH = os.environ.get("LAMPLIGHT_DB", str(ROOT / "data" / "journal.db"))

# (value, label, colour of the glow behind the page)
MOODS = [
    (1, "Heavy", "#6E6BB0"),
    (2, "Low", "#7E95BD"),
    (3, "Okay", "#8DB5A5"),
    (4, "Good", "#E2C46C"),
    (5, "Bright", "#EFA64A"),
]
MOOD_BY_LABEL = {label: (value, color) for value, label, color in MOODS}
MOOD_BY_VALUE = {value: (label, color) for value, label, color in MOODS}

PROMPTS = [
    "What is taking up the most room in your head right now?",
    "What went okay today, even if it was small?",
    "What are you putting off, and what is it protecting you from?",
    "Who or what made today a little easier?",
    "If tomorrow could be one percent lighter, what would change?",
    "What would you say to a friend who felt exactly how you feel?",
    "What is one thing you are carrying that isn't yours to carry?",
    "What did your body tell you today?",
]

st.set_page_config(page_title="Lamplight", page_icon="🕯️", layout="centered")


@st.cache_resource
def get_store() -> Store:
    return Store(DB_PATH)


store = get_store()


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
def inject_css(glow: str) -> None:
    css = """
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,700&family=Literata:ital,opsz,wght@0,7..72,400;0,7..72,500;1,7..72,400&display=swap');
:root{
  --ink:#1B2340; --ink-soft:#4F5878; --mist:#F1F3F8; --line:rgba(27,35,64,.11);
  --lamp:#E8A93B; --paper:#FFFFFF; --lilac:#E9E8F7; --glow:__GLOW__;
  --sans:'Bricolage Grotesque',system-ui,-apple-system,'Segoe UI',sans-serif;
  --serif:'Literata',Georgia,'Times New Roman',serif;
}
html,body,[data-testid="stAppViewContainer"],[data-testid="stApp"]{background:var(--mist)!important;color:var(--ink)}
[data-testid="stAppViewContainer"],[data-testid="stMain"]{
  background:radial-gradient(880px 520px at 50% -160px,color-mix(in srgb,var(--glow) 42%,transparent),transparent 72%),var(--mist)!important;
}
#MainMenu,footer,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
header[data-testid="stHeader"]{background:transparent!important}
.block-container{max-width:760px!important;padding:1.6rem 1.25rem 9.5rem!important}
.stApp,.stMarkdown p,.stMarkdown li,button,input,label,[data-testid="stWidgetLabel"] p{font-family:var(--sans)}
h1,h2,h3{font-family:var(--sans)!important;color:var(--ink)!important;letter-spacing:-.015em}

/* header */
.lp-head{display:flex;align-items:center;gap:.8rem;margin:0 0 .6rem}
.lp-head svg{flex:none}
.lp-name{font:700 1.3rem/1.1 var(--sans);letter-spacing:-.01em}
.lp-tag{font:400 .9rem/1.3 var(--sans);color:var(--ink-soft)}

/* tabs — React Aria selectors (Streamlit ≥1.46) */
[data-testid="stTabs"] [role="tablist"]{gap:1.5rem;border-bottom:1px solid var(--line);margin-top:.4rem;padding-bottom:0}
[data-testid="stTab"]{padding:.7rem 0!important;background:transparent!important;font-family:var(--sans)!important;font-size:1rem!important;color:var(--ink-soft)!important;border:none!important;box-shadow:none!important}
[data-testid="stTab"][aria-selected="true"]{color:var(--ink)!important;font-weight:600!important}
[data-testid="stTab"] .react-aria-SelectionIndicator{background:var(--lamp)!important;height:3px!important}
/* legacy BaseWeb fallback — keeps working if Streamlit ever reverts */
.stTabs [data-baseweb="tab-list"]{gap:1.7rem;border-bottom:1px solid var(--line)}
.stTabs button[data-baseweb="tab"]{padding:.7rem 0;background:transparent;font-size:1rem;color:var(--ink-soft)}
.stTabs button[data-baseweb="tab"][aria-selected="true"]{color:var(--ink);font-weight:600}
.stTabs [data-baseweb="tab-highlight"]{background:var(--lamp)!important;height:3px}
.stTabs [data-baseweb="tab-border"]{display:none}

/* hero */
.lp-hello{font:700 clamp(2rem,6vw,3rem)/1.06 var(--sans);letter-spacing:-.025em;margin:1.7rem 0 .55rem}
.lp-prompt{font:italic 400 1.14rem/1.6 var(--serif);color:var(--ink-soft);max-width:34rem;margin:0 0 1.1rem}
.lp-ask{font:600 .95rem var(--sans);color:var(--ink-soft);margin:1.2rem 0 .35rem}

/* writing page — React Aria selectors (Streamlit ≥1.46) */
[data-testid="stTextAreaRootElement"]{background:var(--paper)!important;border:1px solid var(--line)!important;border-radius:20px!important;box-shadow:0 26px 60px -34px var(--glow),0 1px 0 rgba(27,35,64,.04)!important;transition:box-shadow .3s,border-color .2s}
[data-testid="stTextAreaRootElement"]:focus-within{border-color:var(--lamp)!important;box-shadow:0 0 0 3px rgba(232,169,59,.28),0 26px 60px -34px var(--glow)!important}
[data-testid="stTextAreaRootElement"] textarea{font-family:var(--serif)!important;font-size:1.12rem!important;line-height:1.8!important;color:var(--ink)!important;padding:1.4rem 1.5rem!important;min-height:270px;background:transparent!important}
/* legacy BaseWeb fallback */
.stTextArea [data-baseweb="textarea"],.stTextArea [data-baseweb="base-input"]{background:var(--paper)!important;border:1px solid var(--line)!important;border-radius:20px!important;box-shadow:0 26px 60px -34px var(--glow),0 1px 0 rgba(27,35,64,.04)!important;transition:box-shadow .3s,border-color .2s}
.stTextArea [data-baseweb="textarea"]:focus-within{border-color:var(--lamp)!important;box-shadow:0 0 0 3px rgba(232,169,59,.28),0 26px 60px -34px var(--glow)!important}
.stTextArea textarea{font-family:var(--serif)!important;font-size:1.12rem!important;line-height:1.8!important;color:var(--ink)!important;padding:1.4rem 1.5rem!important;min-height:270px}
.stTextArea textarea::placeholder{font-style:italic;color:#8A91AD}
.stTextArea label{display:none}
/* label hidden for new API too */
[data-testid="stTextArea"] label,[data-testid="stTextArea"] [data-testid="stWidgetLabel"]{display:none!important}

/* select box (Settings provider dropdown) */
[data-testid="stSelectbox"] [data-baseweb="select"] > div:first-child{border-radius:12px!important;border-color:var(--line)!important;background:var(--paper)!important}
/* regular text inputs (Settings name/model) */
[data-testid="stTextInput"] input{border-radius:12px!important;background:var(--paper)!important;border-color:var(--line)!important}
[data-testid="stTextInput"] input:focus{border-color:var(--lamp)!important;box-shadow:0 0 0 3px rgba(232,169,59,.2)!important}
/* destructive delete button */
.lp-delete-btn button{background:#C0392B!important;color:#fff!important;border-color:#C0392B!important}
.lp-delete-btn button:hover{background:#922B21!important}

/* mood segmented control — React Aria (stButtonGroup) */
[data-testid="stButtonGroup"] [role="radiogroup"]{gap:.4rem}
[data-testid="stButtonGroup"] button[data-variant="segmented_control"]{border-radius:999px!important;border:1px solid var(--line)!important;background:var(--paper)!important;color:var(--ink)!important;font-family:var(--sans)!important;font-size:.92rem!important;font-weight:500!important;padding:.45rem 1rem!important;transition:background .15s,border-color .15s}
[data-testid="stButtonGroup"] button[data-variant="segmented_control"]:hover{border-color:var(--ink)!important}
[data-testid="stButtonGroup"] button[data-variant="segmented_control"][aria-checked="true"]{background:var(--ink)!important;color:#fff!important;border-color:var(--ink)!important}

/* buttons */
.stButton>button,.stDownloadButton>button{border-radius:999px;font-weight:600;padding:.6rem 1.35rem;border:1px solid var(--line);background:var(--paper);color:var(--ink);transition:background .15s,transform .05s}
.stButton>button:hover,.stDownloadButton>button:hover{border-color:var(--ink);color:var(--ink)}
.stButton>button:active{transform:translateY(1px)}
.stButton>button[kind="primary"]{background:var(--ink);color:#fff;border-color:var(--ink);padding:.75rem 1.8rem;font-size:1.02rem}
.stButton>button[kind="primary"]:hover{background:#2D3868;color:#fff}
.stButton>button:focus-visible{outline:3px solid var(--lamp);outline-offset:2px}
.stButton>button[kind="tertiary"]{border:none;background:transparent;color:var(--ink-soft);text-decoration:underline;text-underline-offset:3px;padding:.2rem 0}

/* reply */
.lp-reply{background:rgba(255,255,255,.86);border:1px solid var(--line);border-radius:20px;padding:1.5rem 1.7rem;margin:1.3rem 0;box-shadow:0 22px 50px -38px var(--glow)}
.lp-reply-head{display:flex;align-items:center;gap:.55rem;font:600 .95rem var(--sans);color:var(--ink-soft);margin-bottom:.4rem}
.lp-reply p{font:400 1.07rem/1.78 var(--serif);margin:.6rem 0;color:var(--ink);max-width:36rem}
.lp-note{font:400 .85rem/1.5 var(--sans);color:var(--ink-soft);margin:.3rem 0 0}

/* helplines */
.lp-help{background:var(--lilac);border-radius:22px;padding:1.6rem 1.7rem 1.2rem;margin:1.3rem 0;color:var(--ink)}
.lp-help h3{font:700 1.45rem/1.2 var(--sans)!important;margin:0 0 .35rem}
.lp-help .lead{font:400 1rem/1.6 var(--sans);margin:0 0 1rem;max-width:34rem}
a.lp-primary{display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap;background:var(--ink);border-radius:16px;padding:1rem 1.3rem;text-decoration:none;color:#fff!important}
a.lp-primary:hover{background:#2D3868}
a.lp-primary:focus-visible,.lp-row a:focus-visible{outline:3px solid var(--lamp);outline-offset:3px}
.lp-primary .num{font:700 2.5rem/1 var(--sans);letter-spacing:.01em;color:#fff}
.lp-primary .who{font:600 1rem var(--sans);color:#fff}
.lp-primary .sub{font:400 .88rem/1.4 var(--sans);color:rgba(255,255,255,.82);flex-basis:100%}
.lp-row{display:flex;justify-content:space-between;align-items:baseline;gap:1rem;padding:.75rem 0;border-top:1px solid rgba(27,35,64,.12)}
.lp-row:first-of-type{margin-top:1rem}
.lp-row .nm{font:600 1rem var(--sans)}
.lp-row .nt{font:400 .86rem/1.4 var(--sans);color:var(--ink-soft)}
.lp-row a{font:700 1.05rem var(--sans);color:var(--ink);text-decoration:none;white-space:nowrap;border-bottom:2px solid var(--lamp)}

/* pages — tighten nesting; remove double border on inner cards */
.lp-paper{background:var(--paper);border-radius:12px;padding:1rem 1.2rem;margin:.15rem 0 .6rem}
.lp-paper p{font:400 1.05rem/1.75 var(--serif);margin:.4rem 0}
.lp-paper.reply{background:#F6F7FB;border-top:1px solid var(--line)}
.lp-who{font:600 .82rem var(--sans);color:var(--ink-soft);margin-bottom:.35rem}
[data-testid="stExpander"]{background:var(--paper)!important;border:1px solid var(--line)!important;border-radius:16px!important;overflow:hidden}
[data-testid="stExpander"] summary p{font-family:var(--sans)!important;font-weight:600}
/* search bar */
[data-testid="stTextInput"] input{border-radius:12px!important;background:var(--paper)!important;border:1px solid var(--line)!important;padding:.55rem .9rem!important}
[data-testid="stTextInput"] input:focus{border-color:var(--lamp)!important;box-shadow:0 0 0 3px rgba(232,169,59,.2)!important}

/* patterns — constrain grid dots and fix alignment */
.lp-stats{display:flex;gap:2.4rem;flex-wrap:wrap;margin:1.6rem 0 .4rem}
.lp-stat .n{font:700 2.6rem/1 var(--sans);letter-spacing:-.02em}
.lp-stat .l{font:400 .88rem/1.3 var(--sans);color:var(--ink-soft);margin-top:.25rem;max-width:9rem}
.lp-h{font:700 1.2rem var(--sans);margin:2rem 0 .3rem}
.lp-sub{font:400 .95rem/1.55 var(--sans);color:var(--ink-soft);margin:0 0 .9rem;max-width:34rem}
.lp-grid{display:grid;grid-template-columns:repeat(7,24px);gap:6px;width:max-content}
.lp-grid .dow{font:600 .82rem var(--sans);color:var(--ink-soft);text-align:center;width:24px}
.lp-dot{width:24px;height:24px;border-radius:50%;background:rgba(27,35,64,.12);border:1.5px solid transparent;box-sizing:border-box}
.lp-dot.today{border-color:var(--ink)}
.lp-key{display:flex;gap:1rem;flex-wrap:wrap;margin-top:.8rem;font:400 .85rem var(--sans);color:var(--ink-soft)}
.lp-key i{display:inline-block;width:.8rem;height:.8rem;border-radius:50%;margin-right:.35rem;vertical-align:-1px}
.lp-bar{display:grid;grid-template-columns:11rem 1fr 2rem;align-items:center;gap:.8rem;margin:.45rem 0;font:400 .95rem var(--sans)}
.lp-bar .track{height:10px;border-radius:99px;background:rgba(27,35,64,.07);overflow:hidden}
.lp-bar .fill{height:100%;border-radius:99px;background:var(--ink)}
.lp-bar .c{color:var(--ink-soft);text-align:right}

/* breathing */
.lp-breathe{display:flex;flex-direction:column;align-items:center;gap:1rem;padding:1.6rem 0 .6rem}
.lp-orb{width:150px;height:150px;border-radius:50%;background:radial-gradient(circle at 35% 30%,#fff,var(--glow) 70%);box-shadow:0 0 70px 10px color-mix(in srgb,var(--glow) 55%,transparent);animation:orb 14s ease-in-out infinite}
.lp-cue{position:relative;height:1.6rem;width:10rem;text-align:center;font:600 1.05rem var(--sans);color:var(--ink-soft)}
.lp-cue span{position:absolute;inset:0;opacity:0}
.lp-cue .a{animation:cueA 14s infinite}.lp-cue .b{animation:cueB 14s infinite}.lp-cue .c{animation:cueC 14s infinite}
@keyframes orb{0%{transform:scale(.62)}29%,57%{transform:scale(1)}100%{transform:scale(.62)}}
@keyframes cueA{0%,26%{opacity:1}30%,100%{opacity:0}}
@keyframes cueB{0%,28%{opacity:0}32%,54%{opacity:1}58%,100%{opacity:0}}
@keyframes cueC{0%,56%{opacity:0}60%,96%{opacity:1}100%{opacity:0}}
.lp-steps{font:400 1rem/1.7 var(--sans);padding-left:1.2rem;max-width:34rem}

/* footer — increase container padding; collapse footer on mobile */
.lp-foot{position:fixed;left:0;right:0;bottom:0;z-index:60;background:rgba(241,243,248,.92);backdrop-filter:blur(8px);border-top:1px solid var(--line);padding:.6rem 1rem;text-align:center;font:400 .88rem var(--sans);color:var(--ink-soft)}
.lp-foot a{color:var(--ink);font-weight:700;text-decoration:none;border-bottom:2px solid var(--lamp)}

@media (max-width:560px){
  .lp-bar{grid-template-columns:8rem 1fr 1.6rem}
  .lp-primary .num{font-size:2.1rem}
  [data-testid="stTab"]{font-size:.88rem!important}
  .lp-foot{position:static;margin-top:2rem;border-top:1px solid var(--line)}
  .block-container{padding-bottom:2rem!important}
}
@media (min-width:561px){
  .block-container{padding-bottom:9.5rem!important}
}
@media (prefers-reduced-motion:reduce){
  .lp-orb{animation:none;transform:scale(.85)}
  .lp-cue .a,.lp-cue .b,.lp-cue .c{animation:none}
  .lp-cue .a{opacity:1}
}
"""
    st.markdown(f"<style>{css.replace('__GLOW__', glow)}</style>", unsafe_allow_html=True)


def lamp_svg(size: int = 34) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 34 34" aria-hidden="true">'
        '<circle cx="17" cy="17" r="16" fill="#E8A93B" opacity=".18"/>'
        '<path d="M17 6c3.6 3.4 6 6.2 6 9.6a6 6 0 0 1-12 0C11 12.2 13.4 9.4 17 6z" fill="#E8A93B"/>'
        '<rect x="12" y="23.5" width="10" height="3" rx="1.5" fill="#1B2340"/></svg>'
    )


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def paragraphs(text: str) -> str:
    chunks = [c.strip() for c in text.strip().split("\n\n") if c.strip()]
    return "".join(f"<p>{html.escape(c).replace(chr(10), '<br>')}</p>" for c in chunks)


def greeting(name: str) -> str:
    h = datetime.now().hour
    if 5 <= h < 12:
        base = "Good morning"
    elif 12 <= h < 17:
        base = "Good afternoon"
    elif 17 <= h < 21:
        base = "Good evening"
    else:
        base = "Still up"
    return f"{base}, {html.escape(name)}." if name else f"{base}."


def pretty_time(iso: str) -> str:
    dt = datetime.fromisoformat(iso)
    return f"{dt:%a} {dt.day} {dt:%b}, {dt.hour % 12 or 12}:{dt:%M} {'am' if dt.hour < 12 else 'pm'}"


def helpline_panel(level: Level) -> str:
    if level == Level.CRISIS:
        title = "Please talk to someone today"
        lead = (
            "What you wrote sounds really painful. You don't have to carry it alone, and these "
            "lines are free, private and open day and night."
        )
    else:
        title = "You don't have to carry this alone"
        lead = (
            "It sounds like things are heavy right now. Talking to someone can help, and these "
            "lines are free and open day and night."
        )
    p = helplines.TELE_MANAS
    rows = "".join(
        f'<div class="lp-row"><div><div class="nm">{html.escape(h.name)}</div>'
        f'<div class="nt">{html.escape(h.note)}</div></div>'
        f'<a href="tel:{h.dial}" aria-label="Call {html.escape(h.name)}">{html.escape(h.display)}</a></div>'
        for h in helplines.SECONDARY
    )
    return (
        f'<section class="lp-help" aria-label="Helplines"><h3>{title}</h3><p class="lead">{lead}</p>'
        f'<a class="lp-primary" href="tel:{p.dial}"><span class="who">Call {html.escape(p.name)}</span>'
        f'<span class="num">{p.display}</span><span class="sub">{html.escape(p.note)}</span></a>'
        f"{rows}</section>"
    )


def reply_card(reply: str) -> str:
    return (
        f'<section class="lp-reply"><div class="lp-reply-head">{lamp_svg(22)}'
        f"Lamplight</div>{paragraphs(reply)}</section>"
    )


# ---------------------------------------------------------------------------
# Session defaults
# ---------------------------------------------------------------------------
ss = st.session_state
ss.setdefault("prompt_i", date.today().toordinal() % len(PROMPTS))
ss.setdefault("result", None)
ss.setdefault("clear_draft", False)
ss.setdefault("cfg_provider", "auto")
ss.setdefault("cfg_model", "")
ss.setdefault("cfg_key", "")

mood_value, glow = MOOD_BY_LABEL.get(ss.get("mood_label") or "Okay", MOOD_BY_LABEL["Okay"])
inject_css(glow)

st.markdown(
    f'<div class="lp-head">{lamp_svg()}<div><div class="lp-name">Lamplight</div>'
    '<div class="lp-tag">A journal that answers back. Your pages are saved on this device.</div></div></div>',
    unsafe_allow_html=True,
)

name = store.get_setting("name", "")
use_memory = store.get_setting("use_memory", "0") == "1"
cfg = resolve_config(
    provider=None if ss.cfg_provider == "auto" else ss.cfg_provider,
    model=ss.cfg_model or None,
    api_key=ss.cfg_key or None,
)

tab_write, tab_pages, tab_patterns, tab_help, tab_settings = st.tabs(
    ["Write", "Pages", "Patterns", "Help", "Settings"]
)


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------
with tab_write:
    st.markdown(
        f'<h1 class="lp-hello">{greeting(name)}</h1>'
        f'<p class="lp-prompt">{html.escape(PROMPTS[ss.prompt_i])}</p>',
        unsafe_allow_html=True,
    )
    if st.button("Try another prompt", key="next_prompt", type="tertiary"):
        ss.prompt_i = (ss.prompt_i + 1) % len(PROMPTS)
        st.rerun()

    st.markdown('<div class="lp-ask">How are you arriving today?</div>', unsafe_allow_html=True)
    picked = st.segmented_control(
        "Mood",
        [label for _, label, _ in MOODS],
        default="Okay",
        key="mood_label",
        label_visibility="collapsed",
    )

    if ss.clear_draft:
        ss["draft"] = ""
        ss.clear_draft = False
    draft = st.text_area(
        "Your page",
        key="draft",
        height=290,
        max_chars=4000,
        placeholder="Start anywhere. Nobody is grading this.",
        label_visibility="collapsed",
    )

    if st.button("Save and read a reply", type="primary"):
        text = (draft or "").strip()
        if not text:
            st.warning("Write a line or two first. Even one sentence counts.")
        else:
            mood = mood_value
            verdict = assess(text, mood)
            themes = insights.detect_themes(text)
            memory = (
                [{"mood": e["mood"], "text": e["text"]} for e in reversed(store.entries(limit=3))]
                if use_memory
                else []
            )
            with st.spinner("Reading your page..."):
                reply = generate_reply(text, mood, verdict.level, themes, cfg, memory)
            entry_id = store.add_entry(
                text, mood, reply.text, int(verdict.level), themes, reply.source
            )
            ss.result = {
                "id": entry_id,
                "level": int(verdict.level),
                "reply": reply.text,
                "source": reply.source,
                "error": reply.error,
            }
            ss.clear_draft = True
            st.rerun()

    res = ss.result
    if res:
        level = Level(res["level"])
        if level == Level.CRISIS:
            st.markdown(helpline_panel(level), unsafe_allow_html=True)
        st.markdown(reply_card(res["reply"]), unsafe_allow_html=True)
        if level == Level.DISTRESS:
            st.markdown(helpline_panel(level), unsafe_allow_html=True)
        if level == Level.CRISIS:
            st.markdown(
                '<p class="lp-note">If you are in immediate danger, call 112 now.</p>',
                unsafe_allow_html=True,
            )
        if res["source"] == "offline":
            why = (
                f" Couldn't reach {html.escape(cfg.label)}: {html.escape(res['error'])}"
                if res["error"]
                else " Add an API key in Settings for fuller replies."
            )
            st.markdown(f'<p class="lp-note">This reply came from the built-in writer.{why}</p>',
                        unsafe_allow_html=True)
        st.markdown('<p class="lp-note">Saved to Pages.</p>', unsafe_allow_html=True)
        if st.button("Done for now", key="dismiss"):
            ss.result = None
            st.rerun()


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
with tab_pages:
    total = store.count()
    if total == 0:
        st.markdown(
            '<h2 class="lp-h">Nothing here yet</h2>'
            '<p class="lp-sub">Your saved pages will appear here, newest first. Write your first one in the Write tab.</p>',
            unsafe_allow_html=True,
        )
    else:
        q = st.text_input("Search your pages", placeholder="Search your pages", label_visibility="collapsed")
        rows = store.entries(limit=60, search=q.strip() or None)
        st.markdown(
            f'<p class="lp-sub">{len(rows)} of {total} pages</p>', unsafe_allow_html=True
        )
        if not rows:
            st.markdown('<p class="lp-sub">No page contains that. Try a different word.</p>',
                        unsafe_allow_html=True)
        for e in rows:
            label = f"{pretty_time(e['created_at'])}  ·  {MOOD_BY_VALUE.get(e['mood'], ('Okay',''))[0]}"
            with st.expander(label):
                st.markdown(
                    f'<div class="lp-paper"><p>{html.escape(e["text"]).replace(chr(10), "<br>")}</p></div>'
                    f'<div class="lp-paper reply"><div class="lp-who">Lamplight replied</div>{paragraphs(e["reply"])}</div>',
                    unsafe_allow_html=True,
                )
                if e["level"] >= Level.DISTRESS:
                    st.markdown(
                        f'<p class="lp-note">Support is always open: <a href="tel:14416">Tele-MANAS 14416</a>.</p>',
                        unsafe_allow_html=True,
                    )
                with st.popover("Delete this page"):
                    st.write("This removes the page from this device for good.")
                    if st.button("Delete page", key=f"del_{e['id']}"):
                        store.delete_entry(e["id"])
                        st.rerun()


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------
with tab_patterns:
    all_entries = store.entries()
    if len(all_entries) == 0:
        st.markdown(
            '<h2 class="lp-h">Patterns appear after your first few pages</h2>'
            '<p class="lp-sub">Write for a few days and this tab will show how your mood moves and what keeps coming up.</p>',
            unsafe_allow_html=True,
        )
    else:
        run = insights.streak(all_entries)
        this_w, prev_w = insights.weekly_mood(all_entries)
        avg_txt = f"{this_w:.1f}" if this_w is not None else "–"
        st.markdown(
            '<div class="lp-stats">'
            f'<div class="lp-stat"><div class="n">{len(all_entries)}</div><div class="l">pages written</div></div>'
            f'<div class="lp-stat"><div class="n">{run}</div><div class="l">{"day" if run == 1 else "days"} in a row</div></div>'
            f'<div class="lp-stat"><div class="n">{avg_txt}</div><div class="l">average mood this week, out of 5</div></div>'
            "</div>",
            unsafe_allow_html=True,
        )
        if this_w is not None and prev_w is not None:
            diff = this_w - prev_w
            if abs(diff) < 0.3:
                line = "Your mood has been about the same as the week before."
            elif diff > 0:
                line = f"Your mood is up by {diff:.1f} compared with the week before."
            else:
                line = f"Your mood is down by {abs(diff):.1f} compared with the week before. Be gentle with yourself."
            st.markdown(f'<p class="lp-sub">{line}</p>', unsafe_allow_html=True)

        days = insights.mood_by_day(all_entries, days=28)
        first_dow = days[0][0].weekday()
        cells = ['<div class="dow">' + d + "</div>" for d in "MTWTFSS"]
        cells += ["<div></div>"] * first_dow
        palette = {v: c for v, _, c in MOODS}
        for d, avg in days:
            cls = "lp-dot today" if d == date.today() else "lp-dot"
            if avg is None:
                tip = f"{d:%d %b}: no page"
                style = ""
            else:
                nearest = min(5, max(1, round(avg)))
                tip = f"{d:%d %b}: {MOOD_BY_VALUE[nearest][0]}"
                style = f' style="background:{palette[nearest]}"'
            cells.append(f'<div class="{cls}"{style} title="{tip}"></div>')
        key = "".join(f'<span><i style="background:{c}"></i>{l}</span>' for _, l, c in MOODS)
        st.markdown(
            '<h2 class="lp-h">The last four weeks</h2>'
            '<p class="lp-sub">One dot per day, coloured by how you said you felt.</p>'
            f'<div class="lp-grid" role="img" aria-label="Mood by day for the last 28 days">{"".join(cells)}</div>'
            f'<div class="lp-key">{key}</div>',
            unsafe_allow_html=True,
        )

        themes = insights.theme_counts(all_entries, days=30)
        if themes:
            top = themes[0][1]
            bars = "".join(
                f'<div class="lp-bar"><span>{html.escape(n)}</span>'
                f'<div class="track"><div class="fill" style="width:{max(6, round(100 * c / top))}%"></div></div>'
                f'<span class="c">{c}</span></div>'
                for n, c in themes[:6]
            )
            st.markdown(
                '<h2 class="lp-h">What keeps coming up</h2>'
                '<p class="lp-sub">Topics that showed up in your pages over the last 30 days.</p>' + bars,
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
with tab_help:
    st.markdown(
        '<h2 class="lp-h" style="margin-top:1.6rem">Take a minute</h2>'
        '<p class="lp-sub">Follow the light. Breathe in as it grows, hold, then let it out slowly.</p>'
        '<div class="lp-breathe" aria-live="off"><div class="lp-orb"></div>'
        '<div class="lp-cue" aria-live="polite"><span class="a">Breathe in</span><span class="b">Hold</span><span class="c">Breathe out</span></div></div>'
        '<h2 class="lp-h">If your thoughts are racing</h2>'
        '<ol class="lp-steps"><li>Name five things you can see.</li><li>Touch four things near you.</li>'
        "<li>Listen for three sounds.</li><li>Notice two things you can smell.</li>"
        "<li>Take one slow breath and name one thing you can taste.</li></ol>",
        unsafe_allow_html=True,
    )
    st.markdown(helpline_panel(Level.DISTRESS), unsafe_allow_html=True)
    st.markdown(
        '<p class="lp-sub">Lamplight is a reflection tool. It is not therapy, a diagnosis or an emergency service. '
        f"Helpline numbers were last checked in {helplines.LAST_CHECKED}.</p>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
with tab_settings:
    st.markdown('<h2 class="lp-h" style="margin-top:1.6rem">About you</h2>', unsafe_allow_html=True)
    new_name = st.text_input("What should Lamplight call you?", value=name, max_chars=40)
    new_mem = st.checkbox(
        "Let replies remember my last three pages",
        value=use_memory,
        help="Sends your last three entries to the reply model along with the new one.",
    )
    if new_name != name:
        store.set_setting("name", new_name.strip())
        st.rerun()
    if new_mem != use_memory:
        store.set_setting("use_memory", "1" if new_mem else "0")
        st.rerun()

    st.markdown('<h2 class="lp-h">Who writes the replies</h2>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="lp-sub">Right now: {html.escape(cfg.label)}. With a cloud model your entry is sent to that '
        "provider to write the reply. With Ollama or built-in replies, nothing leaves this computer.</p>",
        unsafe_allow_html=True,
    )
    options = ["auto"] + list(PROVIDERS)
    st.selectbox(
        "Provider",
        options,
        key="cfg_provider",
        format_func=lambda k: "Choose automatically from environment" if k == "auto" else PROVIDERS[k],
    )
    if ss.cfg_provider not in ("offline",):
        st.text_input(
            "Model (optional)",
            key="cfg_model",
            placeholder=DEFAULT_MODELS.get(ss.cfg_provider, "uses the provider default"),
        )
        if ss.cfg_provider not in ("ollama",):
            st.text_input(
                "API key (kept for this session only)",
                key="cfg_key",
                type="password",
                help="Not saved to disk. To keep a key, put it in your .env file instead.",
            )

    st.markdown('<h2 class="lp-h">Your data</h2>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="lp-sub">Pages are stored in one file on this computer: '
        f'<code style="font-size:.9em;word-break:break-all;background:rgba(27,35,64,.06);'
        f'padding:.1em .35em;border-radius:5px">{html.escape(str(DB_PATH))}</code></p>',
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    c1.download_button("Download as Markdown", store.export_markdown(),
                       file_name="lamplight-journal.md", mime="text/markdown",
                       use_container_width=True)
    c2.download_button("Download as JSON", store.export_json(),
                       file_name="lamplight-journal.json", mime="application/json",
                       use_container_width=True)
    with st.popover("Delete all my pages"):
        st.write("This permanently deletes every page on this device. Downloaded copies are not affected.")
        st.markdown(
            "<style>.lp-delete-btn button{background:#C0392B!important;color:#fff!important;"
            "border-color:#C0392B!important}.lp-delete-btn button:hover{background:#922B21!important}</style>",
            unsafe_allow_html=True,
        )
        with st.container():
            st.markdown('<div class="lp-delete-btn">', unsafe_allow_html=True)
            if st.button("Yes, delete everything", key="wipe"):
                store.delete_all()
                ss.result = None
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


# Always-visible support line
st.markdown(
    '<div class="lp-foot">Feeling overwhelmed? Call <a href="tel:14416">Tele-MANAS 14416</a>, free, any time. '
    "Lamplight is not a substitute for professional care.</div>",
    unsafe_allow_html=True,
)
