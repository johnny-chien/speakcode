"""voice init — generate .voice-coding/memory.md for a repo."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

INIT_MODEL = "gemini-2.0-flash"

INIT_PROMPT = """\
You are helping a developer set up voice-to-text for coding in their project.

Given the project context below, generate a Voice Coding memory file in markdown format.

The file should have these sections:

## Vocabulary

A markdown table with columns: Term | Hint

Include:
- The project name and how to distinguish it from similar-sounding words
- Key dependencies and libraries used in the project
- Framework names and tools
- Any acronyms or unusual technical terms
- Focus on terms that a speech-to-text model might get wrong

For each term, add a disambiguation hint explaining what it is and what it should NOT be confused with.
Example: | Claude Code | AI coding assistant CLI, not "clock code" or "cloud code" |

## Context

A 1-2 sentence description of what this project is and its tech stack, based on what you can see.

## Notes

Add HTML comments with example customizations the user might want to add:
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


def run_init():
    """Run the voice init command."""
    load_dotenv()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set. Copy .env.example to .env and fill it in.")
        sys.exit(1)

    repo_dir = Path.cwd()
    output_dir = repo_dir / ".voice-coding"
    output_file = output_dir / "memory.md"

    if output_file.exists():
        response = input(f"  {output_file} already exists. Overwrite? [y/N] ")
        if response.lower() != "y":
            print("Aborted.")
            return

    print(f"Scanning {repo_dir.name}/ ...")
    repo_context = _gather_repo_context(repo_dir)

    if not repo_context.strip():
        print("Warning: No project files found. Generating generic memory file.")

    print("Generating vocabulary with Gemini...")
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=INIT_MODEL,
        contents=[
            INIT_PROMPT,
            f"=== Project context ===\n\n{repo_context}",
        ],
        config=types.GenerateContentConfig(
            max_output_tokens=4096,
        ),
    )

    memory_content = response.text.strip()

    output_dir.mkdir(exist_ok=True)
    output_file.write_text(memory_content + "\n", encoding="utf-8")

    print(f"Created {output_file}")
    print("Edit this file to customize vocabulary and add personal notes.")
