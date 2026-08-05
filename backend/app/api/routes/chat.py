from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.db.models import ChatMessage, ChatSession
from app.deps import AppSettings, CurrentUser, DbSession
from app.schemas import ChatMessageIn, ChatMessageOut, ChatSessionOut
from app.services.rag import grounded_answer

router = APIRouter(prefix="/v1/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSessionOut, status_code=status.HTTP_201_CREATED)
def create_session(db: DbSession, user: CurrentUser):
    session = ChatSession(user_id=user.id, title="New chat")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions/{session_id}", response_model=list[ChatMessageOut])
def get_session(session_id: UUID, db: DbSession, user: CurrentUser):
    session = db.get(ChatSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [
        ChatMessageOut(
            id=m.id,
            role=m.role,
            content=m.content,
            confidence=m.confidence,
            sources=m.sources,
            related_documents=(m.related or {}).get("related_documents"),
            related_projects=(m.related or {}).get("related_projects"),
            people_involved=(m.related or {}).get("people_involved"),
            timeline=(m.related or {}).get("timeline"),
            supporting_evidence=(m.related or {}).get("supporting_evidence"),
            created_at=m.created_at,
        )
        for m in messages
    ]


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageOut)
def send_message(
    session_id: UUID,
    payload: ChatMessageIn,
    db: DbSession,
    user: CurrentUser,
    settings: AppSettings,
):
    session = db.get(ChatSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    user_msg = ChatMessage(session_id=session_id, role="user", content=payload.content)
    db.add(user_msg)
    db.commit()

    answer = grounded_answer(db, settings, query=payload.content, user_id=user.id)
    assistant = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=answer["content"],
        confidence=answer["confidence"],
        sources=answer["sources"],
        related={
            "related_documents": answer["related_documents"],
            "related_projects": answer["related_projects"],
            "people_involved": answer["people_involved"],
            "timeline": answer["timeline"],
            "supporting_evidence": answer["supporting_evidence"],
        },
    )
    db.add(assistant)
    if not session.title or session.title == "New chat":
        session.title = payload.content[:80]
    db.commit()
    db.refresh(assistant)

    return ChatMessageOut(
        id=assistant.id,
        role=assistant.role,
        content=assistant.content,
        confidence=assistant.confidence,
        sources=assistant.sources,
        related_documents=answer["related_documents"],
        related_projects=answer["related_projects"],
        people_involved=answer["people_involved"],
        timeline=answer["timeline"],
        supporting_evidence=answer["supporting_evidence"],
        created_at=assistant.created_at,
    )
