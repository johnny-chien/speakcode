"""Entry point — CLI router and global hotkey listener."""

import os
import sys
import threading
from pathlib import Path

import Quartz
from dotenv import load_dotenv

from voice_coding.clipboard import copy_and_paste
from voice_coding.postprocessor import postprocess
from voice_coding.recorder import Recorder, SAMPLE_RATE
from voice_coding.transcriber import transcribe

GLOBAL_ENV = Path.home() / ".voice-coding" / ".env"


def _load_env():
    """Load .env from cwd first, then global ~/.voice-coding/.env as fallback."""
    load_dotenv()
    if not os.environ.get("GEMINI_API_KEY") and GLOBAL_ENV.is_file():
        load_dotenv(GLOBAL_ENV)


def _run_listener():
    """Run the hold-to-record voice coding listener."""
    _load_env()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set.")
        print("  Option 1: export GEMINI_API_KEY=your_key")
        print(f"  Option 2: echo 'GEMINI_API_KEY=your_key' > {GLOBAL_ENV}")
        sys.exit(1)

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
        print("\r⏳ Transcribing...", end="", flush=True)

        wav_bytes = recorder.stop()
        if not wav_bytes:
            print("\r⏳ Too short, skipped.      ")
            processing = False
            return

        try:
            duration_secs = len(wav_bytes) / (SAMPLE_RATE * 4)
            print(f"\r⏳ Transcribing {duration_secs:.1f}s of audio ({len(wav_bytes) / 1024:.0f} KB)...", end="", flush=True)

            raw_text = transcribe(wav_bytes, api_key)
            print(f"\n📝 Raw transcription ({len(raw_text)} chars):")
            print(f"--- START ---\n{raw_text}\n--- END ---")

            text = postprocess(raw_text)
            if text != raw_text:
                print(f"📝 After postprocess ({len(text)} chars):")
                print(f"--- START ---\n{text}\n--- END ---")

            copy_and_paste(text)
            print(f"✅ Pasted ({len(text)} chars)")
        except Exception as e:
            print(f"\r❌ Error: {e}      ")
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

    print("Voice Coding running. Hold Alt to record. Release Alt to stop. Ctrl+C to quit.")

    try:
        Quartz.CFRunLoopRun()
    except KeyboardInterrupt:
        print("\nStopped.")


def main():
    """CLI entry point — route to subcommand or default listener."""
    if len(sys.argv) > 1 and sys.argv[1] == "learn":
        from voice_coding.learn_cmd import run_learn
        run_learn()
    else:
        _run_listener()


if __name__ == "__main__":
    main()
