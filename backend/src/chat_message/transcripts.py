"""Compact transcript + title helpers for cheap auxiliary LLM calls.

Pure functions (no service state) used by title generation and reply/tone
suggestions to build lean prompts from a chat's recent turns.
"""

import re

from src.chat_message.models import Message, MessageRole
from src.chat_session.models import Chat


def clean_title(text: str) -> str:
    """Reduce model output to a single clean title line."""
    stripped = text.strip()
    line = stripped.splitlines()[0] if stripped else ""
    line = line.strip().strip('"').strip("'").strip()
    line = re.sub(r"[.\s]+$", "", line)
    return line[:200]


def title_transcript(chat: Chat, messages: list[Message], max_chars: int = 1500) -> str:
    """Compact speaker-tagged transcript of the latest turns, for titling."""
    char_name = chat.character.name if chat.character else "Character"
    user_name = chat.persona.name if chat.persona else "User"
    lines: list[str] = []
    for msg in messages[-6:]:
        speaker = user_name if msg.role == MessageRole.USER else char_name
        text = " ".join(msg.content.split())
        if text:
            lines.append(f"{speaker}: {text}")
    return "\n".join(lines)[:max_chars]


def persona_hint(chat: Chat, max_chars: int = 240) -> str:
    """A short voice cue for the user's persona, for compact suggestion prompts.

    Keeps reply candidates in the user's voice without shipping the whole persona
    card. Empty when no persona/description is set.
    """
    persona = chat.persona
    if not persona or not persona.description:
        return ""
    desc = " ".join(persona.description.split())
    if len(desc) > max_chars:
        desc = desc[:max_chars].rstrip() + "…"
    return f" {persona.name} is: {desc}"


def recent_transcript(
    chat: Chat, messages: list[Message], turns: int = 4, per_msg: int = 600
) -> str:
    """Compact recent transcript for cheap auxiliary calls (tone chips, replies).

    Unlike title_transcript this caps each message individually so the latest
    turn (the one suggestions react to) is always kept intact, rather than
    truncating the whole joined string from the end.
    """
    char_name = chat.character.name if chat.character else "Character"
    user_name = chat.persona.name if chat.persona else "User"
    lines: list[str] = []
    for msg in messages[-turns:]:
        speaker = user_name if msg.role == MessageRole.USER else char_name
        text = " ".join(msg.content.split())
        if len(text) > per_msg:
            text = text[:per_msg].rstrip() + "…"
        if text:
            lines.append(f"{speaker}: {text}")
    return "\n".join(lines)
