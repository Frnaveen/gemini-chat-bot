import os
import json
import streamlit as st
from dotenv import load_dotenv

import llm_backend

# Load environment variables
load_dotenv(override=True)

# --- Page Configuration ---
st.set_page_config(
    page_title="Gemini AI Chatbot Studio",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Load Custom CSS ---
def load_css():
    css_path = os.path.join(os.path.dirname(__file__), "styles.css")
    if os.path.exists(css_path):
        with open(css_path, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# --- Initialize Session State ---
stored_key = llm_backend.get_stored_gemini_key() or ""

if "messages" not in st.session_state:
    st.session_state.messages = []

if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = "You are a helpful, brilliant, and concise AI assistant powered by Google Gemini."

if "gemini_api_key" not in st.session_state or (not st.session_state.gemini_api_key and stored_key):
    st.session_state.gemini_api_key = stored_key

# --- Callback for API Key Updates ---
def on_api_key_change():
    raw_key = st.session_state.gemini_key_input
    new_key = llm_backend.sanitize_key(raw_key)
    st.session_state.gemini_api_key = new_key
    if new_key:
        llm_backend.persist_gemini_key(new_key)

# --- Sidebar Configuration ---
with st.sidebar:
    st.markdown('<div class="sidebar-header">⚙️ Gemini Configuration</div>', unsafe_allow_html=True)
    
    # 1. Model Selection
    gemini_info = llm_backend.GEMINI_CONFIG
    selected_model = st.selectbox(
        "Gemini Model",
        options=gemini_info["models"],
        index=0,
        help=gemini_info["description"]
    )

    st.markdown("---")

    # 2. API Key Authentication & Auto-Saving
    st.markdown("### 🔑 Gemini API Key")
    
    # Text input with key persistence
    api_key_input = st.text_input(
        "API Key",
        value=st.session_state.gemini_api_key,
        type="password",
        placeholder=gemini_info["key_placeholder"],
        help=f"Enter your Gemini API key. Get a free key at: {gemini_info['doc_url']}",
        key="gemini_key_input",
        on_change=on_api_key_change
    )
    
    # Ensure sync & sanitization
    active_api_key = llm_backend.sanitize_key(api_key_input or st.session_state.gemini_api_key)
    if active_api_key and active_api_key != stored_key:
        llm_backend.persist_gemini_key(active_api_key)
        stored_key = active_api_key

    # Status Indicators & Actions
    col_link, col_status = st.columns([1.2, 1])
    with col_link:
        st.markdown(f"[Get Free Key ↗]({gemini_info['doc_url']})", unsafe_allow_html=True)
    with col_status:
        if active_api_key:
            st.markdown('<span style="color: #4ade80; font-size: 0.85rem; font-weight: 600;">● Saved & Ready</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span style="color: #facc15; font-size: 0.85rem; font-weight: 600;">○ Key Required</span>', unsafe_allow_html=True)

    # Save button for explicit confirmation if user desires
    if active_api_key:
        if st.button("💾 Save Key to .env", use_container_width=True, help="Permanently save key to .env file"):
            llm_backend.persist_gemini_key(active_api_key)
            st.success("API Key saved to .env!")

    st.markdown("---")

    # 3. Advanced Parameters
    with st.expander("🛠️ Advanced Parameters", expanded=False):
        system_prompt = st.text_area(
            "System Instructions / Persona",
            value=st.session_state.system_prompt,
            help="Define how Gemini should behave, its tone, or specific instructions."
        )
        st.session_state.system_prompt = system_prompt

        temperature = st.slider(
            "Temperature (Creativity)",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.05,
            help="Lower values are more deterministic; higher values are more creative."
        )

        max_tokens = st.slider(
            "Max Output Tokens",
            min_value=256,
            max_value=4096,
            value=2048,
            step=256,
            help="Maximum length of the generated response."
        )

    st.markdown("---")

    # 4. Conversation Controls
    st.markdown("### 💬 Chat Controls")
    col_clear, col_export = st.columns(2)
    with col_clear:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    with col_export:
        if st.session_state.messages:
            chat_export_json = json.dumps(st.session_state.messages, indent=2)
            st.download_button(
                label="📥 Export",
                data=chat_export_json,
                file_name="gemini_chat_history.json",
                mime="application/json",
                use_container_width=True
            )
        else:
            st.button("📥 Export", disabled=True, use_container_width=True)


# --- Main Chat Interface ---

# Hero Header
st.markdown(f"""
<div class="hero-header">
    <div class="hero-title">✨ Gemini AI Chatbot</div>
    <div class="hero-subtitle">Interactive Google Gemini assistant with real-time response streaming.</div>
    <div class="status-badge-container">
        <div class="status-badge">⚡ Provider: <strong>Google Gemini</strong></div>
        <div class="status-badge">🤖 Model: <strong>{selected_model}</strong></div>
        <div class="status-badge {'badge-connected' if active_api_key else 'badge-pending'}">
            {'🟢 Backend Ready & Saved' if active_api_key else '🟡 API Key Pending'}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# If no API Key is provided, display friendly setup banner
if not active_api_key:
    st.markdown(f"""
    <div class="api-key-banner">
        <div class="api-key-banner-icon">🔐</div>
        <div>
            <div class="api-key-banner-title">Enter your Google Gemini API Key to connect backend</div>
            <p class="api-key-banner-desc">
                Please enter your Gemini API key in the sidebar before sending messages.
                Don't have a key? <a href="{gemini_info['doc_url']}" target="_blank" style="color: #60a5fa; text-decoration: underline;">Get a free Gemini API key from Google AI Studio</a>.
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Starter Suggestions when conversation is empty
if not st.session_state.messages:
    st.markdown("##### 💡 Starter Prompts")
    col1, col2 = st.columns(2)
    
    starter_prompts = [
        ("🚀 Code Architecture", "Design a scalable REST API architecture using FastAPI and PostgreSQL."),
        ("🧠 Explain a Concept", "Explain Quantum Computing and superposition using a simple analogy."),
        ("📊 Data Analysis Plan", "Outline a comprehensive machine learning pipeline for customer churn prediction."),
        ("✍️ Creative Writing", "Write an engaging sci-fi short story about an AI discovering emotion.")
    ]
    
    for i, (title, prompt_text) in enumerate(starter_prompts):
        col = col1 if i % 2 == 0 else col2
        with col:
            if st.button(f"**{title}**\n\n_{prompt_text}_", key=f"starter_{i}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": prompt_text})
                st.rerun()

# Display Conversation History
for msg in st.session_state.messages:
    avatar = "👤" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# Chat Input Handler
user_input = st.chat_input("Type your message here...")

if user_input:
    # Append user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Display user message
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    # Generate assistant response
    with st.chat_message("assistant", avatar="🤖"):
        if not active_api_key:
            error_msg = "⚠️ **API Key Required**: Please enter your Gemini API key in the left sidebar to connect the backend and receive responses."
            st.warning(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
        else:
            response_stream = llm_backend.stream_gemini(
                api_key=active_api_key,
                model=selected_model,
                messages=st.session_state.messages,
                system_prompt=st.session_state.system_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
            # Stream tokens in real-time
            full_response = st.write_stream(response_stream)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
