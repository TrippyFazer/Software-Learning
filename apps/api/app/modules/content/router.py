"""Read-only curriculum endpoints.

Everything here requires authentication (single-learner private app) and is
carefully answer-free: quiz questions are served WITHOUT answer_index /
accept / explanation — grading happens server-side in the learning module,
so the browser never holds the answer key.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.modules.auth.deps import CurrentUser
from app.modules.content.loader import get_content_index
from app.modules.content.schema import Flashcard, VocabularyTerm

router = APIRouter(prefix="/content", tags=["content"])


# --- curriculum map ----------------------------------------------------------

class LessonSummary(BaseModel):
    slug: str
    title: str
    difficulty: str
    concepts: list[str]
    has_quiz: bool
    has_exercise: bool


class ModuleOut(BaseModel):
    id: str
    number: int
    stage: int
    title: str
    description: str
    implemented: bool
    lessons: list[LessonSummary]


class CurriculumOut(BaseModel):
    modules: list[ModuleOut]
    challenges: list[dict]


@router.get("/curriculum", response_model=CurriculumOut)
def curriculum(_: CurrentUser):
    idx = get_content_index()
    modules = []
    for m in sorted(idx.modules.values(), key=lambda m: m.number):
        lessons = []
        for slug in m.lessons:
            lesson = idx.lessons[f"{m.id}/{slug}"]
            lessons.append(
                LessonSummary(
                    slug=lesson.meta.slug,
                    title=lesson.meta.title,
                    difficulty=lesson.meta.difficulty,
                    concepts=lesson.meta.concepts,
                    has_quiz=lesson.meta.quiz is not None,
                    has_exercise=lesson.meta.exercise is not None,
                )
            )
        modules.append(
            ModuleOut(
                id=m.id, number=m.number, stage=m.stage, title=m.title,
                description=m.description, implemented=m.implemented, lessons=lessons,
            )
        )
    challenges = [
        {"id": c.id, "title": c.title, "stage": c.stage} for c in idx.challenges.values()
    ]
    return CurriculumOut(modules=modules, challenges=challenges)


# --- lessons -----------------------------------------------------------------

class LessonOut(BaseModel):
    slug: str
    title: str
    module: str
    difficulty: str
    concepts: list[str]
    prerequisites: list[str]
    quiz: str | None
    exercise: str | None
    flashcards: list[str]
    body: str


@router.get("/lessons/{module}/{lesson}", response_model=LessonOut)
def lesson(module: str, lesson: str, _: CurrentUser):
    idx = get_content_index()
    found = idx.lessons.get(f"{module}/{lesson}")
    if found is None:
        raise HTTPException(404, "Lesson not found")
    m = found.meta
    return LessonOut(
        slug=m.slug, title=m.title, module=m.module, difficulty=m.difficulty,
        concepts=m.concepts, prerequisites=m.prerequisites, quiz=m.quiz,
        exercise=m.exercise, flashcards=m.flashcards, body=found.body,
    )


# --- vocabulary --------------------------------------------------------------

@router.get("/vocabulary", response_model=list[VocabularyTerm])
def vocabulary(_: CurrentUser):
    return sorted(get_content_index().vocabulary.values(), key=lambda t: t.term.lower())


# --- quizzes (answer-free) ---------------------------------------------------

class QuestionOut(BaseModel):
    id: str
    type: str
    prompt: str
    concepts: list[str]
    options: list[str] | None = None   # multiple_choice only; no answer_index


class QuizOut(BaseModel):
    id: str
    questions: list[QuestionOut]


def _strip_answers(questions) -> list[QuestionOut]:
    return [
        QuestionOut(id=q.id, type=q.type, prompt=q.prompt, concepts=q.concepts, options=q.options)
        for q in questions
    ]


@router.get("/quizzes/{module}/{name}", response_model=QuizOut)
def quiz(module: str, name: str, _: CurrentUser):
    idx = get_content_index()
    q = idx.quizzes.get(f"{module}/{name}")
    if q is None:
        raise HTTPException(404, "Quiz not found")
    return QuizOut(id=q.id, questions=_strip_answers(q.questions))


# --- exercises ---------------------------------------------------------------

class ExerciseOut(BaseModel):
    id: str
    title: str
    mission: str
    concepts: list[str]
    goal_checklist: list[str]      # human descriptions only, not the machine spec
    hint_count: int


@router.get("/exercises/{module}/{name}", response_model=ExerciseOut)
def exercise(module: str, name: str, _: CurrentUser):
    idx = get_content_index()
    ex = idx.exercises.get(f"{module}/{name}")
    if ex is None:
        raise HTTPException(404, "Exercise not found")
    return ExerciseOut(
        id=ex.id, title=ex.title, mission=ex.mission, concepts=ex.concepts,
        goal_checklist=[g.description for g in ex.goal], hint_count=len(ex.hints),
    )


class HintOut(BaseModel):
    index: int
    hint: str


@router.get("/exercises/{module}/{name}/hints/{index}", response_model=HintOut)
def exercise_hint(module: str, name: str, index: int, _: CurrentUser):
    """Hints are fetched one at a time, on explicit request — the difficulty
    is part of the learning (dev philosophy §37)."""
    idx = get_content_index()
    ex = idx.exercises.get(f"{module}/{name}")
    if ex is None:
        raise HTTPException(404, "Exercise not found")
    if not (0 <= index < len(ex.hints)):
        raise HTTPException(404, "No such hint")
    return HintOut(index=index, hint=ex.hints[index])


# --- challenges --------------------------------------------------------------

class ChallengeOut(BaseModel):
    id: str
    title: str
    stage: int
    briefing: str
    questions: list[QuestionOut]
    goal_checklist: list[str]


@router.get("/challenges/{name}", response_model=ChallengeOut)
def challenge(name: str, _: CurrentUser):
    idx = get_content_index()
    ch = idx.challenges.get(name)
    if ch is None:
        raise HTTPException(404, "Challenge not found")
    return ChallengeOut(
        id=ch.id, title=ch.title, stage=ch.stage, briefing=ch.briefing,
        questions=_strip_answers(ch.questions),
        goal_checklist=[g.description for g in ch.goal],
    )


# --- flashcards --------------------------------------------------------------

@router.get("/flashcards", response_model=list[Flashcard])
def flashcards(_: CurrentUser):
    return list(get_content_index().flashcards.values())
