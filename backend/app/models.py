from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


CoreStatKey = Literal["strength", "dexterity", "stamina", "magic_affinity", "mana"]


class PreviewRequest(BaseModel):
    character_id: UUID
    target_stats: dict[CoreStatKey, int] = Field(default_factory=dict)

    @field_validator("target_stats")
    @classmethod
    def validate_targets(cls, value: dict[str, int]) -> dict[str, int]:
        if not value:
            raise ValueError("At least one target stat is required.")
        for stat_key, target in value.items():
            if target < 0:
                raise ValueError(f"{stat_key} cannot be negative.")
            if target > 10000:
                raise ValueError(f"{stat_key} is too high.")
        return value


class SubmitStatRequest(PreviewRequest):
    requested_by_discord_id: int = Field(gt=0)
    submitter_note: str | None = Field(default=None, max_length=1000)


class StaffActionRequest(BaseModel):
    staff_discord_id: int | None = Field(default=None, gt=0)
    staff_note: str | None = Field(default=None, max_length=1000)


class ManualDerivedStatsRequest(BaseModel):
    strength: int = Field(ge=0)
    dexterity: int = Field(ge=0)
    stamina: int = Field(ge=0)
    magic_affinity: int = Field(ge=0)
    mana: int = Field(ge=0)

class LoadoutSaveRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    items: dict[str, int] | None = None

class ActiveLoadoutRequest(BaseModel):
    name: str | None = Field(default=None, max_length=80)

class ShopPatchRequest(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=4000)
    banner_url: str | None = Field(default=None, max_length=500)
    logo_url: str | None = Field(default=None, max_length=500)

class ShopItemPatchRequest(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    price: int | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    review_status: str | None = Field(default=None, max_length=80)

class SkillPurchaseRequest(BaseModel):
    character_id: UUID
    skill_key: str = Field(min_length=1, max_length=120)
    requested_by_discord_id: int = Field(gt=0)
    submitter_note: str | None = Field(default=None, max_length=1000)
