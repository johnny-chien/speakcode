"""Load global voice coding memory from ~/.voice-coding/memory.md."""

from pathlib import Path

GLOBAL_MEMORY_FILE = Path.home() / ".voice-coding" / "memory.md"


def load_memory() -> str:
    """Load global memory.md content, or return empty string if not found."""
    if GLOBAL_MEMORY_FILE.is_file():
        return GLOBAL_MEMORY_FILE.read_text(encoding="utf-8")
    return ""
