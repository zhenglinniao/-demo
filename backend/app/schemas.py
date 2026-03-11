from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TagOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    title: Optional[str] = None
    tags: List[str] = []


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    tags: Optional[List[str]] = None


class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    tags: List[TagOut]

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)


class MessageOut(BaseModel):
    id: int
    sender_type: str
    content: str
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AIMessageResponse(BaseModel):
    user_message: MessageOut
    ai_message: MessageOut
    ai_error: bool
    error_message: Optional[str] = None


class BotOut(BaseModel):
    id: int
    name: str
    persona: str

    class Config:
        from_attributes = True


class GroupBotOut(BaseModel):
    bot_id: int
    name: str
    persona: str
    system_prompt: Optional[str] = None


class GroupCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    bot_ids: Optional[List[int]] = None
    bot_systems: Optional[Dict[int, str]] = None


class GroupBotUpdate(BaseModel):
    system_prompt: Optional[str] = None


class GroupOut(BaseModel):
    id: int
    title: str
    created_at: datetime

    class Config:
        from_attributes = True


class GroupDetail(GroupOut):
    bots: List[BotOut]


class GroupMemberAdd(BaseModel):
    username: str


class GroupMessageCreate(BaseModel):
    content: str = Field(..., min_length=1)


class GroupMessageOut(BaseModel):
    id: int
    sender_type: str
    user_id: Optional[int]
    bot_id: Optional[int]
    content: str
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class GroupMessageResponse(BaseModel):
    user_message: GroupMessageOut
    bot_messages: List[GroupMessageOut]
    ai_error: bool
    error_message: Optional[str] = None
