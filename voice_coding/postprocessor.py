"""Coding-aware text transforms applied after transcription."""

import re

CODING_RULES: dict[str, str] = {
    "dot env": ".env",
    "double equals": "==",
    "triple equals": "===",
    "not equals": "!=",
    "arrow": "=>",
    "slash": "/",
    "dot": ".",
    "dash": "-",
    "underscore": "_",
    "equals": "=",
    "hash": "#",
    "at sign": "@",
    "ampersand": "&",
    "pipe": "|",
    "tilde": "~",
    "backtick": "`",
    "open paren": "(",
    "close paren": ")",
    "open bracket": "[",
    "close bracket": "]",
    "open brace": "{",
    "close brace": "}",
    "new line": "\n",
    "tab": "\t",
}


def _apply_coding_rules(text: str) -> str:
    """Replace spoken coding phrases with their symbol equivalents."""
    # Sort by length descending so multi-word rules match first
    for phrase, replacement in sorted(
        CODING_RULES.items(), key=lambda x: len(x[0]), reverse=True
    ):
        # Use word boundaries to avoid matching inside words (e.g. "dash" in "Dashboard")
        pattern = r"\b" + re.escape(phrase) + r"\b"
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def _apply_camel_case(text: str) -> str:
    """Convert 'camel case foo bar baz' → 'fooBarBaz'."""

    def _to_camel(m: re.Match) -> str:
        words = m.group(1).strip().split()
        if not words:
            return ""
        return words[0].lower() + "".join(w.capitalize() for w in words[1:])

    return re.sub(r"camel case\s+((?:\w+\s*){2,})", _to_camel, text, flags=re.IGNORECASE)


def _apply_snake_case(text: str) -> str:
    """Convert 'snake case foo bar baz' → 'foo_bar_baz'."""

    def _to_snake(m: re.Match) -> str:
        words = m.group(1).strip().split()
        return "_".join(w.lower() for w in words)

    return re.sub(r"snake case\s+((?:\w+\s*){2,})", _to_snake, text, flags=re.IGNORECASE)


def postprocess(text: str) -> str:
    """Apply all coding-aware transforms to transcribed text."""
    text = _apply_camel_case(text)
    text = _apply_snake_case(text)
    text = _apply_coding_rules(text)
    return text
