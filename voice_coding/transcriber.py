"""Gemini Flash transcription."""

from google import genai
from google.genai import types

from voice_coding.memory import load_memory

MODEL = "gemini-2.0-flash"

BASE_PROMPT = (
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


def _build_prompt() -> str:
    """Build transcription prompt, appending memory.md if found."""
    memory = load_memory()
    if not memory:
        return BASE_PROMPT
    return BASE_PROMPT + "\n\n--- Project-specific context (from .voice-coding/memory.md) ---\n\n" + memory


def transcribe(wav_bytes: bytes, api_key: str) -> str:
    """Send WAV audio to Gemini Flash and return the transcription text."""
    client = genai.Client(api_key=api_key)
    prompt = _build_prompt()

    response = client.models.generate_content(
        model=MODEL,
        contents=[
            prompt,
            types.Part.from_bytes(data=wav_bytes, mime_type="audio/wav"),
        ],
        config=types.GenerateContentConfig(
            max_output_tokens=8192,
        ),
    )

    # Log finish reason and token usage for debugging
    if response.candidates:
        candidate = response.candidates[0]
        print(f"🔍 Finish reason: {candidate.finish_reason}")
    if response.usage_metadata:
        meta = response.usage_metadata
        print(f"🔍 Tokens — prompt: {meta.prompt_token_count}, output: {meta.candidates_token_count}")

    return response.text.strip()
