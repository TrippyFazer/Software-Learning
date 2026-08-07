"""Simulated-terminal endpoints for exercises and challenges.

State model: each (user, exercise) has one resumable ExerciseState row —
the current VFS snapshot and transcript. Completion (all goals met) records
an append-only Attempt via the learning module and updates mastery. The
learner can reset to the exercise's initial state at any time; the Attempt
log keeps the history.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.auth.deps import CurrentUser
from app.modules.content.loader import get_content_index
from app.modules.content.schema import Challenge, Exercise
from app.modules.learning import service as learning_service
from app.modules.learning.models import Attempt, ExerciseState
from app.modules.simterm import commands, goals
from app.modules.simterm.vfs import VirtualFileSystem

router = APIRouter(prefix="/simterm", tags=["simterm"])

MAX_TRANSCRIPT = 400  # lines kept per exercise state


class TermState(BaseModel):
    cwd: str
    transcript: list[dict]
    goals: list[dict]
    completed: bool


class InputIn(BaseModel):
    line: str = Field(max_length=commands.MAX_LINE_LENGTH)


def _load_item(kind: str, slug: str) -> Exercise | Challenge:
    idx = get_content_index()
    item = idx.exercises.get(slug) if kind == "exercise" else idx.challenges.get(slug)
    if item is None:
        raise HTTPException(404, f"{kind} not found")
    return item


def _state_slug(kind: str, slug: str) -> str:
    return slug if kind == "exercise" else f"challenge:{slug}"


def _get_state(db: Session, user_id: int, kind: str, slug: str) -> ExerciseState | None:
    return db.scalar(
        select(ExerciseState).where(
            ExerciseState.user_id == user_id,
            ExerciseState.exercise_slug == _state_slug(kind, slug),
        )
    )


def _fresh_vfs(item: Exercise | Challenge) -> VirtualFileSystem:
    return VirtualFileSystem.from_spec(item.cwd, item.initial_files)


def _already_completed(db: Session, user_id: int, kind: str, slug: str) -> bool:
    return (
        db.scalar(
            select(Attempt.id)
            .where(
                Attempt.user_id == user_id,
                Attempt.item_slug == slug,
                Attempt.correct.is_(True),
            )
            .limit(1)
        )
        is not None
    )


def _respond(
    db: Session, user_id: int, kind: str, slug: str,
    item: Exercise | Challenge, state: ExerciseState, vfs: VirtualFileSystem,
) -> TermState:
    goal_status = goals.evaluate(vfs, item.goal)
    all_met = bool(item.goal) and all(g["met"] for g in goal_status)
    # Exercises complete on goals alone. Challenges also require their
    # diagnosis questions — recording happens in challenge_status instead.
    if kind == "exercise" and all_met and not _already_completed(db, user_id, kind, slug):
        payload = {"transcript_tail": state.transcript[-40:]}
        learning_service.record_exercise_passed(db, user_id, slug, item.concepts, payload)
    return TermState(
        cwd=vfs.cwd, transcript=state.transcript, goals=goal_status,
        completed=all_met or (kind == "exercise" and _already_completed(db, user_id, kind, slug)),
    )


def _start(db: Session, user: CurrentUser, kind: str, slug: str) -> TermState:
    item = _load_item(kind, slug)
    state = _get_state(db, user.id, kind, slug)
    if state is None:
        vfs = _fresh_vfs(item)
        state = ExerciseState(
            user_id=user.id,
            exercise_slug=_state_slug(kind, slug),
            vfs_snapshot=vfs.to_dict(),
            transcript=[],
        )
        db.add(state)
        db.flush()
    else:
        vfs = VirtualFileSystem.from_dict(state.vfs_snapshot)
    return _respond(db, user.id, kind, slug, item, state, vfs)


def _input(db: Session, user: CurrentUser, kind: str, slug: str, line: str) -> TermState:
    item = _load_item(kind, slug)
    state = _get_state(db, user.id, kind, slug)
    if state is None:
        raise HTTPException(409, "Start the exercise first")
    vfs = VirtualFileSystem.from_dict(state.vfs_snapshot)

    output = commands.run_line(vfs, line)
    entry = {"input": line, "output": output, "cwd_after": vfs.cwd}
    state.transcript = (state.transcript + [entry])[-MAX_TRANSCRIPT:]
    state.vfs_snapshot = vfs.to_dict()
    return _respond(db, user.id, kind, slug, item, state, vfs)


def _reset(db: Session, user: CurrentUser, kind: str, slug: str) -> TermState:
    item = _load_item(kind, slug)
    state = _get_state(db, user.id, kind, slug)
    vfs = _fresh_vfs(item)
    if state is None:
        state = ExerciseState(
            user_id=user.id, exercise_slug=_state_slug(kind, slug),
            vfs_snapshot=vfs.to_dict(), transcript=[],
        )
        db.add(state)
        db.flush()
    else:
        state.vfs_snapshot = vfs.to_dict()
        state.transcript = []
    return _respond(db, user.id, kind, slug, item, state, vfs)


# --- exercises ---------------------------------------------------------------

@router.post("/exercises/{module}/{name}/start", response_model=TermState)
def start_exercise(
    module: str, name: str, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
):
    return _start(db, user, "exercise", f"{module}/{name}")


@router.post("/exercises/{module}/{name}/input", response_model=TermState)
def exercise_input(
    module: str, name: str, body: InputIn, user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    return _input(db, user, "exercise", f"{module}/{name}", body.line)


@router.post("/exercises/{module}/{name}/reset", response_model=TermState)
def reset_exercise(
    module: str, name: str, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
):
    return _reset(db, user, "exercise", f"{module}/{name}")


# --- challenges --------------------------------------------------------------

@router.post("/challenges/{name}/start", response_model=TermState)
def start_challenge(name: str, user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    return _start(db, user, "challenge", name)


@router.post("/challenges/{name}/input", response_model=TermState)
def challenge_input(
    name: str, body: InputIn, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
):
    return _input(db, user, "challenge", name, body.line)


@router.post("/challenges/{name}/reset", response_model=TermState)
def reset_challenge(name: str, user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    return _reset(db, user, "challenge", name)


class ChallengeStatus(BaseModel):
    goals_met: bool
    questions_total: int
    questions_correct: int
    completed: bool
    success_text: str | None


@router.get("/challenges/{name}/status", response_model=ChallengeStatus)
def challenge_status(name: str, user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    """A challenge is complete when its terminal goals are met AND every
    diagnosis question has been answered correctly at least once."""
    item = _load_item("challenge", name)
    state = _get_state(db, user.id, "challenge", name)
    vfs = VirtualFileSystem.from_dict(state.vfs_snapshot) if state else _fresh_vfs(item)
    goal_status = goals.evaluate(vfs, item.goal)
    goals_met = all(g["met"] for g in goal_status) if item.goal else True

    correct_q = 0
    for q in item.questions:
        if (
            db.scalar(
                select(Attempt.id)
                .where(
                    Attempt.user_id == user.id,
                    Attempt.item_slug == q.id,
                    Attempt.correct.is_(True),
                )
                .limit(1)
            )
            is not None
        ):
            correct_q += 1

    completed = goals_met and correct_q == len(item.questions)
    if completed and not _already_completed(db, user.id, "challenge", item.id):
        learning_service.record_challenge_passed(
            db, user.id, item.id, item.concepts, {"questions_correct": correct_q}
        )
    return ChallengeStatus(
        goals_met=goals_met,
        questions_total=len(item.questions),
        questions_correct=correct_q,
        completed=completed,
        success_text=item.success_text if completed else None,
    )
