"""Domain errors for SillyTavern preset import."""


class STImportError(Exception):
    """Raised when an uploaded file is not a valid ST chat-completion preset.

    Carries a human-readable message; the router/service maps it to HTTP 400.
    """
