"""Maintains the denormalized model-name snapshot carried on chats."""

from src.chat_session.repository import ChatRepository


class ChatModelSnapshotService:
    """Owns the denormalized ``Chat.model_name`` snapshot.

    Chats store a copy of their model's display name so listings don't have to
    join the model registry. When a model is renamed, the model domain asks this
    service to refresh the affected chats instead of reaching into
    ``ChatRepository`` itself — keeping cross-domain access at the service layer.

    A narrow, single-collaborator service (rather than a method on ``ChatService``)
    on purpose: the model DI factory can build it from just a ``ChatRepository``,
    avoiding the ``model.dependencies`` <-> ``chat_session.dependencies`` import
    cycle that pulling in the full ``ChatService`` would create.

    Does not commit — the caller owns the transaction boundary so the rename
    stays atomic with the model update.
    """

    def __init__(self, chat_repo: ChatRepository):
        self.chat_repo = chat_repo

    def refresh_model_name(self, model_id: str, new_name: str) -> None:
        """Refresh the model-name snapshot on every chat using ``model_id``."""
        self.chat_repo.update_model_name_for_model_id(model_id, new_name)
