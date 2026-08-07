"""Learning service: grading, attempts, mastery updates, flashcards, progress.

Grading happens HERE, server-side — the browser never receives answer keys
(see content/router.py, which strips them). Every graded interaction also
appends an Attempt row: that log is the permanent evidence base.
"""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.modules.content.loader import get_content_index
from app.modules.content.schema import QuizQuestion
from app.modules.learning import mastery
from app.modules.learning.models import (
    Attempt,
    AttemptKind,
    FlashcardState,
    LearningSession,
    LessonProgress,
    MasteryRecord,
)

# Leitner review intervals per box (days). Box 0 = relearn now.
LEITNER_INTERVALS = [0, 1, 3, 7, 14]


# --- mastery plumbing --------------------------------------------------------

def _get_or_create_mastery(db: Session, user_id: int, concept_slug: str) -> MasteryRecord:
    record = db.scalar(
        select(MasteryRecord).where(
            MasteryRecord.user_id == user_id, MasteryRecord.concept_slug == concept_slug
        )
    )
    if record is None:
        record = MasteryRecord(user_id=user_id, concept_slug=concept_slug)
        db.add(record)
        db.flush()
    return record


def _apply_evidence(db: Session, user_id: int, concept_slugs: list[str], **updates) -> None:
    """Update evidence counters for each concept, then recompute its score."""
    for slug in concept_slugs:
        record = _get_or_create_mastery(db, user_id, slug)
        for key, value in updates.items():
            if key in ("quiz_correct", "quiz_total", "retention_correct", "retention_total"):
                setattr(record, key, getattr(record, key) + value)
            else:
                # booleans only ever ratchet upward: passing once counts
                if value:
                    setattr(record, key, True)
        record.score = mastery.compute_score(record)


# --- quiz grading ------------------------------------------------------------

class UnknownQuestion(Exception):
    pass


def grade_answer(question: QuizQuestion, answer: str | int) -> bool:
    if question.type == "multiple_choice":
        try:
            return int(answer) == question.answer_index
        except (TypeError, ValueError):
            return False
    # text: case-insensitive, stripped comparison against accepted answers
    normalized = str(answer).strip().lower()
    return normalized in [a.strip().lower() for a in question.accept or []]


def submit_quiz_answer(
    db: Session, user_id: int, question_id: str, answer: str | int
) -> dict:
    """Grade one answer, record the attempt, update mastery. Returns the
    result INCLUDING the explanation — mistakes become teaching moments,
    but only after the learner has committed to an answer."""
    idx = get_content_index()
    question = idx.question_by_id(question_id)
    if question is None:
        raise UnknownQuestion(question_id)

    correct = grade_answer(question, answer)
    db.add(
        Attempt(
            user_id=user_id,
            kind=AttemptKind.QUIZ,
            item_slug=question_id,
            concept_slugs=question.concepts,
            payload={"answer": answer},
            correct=correct,
        )
    )
    _apply_evidence(
        db, user_id, question.concepts,
        quiz_total=1, quiz_correct=1 if correct else 0,
    )
    touch_learning_session(db, user_id)
    return {
        "correct": correct,
        "explanation": question.explanation,
        "correct_answer": question.answer_index
        if question.type == "multiple_choice"
        else (question.accept or [None])[0],
    }


# --- exercise / challenge outcomes (called by simterm) -----------------------

def record_exercise_passed(
    db: Session, user_id: int, exercise_slug: str, concept_slugs: list[str], payload: dict
) -> None:
    db.add(
        Attempt(
            user_id=user_id,
            kind=AttemptKind.EXERCISE,
            item_slug=exercise_slug,
            concept_slugs=concept_slugs,
            payload=payload,
            correct=True,
        )
    )
    _apply_evidence(db, user_id, concept_slugs, exercise_passed=True)
    touch_learning_session(db, user_id)


def record_challenge_passed(
    db: Session, user_id: int, challenge_slug: str, concept_slugs: list[str], payload: dict
) -> None:
    db.add(
        Attempt(
            user_id=user_id,
            kind=AttemptKind.CHALLENGE,
            item_slug=challenge_slug,
            concept_slugs=concept_slugs,
            payload=payload,
            correct=True,
        )
    )
    _apply_evidence(db, user_id, concept_slugs, applied_passed=True)
    touch_learning_session(db, user_id)


# --- lesson progress ---------------------------------------------------------

def start_lesson(db: Session, user_id: int, lesson_slug: str) -> None:
    existing = db.scalar(
        select(LessonProgress).where(
            LessonProgress.user_id == user_id, LessonProgress.lesson_slug == lesson_slug
        )
    )
    if existing is None:
        db.add(LessonProgress(user_id=user_id, lesson_slug=lesson_slug))
    touch_learning_session(db, user_id)


def complete_lesson(db: Session, user_id: int, lesson_slug: str) -> None:
    """Completing a lesson marks its concepts 'introduced' — the first and
    weakest form of mastery evidence."""
    idx = get_content_index()
    lesson = idx.lessons.get(lesson_slug)
    if lesson is None:
        raise UnknownQuestion(lesson_slug)  # same 404 semantics
    progress = db.scalar(
        select(LessonProgress).where(
            LessonProgress.user_id == user_id, LessonProgress.lesson_slug == lesson_slug
        )
    )
    if progress is None:
        progress = LessonProgress(user_id=user_id, lesson_slug=lesson_slug)
        db.add(progress)
    if progress.completed_at is None:
        progress.completed_at = utcnow()
    _apply_evidence(db, user_id, lesson.meta.concepts, introduced=True)
    touch_learning_session(db, user_id)


# --- flashcards (Leitner boxes) ----------------------------------------------

def review_flashcard(db: Session, user_id: int, card_slug: str, correct: bool) -> dict:
    idx = get_content_index()
    card = idx.flashcards.get(card_slug)
    if card is None:
        raise UnknownQuestion(card_slug)

    state = db.scalar(
        select(FlashcardState).where(
            FlashcardState.user_id == user_id, FlashcardState.card_slug == card_slug
        )
    )
    if state is None:
        state = FlashcardState(user_id=user_id, card_slug=card_slug)
        db.add(state)
        db.flush()

    state.times_seen += 1
    if correct:
        state.times_correct += 1
        state.box = min(state.box + 1, len(LEITNER_INTERVALS) - 1)
    else:
        state.box = 0
    state.last_reviewed_at = utcnow()
    state.next_due_at = utcnow() + timedelta(days=LEITNER_INTERVALS[state.box])

    db.add(
        Attempt(
            user_id=user_id,
            kind=AttemptKind.FLASHCARD,
            item_slug=card_slug,
            concept_slugs=card.concepts,
            payload={"correct": correct, "box": state.box},
            correct=correct,
        )
    )
    touch_learning_session(db, user_id)
    return {"box": state.box, "next_due_at": state.next_due_at.isoformat()}


def due_flashcards(db: Session, user_id: int) -> list[str]:
    """Card slugs due for review: never-seen cards for completed lessons,
    plus any card whose next_due_at has passed."""
    idx = get_content_index()
    states = {
        s.card_slug: s
        for s in db.scalars(select(FlashcardState).where(FlashcardState.user_id == user_id))
    }
    completed = {
        p.lesson_slug
        for p in db.scalars(
            select(LessonProgress).where(
                LessonProgress.user_id == user_id, LessonProgress.completed_at.isnot(None)
            )
        )
    }
    now = utcnow()
    due: list[str] = []
    for slug in idx.flashcards:
        state = states.get(slug)
        if state is None:
            # unseen: only surface once its lesson has been completed
            introduced = any(
                slug in lesson.meta.flashcards and lesson.meta.slug in completed
                for lesson in idx.lessons.values()
            )
            if introduced:
                due.append(slug)
        elif state.next_due_at is not None and state.next_due_at <= now:
            due.append(slug)
    return due


# --- learning sessions & progress --------------------------------------------

SESSION_GAP = timedelta(minutes=30)  # inactivity that splits two study sessions


def touch_learning_session(db: Session, user_id: int) -> None:
    latest = db.scalar(
        select(LearningSession)
        .where(LearningSession.user_id == user_id)
        .order_by(LearningSession.last_activity_at.desc())
        .limit(1)
    )
    now = utcnow()
    if latest is not None and now - latest.last_activity_at < SESSION_GAP:
        latest.last_activity_at = now
    else:
        db.add(LearningSession(user_id=user_id, started_at=now, last_activity_at=now))


def progress_summary(db: Session, user_id: int) -> dict:
    """Everything the dashboard needs, in one query-bounded call."""
    idx = get_content_index()
    progress_rows = list(
        db.scalars(select(LessonProgress).where(LessonProgress.user_id == user_id))
    )
    completed = {p.lesson_slug for p in progress_rows if p.completed_at is not None}
    started = {p.lesson_slug for p in progress_rows}
    mastery_rows = list(
        db.scalars(select(MasteryRecord).where(MasteryRecord.user_id == user_id))
    )

    modules_out = []
    next_lesson = None
    for m in sorted(idx.modules.values(), key=lambda m: m.number):
        lesson_slugs = [f"{m.id}/{ls}" for ls in m.lessons]
        done = sum(1 for s in lesson_slugs if s in completed)
        modules_out.append(
            {
                "id": m.id,
                "title": m.title,
                "stage": m.stage,
                "number": m.number,
                "implemented": m.implemented,
                "lessons_total": len(lesson_slugs),
                "lessons_completed": done,
            }
        )
        if next_lesson is None and m.implemented:
            for s in lesson_slugs:
                if s not in completed:
                    next_lesson = s
                    break

    recent = sorted(mastery_rows, key=lambda r: r.updated_at, reverse=True)[:8]
    # "needs review": introduced but weak (below 0.5)
    weak = sorted(
        (r for r in mastery_rows if r.introduced and r.score < 0.5),
        key=lambda r: r.score,
    )[:8]

    sessions = list(
        db.scalars(
            select(LearningSession)
            .where(LearningSession.user_id == user_id)
            .order_by(LearningSession.started_at.desc())
            .limit(30)
        )
    )
    total_minutes = sum(
        max(1, int((s.last_activity_at - s.started_at).total_seconds() // 60)) for s in sessions
    )

    return {
        "modules": modules_out,
        "lessons_started": len(started),
        "lessons_completed": len(completed),
        "concepts_tracked": len(mastery_rows),
        "concepts_mastered": sum(1 for r in mastery_rows if r.score >= 0.8),
        "recently_learned": [
            {"concept": r.concept_slug, "score": r.score} for r in recent
        ],
        "needs_review": [{"concept": r.concept_slug, "score": r.score} for r in weak],
        "due_flashcards": len(due_flashcards(db, user_id)),
        "next_lesson": next_lesson,
        "study_minutes_recent": total_minutes,
    }


def mastery_detail(db: Session, user_id: int) -> list[dict]:
    rows = list(db.scalars(select(MasteryRecord).where(MasteryRecord.user_id == user_id)))
    idx = get_content_index()
    out = []
    for r in sorted(rows, key=lambda r: r.concept_slug):
        term = idx.vocabulary.get(r.concept_slug)
        out.append(
            {
                "concept": r.concept_slug,
                "term": term.term if term else r.concept_slug,
                "score": r.score,
                "breakdown": mastery.breakdown(r),
                "updated_at": r.updated_at.isoformat(),
            }
        )
    return out
