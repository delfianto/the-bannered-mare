"""Pydantic schemas for Lorebook API validation"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.core.persistence.enums import InsertionPosition, MessageRole, SecondaryLogic


class LoreEntryBase(BaseModel):
    """Base lore entry schema"""

    name: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, description="Lore text injected into prompt")
    keys: list[str] = Field(default_factory=list, description="Primary trigger keywords")
    secondary_keys: list[str] = Field(default_factory=list)
    secondary_logic: SecondaryLogic = SecondaryLogic.AND_ANY
    case_sensitive: bool = False
    match_whole_words: bool = False
    use_regex: bool = False
    enabled: bool = True
    constant: bool = False
    position: InsertionPosition = InsertionPosition.AFTER_CHARACTER
    depth: int = Field(default=4, ge=0, description="Message depth for AT_DEPTH")
    role: MessageRole = MessageRole.SYSTEM
    priority: int = Field(default=100, ge=0)
    scan_depth: int | None = None
    ignore_budget: bool = False
    order: int = 0


class LoreEntryCreate(LoreEntryBase):
    """Schema for creating a lore entry"""


class LoreEntryUpdate(BaseModel):
    """Schema for updating a lore entry (all fields optional)"""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1)
    keys: list[str] | None = None
    secondary_keys: list[str] | None = None
    secondary_logic: SecondaryLogic | None = None
    case_sensitive: bool | None = None
    match_whole_words: bool | None = None
    use_regex: bool | None = None
    enabled: bool | None = None
    constant: bool | None = None
    position: InsertionPosition | None = None
    depth: int | None = Field(default=None, ge=0)
    role: MessageRole | None = None
    priority: int | None = Field(default=None, ge=0)
    scan_depth: int | None = None
    ignore_budget: bool | None = None
    order: int | None = None


class LoreEntryResponse(LoreEntryBase):
    """Schema for lore entry responses"""

    id: str
    lorebook_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LorebookBase(BaseModel):
    """Base lorebook schema"""

    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    is_global: bool = False
    character_id: str | None = None


class LorebookCreate(LorebookBase):
    """Schema for creating a lorebook"""


class LorebookUpdate(BaseModel):
    """Schema for updating a lorebook"""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    is_global: bool | None = None


class LorebookResponse(LorebookBase):
    """Schema for lorebook responses (without entries)"""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LorebookDetailResponse(LorebookResponse):
    """Schema for lorebook with entries"""

    entries: list[LoreEntryResponse] = []
