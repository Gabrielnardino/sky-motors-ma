from typing import Any
from pydantic import BaseModel, Field


class WahaMessagePayload(BaseModel):
    id: str | None = None
    from_: str = Field(alias="from")
    body: str | None = None
    fromMe: bool = False
    isGroup: bool = False
    pushName: str | None = None
    hasMedia: bool = False
    type: str | None = None  # "chat", "ptt", "audio", "image", etc.

    model_config = {"populate_by_name": True}


class WahaWebhookEvent(BaseModel):
    event: str
    session: str
    payload: Any  # varies by event type (message, presence.update, etc.)

    model_config = {"extra": "allow"}
