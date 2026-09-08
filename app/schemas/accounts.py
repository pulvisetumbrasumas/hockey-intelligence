from typing import Any

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=60, pattern=r"^[a-zA-Z0-9_.-]+$")
    display_name: str | None = Field(default=None, max_length=120)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)


class FavoriteAdd(BaseModel):
    item_type: str = Field(pattern=r"^(player|team|franchise)$")
    item_key: int
    label: str | None = None


class PrefsUpdate(BaseModel):
    event_keys: list[str] = []
    lead_days: int = Field(default=3, ge=0, le=30)


def user_out(user: Any) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name or user.username,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }
