import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class GroupCreate(BaseModel):
    name: str


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: uuid.UUID
    role: str
    display_name: str | None = None
    joined_at: datetime


class GroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    invite_code: str
    created_by: uuid.UUID
    created_at: datetime
    members: list[MemberResponse] = []


class GroupListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    created_at: datetime


class InviteResponse(BaseModel):
    invite_code: str
    invite_url: str
