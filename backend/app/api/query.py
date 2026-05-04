from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.identity import require_roles
from app.db.database import get_db
from app.schemas.query import AskRequest, AskResponseOut, ChatSessionDetailOut, ChatSessionOut, SearchResultOut
from app.core.runtime_config import load_runtime_snapshot
from app.schemas.source import PageOut
from app.services.auth import Actor
from app.services.query import ask, delete_chat_session, get_chat_session, list_chat_sessions, save_answer_as_draft_page, search

router = APIRouter()


class SaveAnswerPayload(BaseModel):
    messageId: str
    title: str | None = None


@router.post("/ask", response_model=AskResponseOut)
async def ask_question(payload: AskRequest, db: Session = Depends(get_db)):
    return ask(
        db,
        payload.question,
        payload.sessionId,
        collection_id=payload.collectionId,
        page_id=payload.pageId,
    )


@router.post("/ask/save-draft", response_model=PageOut)
async def save_ask_answer(payload: SaveAnswerPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    page = save_answer_as_draft_page(db, payload.messageId, title=payload.title, owner=actor.name)
    if not page:
        raise HTTPException(status_code=404, detail="Ask answer message not found")
    return page


@router.get("/ask/sessions", response_model=list[ChatSessionOut])
async def list_ask_sessions(limit: int = 30, db: Session = Depends(get_db)):
    runtime = load_runtime_snapshot(db)
    return list_chat_sessions(db, limit=max(1, min(limit, runtime.search_result_limit)))


@router.get("/ask/sessions/{session_id}", response_model=ChatSessionDetailOut)
async def get_ask_session(session_id: str, db: Session = Depends(get_db)):
    session = get_chat_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session


@router.delete("/ask/sessions/{session_id}")
async def delete_ask_session(session_id: str, db: Session = Depends(get_db)):
    if not delete_chat_session(db, session_id):
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"success": True}


@router.get("/search", response_model=list[SearchResultOut])
async def search_query(query: str, type: str = "all", limit: int = 10, db: Session = Depends(get_db)):
    return search(db, query=query, result_type=type, limit=limit)
