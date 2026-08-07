"""Learner-state models.

The database stores *evidence about the learner*, never curriculum
(ADR-0002/0003). Content is referenced by stable slug strings — e.g. concept
"docker-volume", lesson "linux/filesystem", question "linux-q3" — which are
contracts defined in content/ and validated at content load time.

Attempt is append-only by design: it is the raw material a future
spaced-repetition scheduler will need, so nothing ever updates or deletes
attempt rows.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow


class AttemptKind(enum.StrEnum):
    QUIZ = "quiz"
    EXERCISE = "exercise"      # simulated-terminal exercise
    CHALLENGE = "challenge"    # boss / cumulative challenge
    FLASHCARD = "flashcard"
    RETENTION = "retention"    # future delayed retention checks


class Attempt(Base):
    """One submission against one item. Append-only evidence log."""

    __tablename__ = "attempts"
    __table_args__ = (Index("ix_attempts_user_item", "user_id", "item_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[AttemptKind] = mapped_column(Enum(AttemptKind, native_enum=False, length=20))
    item_slug: Mapped[str] = mapped_column(String(200))
    # Concepts this item exercises — denormalized from content at submit time
    # so history stays meaningful even if content later changes.
    concept_slugs: Mapped[list] = mapped_column(JSON, default=list)
    # What the learner actually did: chosen option, free text, or a VFS
    # snapshot + transcript for terminal exercises.
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class MasteryRecord(Base):
    """Current mastery per (user, concept) — a cache derived from attempts.

    The evidence counters are stored alongside the score so the UI can always
    show *why* a concept sits at 72% (docs/ARCHITECTURE.md, mastery model).
    Recomputable from the attempts log at any time.
    """

    __tablename__ = "mastery_records"
    __table_args__ = (UniqueConstraint("user_id", "concept_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    concept_slug: Mapped[str] = mapped_column(String(200), index=True)

    introduced: Mapped[bool] = mapped_column(Boolean, default=False)
    quiz_correct: Mapped[int] = mapped_column(Integer, default=0)
    quiz_total: Mapped[int] = mapped_column(Integer, default=0)
    exercise_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    applied_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    retention_correct: Mapped[int] = mapped_column(Integer, default=0)
    retention_total: Mapped[int] = mapped_column(Integer, default=0)

    score: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class FlashcardState(Base):
    """Per-card review state. Leitner-style boxes — deliberately simple, but
    with enough history (via attempts) for a real SRS later (ROADMAP)."""

    __tablename__ = "flashcard_states"
    __table_args__ = (UniqueConstraint("user_id", "card_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    card_slug: Mapped[str] = mapped_column(String(200))
    box: Mapped[int] = mapped_column(Integer, default=0)  # 0..4, higher = better known
    times_seen: Mapped[int] = mapped_column(Integer, default=0)
    times_correct: Mapped[int] = mapped_column(Integer, default=0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (UniqueConstraint("user_id", "lesson_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    lesson_slug: Mapped[str] = mapped_column(String(200))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LearningSession(Base):
    """Coarse study-span tracking for the dashboard ("you studied 40 min")."""

    __tablename__ = "learning_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ExerciseState(Base):
    """Resumable working state for a terminal exercise: the learner's current
    virtual filesystem snapshot and transcript. One live row per exercise;
    completed runs are recorded as Attempts."""

    __tablename__ = "exercise_states"
    __table_args__ = (UniqueConstraint("user_id", "exercise_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    exercise_slug: Mapped[str] = mapped_column(String(200))
    vfs_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    transcript: Mapped[list] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
