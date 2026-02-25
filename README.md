# Voice Coding

Private voice-to-text for developers. Hold a hotkey, speak, get text pasted into any app.

- **Private** — audio goes to Gemini Flash (your own API key), nowhere else
- **Fast** — ~1 second transcription via Gemini 3.0 Flash
- **Universal** — auto-pastes into any focused app: VS Code, Terminal, Slack, browser, etc.
- **Coding-aware** — "dot env" → `.env`, "camel case foo bar" → `fooBar`

## Install

```bash
pip install voice-coding
```

## Setup

1. Get a [Gemini API key](https://aistudio.google.com/apikey)
2. Set your API key:
   ```bash
   export GEMINI_API_KEY=your_key_here
   ```
   Or create a `~/.voice-coding/.env` file:
   ```
   GEMINI_API_KEY=your_key_here
   ```

### macOS Permissions

Your terminal app (Terminal.app / iTerm / VS Code) needs two permissions in **System Settings → Privacy & Security**:

- **Microphone** — for audio recording
- **Accessibility** — for global hotkey detection and auto-paste keystroke simulation

After granting Accessibility, **restart your terminal app** for the permission to take effect.

## Learn Project Vocabulary (Optional)

Teach Voice Coding the vocabulary of any project you work on:

```bash
cd /path/to/your/project
voice learn
```

This scans the repo (README, package.json, etc.) and merges its vocabulary into your global memory at `~/.voice-coding/memory.md`. Run it in each repo you work on — terms accumulate across projects.

The memory file includes:

- **Vocabulary** — project-specific terms with disambiguation hints (e.g., "Claude Code" not "clock code")
- **Context** — brief descriptions of your projects and tech stacks
- **Notes** — space for personal customizations (accent, language mixing, corrections you've noticed)

Edit `~/.voice-coding/memory.md` anytime to add or fix terms.

## Usage

```bash
voice
```

**Hold Alt (⌥)** to start recording. **Release Alt** to stop, transcribe, and auto-paste into whichever app is focused.

Press **Ctrl+C** to quit.

### Tips

- Speak naturally — filler words (um, uh, like, you know) are automatically removed
- Minor grammar is corrected while preserving your original wording
- Recordings shorter than 0.5 seconds are ignored to prevent accidental triggers

## Coding Transforms

Voice Coding post-processes transcriptions with coding-aware rules:

| You say | You get |
|---------|---------|
| "dot env" | `.env` |
| "slash api" | `/api` |
| "camel case foo bar" | `fooBar` |
| "snake case my variable" | `my_variable` |
| "open paren" | `(` |
| "arrow" | `=>` |
| "triple equals" | `===` |
| "new line" | newline character |

## How It Works

1. A macOS `CGEventTap` listens for the Alt key globally (works in any app, including VS Code)
2. `sounddevice` captures mic audio at 16kHz mono while the hotkey is held
3. Audio is sent to Gemini 3.0 Flash for transcription, with vocabulary from `~/.voice-coding/memory.md` if present
4. Post-processor applies coding-aware text transforms
5. Result is copied to clipboard via `pbcopy` and pasted via `osascript` Cmd+V simulation
