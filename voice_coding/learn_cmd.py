"""voice learn — scan a repo and merge its vocabulary into global memory."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

LEARN_MODEL = "gemini-3-flash-preview"

GLOBAL_MEMORY_DIR = Path.home() / ".voice-coding"
GLOBAL_MEMORY_FILE = GLOBAL_MEMORY_DIR / "memory.md"

LEARN_PROMPT = """\
You are helping a developer add project-specific vocabulary to their voice-to-text memory file.

Given:
1. The developer's EXISTING memory file (may be empty if this is their first time)
2. A NEW project's context (README, package files, etc.)

Generate an UPDATED memory file that MERGES the new project's vocabulary into the existing one.

Rules:
- Keep ALL existing vocabulary entries — do not remove anything
- Add new terms from the project that are not already covered
- If a term already exists, keep the existing entry (don't duplicate)
- Keep all existing Context and Notes sections, and append new context about this project
- Focus on terms that a speech-to-text model might get wrong
- For each new term, add a disambiguation hint explaining what it is and what it should NOT be confused with
- Example entry: | Claude Code | AI coding assistant CLI, not "clock code" or "cloud code" |

The file should have these sections:

## Vocabulary

A markdown table with columns: Term | Hint
(merged from existing + new project)

## Context

Brief descriptions of all projects the developer works on.

## Notes

Keep any existing notes. If this is the first time, add HTML comment examples:
<!-- Add your own notes here -->
<!-- Examples: -->
<!-- - I have a [nationality] accent -->
<!-- - When I say "X", I usually mean Y -->
<!-- - I sometimes mix [language] and English -->

Output ONLY the markdown content. Start with "# Voice Coding Memory" as the first line.
Do NOT wrap in code fences.
"""


def _gather_repo_context(repo_dir: Path) -> str:
    """Read key files from the repo to send as context."""
    context_parts = []

    for filename in [
        "README.md",
        "README",
        "package.json",
        "pyproject.toml",
        "Cargo.toml",
        "go.mod",
        "Gemfile",
        "CLAUDE.md",
        "requirements.txt",
    ]:
        filepath = repo_dir / filename
        if filepath.is_file():
            content = filepath.read_text(encoding="utf-8", errors="ignore")[:4000]
            context_parts.append(f"=== {filename} ===\n{content}")

    try:
        entries = sorted(p.name for p in repo_dir.iterdir() if not p.name.startswith("."))
        context_parts.append(f"=== Directory listing ===\n{chr(10).join(entries)}")
    except OSError:
        pass

    return "\n\n".join(context_parts)


def run_learn():
    """Scan current repo and merge its vocabulary into global memory."""
    load_dotenv()
    global_env = GLOBAL_MEMORY_DIR / ".env"
    if not os.environ.get("GEMINI_API_KEY") and global_env.is_file():
        load_dotenv(global_env)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set.")
        print("  Option 1: export GEMINI_API_KEY=your_key")
        print(f"  Option 2: echo 'GEMINI_API_KEY=your_key' > {global_env}")
        sys.exit(1)

    repo_dir = Path.cwd()

    print(f"Scanning {repo_dir.name}/ ...")
    repo_context = _gather_repo_context(repo_dir)

    if not repo_context.strip():
        print("Warning: No project files found. Generating generic vocabulary.")

    # Load existing global memory
    existing_memory = ""
    if GLOBAL_MEMORY_FILE.is_file():
        existing_memory = GLOBAL_MEMORY_FILE.read_text(encoding="utf-8")
        print(f"Found existing memory at {GLOBAL_MEMORY_FILE}")

    print("Generating vocabulary with Gemini...")
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=LEARN_MODEL,
        contents=[
            LEARN_PROMPT,
            f"=== Existing memory file ===\n\n{existing_memory}" if existing_memory else "=== Existing memory file ===\n\n(empty — first time setup)",
            f"=== New project context ===\n\n{repo_context}",
        ],
        config=types.GenerateContentConfig(
            max_output_tokens=4096,
        ),
    )

    memory_content = response.text.strip()

    GLOBAL_MEMORY_DIR.mkdir(exist_ok=True)
    GLOBAL_MEMORY_FILE.write_text(memory_content + "\n", encoding="utf-8")

    print(f"Updated {GLOBAL_MEMORY_FILE}")
    print("Edit this file anytime to add or fix terms.")
