"""Pydantic schemas for everything under content/.

These are the contracts that make curriculum authoring safe: any file that
doesn't validate stops the app at startup with a precise error naming the
file and field (ADR-0002). Slugs are stable identifiers referenced by
learner state in PostgreSQL — treat renames as breaking changes.
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

Slug = Field(pattern=r"^[a-z0-9][a-z0-9/-]*$")


class ModuleManifest(BaseModel):
    """content/modules/<dir>/module.yaml"""

    id: str = Slug
    number: int
    stage: int
    title: str
    description: str
    lessons: list[str] = []          # lesson slugs in teaching order
    implemented: bool = True         # False → shown on the map as "planned"


class LessonMeta(BaseModel):
    """Frontmatter of content/modules/<module>/<lesson>.md"""

    module: str = Slug
    lesson: str = Slug
    title: str
    difficulty: Literal["beginner", "intermediate", "advanced"] = "beginner"
    concepts: list[str] = []
    prerequisites: list[str] = []    # lesson slugs ("module/lesson")
    quiz: str | None = None          # quiz id, e.g. "linux/filesystem"
    exercise: str | None = None      # exercise id
    flashcards: list[str] = []       # card slugs surfaced by this lesson

    @property
    def slug(self) -> str:
        return f"{self.module}/{self.lesson}"


class Lesson(BaseModel):
    meta: LessonMeta
    body: str                        # Markdown, rendered by the frontend


class VocabularyTerm(BaseModel):
    """Entries in content/vocabulary/<module>.yaml"""

    slug: str = Slug
    term: str
    mental_model: str                # plain-language definition
    technical: str                   # precise definition
    why_it_matters: str
    related: list[str] = []
    module: str = Slug


# --- Quizzes -----------------------------------------------------------------

class QuizQuestion(BaseModel):
    id: str = Slug
    type: Literal["multiple_choice", "text"]
    prompt: str
    concepts: list[str] = []
    # multiple_choice
    options: list[str] | None = None
    answer_index: int | None = None
    # text: accepted answers, compared case-insensitively after stripping
    accept: list[str] | None = None
    explanation: str = ""

    @model_validator(mode="after")
    def _check_shape(self) -> "QuizQuestion":
        if self.type == "multiple_choice":
            if not self.options or self.answer_index is None:
                raise ValueError(f"question {self.id}: multiple_choice needs options and answer_index")
            if not (0 <= self.answer_index < len(self.options)):
                raise ValueError(f"question {self.id}: answer_index out of range")
        if self.type == "text" and not self.accept:
            raise ValueError(f"question {self.id}: text question needs an accept list")
        return self


class Quiz(BaseModel):
    """content/quizzes/<module>/<lesson>.yaml"""

    id: str = Slug
    questions: list[QuizQuestion]


# --- Terminal exercises ------------------------------------------------------

class GoalCheck(BaseModel):
    """One assertion about the learner's virtual filesystem after practice.

    Exercises are graded on resulting STATE, never on typed command strings,
    so any valid approach passes (ADR-0004).
    """

    type: Literal[
        "dir_exists", "file_exists", "path_absent",
        "file_contains", "cwd_is", "mode_is",
    ]
    path: str
    text: str | None = None          # for file_contains
    mode: str | None = None          # for mode_is, e.g. "755"
    description: str                 # learner-facing checklist line

    @model_validator(mode="after")
    def _check_args(self) -> "GoalCheck":
        if self.type == "file_contains" and self.text is None:
            raise ValueError("file_contains needs text")
        if self.type == "mode_is" and self.mode is None:
            raise ValueError("mode_is needs mode")
        return self


class VfsFileSpec(BaseModel):
    """Initial state of one VFS node."""

    content: str = ""
    mode: str = "644"                # octal string; dirs default to 755
    owner: str = "learner"


class Exercise(BaseModel):
    """content/exercises/<module>/<slug>.yaml"""

    id: str = Slug
    title: str
    mission: str                     # Markdown shown to the learner
    concepts: list[str] = []
    cwd: str = "/home/learner"
    # path -> spec for files, path -> None (i.e. {}) for directories
    initial_files: dict[str, VfsFileSpec | None] = {}
    goal: list[GoalCheck]
    hints: list[str] = []            # revealed one at a time on request


class Challenge(BaseModel):
    """content/challenges/<slug>.yaml — a cumulative 'boss' scenario.

    A challenge combines exploration of a broken VFS with diagnosis
    questions and (optionally) repair goals. It never names the concepts
    that solve it — that's the point.
    """

    id: str = Slug
    title: str
    stage: int
    briefing: str                    # Markdown scenario text
    concepts: list[str] = []
    cwd: str = "/home/learner"
    initial_files: dict[str, VfsFileSpec | None] = {}
    questions: list[QuizQuestion] = []
    goal: list[GoalCheck] = []
    success_text: str = "Challenge complete."


class Flashcard(BaseModel):
    """Entries in content/flashcards/<module>.yaml"""

    slug: str = Slug
    front: str
    back: str
    concepts: list[str] = []
    module: str = Slug
