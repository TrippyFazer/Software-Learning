"""Learning endpoints: grading, progress, mastery, flashcards."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.auth.deps import CurrentUser
from app.modules.content.loader import get_content_index
from app.modules.learning import service

router = APIRouter(prefix="/learning", tags=["learning"])


# --- quiz answers ------------------------------------------------------------

class AnswerIn(BaseModel):
    question_id: str
    answer: str | int


class AnswerOut(BaseModel):
    correct: bool
    explanation: str
    correct_answer: str | int | None


@router.post("/answers", response_model=AnswerOut)
def submit_answer(body: AnswerIn, user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    try:
        return service.submit_quiz_answer(db, user.id, body.question_id, body.answer)
    except service.UnknownQuestion as e:
        raise HTTPException(404, "Unknown question") from e


# --- lesson progress ---------------------------------------------------------

@router.post("/lessons/{module}/{lesson}/start")
def start_lesson(module: str, lesson: str, user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    slug = f"{module}/{lesson}"
    if slug not in get_content_index().lessons:
        raise HTTPException(404, "Lesson not found")
    service.start_lesson(db, user.id, slug)
    return {"ok": True}


@router.post("/lessons/{module}/{lesson}/complete")
def complete_lesson(module: str, lesson: str, user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    slug = f"{module}/{lesson}"
    try:
        service.complete_lesson(db, user.id, slug)
    except service.UnknownQuestion as e:
        raise HTTPException(404, "Lesson not found") from e
    return {"ok": True}


@router.get("/lessons/progress")
def lessons_progress(user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    from sqlalchemy import select

    from app.modules.learning.models import LessonProgress

    rows = db.scalars(select(LessonProgress).where(LessonProgress.user_id == user.id))
    return {
        r.lesson_slug: {"completed": r.completed_at is not None} for r in rows
    }


# --- flashcards --------------------------------------------------------------

class ReviewIn(BaseModel):
    card_slug: str
    correct: bool


@router.post("/flashcards/review")
def review_flashcard(body: ReviewIn, user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    try:
        return service.review_flashcard(db, user.id, body.card_slug, body.correct)
    except service.UnknownQuestion as e:
        raise HTTPException(404, "Unknown flashcard") from e


@router.get("/flashcards/due")
def flashcards_due(user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    idx = get_content_index()
    due = service.due_flashcards(db, user.id)
    return [
        {"slug": s, "front": idx.flashcards[s].front, "back": idx.flashcards[s].back}
        for s in due
    ]


# --- progress & mastery ------------------------------------------------------

@router.get("/progress")
def progress(user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    return service.progress_summary(db, user.id)


@router.get("/mastery")
def mastery(user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    return service.mastery_detail(db, user.id)
