from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator


class RegisterIn(BaseModel):
    email: EmailStr
    display_name: str | None = None
    timezone: str | None = None


class VerifyEmailIn(BaseModel):
    token: str


class LoginRequestIn(BaseModel):
    email: EmailStr


class LoginVerifyIn(BaseModel):
    token: str


class UserOut(BaseModel):
    user_id: str
    email: str
    verified: bool
    display_name: str | None = None
    avatar_url: str | None = None
    timezone: str | None = None
    telegram: dict | None = None

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def _map_id(cls, data):
        # Accept ORM objects (User.id) as well as plain dicts.
        if not isinstance(data, dict) and hasattr(data, "id"):
            return {
                "user_id": data.id,
                "email": data.email,
                "verified": data.verified,
                "display_name": data.display_name,
                "avatar_url": data.avatar_url,
                "timezone": data.timezone,
                "telegram": (
                    {"bound": True, "telegram_id": data.telegram_id, "username": data.telegram_username}
                    if data.telegram_id
                    else None
                ),
            }
        if isinstance(data, dict) and "user_id" not in data and "id" in data:
            data = {**data, "user_id": data["id"]}
        return data


class MeUpdate(BaseModel):
    display_name: str | None = None
    avatar_url: str | None = None
    timezone: str | None = None


class TelegramBindIn(BaseModel):
    init_data: str


class ServiceKeyIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scopes: list[str] = Field(min_length=1)


class PointsAdjustIn(BaseModel):
    delta: int
    reason: str = Field(min_length=1, max_length=64)
    ref_type: str | None = None
    ref_id: str | None = None


class CheckinTokenIn(BaseModel):
    event_id: str
    registration_id: str
    event_url: str
    ttl_seconds: int = Field(default=86400, ge=60, le=30 * 86400)
    max_uses: int = Field(default=1, ge=1, le=1000)


class CheckinClaimIn(BaseModel):
    token_id: str
    sig: str


class NftClaimIn(BaseModel):
    nft_contract: str
    token_id: str
    tx_hash: str


class WebhookSubscriptionIn(BaseModel):
    url: str
    secret: str = Field(min_length=8)
    events: list[str] = Field(min_length=1)


class LedgerEntryOut(BaseModel):
    id: str
    user_id: str
    delta: int
    reason: str
    ref_type: str | None
    ref_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CheckinTokenOut(BaseModel):
    token_id: str
    claim_url: str
    expires_at: datetime

    model_config = {"from_attributes": True}
