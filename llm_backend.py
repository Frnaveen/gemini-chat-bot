"""
Backend module for handling Google Gemini streaming interactions.
"""

import os
import warnings
from typing import Generator, List, Dict, Optional
from dotenv import load_dotenv, set_key

# Suppress deprecation and AFC warnings from SDK internals
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Dynamic SDK loading with type suppression
try:
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore
    HAS_GENAI = True
except (ImportError, AttributeError):
    HAS_GENAI = False
    genai = None  # type: ignore
    types = None  # type: ignore

try:
    import google.generativeai as legacy_genai  # type: ignore
    HAS_LEGACY_GENAI = True
except (ImportError, AttributeError):
    HAS_LEGACY_GENAI = False
    legacy_genai = None  # type: ignore

ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")
ENV_EXAMPLE_FILE = os.path.join(os.path.dirname(__file__), ".env.example")

# Gemini Model Catalog & Configuration
GEMINI_CONFIG = {
    "env_var": "GEMINI_API_KEY",
    "doc_url": "https://aistudio.google.com/app/apikey",
    "key_placeholder": "AIzaSy...",
    "default_model": "gemini-3.6-flash",
    "models": [
        "gemini-3.6-flash",
        "gemini-2.5-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro"
    ],
    "description": "Google's latest Gemini models with ultra-fast inference and reasoning."
}


def sanitize_key(key: Optional[str]) -> str:
    """Strip whitespace, quotes, and newlines from the API key."""
    if not key:
        return ""
    return key.strip().strip("'").strip('"').strip()


def get_stored_gemini_key() -> Optional[str]:
    """Retrieve Gemini API key from environment variables, .env, or .env.example."""
    # Check .env
    if os.path.exists(ENV_FILE):
        load_dotenv(ENV_FILE, override=True)
    key = os.environ.get("GEMINI_API_KEY")
    sanitized = sanitize_key(key)
    if sanitized:
        return sanitized
    
    # Fallback check in .env.example
    if os.path.exists(ENV_EXAMPLE_FILE):
        try:
            with open(ENV_EXAMPLE_FILE, "r") as f:
                for line in f:
                    if line.strip().startswith("GEMINI_API_KEY="):
                        val = line.strip().split("GEMINI_API_KEY=", 1)[1]
                        sanitized_val = sanitize_key(val)
                        if sanitized_val:
                            # Automatically persist to .env
                            persist_gemini_key(sanitized_val)
                            return sanitized_val
        except Exception:
            pass

    return None


def persist_gemini_key(api_key: str) -> bool:
    """Save the Gemini API key permanently to the .env file and environment."""
    clean_key = sanitize_key(api_key)
    if not clean_key:
        return False
    try:
        if not os.path.exists(ENV_FILE):
            with open(ENV_FILE, "w") as f:
                f.write("# Google Gemini API Key\n")
        set_key(ENV_FILE, "GEMINI_API_KEY", clean_key, quote_mode="never")
        os.environ["GEMINI_API_KEY"] = clean_key
        return True
    except Exception as e:
        print(f"Error persisting key to .env: {e}")
        os.environ["GEMINI_API_KEY"] = clean_key
        return False


def stream_gemini(
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048
) -> Generator[str, None, None]:
    """Stream completions from Google Gemini."""
    clean_key = sanitize_key(api_key)
    if not clean_key:
        yield "⚠️ **API Key Missing**: Please provide your Google Gemini API key in the sidebar before sending messages."
        return

    # Basic format sanity check for Gemini API keys
    if clean_key.startswith("sk-"):
        yield "⚠️ **Invalid Key Format**: It looks like you entered an OpenAI key (`sk-...`). For Gemini, please use a Google Gemini key from [Google AI Studio](https://aistudio.google.com/app/apikey) (starts with `AIzaSy...`)."
        return

    try:
        if HAS_GENAI and genai is not None and types is not None:
            # Modern google-genai SDK
            client = genai.Client(api_key=clean_key)
            contents = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["content"])]
                ))

            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                system_instruction=system_prompt if system_prompt else None
            )

            response = client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=config
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text

        elif HAS_LEGACY_GENAI and legacy_genai is not None:
            # Fallback legacy google-generativeai SDK
            legacy_genai.configure(api_key=clean_key)
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
            gemini_model = legacy_genai.GenerativeModel(
                model_name=model,
                generation_config=generation_config,
                system_instruction=system_prompt if system_prompt else None
            )
            
            history = []
            for msg in messages[:-1]:
                role = "user" if msg["role"] == "user" else "model"
                history.append({"role": role, "parts": [msg["content"]]})

            chat = gemini_model.start_chat(history=history)
            latest_prompt = messages[-1]["content"] if messages else ""
            response = chat.send_message(latest_prompt, stream=True)
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        else:
            yield "❌ **SDK Error**: Neither `google-genai` nor `google-generativeai` package could be loaded. Please run `pip install -r requirements.txt`."

    except Exception as e:
        err_str = str(e)
        if "API_KEY_INVALID" in err_str or "API key not valid" in err_str:
            yield (
                "❌ **Google Gemini Error**: The provided API key is invalid.\n\n"
                "👉 Please check that your key was copied correctly without extra spaces from "
                "[Google AI Studio](https://aistudio.google.com/app/apikey) (it usually starts with `AIzaSy...`)."
            )
        elif "404" in err_str or "NOT_FOUND" in err_str:
            yield (
                f"❌ **Model Error (404)**: `{model}` is not available. "
                f"Please switch model to `gemini-3.6-flash` or `gemini-1.5-flash` in the sidebar."
            )
        else:
            yield f"\n\n❌ **Google Gemini Error**: {err_str}"
