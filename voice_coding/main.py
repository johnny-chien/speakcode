"""Entry point — CLI router and global hotkey listener."""

import os
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path

import Quartz
from dotenv import load_dotenv

from voice_coding.clipboard import copy_and_paste
from voice_coding.postprocessor import postprocess
from voice_coding.recorder import Recorder, SAMPLE_RATE
from voice_coding.transcriber import transcribe

GLOBAL_ENV = Path.home() / ".voice-coding" / ".env"
LOG_FILE = Path.home() / ".voice-coding" / "speak.log"


def _load_env():
    """Load .env from cwd first, then global ~/.voice-coding/.env as fallback."""
    load_dotenv()
    if GLOBAL_ENV.is_file():
        load_dotenv(GLOBAL_ENV, override=False)


VALID_BACKENDS = ("gemini", "openai")


def _select_backend(cli_backend: str | None) -> tuple[str, str]:
    """Pick backend from CLI flag, else TRANSCRIBE_BACKEND env, else gemini."""
    backend = (cli_backend or os.environ.get("TRANSCRIBE_BACKEND") or "gemini").lower()

    if backend == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("Error: OPENAI_API_KEY not set (TRANSCRIBE_BACKEND=openai).")
            print("  export OPENAI_API_KEY=your_key")
            print(f"  or add it to {GLOBAL_ENV}")
            sys.exit(1)
        return backend, api_key

    if backend == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("Error: GEMINI_API_KEY not set.")
            print("  Option 1: export GEMINI_API_KEY=your_key")
            print(f"  Option 2: echo 'GEMINI_API_KEY=your_key' > {GLOBAL_ENV}")
            print("  Option 3: export TRANSCRIBE_BACKEND=openai (with OPENAI_API_KEY)")
            sys.exit(1)
        return backend, api_key

    print(f"Error: Unknown backend {backend!r}. Use 'gemini' or 'openai'.")
    sys.exit(1)


def _explain_error(e: Exception) -> str | None:
    """Map a known failure to a one-line, actionable hint (or None if unknown)."""
    name = type(e).__name__
    msg = str(e).lower()
    if "insufficient_quota" in msg or "resource_exhausted" in msg or (
        "429" in msg and "quota" in msg
    ):
        return (
            "API quota exhausted — top up billing, or switch backend "
            "(speak --gemini / speak --openai)."
        )
    if name == "AuthenticationError" or "401" in msg or "api key" in msg or "unauthorized" in msg:
        return "API key rejected — check the key in ~/.voice-coding/.env."
    if "assistive access" in msg or "not allowed" in msg or "-1719" in msg or "(1002)" in msg:
        return (
            "Auto-paste blocked — grant Accessibility to your terminal: "
            "System Settings → Privacy & Security → Accessibility."
        )
    if "microphone" in msg or "operation not permitted" in msg:
        return (
            "Mic capture failed — grant Microphone access to your terminal: "
            "System Settings → Privacy & Security → Microphone."
        )
    return None


def _append_traceback_log() -> bool:
    """Append the current exception's traceback to LOG_FILE. Returns False on failure."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"\n{'=' * 60}\n{datetime.now().isoformat(timespec='seconds')}\n")
            traceback.print_exc(file=f)
        return True
    except Exception:
        return False


def _report_error(e: Exception) -> None:
    """Surface an error on its own line and persist the full traceback to LOG_FILE.

    Called from within an ``except`` block, so ``traceback`` sees the live
    exception. Known failures get a clean one-line hint; unknown ones dump the
    full traceback inline so nothing is hidden.
    """
    hint = _explain_error(e)
    print(f"\n❌ {type(e).__name__}: {e}")
    if hint:
        print(f"   → {hint}")

    if _append_traceback_log():
        print(f"   (full traceback → {LOG_FILE})")
    if not hint:
        # Unrecognized failure — show the whole traceback inline too.
        traceback.print_exc()


def _run_listener(cli_backend: str | None = None):
    """Run the hold-to-record voice coding listener."""
    _load_env()

    backend, api_key = _select_backend(cli_backend)

    recorder = Recorder()
    recording = False
    alt_held = False
    processing = False

    def _finish_recording():
        nonlocal recording, processing
        if processing:
            return
        recording = False
        processing = True
        try:
            print("\r⏳ Transcribing...", end="", flush=True)

            # recorder.stop() lives inside the try: a failure here (e.g. a
            # PortAudio/device error) must not escape this daemon thread, or
            # `processing` would stay True and silently wedge every later press.
            wav_bytes = recorder.stop()
            if not wav_bytes:
                print("\r⏳ Too short, skipped.      ")
                return

            duration_secs = len(wav_bytes) / (SAMPLE_RATE * 4)
            print(f"\r⏳ Transcribing {duration_secs:.1f}s of audio ({len(wav_bytes) / 1024:.0f} KB)...", end="", flush=True)

            raw_text = transcribe(wav_bytes, backend, api_key)
            print(f"\n📝 Raw transcription ({len(raw_text)} chars):")
            print(f"--- START ---\n{raw_text}\n--- END ---")

            text = postprocess(raw_text)
            if text != raw_text:
                print(f"📝 After postprocess ({len(text)} chars):")
                print(f"--- START ---\n{text}\n--- END ---")

            copy_and_paste(text)
            print(f"✅ Pasted ({len(text)} chars)")
        except Exception as e:
            _report_error(e)
        finally:
            processing = False

    def cg_event_callback(proxy, event_type, event, refcon):
        nonlocal recording, alt_held

        if event_type == Quartz.kCGEventFlagsChanged:
            flags = Quartz.CGEventGetFlags(event)
            alt_now = bool(flags & Quartz.kCGEventFlagMaskAlternate)
            if alt_now and not alt_held:
                alt_held = True
                if not recording and not processing:
                    recording = True
                    recorder.start()
                    print("\r🎙  Recording... (release Alt to stop)", end="", flush=True)
            elif not alt_now and alt_held:
                alt_held = False
                if recording:
                    threading.Thread(target=_finish_recording, daemon=True).start()

        return event

    event_mask = (1 << Quartz.kCGEventFlagsChanged)

    tap = Quartz.CGEventTapCreate(
        Quartz.kCGSessionEventTap,
        Quartz.kCGHeadInsertEventTap,
        Quartz.kCGEventTapOptionDefault,
        event_mask,
        cg_event_callback,
        None,
    )

    if tap is None:
        print("Error: Failed to create event tap. Grant Accessibility permission to your terminal app.")
        print("  System Settings → Privacy & Security → Accessibility")
        sys.exit(1)

    run_loop_source = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
    Quartz.CFRunLoopAddSource(
        Quartz.CFRunLoopGetCurrent(),
        run_loop_source,
        Quartz.kCFRunLoopCommonModes,
    )
    Quartz.CGEventTapEnable(tap, True)

    print(f"SpeakCode running (backend: {backend}). Hold Alt to record. Release Alt to stop. Ctrl+C to quit.")

    try:
        Quartz.CFRunLoopRun()
    except KeyboardInterrupt:
        print("\nStopped.")


USAGE = (
    "Usage: speak [--openai | --gemini | --backend {openai,gemini}]\n"
    "       speak learn\n"
    "       speak -h | --help"
)


def _parse_backend_flags(args: list[str]) -> str | None:
    """Extract a backend selection from CLI args. Returns None if not specified."""
    backend: str | None = None
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("-h", "--help"):
            print(USAGE)
            sys.exit(0)
        elif arg == "--openai":
            backend = "openai"
        elif arg == "--gemini":
            backend = "gemini"
        elif arg == "--backend":
            if i + 1 >= len(args):
                print(f"Error: --backend needs a value ({'|'.join(VALID_BACKENDS)}).")
                sys.exit(2)
            backend = args[i + 1].lower()
            i += 1
        elif arg.startswith("--backend="):
            backend = arg.split("=", 1)[1].lower()
        else:
            print(f"Error: unknown argument {arg!r}.\n{USAGE}")
            sys.exit(2)
        i += 1
    return backend


def main():
    """CLI entry point — route to subcommand or default listener."""
    if len(sys.argv) > 1 and sys.argv[1] == "learn":
        from voice_coding.learn_cmd import run_learn
        run_learn()
    else:
        backend = _parse_backend_flags(sys.argv[1:])
        _run_listener(backend)


if __name__ == "__main__":
    main()
