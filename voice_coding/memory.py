"""Find and load .voice-coding/memory.md from the current or parent directories."""

from pathlib import Path


def find_memory_file(start_dir: Path | None = None) -> Path | None:
    """Walk up from start_dir to find .voice-coding/memory.md."""
    current = start_dir or Path.cwd()
    current = current.resolve()

    while True:
        candidate = current / ".voice-coding" / "memory.md"
        if candidate.is_file():
            return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def load_memory(start_dir: Path | None = None) -> str:
    """Load memory.md content, or return empty string if not found."""
    path = find_memory_file(start_dir)
    if path is None:
        return ""
    return path.read_text(encoding="utf-8")
