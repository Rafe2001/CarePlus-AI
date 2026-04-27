"""
CarePlus Clinic — Appointment Booking Chatbot Frontend
Run from project root:  streamlit run ui/streamlit.py
"""

import os
import sys
import uuid

import streamlit as st

# ── Path setup ─────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# ── Page config (must be first Streamlit call) ─────────────────────────────────
st.set_page_config(
    page_title="CarePlus Clinic | Book Appointment",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state defaults ─────────────────────────────────────────────────────
_DEFAULTS = {
    "thread_id": str(uuid.uuid4()),
    "booking_state": None,
    "initialized": False,
    "dark_mode": True,
    "pending_message": None,
}
def ensure_session_state_defaults():
    for _k, _v in _DEFAULTS.items():
        if _k not in st.session_state:
            st.session_state[_k] = _v

# ── Agent import ───────────────────────────────────────────────────────────────
_agent_error = None
try:
    from agent.booking_agent import process_message
    from agent.state import create_initial_stand
    from data.db import init_db, DATABASE_URL
    _AGENT_OK = True
except Exception as _e:
    _agent_error = str(_e)
    _AGENT_OK = False

    def create_initial_stand():
        return {"messages": [], "stage": "greeting", "available_options": []}

    def process_message(s, m, t):
        s["messages"].append({"role": "assistant", "content": "⚠️ Agent unavailable."})
        return s


_db_init_error = None
if _AGENT_OK:
    if DATABASE_URL:
        try:
            init_db()
        except Exception as _e:
            _db_init_error = str(_e)
    else:
        _db_init_error = "DATABASE_URL is not set"


# ── Theme tokens ───────────────────────────────────────────────────────────────
DARK = dict(
    scheme="dark",
    bg="#0D1B2A", bg2="#112233",
    card="rgba(255,255,255,0.05)", card_solid="#1A2B3C",
    border="rgba(0,191,165,0.25)", border_solid="#1E3A4A",
    text="#E8F0FE", muted="#64748B",
    accent="#00BFA5", accent_dk="#007A68",
    user_bubble="rgba(0,191,165,0.18)", bot_bubble="rgba(255,255,255,0.07)",
    sidebar="#081522",
    step_done="#00BFA5", step_active="#38BDF8", step_todo="#334155",
    shadow="0 8px 40px rgba(0,0,0,0.5)",
    input_border="rgba(0,191,165,0.4)",
    success="#10B981", error="#F87171",
)
LIGHT = dict(
    scheme="light",
    bg="#F7FAFC", bg2="#EDF3F8",
    card="rgba(255,255,255,0.96)", card_solid="#FFFFFF",
    border="rgba(0,137,123,0.18)", border_solid="#D3DCE6",
    text="#0F172A", muted="#475569",
    accent="#007C73", accent_dk="#00645D",
    user_bubble="rgba(0,124,115,0.12)", bot_bubble="rgba(255,255,255,0.98)",
    sidebar="#EAF1F7",
    step_done="#00897B", step_active="#0284C7", step_todo="#94A3B8",
    shadow="0 8px 40px rgba(0,0,0,0.1)",
    input_border="rgba(0,137,123,0.4)",
    success="#059669", error="#DC2626",
)


def T():
    return DARK if st.session_state.get("dark_mode", True) else LIGHT


# ── Booking stage metadata ─────────────────────────────────────────────────────
STAGES = [
    ("greeting",          "Greeting",       "👋"),
    ("select_speciality", "Speciality",     "🩺"),
    ("select_doctor",     "Doctor",         "👨‍⚕️"),
    ("select_date",       "Date",           "📅"),
    ("select_slot",       "Time Slot",      "🕐"),
    ("confirm",           "Review",         "📋"),
    ("collect_details",   "Your Details",   "📝"),
    ("completed",         "Confirmed",      "✅"),
]


def _stage_idx(stage: str) -> int:
    for i, (s, _, _) in enumerate(STAGES):
        if s == stage:
            return i
    return 0


def _stage_label(stage: str) -> str:
    for s, label, _ in STAGES:
        if s == stage:
            return label
    return "Greeting"


def _short_thread_id() -> str:
    thread_id = st.session_state.get("thread_id", "")
    return thread_id[:8] if thread_id else "pending"


# ── CSS injection ──────────────────────────────────────────────────────────────
def inject_css():
    t = T()
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] {{ font-family: 'Inter', sans-serif !important; }}

/* ── Input reset for cross-browser consistency ── */
input::placeholder, textarea::placeholder {{
    opacity: 0.6 !important;
}}

/* ── Background ── */
.stApp {{
    background: linear-gradient(135deg, {t['bg']} 0%, {t['bg2']} 100%) !important;
    min-height: 100vh;
    color-scheme: {t['scheme']};
}}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header {{ visibility: hidden !important; }}
.stDeployButton {{ display: none !important; }}
.viewerBadge_container__r5tak {{ display: none !important; }}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background: {t['sidebar']} !important;
    border-right: 1px solid {t['border']} !important;
}}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {{
    background: transparent !important;
    animation: fadeSlide 0.35s ease-out;
    padding: 0.2rem 0.5rem;
    margin: 0.5rem 0 !important;
}}
[data-testid="stChatMessage"] .stMarkdown p {{
    color: {t['text']} !important;
    margin: 0;
    line-height: 1.6;
}}

/* ── Ensure consistent rendering across all environments ── */
[data-testid="stChatMessage"] [data-testid="chatAvatarIcon"] {{
    font-size: 1.5rem;
}}

/* â”€â”€ Page layout â”€â”€ */
[data-testid="stAppViewContainer"] > .main > div {{
    padding-top: 1rem;
}}
[data-testid="stAppViewContainer"] .block-container {{
    max-width: 1040px;
    padding-left: 1.1rem;
    padding-right: 1.1rem;
}}
section[data-testid="stSidebar"] > div {{
    padding-top: 1rem;
}}
.hero-title {{
    font-size: 1.7rem;
    line-height: 1.1;
    font-weight: 800;
    margin: 0;
    color: {t['text']};
    letter-spacing: -0.01em;
    text-shadow: none;
}}
.hero-subtitle {{
    margin: 0.35rem 0 0 0;
    color: {t['muted']};
    font-size: 0.84rem;
    line-height: 1.5;
    max-width: 54ch;
}}
.hero-shell, .hero-meta, .hero-meta-label, .hero-meta-value {{
    display: none !important;
}}

/* ── Chat input ── */
[data-testid="stBottomBlockContainer"],
[data-testid="stBottomBlockContainer"] > div,
[data-testid="stChatInput"] {{
    background: {t['bg']} !important;
}}

[data-testid="stChatInput"] > div {{
    background: {t['card_solid']} !important;
    border: 1.5px solid {t['input_border']} !important;
    border-radius: 18px !important;
    box-shadow: 0 6px 24px rgba(15,23,42,0.10) !important;
    transition: all 0.2s ease !important;
    padding: 0.65rem 1.2rem !important;
}}

[data-testid="stChatInput"] > div:focus-within {{
    border-color: {t['accent']} !important;
    box-shadow: 0 8px 28px rgba(0,124,115,0.16) !important;
}}
[data-testid="stChatInput"] textarea {{
    color: {t['text']} !important;
    background: transparent !important;
    font-family: 'Inter', sans-serif !important;
    line-height: 1.5 !important;
    transition: all 0.2s ease !important;
    caret-color: {t['accent']} !important;
}}

[data-testid="stChatInput"] textarea::placeholder {{
    color: {t['muted']} !important;
    opacity: 1 !important;
    -webkit-text-fill-color: {t['muted']} !important;
    text-fill-color: {t['muted']} !important;
}}

[data-testid="stChatInput"] textarea:focus {{
    outline: none !important;
}}

[data-testid="stChatInput"] textarea::-webkit-scrollbar {{
    width: 6px;
}}

[data-testid="stChatInput"] textarea::-webkit-scrollbar-track {{
    background: transparent;
}}

[data-testid="stChatInput"] textarea::-webkit-scrollbar-thumb {{
    background: {t['accent']};
    border-radius: 3px;
    opacity: 0.5;
}}

/* ── Chat input button ── */
[data-testid="stChatInput"] button {{
    background: {t['accent']} !important;
    color: white !important;
    border: none !important;
    transition: all 0.2s ease !important;
}}

[data-testid="stChatInput"] button:hover {{
    background: {t['accent_dk']} !important;
    transform: scale(1.05) !important;
}}

/* ── Buttons (quick-reply) ── */
div[data-testid="stButton"] > button {{
    background: transparent !important;
    color: {t['accent']} !important;
    border: 1.5px solid {t['accent']} !important;
    border-radius: 24px !important;
    padding: 0.38rem 1rem !important;
    font-size: 0.83rem !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
    font-family: 'Inter', sans-serif !important;
    white-space: nowrap !important;
}}
div[data-testid="stButton"] > button:hover {{
    background: {t['accent']} !important;
    color: #fff !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 18px rgba(0,124,115,0.26) !important;
}}

/* ── Reset button ── */
.reset-btn > button {{
    background: rgba(248,113,113,0.08) !important;
    color: {t['error']} !important;
    border-color: {t['error']} !important;
    width: 100% !important;
    border-radius: 12px !important;
}}
.reset-btn > button:hover {{
    background: {t['error']} !important;
    color: #fff !important;
    box-shadow: 0 4px 16px rgba(248,113,113,0.3) !important;
}}

/* ── Toggle ── */
[data-testid="stToggle"] label {{ color: {t['text']} !important; }}

/* ── Card ── */
.kp-card {{
    background: {t['card']};
    border: 1px solid {t['border']};
    border-radius: 16px;
    padding: 1rem 1.25rem;
    backdrop-filter: blur(12px);
    box-shadow: {t['shadow']};
    margin-bottom: 0.75rem;
}}

/* ── Summary rows ── */
.sum-row {{
    display: flex;
    align-items: baseline;
    gap: 8px;
    padding: 0.35rem 0;
    border-bottom: 1px solid {t['border']};
    font-size: 0.82rem;
    color: {t['text']};
}}
.sum-row:last-child {{ border-bottom: none; }}
.sum-label {{
    color: {t['muted']};
    min-width: 72px;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.7px;
    flex-shrink: 0;
}}
.sum-val {{ font-weight: 600; }}

/* ── Typing dots ── */
.typing-wrap {{
    display: flex; align-items: center; gap: 5px; padding: 0.6rem 0;
}}
.dot {{
    width: 8px; height: 8px;
    background: {t['accent']};
    border-radius: 50%;
    animation: bounce 1.1s infinite;
}}
.dot:nth-child(2) {{ animation-delay: 0.18s; }}
.dot:nth-child(3) {{ animation-delay: 0.36s; }}

@keyframes bounce {{
    0%, 60%, 100% {{ transform: translateY(0); }}
    30% {{ transform: translateY(-7px); }}
}}
@keyframes fadeSlide {{
    from {{ opacity: 0; transform: translateY(8px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}

/* ── Step tracker ── */
.step-row {{ display: flex; align-items: center; gap: 8px; padding: 0.28rem 0; font-size: 0.83rem; }}
.step-done  {{ color: {t['step_done']}; font-weight: 600; }}
.step-active{{ color: {t['accent']}; font-weight: 700; }}
.step-todo  {{ color: {t['step_todo']}; opacity: 0.88; }}

/* ── Section labels ── */
.sec-label {{
    font-size: 0.67rem;
    color: {t['muted']};
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin: 0.75rem 0 0.4rem 0;
}}

[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown div {{
    color: {t['text']} !important;
}}

/* ── Divider ── */
hr {{ border-color: {t['border']} !important; margin: 0.6rem 0 !important; }}

/* ── Success banner ── */
.success-banner {{
    background: rgba(16,185,129,0.12);
    border: 1px solid {t['success']};
    border-radius: 14px;
    padding: 1.2rem 1.5rem;
    color: {t['text']};
    text-align: center;
    margin-top: 1rem;
}}
.booking-id {{
    font-size: 1.4rem;
    font-weight: 800;
    color: {t['success']};
    letter-spacing: 1px;
}}

/* ── Pulse badge ── */
@keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50%       {{ opacity: 0.4; }}
}}
.live-badge {{
    display: inline-flex; align-items: center; gap: 5px;
    font-size: 0.65rem; color: {t['accent']};
    text-transform: uppercase; letter-spacing: 1px;
}}
.live-dot {{
    width: 6px; height: 6px;
    background: {t['accent']}; border-radius: 50%;
    animation: pulse 1.6s infinite;
}}

.status-strip {{
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.65rem;
    margin: 0.4rem 0 1rem 0;
}}
.status-chip {{
    border: 1px solid {t['border']};
    background: {t['card']};
    border-radius: 14px;
    padding: 0.7rem 0.85rem;
    box-shadow: {t['shadow']};
}}
.status-chip-label {{
    font-size: 0.62rem;
    letter-spacing: 1.4px;
    text-transform: uppercase;
    color: {t['muted']};
}}
.status-chip-value {{
    margin-top: 0.25rem;
    font-size: 0.9rem;
    font-weight: 700;
    color: {t['text']};
}}
.status-chip-note {{
    margin-top: 0.2rem;
    font-size: 0.78rem;
    color: {t['muted']};
    line-height: 1.4;
}}
@media (max-width: 860px) {{
    .hero-shell {{
        flex-direction: column;
        align-items: flex-start;
    }}
    .hero-meta {{
        width: 100%;
    }}
    .status-strip {{
        grid-template-columns: 1fr;
    }}
}}
</style>
""", unsafe_allow_html=True)


# ── Agent helpers ──────────────────────────────────────────────────────────────
def send_message(user_msg: str):
    state = st.session_state.booking_state or create_initial_stand()
    try:
        new_state = process_message(state, user_msg, st.session_state.thread_id)
        st.session_state.booking_state = new_state
    except Exception as exc:
        state["messages"].append({
            "role": "assistant",
            "content": f"⚠️ Something went wrong: {exc}. Please try again or click *Start Over*.",
        })
        st.session_state.booking_state = state


def reset_session():
    st.session_state.booking_state = None
    st.session_state.initialized = False
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.pending_message = None


# ── Sidebar ────────────────────────────────────────────────────────────────────
def render_sidebar():
    t = T()
    state = st.session_state.booking_state
    current_stage = state["stage"] if state else "greeting"
    with st.sidebar:
        # ── Branding ──
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        if os.path.exists(logo_path):
            st.image(logo_path, width=148)
        else:
            st.markdown(f"""
<div style="text-align:left;padding:0.5rem 0 0.4rem 0;">
  <div style="font-size:2.8rem;line-height:1;">🏥</div>
  <div style="font-size:1.4rem;font-weight:800;color:{t['accent']};letter-spacing:-0.5px;margin-top:0.3rem;">CarePlus</div>
  <div style="font-size:0.65rem;color:{t['muted']};letter-spacing:3px;text-transform:uppercase;">CLINIC</div>
  <div class="live-badge" style="margin-bottom:0.45rem;">
    <span class="live-dot"></span> AI Assistant
  </div>
</div>""", unsafe_allow_html=True)

        st.markdown("<hr>", unsafe_allow_html=True)

        # ── Dark / Light toggle ──
        st.markdown(
            f"<div style='padding:0.1rem 0 0.55rem 0;color:{t['muted']};font-size:0.78rem;line-height:1.5;'>"
            f"Thread {_short_thread_id()} · {_stage_label(current_stage)}"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.markdown(f"<p class='sec-label'>🎨 Appearance</p>", unsafe_allow_html=True)
        current_dark = st.session_state.get("dark_mode", True)
        new_dark = st.toggle("Dark Mode", value=current_dark, key="dark_toggle")
        if new_dark != current_dark:
            st.session_state.dark_mode = new_dark
            st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)

        # ── Progress tracker ──
        state = st.session_state.booking_state
        current_stage = state["stage"] if state else "greeting"
        current_idx = _stage_idx(current_stage)

        st.markdown(f"<p class='sec-label'>📍 Booking Progress</p>", unsafe_allow_html=True)

        steps_html = ""
        for i, (_, label, icon) in enumerate(STAGES):
            if i < current_idx:
                css = "step-done";  marker = "✓"
            elif i == current_idx:
                css = "step-active"; marker = "▶"
            else:
                css = "step-todo";  marker = "○"
            steps_html += f'<div class="step-row {css}"><span>{marker}</span><span>{icon} {label}</span></div>'

        st.markdown(steps_html, unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)

        # ── Booking summary ──
        if state:
            items = []
            if state.get("selected_speciality"):
                items.append(("🩺 Dept",    state["selected_speciality"]))
            if state.get("selected_doctor"):
                doc = state["selected_doctor"]
                items.append(("👨‍⚕️ Doctor", doc.get("name", "—")))
            if state.get("selected_date"):
                items.append(("📅 Date",    state["selected_date"]))
            if state.get("selected_time"):
                items.append(("🕐 Time",    state["selected_time"]))
            if state.get("customer_name"):
                items.append(("👤 Patient", state["customer_name"]))

            if items:
                st.markdown(f"<p class='sec-label'>📋 Your Booking</p>", unsafe_allow_html=True)
                rows = "".join(
                    f'<div class="sum-row"><span class="sum-label">{lbl}</span><span class="sum-val">{val}</span></div>'
                    for lbl, val in items
                )
                st.markdown(f'<div class="kp-card" style="padding:0.6rem 0.9rem;">{rows}</div>',
                            unsafe_allow_html=True)

        # ── Reset ──
        st.markdown("<br>", unsafe_allow_html=True)
        with st.container():
            st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
            if st.button("🔄 Start Over", use_container_width=True, key="reset_btn"):
                reset_session()
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # ── Footer ──
        st.markdown(f"""
<div style="position:fixed;bottom:0.8rem;left:0;right:0;text-align:center;pointer-events:none;">
  <p style="font-size:0.65rem;color:{t['muted']};margin:0;">CarePlus Clinic © 2026 · AI Booking Assistant</p>
</div>""", unsafe_allow_html=True)


# ── Header ─────────────────────────────────────────────────────────────────────
def render_header(state: dict | None = None):
    t = T()
    st.markdown(f"""
<div style="padding:0.65rem 0 0.25rem 0;">
  <div class="live-badge" style="margin-bottom:0.3rem;">
    <span class="live-dot"></span> Clinic intake
  </div>
  <h1 class="hero-title">Appointment Booking</h1>
  <p class="hero-subtitle">CarePlus Clinic · AI-powered intake for booking, rescheduling, and appointment support.</p>
</div>""", unsafe_allow_html=True)


# ── Message list ───────────────────────────────────────────────────────────────
def render_messages():
    state = st.session_state.booking_state
    if not state:
        return
    for msg in state.get("messages", []):
        role    = msg.get("role", "assistant")
        content = msg.get("content", "").strip()
        if not content:
            continue
        avatar = "🏥" if role == "assistant" else "👤"
        with st.chat_message(role, avatar=avatar):
            st.markdown(content)


# ── Quick-reply buttons ────────────────────────────────────────────────────────
def render_quick_replies():
    state = st.session_state.booking_state
    if not state:
        return

    options = []
    for msg in reversed(state.get("messages", [])):
        if msg.get("role") == "assistant" and msg.get("options"):
            options = msg["options"]
            break
    if not options:
        options = state.get("available_options", [])

    if not options:
        return

    t = T()
    st.markdown(f"<p style='font-size:0.75rem;color:{t['muted']};margin:0.5rem 0 0.3rem 0;'>Quick replies:</p>",
                unsafe_allow_html=True)

    per_row = 2 if len(options) > 2 else len(options)
    cols = st.columns(per_row)
    for i, opt in enumerate(options):
        with cols[i % per_row]:
            if st.button(opt, key=f"qr_{opt}_{i}"):
                st.session_state.pending_message = opt
                st.rerun()


# ── Completion banner ──────────────────────────────────────────────────────────
def render_completion(state: dict):
    t = T()
    stage = state.get("stage", "")

    if stage == "completed":
        booking_id = state.get("booking_id", "N/A")
        doctor     = state.get("selected_doctor", {})
        date       = state.get("selected_date", "—")
        time       = state.get("selected_time", "—")
        name       = state.get("customer_name", "—")

        st.markdown(f"""
<div class="success-banner">
  <div style="font-size:2rem;margin-bottom:0.4rem;">🎉</div>
  <div style="font-weight:700;font-size:1.05rem;margin-bottom:0.6rem;">Appointment Confirmed!</div>
  <div class="booking-id">{booking_id}</div>
  <div style="font-size:0.82rem;margin-top:0.8rem;opacity:0.85;">
    <b>Doctor:</b> {doctor.get('name','—')} &nbsp;|&nbsp;
    <b>Date:</b> {date} &nbsp;|&nbsp;
    <b>Time:</b> {time}<br>
    <b>Patient:</b> {name}
  </div>
</div>""", unsafe_allow_html=True)

        ics_data = state.get("ics_data")
        if ics_data:
            st.markdown("<br>", unsafe_allow_html=True)
            st.download_button(
                label="📅 Download Calendar Invite (.ics)",
                data=ics_data,
                file_name=f"CarePlus_appointment_{booking_id}.ics",
                mime="text/calendar",
                use_container_width=True,
                type="primary",
            )

    elif stage == "cancelled":
        st.info("🚫 Your booking was cancelled. Click **Start Over** in the sidebar to begin again.")


# ── Main ───────────────────────────────────────────────────────────────────────
def render_sidebar():
    t = T()
    state = st.session_state.booking_state
    current_stage = state["stage"] if state else "greeting"
    with st.sidebar:
        st.markdown(f"""
<div style="padding:0.35rem 0 0.15rem 0;">
  <div style="font-size:2rem;line-height:1;">🏥</div>
  <div style="font-size:1.18rem;font-weight:800;color:{t['text']};letter-spacing:-0.3px;margin-top:0.18rem;">CarePlus</div>
  <div style="font-size:0.62rem;color:{t['muted']};letter-spacing:3px;text-transform:uppercase;">Clinic</div>
  <div class="live-badge" style="margin-top:0.28rem;">
    <span class="live-dot"></span> AI Assistant
  </div>
</div>""", unsafe_allow_html=True)

        current_dark = st.session_state.get("dark_mode", True)
        new_dark = st.toggle("Dark Mode", value=current_dark, key="dark_toggle")
        if new_dark != current_dark:
            st.session_state.dark_mode = new_dark
            st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)

        current_idx = _stage_idx(current_stage)
        steps_html = ""
        for i, (_, label, icon) in enumerate(STAGES):
            if i < current_idx:
                css = "step-done"; marker = "✓"
            elif i == current_idx:
                css = "step-active"; marker = "▶"
            else:
                css = "step-todo"; marker = "○"
            steps_html += f'<div class="step-row {css}"><span>{marker}</span><span>{icon} {label}</span></div>'
        st.markdown(steps_html, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Start Over", use_container_width=True, key="reset_btn"):
            reset_session()
            st.rerun()


def render_header(state: dict | None = None):
    st.markdown("""
<div style="padding:0.4rem 0 0.2rem 0;">
  <div class="live-badge" style="margin-bottom:0.35rem;">
    <span class="live-dot"></span> Clinic intake
  </div>
  <h1 class="hero-title">Appointment Booking</h1>
  <p class="hero-subtitle">CarePlus Clinic · AI-powered intake for booking, rescheduling, and appointment support.</p>
</div>""", unsafe_allow_html=True)


def main():
    ensure_session_state_defaults()
    inject_css()
    render_sidebar()

    if _db_init_error:
        st.warning(f"Database startup notice: {_db_init_error}")

    # ── Agent error banner ──
    if _agent_error:
        st.error(f"⚠️ **Agent failed to load:** `{_agent_error}`")
        st.info("Run `streamlit run ui/streamlit.py` from the **project root** (`d:/clinic_chatbot`) and ensure all dependencies are installed.")
        st.stop()

    render_header(st.session_state.booking_state)
    st.markdown("<hr>", unsafe_allow_html=True)

    # ── First-run: trigger greeting ──
    if not st.session_state.initialized:
        st.session_state.initialized = True
        with st.spinner(""):
            send_message("hi")
        st.rerun()

    # ── Handle pending quick-reply ──
    if st.session_state.pending_message:
        msg = st.session_state.pending_message
        st.session_state.pending_message = None
        
        # Immediate UI feedback
        with st.chat_message("user", avatar="👤"):
            st.markdown(msg)
        typing_placeholder = st.empty()
        with typing_placeholder.chat_message("assistant", avatar="🏥"):
            st.markdown('<div class="typing-wrap"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>', unsafe_allow_html=True)
            
        send_message(msg)
        st.rerun()

    # ── Render chat history ──
    render_messages()

    # ── Terminal states ──
    state = st.session_state.booking_state
    stage = state["stage"] if state else "greeting"

    if stage in ("completed", "cancelled"):
        render_completion(state)
        return

    # ── Quick-reply options ──
    render_quick_replies()

    # ── Free-text input ──
    if user_input := st.chat_input("Type your message…"):
        # Immediate UI feedback
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)
        typing_placeholder = st.empty()
        with typing_placeholder.chat_message("assistant", avatar="🏥"):
            st.markdown('<div class="typing-wrap"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>', unsafe_allow_html=True)
            
        send_message(user_input)
        st.rerun()


if __name__ == "__main__":
    main()
