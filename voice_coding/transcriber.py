"""Transcription backends — Gemini Flash and OpenAI gpt-4o-mini-transcribe."""

from google import genai
from google.genai import types
from openai import OpenAI

from voice_coding.memory import load_memory

GEMINI_MODEL = "gemini-3-flash-preview"
OPENAI_MODEL = "gpt-4o-mini-transcribe"

GEMINI_BASE_PROMPT = (
    "Transcribe this audio exactly as spoken. Output ONLY the transcription text. "
    "No preamble, no labels, no commentary. Start directly with the spoken content. "
    "Rules:\n"
    "- Remove filler words: um, uh, like, you know, hmm, so, basically, right\n"
    "- Fix minor grammar issues (subject-verb agreement, missing articles) but preserve the speaker's original wording and meaning\n"
    "- Do NOT rephrase, summarize, or add content that was not spoken\n"
    "- Do NOT hallucinate or generate text if the audio is silent or unclear — output nothing instead\n"
    "- Preserve technical terms, code references, and proper nouns exactly as spoken\n"
    "- This is a software developer dictating into a text field\n"
    "- Default developer vocabulary (prefer these spellings when the audio matches):\n"
    "  - 'VS Code' (editor, not 'V.S. code')\n"
    "  - 'GitHub' (not 'get hub')\n"
    "  - 'npm' (package manager)\n"
    "  - 'API' (not 'A.P.I.')\n"
    "  - 'CLI' (command line interface)\n"
    "  - 'JSON' (not 'Jason')\n"
    "  - 'regex' (regular expression)\n"
    "  - 'localhost' (not 'local host')"
)

# OpenAI's transcription prompt param biases vocabulary/style — it is not an
# instruction channel like a chat system prompt. Keep it term-focused.
OPENAI_VOCAB_PROMPT = (
    "Software developer dictating code, code-switching between English and "
    "Traditional Chinese (繁體中文). Common terms: VS Code, GitHub, npm, API, "
    "CLI, JSON, regex, localhost, TypeScript, Python, Docker, Kubernetes, "
    "PostgreSQL, Redis, async, await, bash, zsh, stdout, stderr."
)

# Cap memory injected into OpenAI prompt. gpt-4o-transcribe's prompt accepts
# more than Whisper's 224 tokens, but there is still a limit — stay well under.
OPENAI_MEMORY_CHAR_LIMIT = 2000


def _build_gemini_prompt() -> str:
    """Build Gemini prompt, appending memory.md if found."""
    memory = load_memory()
    if not memory:
        return GEMINI_BASE_PROMPT
    return GEMINI_BASE_PROMPT + "\n\n--- Project-specific context (from .voice-coding/memory.md) ---\n\n" + memory


def _transcribe_gemini(wav_bytes: bytes, api_key: str) -> str:
    client = genai.Client(api_key=api_key)
    prompt = _build_gemini_prompt()

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            prompt,
            types.Part.from_bytes(data=wav_bytes, mime_type="audio/wav"),
        ],
        config=types.GenerateContentConfig(
            max_output_tokens=8192,
        ),
    )

    if response.candidates:
        print(f"🔍 Finish reason: {response.candidates[0].finish_reason}")
    if response.usage_metadata:
        meta = response.usage_metadata
        print(f"🔍 Tokens — prompt: {meta.prompt_token_count}, output: {meta.candidates_token_count}")

    # response.text is None when the model returns no text part (e.g. a SAFETY
    # or MAX_TOKENS finish) — turn that into a clear error, not a bare
    # AttributeError on .strip().
    if response.text is None:
        reason = response.candidates[0].finish_reason if response.candidates else "unknown"
        raise RuntimeError(
            f"Gemini returned no text (finish_reason={reason}) — audio may be silent or blocked."
        )
    return response.text.strip()


def _build_openai_prompt() -> str:
    """Short vocab prompt, with a truncated memory.md appended if present."""
    memory = load_memory()
    if not memory:
        return OPENAI_VOCAB_PROMPT
    return OPENAI_VOCAB_PROMPT + "\n\n" + memory[:OPENAI_MEMORY_CHAR_LIMIT]


def _transcribe_openai(wav_bytes: bytes, api_key: str) -> str:
    client = OpenAI(api_key=api_key)
    response = client.audio.transcriptions.create(
        model=OPENAI_MODEL,
        file=("audio.wav", wav_bytes, "audio/wav"),
        prompt=_build_openai_prompt(),
    )
    return response.text.strip()


def transcribe(wav_bytes: bytes, backend: str, api_key: str) -> str:
    """Dispatch to the configured transcription backend ('gemini' or 'openai')."""
    if backend == "openai":
        return _transcribe_openai(wav_bytes, api_key)
    return _transcribe_gemini(wav_bytes, api_key)
