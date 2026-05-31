"""Copy text to clipboard and auto-paste into the focused app."""

import subprocess
import time


def copy_and_paste(text: str):
    """Copy text to macOS clipboard via pbcopy, then simulate Cmd+V.

    Captures subprocess stderr so a real failure (e.g. System Events lacking
    Accessibility permission) surfaces its actual message instead of a bare
    "non-zero exit status" — the caller logs whatever we raise.
    """
    copy = subprocess.run(["pbcopy"], input=text.encode(), capture_output=True)
    if copy.returncode != 0:
        err = copy.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"pbcopy failed: {err or f'exit {copy.returncode}'}")

    # Small delay for clipboard to settle
    time.sleep(0.05)

    # Simulate Cmd+V in the focused app
    paste = subprocess.run(
        [
            "osascript",
            "-e",
            'tell application "System Events" to keystroke "v" using command down',
        ],
        capture_output=True,
    )
    if paste.returncode != 0:
        err = paste.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"auto-paste (osascript) failed: {err or f'exit {paste.returncode}'}")
