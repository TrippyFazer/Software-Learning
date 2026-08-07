"""Curriculum loader: parses everything under content/ into a validated,
in-memory index.

Fail-fast philosophy: any malformed file raises ContentError naming the file
and the problem, and the application refuses to start (ADR-0002). A content
bug should never become a runtime 500.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import ValidationError

from app.core.settings import get_settings
from app.modules.content.schema import (
    Challenge,
    Exercise,
    Flashcard,
    Lesson,
    LessonMeta,
    ModuleManifest,
    Quiz,
    VocabularyTerm,
)

logger = logging.getLogger(__name__)


class ContentError(Exception):
    """Raised when content/ fails to parse or validate."""


@dataclass
class ContentIndex:
    modules: dict[str, ModuleManifest] = field(default_factory=dict)
    lessons: dict[str, Lesson] = field(default_factory=dict)          # "module/lesson"
    vocabulary: dict[str, VocabularyTerm] = field(default_factory=dict)
    quizzes: dict[str, Quiz] = field(default_factory=dict)
    exercises: dict[str, Exercise] = field(default_factory=dict)
    challenges: dict[str, Challenge] = field(default_factory=dict)
    flashcards: dict[str, Flashcard] = field(default_factory=dict)
    concepts: set[str] = field(default_factory=set)                   # all declared concept slugs

    def question_by_id(self, question_id: str):
        """Find a quiz/challenge question anywhere in the index."""
        for quiz in self.quizzes.values():
            for q in quiz.questions:
                if q.id == question_id:
                    return q
        for ch in self.challenges.values():
            for q in ch.questions:
                if q.id == question_id:
                    return q
        return None


def _read_yaml(path: Path):
    try:
        with path.open(encoding="utf-8") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ContentError(f"{path}: invalid YAML: {e}") from e


def _split_frontmatter(path: Path) -> tuple[dict, str]:
    """Split '---\\n<yaml>\\n---\\n<markdown>' — the one lesson file format."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ContentError(f"{path}: missing YAML frontmatter (file must start with ---)")
    parts = text.split("\n---", 2)
    # parts[0] == '---' prefix chunk; find the closing fence
    end = text.find("\n---", 3)
    if end == -1:
        raise ContentError(f"{path}: unterminated frontmatter (no closing ---)")
    raw_meta = text[3:end]
    body = text[end + 4 :].lstrip("\n")
    meta = yaml.safe_load(raw_meta)
    if not isinstance(meta, dict):
        raise ContentError(f"{path}: frontmatter must be a YAML mapping")
    return meta, body


def load_content(root: Path) -> ContentIndex:
    if not root.is_dir():
        raise ContentError(f"content root {root} does not exist")
    index = ContentIndex()

    # --- modules + lessons ---------------------------------------------------
    modules_dir = root / "modules"
    for manifest_path in sorted(modules_dir.glob("*/module.yaml")):
        try:
            manifest = ModuleManifest.model_validate(_read_yaml(manifest_path))
        except ValidationError as e:
            raise ContentError(f"{manifest_path}: {e}") from e
        if manifest.id in index.modules:
            raise ContentError(f"{manifest_path}: duplicate module id {manifest.id}")
        index.modules[manifest.id] = manifest

        for lesson_slug in manifest.lessons:
            lesson_path = manifest_path.parent / f"{lesson_slug}.md"
            if not lesson_path.is_file():
                raise ContentError(
                    f"{manifest_path}: lists lesson '{lesson_slug}' but {lesson_path} is missing"
                )
            meta_dict, body = _split_frontmatter(lesson_path)
            try:
                meta = LessonMeta.model_validate(meta_dict)
            except ValidationError as e:
                raise ContentError(f"{lesson_path}: {e}") from e
            if meta.module != manifest.id or meta.lesson != lesson_slug:
                raise ContentError(
                    f"{lesson_path}: frontmatter says {meta.module}/{meta.lesson}, "
                    f"expected {manifest.id}/{lesson_slug}"
                )
            index.lessons[meta.slug] = Lesson(meta=meta, body=body)
            index.concepts.update(meta.concepts)

    # --- vocabulary ----------------------------------------------------------
    for vocab_path in sorted((root / "vocabulary").glob("*.yaml")):
        data = _read_yaml(vocab_path) or []
        for i, entry in enumerate(data):
            try:
                term = VocabularyTerm.model_validate(entry)
            except ValidationError as e:
                raise ContentError(f"{vocab_path} (entry {i}): {e}") from e
            if term.slug in index.vocabulary:
                raise ContentError(f"{vocab_path}: duplicate vocabulary slug {term.slug}")
            index.vocabulary[term.slug] = term
            index.concepts.add(term.slug)

    # --- quizzes -------------------------------------------------------------
    for quiz_path in sorted((root / "quizzes").rglob("*.yaml")):
        try:
            quiz = Quiz.model_validate(_read_yaml(quiz_path))
        except ValidationError as e:
            raise ContentError(f"{quiz_path}: {e}") from e
        if quiz.id in index.quizzes:
            raise ContentError(f"{quiz_path}: duplicate quiz id {quiz.id}")
        seen_q = set()
        for q in quiz.questions:
            if q.id in seen_q:
                raise ContentError(f"{quiz_path}: duplicate question id {q.id}")
            seen_q.add(q.id)
        index.quizzes[quiz.id] = quiz

    # --- exercises -----------------------------------------------------------
    for ex_path in sorted((root / "exercises").rglob("*.yaml")):
        try:
            ex = Exercise.model_validate(_read_yaml(ex_path))
        except ValidationError as e:
            raise ContentError(f"{ex_path}: {e}") from e
        if ex.id in index.exercises:
            raise ContentError(f"{ex_path}: duplicate exercise id {ex.id}")
        index.exercises[ex.id] = ex

    # --- challenges ----------------------------------------------------------
    for ch_path in sorted((root / "challenges").glob("*.yaml")):
        try:
            ch = Challenge.model_validate(_read_yaml(ch_path))
        except ValidationError as e:
            raise ContentError(f"{ch_path}: {e}") from e
        index.challenges[ch.id] = ch

    # --- flashcards ----------------------------------------------------------
    for fc_path in sorted((root / "flashcards").glob("*.yaml")):
        data = _read_yaml(fc_path) or []
        for i, entry in enumerate(data):
            try:
                card = Flashcard.model_validate(entry)
            except ValidationError as e:
                raise ContentError(f"{fc_path} (entry {i}): {e}") from e
            if card.slug in index.flashcards:
                raise ContentError(f"{fc_path}: duplicate flashcard slug {card.slug}")
            index.flashcards[card.slug] = card

    # --- cross-reference checks ---------------------------------------------
    for lesson in index.lessons.values():
        if lesson.meta.quiz and lesson.meta.quiz not in index.quizzes:
            raise ContentError(f"lesson {lesson.meta.slug}: unknown quiz '{lesson.meta.quiz}'")
        if lesson.meta.exercise and lesson.meta.exercise not in index.exercises:
            raise ContentError(
                f"lesson {lesson.meta.slug}: unknown exercise '{lesson.meta.exercise}'"
            )
        for prereq in lesson.meta.prerequisites:
            if prereq not in index.lessons:
                raise ContentError(f"lesson {lesson.meta.slug}: unknown prerequisite '{prereq}'")
        for card_slug in lesson.meta.flashcards:
            if card_slug not in index.flashcards:
                raise ContentError(f"lesson {lesson.meta.slug}: unknown flashcard '{card_slug}'")

    return index


# --- cached access -----------------------------------------------------------

_index: ContentIndex | None = None


def get_content_index() -> ContentIndex:
    """Cached index; re-reads from disk when CONTENT_HOT_RELOAD is on (dev)."""
    global _index
    settings = get_settings()
    if _index is None or settings.content_hot_reload:
        _index = load_content(Path(settings.content_root).resolve())
    return _index


def reset_content_cache() -> None:
    global _index
    _index = None
