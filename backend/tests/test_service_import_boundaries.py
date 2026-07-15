"""Architectural guard (BE-H2 Step 4): slices must not reach into each other's data layer.

A ``src/<slice>/service.py`` must never import another slice's ``repository`` or
``repository_async``. Cross-slice READS go through a structural ``ReadPort``;
cross-slice WRITES go through the target slice's published service. This test AST-walks
every service module and fails if the boundary regresses — even under ``TYPE_CHECKING``.

It runs inside the normal test gate (not a separate CI step that could be silently
skipped, cf. BE-H3), so a violation turns the pipeline red locally and in CI.

Documented exceptions live in ``_ALLOWED_PAIRS`` / ``_ALLOWED_IMPORTERS`` below; add
to them only with a WHY, never to paper over a fixable coupling.
"""

import ast
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
_DATA_LAYER = {"repository", "repository_async"}

# (importer_slice, imported_slice) pairs allowed to cross into the data layer, with why.
_ALLOWED_PAIRS = {
    # A chat message belongs to a chat: the async ChatMessageService loads its parent
    # chat (an async read on the streaming hot path). chat_message is a sub-aggregate
    # of chat_session, so this coupling is intrinsic — not the spurious kind BE-H2 targets.
    ("chat_message", "chat_session"),
}
# Slices whose service legitimately wires many repositories directly.
_ALLOWED_IMPORTERS = {
    # Startup seeding runs outside the request/DI lifecycle and populates every slice.
    "fixtures",
}


def _imported_data_layer_slices(service_file: Path) -> set[str]:
    """Slices whose repository/repository_async ``service_file`` imports (any import form)."""
    tree = ast.parse(service_file.read_text(), filename=str(service_file))
    imported: set[str] = set()

    def record(dotted: str) -> None:
        parts = dotted.split(".")
        # src.<slice>.repository[_async]
        if len(parts) >= 3 and parts[0] == "src" and parts[2] in _DATA_LAYER:
            imported.add(parts[1])

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            record(node.module)
            # `from src.<slice> import repository[_async]`
            if node.module.startswith("src."):
                for alias in node.names:
                    record(f"{node.module}.{alias.name}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                record(alias.name)
    return imported


def test_no_service_imports_foreign_repository() -> None:
    offenders: list[str] = []
    for service_file in sorted(_SRC.glob("*/service.py")):
        importer = service_file.parent.name
        if importer in _ALLOWED_IMPORTERS:
            continue
        for imported in sorted(_imported_data_layer_slices(service_file)):
            if imported == importer or (importer, imported) in _ALLOWED_PAIRS:
                continue
            offenders.append(f"{importer}/service.py imports {imported}'s repository")

    assert not offenders, (
        "A service.py imports another slice's repository (BE-H2). Route reads through a "
        "ReadPort and writes through the target slice's published service:\n  "
        + "\n  ".join(offenders)
    )
