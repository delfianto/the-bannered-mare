#!/usr/bin/env python3
"""Analyze / decode a character card — inspect its embedded metadata.

Reads TavernCard V1/V2/V3 PNG cards (base64 JSON in a `chara` tEXt chunk) or
plain JSON cards and prints the normalized fields. Pure inspection — no database.

Run with the backend virtualenv (it uses the backend's card parser + Pillow):

    backend/.venv/bin/python scripts/analyze_card.py CARD [CARD ...]
    backend/.venv/bin/python scripts/analyze_card.py characters/*.png
    backend/.venv/bin/python scripts/analyze_card.py --json characters/mina.png
"""

import argparse
import dataclasses
import json
import os
import sys

# Backend lives one level up from this repo-root scripts/ folder.
_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, _BACKEND)

from src.character.card_parser import ParsedCard, parse_card_json, parse_card_png


def load_card(path: str) -> ParsedCard:
    """Parse a .png or .json card into a normalized ParsedCard."""
    with open(path, "rb") as fh:
        data = fh.read()
    if path.lower().endswith(".png"):
        return parse_card_png(data)
    return parse_card_json(data.decode("utf-8"))


def summarize(path: str, card: ParsedCard) -> None:
    """Print a human-readable summary of one card."""
    book = card.character_book if isinstance(card.character_book, dict) else {}
    entries = book.get("entries", [])
    gender = card.gender or card.custom_gender or "—"
    print(f"\n{os.path.basename(path)}")
    print(f"  name         : {card.name}")
    print(f"  spec         : {card.spec} {card.spec_version}")
    print(f"  creator      : {card.creator or '—'}  (version {card.character_version or '—'})")
    print(f"  traits       : species={card.species or '—'}  gender={gender}  age={card.age or '—'}")
    print(f"  tags         : {', '.join(card.tags) if card.tags else '—'}")
    print(f"  description  : {len(card.description)} chars")
    print(
        f"  greetings    : first_mes={'yes' if card.first_message else 'no'}"
        f" + {len(card.alternate_greetings)} alternate"
    )
    print(f"  system_prompt: {'yes' if card.system_prompt else 'no'}")
    if entries:
        print(f"  lorebook     : {book.get('name') or '(unnamed)'} — {len(entries)} entries")
        for entry in entries:
            title = entry.get("name") or entry.get("comment") or "(unnamed)"
            print(f"      · {title}  keys={entry.get('keys', [])}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze / decode character cards.")
    parser.add_argument("cards", nargs="+", help="Path(s) to .png or .json character cards")
    parser.add_argument(
        "--json", action="store_true", help="Dump the full normalized card as JSON"
    )
    args = parser.parse_args()

    exit_code = 0
    for path in args.cards:
        try:
            card = load_card(path)
        except Exception as exc:  # noqa: BLE001 — report and continue to the next card
            print(f"\n{os.path.basename(path)}\n  ERROR: {exc}", file=sys.stderr)
            exit_code = 1
            continue
        if args.json:
            print(json.dumps(dataclasses.asdict(card), indent=2, ensure_ascii=False))
        else:
            summarize(path, card)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
