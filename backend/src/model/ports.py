"""Ports the model slice depends on but does not implement (BE-H7).

``model`` must refresh the denormalized model-name snapshot chats carry when a
model is renamed, but it must not depend on the ``chat_session`` slice to do so.
It declares that need here as a structural ``Protocol``; ``chat_session``'s
``ChatModelSnapshotService`` satisfies it structurally (without importing this
module), so DI passes the concrete service and neither domain imports the other.
"""

from typing import Protocol


class ChatSnapshotPort(Protocol):
    """Refresh the ``Chat.model_name`` snapshot for every chat using a model.

    Called inside the model update's transaction (the implementation must not
    commit — the caller owns the boundary so the rename stays atomic).
    """

    def refresh_model_name(self, model_id: str, new_name: str) -> None: ...
