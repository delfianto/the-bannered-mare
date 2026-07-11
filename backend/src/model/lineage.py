"""Best-effort mapping of a raw provider identifier to a family and a canonical slug.

Provider identifiers are spelled differently per provider (`deepseek/deepseek-v4-pro`
on OpenRouter, bare `deepseek-v4-pro` on OpenCode). These helpers derive a
provider-independent slug and guess the owning family for models discovered at
runtime. Seed data declares family + slug explicitly, so this is only a fallback
for auto-created (persisted-from-discovery) models — the user can correct afterward.
"""

from sqlalchemy.orm import Session

from src.model_family.models import ModelFamily

# Ordered most-specific first; the first rule whose every keyword appears in the
# lowercased identifier wins and resolves to the first family matching the pattern.
_FAMILY_MATCH_RULES: list[tuple[tuple[str, ...], str]] = [
    (("deepseek", "r1"), "%r1%"),
    (("deepseek", "v4"), "%deepseek v4%"),
    (("deepseek",), "%deepseek%"),
    (("glm-5",), "%glm 5%"),
    (("glm",), "%glm%"),
    (("minimax-m3",), "%minimax m3%"),
    (("minimax",), "%minimax%"),
    (("kimi",), "%kimi%"),
    (("mimo",), "%mimo%"),
    (("qwen",), "%qwen%"),
    (("gemma",), "%gemma%"),
    (("mistral",), "%mistral%"),
    (("llama",), "%llama%"),
]


def normalize_slug(model_identifier: str) -> str:
    """Provider-independent slug: drop any vendor prefix and variant suffix, lowercase.

    ``deepseek/deepseek-v4-pro`` -> ``deepseek-v4-pro``; ``llama-3.3-70b:free`` ->
    ``llama-3.3-70b``. Not guaranteed to unify proprietary delimiter differences
    (``claude-opus-4.8`` vs ``claude-opus-4-8``) — those rely on declared seed slugs.
    """
    tail = model_identifier.rsplit("/", 1)[-1]
    tail = tail.split(":", 1)[0]
    return tail.strip().lower()


def resolve_family(db: Session, model_identifier: str) -> ModelFamily | None:
    """Best-effort family for a raw identifier via keyword rules; None if no rule matches."""
    lower_id = model_identifier.lower()
    for keywords, name_pattern in _FAMILY_MATCH_RULES:
        if all(keyword in lower_id for keyword in keywords):
            family = db.query(ModelFamily).filter(ModelFamily.name.ilike(name_pattern)).first()
            if family:
                return family
    return None
