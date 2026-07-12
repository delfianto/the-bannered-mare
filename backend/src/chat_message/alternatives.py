"""Message-alternative (swipe) management, split out of ChatMessageService.

Regeneration preserves the prior reply as an alternative and lets the user switch
between them. This owns that logic; ChatMessageService delegates to it.
"""

from src.chat_message.models import Message
from src.chat_message.repository_async import (
    AsyncMessageAlternativeRepository,
    AsyncMessageRepository,
)
from src.core.exceptions import NotFoundError, ValidationError
from src.core.persistence.models import MessageAlternative


class AlternativesService:
    """Store / list / activate regeneration alternatives for a message."""

    def __init__(
        self,
        message_repo: AsyncMessageRepository,
        alt_repo: AsyncMessageAlternativeRepository | None,
    ) -> None:
        self.message_repo = message_repo
        self.alt_repo = alt_repo

    async def store(self, message: Message, new_content: str, token_count: int) -> None:
        """Preserve old content as an alternative and update the message in place."""
        if not self.alt_repo:
            return

        # On first regeneration, preserve original content as ordinal 0.
        existing_count = await self.alt_repo.count_by_message_id(message.id)
        if existing_count == 0:
            await self.alt_repo.create(
                MessageAlternative(
                    message_id=message.id,
                    content=message.content,
                    token_count=message.token_count,
                    ordinal=0,
                )
            )
            existing_count = 1

        await self.alt_repo.create(
            MessageAlternative(
                message_id=message.id,
                content=new_content,
                token_count=token_count,
                ordinal=existing_count,
            )
        )

        message.content = new_content
        message.token_count = token_count
        message.active_index = existing_count
        await self.message_repo.update(message)
        await self.message_repo.commit()

    async def list(self, chat_id: str, message_id: str) -> list[MessageAlternative]:
        """List all alternatives for a message."""
        message = await self.message_repo.find_by_id_in_chat(message_id, chat_id)
        if not message:
            raise NotFoundError(f"Message '{message_id}' not found")
        if not self.alt_repo:
            return []
        return await self.alt_repo.find_by_message_id(message_id)

    async def activate(self, chat_id: str, message_id: str, alternative_id: str) -> Message:
        """Switch the active alternative on a message."""
        message = await self.message_repo.find_by_id_in_chat(message_id, chat_id)
        if not message:
            raise NotFoundError(f"Message '{message_id}' not found")
        if not self.alt_repo:
            raise ValidationError("Alternatives system not available")
        alt = await self.alt_repo.find_by_id(alternative_id)
        if not alt or alt.message_id != message_id:
            raise NotFoundError(
                f"Alternative '{alternative_id}' not found for message '{message_id}'"
            )
        message.content = alt.content
        message.token_count = alt.token_count
        message.active_index = alt.ordinal
        await self.message_repo.update(message)
        await self.message_repo.commit()
        return message
