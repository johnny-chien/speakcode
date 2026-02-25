"""Copy text to clipboard and auto-paste into the focused app."""

import subprocess
import time


def copy_and_paste(text: str):
    """Copy text to macOS clipboard via pbcopy, then simulate Cmd+V."""
    # Copy to clipboard
    subprocess.run(["pbcopy"], input=text.encode(), check=True)

    # Small delay for clipboard to settle
    time.sleep(0.05)

    # Simulate Cmd+V in the focused app
    subprocess.run(
        [
            "osascript",
            "-e",
            'tell application "System Events" to keystroke "v" using command down',
        ],
        check=True,
    )
