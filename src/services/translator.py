"""LLM-backed translation service.

Calls an OpenAI-compatible chat-completions endpoint (Gitee AI by default) to
translate a note. The prompt template lives in ``prompts/translate_prompt.md``
at the repository root, so it can be edited without touching Python code.

Credentials are read from ``.env`` at the repository root:

    API_KEY=...
    BASE_URL=https://ai.gitee.com/v1
    MODEL_NAME=Qwen3-Next-80B-A3B-Instruct

See ``.env.example`` for a template. ``.env`` is git-ignored -- never commit it.
"""

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# .../MyNoteTaking-main   (this file is src/services/translator.py)
ROOT_DIR = Path(__file__).resolve().parents[2]
PROMPT_PATH = ROOT_DIR / "prompts" / "translate_prompt.md"

load_dotenv(ROOT_DIR / ".env")

API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL", "https://ai.gitee.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen3-Coder-30B-A3B-Instruct")

# Seconds to wait for the model before giving up, so a hung request cannot
# block a Flask worker forever.
REQUEST_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "90"))

# Languages the UI offers. Kept in one place so the frontend and backend agree.
SUPPORTED_LANGUAGES = [
    "Chinese",
    "English",
    "Japanese",
    "Korean",
    "French",
    "German",
    "Spanish",
    "Russian",
]

SYSTEM_MESSAGE = (
    "You are a professional translator. "
    "You always reply with a single valid JSON object and nothing else."
)


class TranslationError(Exception):
    """Raised when the translation service cannot produce a result."""


def load_prompt_template(prompt_path: Path = PROMPT_PATH) -> str:
    """Read the prompt template from disk."""
    if not prompt_path.exists():
        raise TranslationError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def build_prompt(title: str, content: str, target_language: str) -> str:
    """Fill the template's placeholders.

    Uses plain string replacement (not str.format) so the JSON braces in the
    template stay literal.
    """
    return (
        load_prompt_template()
        .replace("{{target_language}}", target_language)
        .replace("{{title}}", title or "")
        .replace("{{content}}", content or "")
    )


# Some models (e.g. Qwen3 in thinking mode) prepend a reasoning block that
# must not reach the JSON parser. The tag is assembled from fragments so the
# literal markup never appears in this source file.
_THINK_OPEN = "<thi" "nk>"
_THINK_CLOSE = "</thi" "nk>"
_THINK_RE = re.compile(
    re.escape(_THINK_OPEN) + r".*?" + re.escape(_THINK_CLOSE),
    re.DOTALL,
)


def _strip_thinking(text: str) -> str:
    """Remove any chain-of-thought block some models prepend."""
    return _THINK_RE.sub("", text).strip()


def _extract_json(text: str) -> dict:
    """Pull a JSON object out of the model's reply.

    Models occasionally wrap the object in ```json fences or add a sentence
    around it, so we try progressively looser strategies.
    """
    text = _strip_thinking(text)

    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError as exc:
            raise TranslationError("Model returned malformed JSON") from exc

    raise TranslationError("Model did not return JSON")


def translate_note(title: str, content: str, target_language: str) -> dict:
    """Translate a note into ``target_language``.

    Returns a dict with ``detected_source_language``, ``target_language``,
    ``translated_title`` and ``translated_content``.
    """
    if not API_KEY:
        raise TranslationError(
            "API_KEY is not set. Create a .env file at the repository root "
            "(copy .env.example) and fill in your credentials."
        )

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=REQUEST_TIMEOUT)

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user", "content": build_prompt(title, content, target_language)},
            ],
            temperature=0.3,
        )
    except Exception as exc:  # network / auth / rate-limit errors
        raise TranslationError(f"LLM request failed: {exc}") from exc

    raw = response.choices[0].message.content or ""
    result = _extract_json(raw)

    return {
        "detected_source_language": result.get("detected_source_language", ""),
        "target_language": result.get("target_language") or target_language,
        "translated_title": result.get("translated_title", ""),
        "translated_content": result.get("translated_content", ""),
    }
