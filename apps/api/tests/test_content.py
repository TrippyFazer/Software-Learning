"""Content engine: real-content loading, answer stripping, and fail-fast
validation of malformed curriculum files."""

from pathlib import Path

import pytest

from app.modules.content.loader import ContentError, load_content
from tests.conftest import REPO_ROOT


def test_real_content_loads_and_cross_validates():
    idx = load_content(REPO_ROOT / "content")
    assert len(idx.modules) == 31          # 4 implemented + 27 planned
    assert len(idx.lessons) >= 12
    assert "systems/what-is-a-server" in idx.lessons
    assert "server-rookie" in idx.challenges
    # every implemented lesson's declared quiz/exercise exists (loader enforces)
    for lesson in idx.lessons.values():
        if lesson.meta.quiz:
            assert lesson.meta.quiz in idx.quizzes


def test_lesson_endpoint_serves_body(auth_client):
    res = auth_client.get("/api/content/lessons/linux/filesystem")
    assert res.status_code == 200
    body = res.json()
    assert body["title"].startswith("The Filesystem")
    assert "## Mental model" in body["body"]
    assert res.status_code == 200


def test_unknown_lesson_404(auth_client):
    assert auth_client.get("/api/content/lessons/linux/nope").status_code == 404


def test_quiz_payload_never_contains_answers(auth_client):
    """The answer key must not reach the browser, in any field."""
    res = auth_client.get("/api/content/quizzes/linux/filesystem")
    assert res.status_code == 200
    for q in res.json()["questions"]:
        assert set(q.keys()) <= {"id", "type", "prompt", "concepts", "options"}, (
            f"question {q['id']} leaks fields beyond the public five: {sorted(q)}"
        )


def test_challenge_payload_never_contains_answers(auth_client):
    res = auth_client.get("/api/content/challenges/server-rookie")
    assert res.status_code == 200
    assert "answer_index" not in res.text
    # the machine-readable goal spec stays server-side too
    assert "mode_is" not in res.text


# --- invalid content must fail loudly at load time ---------------------------

def _write_minimal_content(root: Path) -> None:
    (root / "modules" / "m1").mkdir(parents=True)
    (root / "modules" / "m1" / "module.yaml").write_text(
        "id: m1\nnumber: 0\nstage: 1\ntitle: T\ndescription: D\nlessons: [l1]\n"
    )
    (root / "modules" / "m1" / "l1.md").write_text(
        "---\nmodule: m1\nlesson: l1\ntitle: L\n---\nBody\n"
    )


def test_minimal_valid_content_loads(tmp_path):
    _write_minimal_content(tmp_path)
    idx = load_content(tmp_path)
    assert "m1/l1" in idx.lessons


def test_missing_lesson_file_fails(tmp_path):
    _write_minimal_content(tmp_path)
    (tmp_path / "modules" / "m1" / "l1.md").unlink()
    with pytest.raises(ContentError, match="missing"):
        load_content(tmp_path)


def test_missing_frontmatter_fails(tmp_path):
    _write_minimal_content(tmp_path)
    (tmp_path / "modules" / "m1" / "l1.md").write_text("Just markdown, no frontmatter")
    with pytest.raises(ContentError, match="frontmatter"):
        load_content(tmp_path)


def test_frontmatter_slug_mismatch_fails(tmp_path):
    _write_minimal_content(tmp_path)
    (tmp_path / "modules" / "m1" / "l1.md").write_text(
        "---\nmodule: m1\nlesson: other\ntitle: L\n---\nBody\n"
    )
    with pytest.raises(ContentError, match="frontmatter says"):
        load_content(tmp_path)


def test_quiz_answer_index_out_of_range_fails(tmp_path):
    _write_minimal_content(tmp_path)
    (tmp_path / "quizzes").mkdir()
    (tmp_path / "quizzes" / "bad.yaml").write_text(
        "id: m1/bad\nquestions:\n"
        "  - id: q1\n    type: multiple_choice\n    prompt: P\n"
        "    options: [a, b]\n    answer_index: 5\n"
    )
    with pytest.raises(ContentError, match="answer_index"):
        load_content(tmp_path)


def test_unknown_quiz_reference_fails(tmp_path):
    _write_minimal_content(tmp_path)
    (tmp_path / "modules" / "m1" / "l1.md").write_text(
        "---\nmodule: m1\nlesson: l1\ntitle: L\nquiz: m1/ghost\n---\nBody\n"
    )
    with pytest.raises(ContentError, match="unknown quiz"):
        load_content(tmp_path)


def test_unknown_prerequisite_fails(tmp_path):
    _write_minimal_content(tmp_path)
    (tmp_path / "modules" / "m1" / "l1.md").write_text(
        "---\nmodule: m1\nlesson: l1\ntitle: L\nprerequisites: [ghost/lesson]\n---\nBody\n"
    )
    with pytest.raises(ContentError, match="unknown prerequisite"):
        load_content(tmp_path)


def test_invalid_yaml_fails_with_filename(tmp_path):
    _write_minimal_content(tmp_path)
    (tmp_path / "vocabulary").mkdir()
    (tmp_path / "vocabulary" / "broken.yaml").write_text("- slug: x\n  term: a: b: c\n")
    with pytest.raises(ContentError, match="broken.yaml"):
        load_content(tmp_path)


def test_duplicate_flashcard_slug_fails(tmp_path):
    _write_minimal_content(tmp_path)
    (tmp_path / "flashcards").mkdir()
    (tmp_path / "flashcards" / "cards.yaml").write_text(
        "- slug: c1\n  front: F\n  back: B\n  module: m1\n"
        "- slug: c1\n  front: F2\n  back: B2\n  module: m1\n"
    )
    with pytest.raises(ContentError, match="duplicate flashcard"):
        load_content(tmp_path)
