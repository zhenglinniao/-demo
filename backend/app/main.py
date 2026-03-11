from datetime import datetime
import random
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session

from .ai_client import call_ai_api
from .auth import create_access_token, get_current_user, get_db, hash_password, verify_password
from .config import AI_MAX_RETRIES, AI_REPLY_STRATEGY, SEED_USERS
from .database import engine
from .models import (
    Base,
    Bot,
    Conversation,
    ConversationTag,
    Group,
    GroupBot,
    GroupMember,
    GroupMessage,
    Message,
    Tag,
    User,
)
from .schemas import (
    AIMessageResponse,
    BotOut,
    ConversationCreate,
    ConversationOut,
    ConversationUpdate,
    GroupCreate,
    GroupDetail,
    GroupMemberAdd,
    GroupMessageCreate,
    GroupMessageResponse,
    GroupMessageOut,
    GroupOut,
    MessageCreate,
    MessageOut,
    TagOut,
    Token,
    UserCreate,
    UserLogin,
)

app = FastAPI(title="Chat Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    seed_bots()
    seed_users()


def seed_bots() -> None:
    from .database import SessionLocal

    db = SessionLocal()
    try:
        if db.query(Bot).count() == 0:
            bots = [
                Bot(name="CustomerBot", persona="Helpful customer support"),
                Bot(name="TechBot", persona="Technical and precise"),
                Bot(name="HumorBot", persona="Light humor and friendly"),
                Bot(name="FallbackBot", persona="Short neutral fallback"),
            ]
            db.add_all(bots)
            db.commit()
    finally:
        db.close()


def seed_users() -> None:
    if not SEED_USERS:
        return

    from .database import SessionLocal

    db = SessionLocal()
    try:
        entries = [entry.strip() for entry in SEED_USERS.split(",") if entry.strip()]
        for entry in entries:
            if ":" not in entry:
                continue
            username, password = entry.split(":", 1)
            username = username.strip()
            password = password.strip()
            if not username or not password:
                continue
            exists = db.query(User).filter(User.username == username).first()
            if exists:
                continue
            user = User(username=username, password_hash=hash_password(password))
            db.add(user)
        db.commit()
    finally:
        db.close()


def _frontend_path() -> Path:
    return (Path(__file__).resolve().parents[2] / "frontend").resolve()


frontend_dir = _frontend_path()
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


@app.get("/")
def serve_frontend():
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path), media_type="text/html; charset=utf-8")
    raise HTTPException(status_code=404, detail="Frontend not found")


@app.post("/auth/register", response_model=Token)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(username=payload.username, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    token = create_access_token(user.username)
    return Token(access_token=token)


@app.post("/auth/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token(user.username)
    return Token(access_token=token)


@app.post("/conversations", response_model=ConversationOut)
def create_conversation(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    title = payload.title or "New Conversation"
    convo = Conversation(user_id=current_user.id, title=title)
    db.add(convo)
    db.commit()
    db.refresh(convo)

    if payload.tags:
        _set_conversation_tags(db, current_user.id, convo, payload.tags)
    return _build_conversation_out(db, convo)


@app.get("/conversations", response_model=List[ConversationOut])
def list_conversations(
    tags: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Conversation).filter(Conversation.user_id == current_user.id)
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        if tag_list:
            query = (
                query.join(ConversationTag)
                .join(Tag)
                .filter(Tag.name.in_(tag_list), Tag.user_id == current_user.id)
                .group_by(Conversation.id)
                .having(func.count(func.distinct(Tag.id)) >= len(tag_list))
            )
    convos = query.order_by(Conversation.updated_at.desc()).all()
    return [_build_conversation_out(db, convo) for convo in convos]


@app.patch("/conversations/{conversation_id}", response_model=ConversationOut)
def update_conversation(
    conversation_id: int,
    payload: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    convo = _get_conversation_or_404(db, conversation_id, current_user.id)
    if payload.title is not None:
        convo.title = payload.title
    if payload.tags is not None:
        _set_conversation_tags(db, current_user.id, convo, payload.tags)
    convo.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(convo)
    return _build_conversation_out(db, convo)


@app.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    convo = _get_conversation_or_404(db, conversation_id, current_user.id)
    db.delete(convo)
    db.commit()
    return {"status": "deleted"}


@app.post("/conversations/{conversation_id}/messages", response_model=AIMessageResponse)
def send_message(
    conversation_id: int,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    convo = _get_conversation_or_404(db, conversation_id, current_user.id)
    user_message = Message(
        conversation_id=convo.id,
        sender_type="user",
        content=payload.content,
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    if convo.title == "New Conversation":
        convo.title = payload.content[:80]

    ai_message, error_message = _create_ai_message(db, convo.id, payload.content)
    convo.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(convo)

    return AIMessageResponse(
        user_message=MessageOut.model_validate(user_message),
        ai_message=MessageOut.model_validate(ai_message),
        ai_error=ai_message.status == "error",
        error_message=error_message,
    )


@app.get("/conversations/{conversation_id}/messages", response_model=List[MessageOut])
def list_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_conversation_or_404(db, conversation_id, current_user.id)
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return [MessageOut.model_validate(msg) for msg in messages]


@app.get("/bots", response_model=List[BotOut])
def list_bots(db: Session = Depends(get_db)):
    bots = db.query(Bot).filter(Bot.is_active.is_(True)).order_by(Bot.id.asc()).all()
    return [BotOut.model_validate(bot) for bot in bots]


@app.post("/groups", response_model=GroupDetail)
def create_group(
    payload: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = Group(title=payload.title, owner_id=current_user.id)
    db.add(group)
    db.commit()
    db.refresh(group)

    member = GroupMember(group_id=group.id, user_id=current_user.id, role="owner")
    db.add(member)

    bot_ids = payload.bot_ids
    if not bot_ids:
        bot_ids = [bot.id for bot in db.query(Bot).filter(Bot.is_active.is_(True)).all()]
    if not bot_ids:
        raise HTTPException(status_code=400, detail="No bots available")
    for bot_id in bot_ids:
        db.add(GroupBot(group_id=group.id, bot_id=bot_id))

    db.commit()
    db.refresh(group)
    return _build_group_detail(db, group)


@app.get("/groups", response_model=List[GroupOut])
def list_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    groups = (
        db.query(Group)
        .join(GroupMember)
        .filter(GroupMember.user_id == current_user.id)
        .order_by(Group.created_at.desc())
        .all()
    )
    return [GroupOut.model_validate(group) for group in groups]


@app.get("/groups/{group_id}", response_model=GroupDetail)
def get_group_detail(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = _get_group_or_404(db, group_id, current_user.id)
    return _build_group_detail(db, group)


@app.post("/groups/{group_id}/members")
def add_group_member(
    group_id: int,
    payload: GroupMemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = _get_group_or_404(db, group_id, current_user.id)
    if group.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can add members")

    user = db.query(User).filter(User.username == payload.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    exists = (
        db.query(GroupMember)
        .filter(GroupMember.group_id == group.id, GroupMember.user_id == user.id)
        .first()
    )
    if exists:
        return {"status": "already_member"}

    db.add(GroupMember(group_id=group.id, user_id=user.id, role="member"))
    db.commit()
    return {"status": "added"}


@app.delete("/groups/{group_id}/members/{user_id}")
def remove_group_member(
    group_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = _get_group_or_404(db, group_id, current_user.id)
    if group.owner_id != current_user.id and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not allowed")

    member = (
        db.query(GroupMember)
        .filter(GroupMember.group_id == group.id, GroupMember.user_id == user_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(member)
    db.commit()
    return {"status": "removed"}


@app.post("/groups/{group_id}/messages", response_model=GroupMessageResponse)
def send_group_message(
    group_id: int,
    payload: GroupMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_group_or_404(db, group_id, current_user.id)

    user_message = GroupMessage(
        group_id=group_id,
        sender_type="user",
        user_id=current_user.id,
        content=payload.content,
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    bot_messages: List[GroupMessage] = []
    error_message = None

    bots = (
        db.query(Bot)
        .join(GroupBot, GroupBot.bot_id == Bot.id)
        .filter(GroupBot.group_id == group_id, Bot.is_active.is_(True))
        .all()
    )
    if not bots:
        bots = db.query(Bot).filter(Bot.name == "FallbackBot").all()

    selected_bots = _select_bots_for_reply(bots)
    for bot in selected_bots:
        bot_message, ai_error = _create_group_ai_message(db, group_id, bot, payload.content)
        bot_messages.append(bot_message)
        if ai_error:
            error_message = error_message or ai_error

    db.commit()

    return GroupMessageResponse(
        user_message=GroupMessageOut.model_validate(user_message),
        bot_messages=[GroupMessageOut.model_validate(msg) for msg in bot_messages],
        ai_error=error_message is not None,
        error_message=error_message,
    )


@app.get("/groups/{group_id}/messages", response_model=List[GroupMessageOut])
def list_group_messages(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_group_or_404(db, group_id, current_user.id)
    messages = (
        db.query(GroupMessage)
        .filter(GroupMessage.group_id == group_id)
        .order_by(GroupMessage.created_at.asc())
        .all()
    )
    return [GroupMessageOut.model_validate(msg) for msg in messages]


def _get_conversation_or_404(db: Session, conversation_id: int, user_id: int) -> Conversation:
    convo = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return convo


def _build_conversation_out(db: Session, convo: Conversation) -> ConversationOut:
    tags = (
        db.query(Tag)
        .join(ConversationTag)
        .filter(ConversationTag.conversation_id == convo.id)
        .order_by(Tag.name.asc())
        .all()
    )
    return ConversationOut(
        id=convo.id,
        title=convo.title,
        created_at=convo.created_at,
        updated_at=convo.updated_at,
        tags=[TagOut.model_validate(tag) for tag in tags],
    )


def _set_conversation_tags(db: Session, user_id: int, convo: Conversation, tag_names: List[str]) -> None:
    normalized = [name.strip()[:50] for name in tag_names if name.strip()]
    existing = (
        db.query(ConversationTag).filter(ConversationTag.conversation_id == convo.id).all()
    )
    for link in existing:
        db.delete(link)
    db.flush()

    for name in normalized:
        tag = db.query(Tag).filter(Tag.user_id == user_id, Tag.name == name).first()
        if not tag:
            tag = Tag(user_id=user_id, name=name)
            db.add(tag)
            db.flush()
        db.add(ConversationTag(conversation_id=convo.id, tag_id=tag.id))
    convo.updated_at = datetime.utcnow()
    db.commit()


def _create_ai_message(db: Session, conversation_id: int, prompt: str) -> tuple[Message, str | None]:
    attempts = 0
    error_message = None
    while attempts <= AI_MAX_RETRIES:
        try:
            response = call_ai_api(prompt)
            ai_message = Message(
                conversation_id=conversation_id,
                sender_type="assistant",
                content=response,
                status="ok",
            )
            db.add(ai_message)
            db.commit()
            db.refresh(ai_message)
            return ai_message, None
        except Exception as exc:  # noqa: BLE001
            attempts += 1
            error_message = str(exc)

    ai_message = Message(
        conversation_id=conversation_id,
        sender_type="assistant",
        content="AI response failed. Please retry.",
        status="error",
        error_message=error_message,
    )
    db.add(ai_message)
    db.commit()
    db.refresh(ai_message)
    return ai_message, error_message


def _get_group_or_404(db: Session, group_id: int, user_id: int) -> Group:
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    member = (
        db.query(GroupMember)
        .filter(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")
    return group


def _build_group_detail(db: Session, group: Group) -> GroupDetail:
    bots = (
        db.query(Bot)
        .join(GroupBot)
        .filter(GroupBot.group_id == group.id)
        .order_by(Bot.id.asc())
        .all()
    )
    return GroupDetail(
        id=group.id,
        title=group.title,
        created_at=group.created_at,
        bots=[BotOut.model_validate(bot) for bot in bots],
    )


def _select_bots_for_reply(bots: List[Bot]) -> List[Bot]:
    if not bots:
        return []
    strategy = AI_REPLY_STRATEGY.lower()
    if strategy == "random":
        return [random.choice(bots)]
    return bots


def _create_group_ai_message(db: Session, group_id: int, bot: Bot, prompt: str) -> tuple[GroupMessage, str | None]:
    attempts = 0
    error_message = None
    while attempts <= AI_MAX_RETRIES:
        try:
            response = call_ai_api(prompt, persona=bot.persona)
            msg = GroupMessage(
                group_id=group_id,
                sender_type="bot",
                bot_id=bot.id,
                content=response,
                status="ok",
            )
            db.add(msg)
            db.flush()
            return msg, None
        except Exception as exc:  # noqa: BLE001
            attempts += 1
            error_message = str(exc)

    msg = GroupMessage(
        group_id=group_id,
        sender_type="bot",
        bot_id=bot.id,
        content="I don't know yet. Please try again later.",
        status="error",
        error_message=error_message,
    )
    db.add(msg)
    db.flush()
    return msg, error_message

