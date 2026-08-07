"""Quiz grading, attempt persistence, mastery math, flashcards, progress."""

from sqlalchemy import select

from app.modules.learning import mastery
from app.modules.learning.models import Attempt, MasteryRecord


def test_multiple_choice_grading_and_explanation(auth_client):
    wrong = auth_client.post(
        "/api/learning/answers", json={"question_id": "linux-fs-q1", "answer": 0}
    ).json()
    assert wrong["correct"] is False
    assert wrong["explanation"]  # mistakes teach — explanation present
    right = auth_client.post(
        "/api/learning/answers", json={"question_id": "linux-fs-q1", "answer": 3}
    ).json()
    assert right["correct"] is True


def test_text_answer_normalization(auth_client):
    res = auth_client.post(
        "/api/learning/answers", json={"question_id": "linux-fs-q3", "answer": "  PWD "}
    ).json()
    assert res["correct"] is True


def test_unknown_question_404(auth_client):
    res = auth_client.post("/api/learning/answers", json={"question_id": "ghost-q", "answer": 1})
    assert res.status_code == 404


def test_attempts_are_persisted_append_only(auth_client, db_session):
    for answer in (0, 3, 3):
        auth_client.post(
            "/api/learning/answers", json={"question_id": "linux-fs-q1", "answer": answer}
        )
    attempts = list(db_session.scalars(select(Attempt)))
    assert len(attempts) == 3  # every submission kept, including repeats
    assert [a.correct for a in attempts] == [False, True, True]
    assert attempts[0].payload == {"answer": 0}
    assert attempts[0].kind == "quiz"


def test_mastery_math_matches_documented_weights(auth_client, db_session):
    # linux-fs-q1 exercises concept "path": one wrong, one right → 50% quiz accuracy
    auth_client.post("/api/learning/answers", json={"question_id": "linux-fs-q1", "answer": 0})
    auth_client.post("/api/learning/answers", json={"question_id": "linux-fs-q1", "answer": 3})
    record = db_session.scalar(select(MasteryRecord).where(MasteryRecord.concept_slug == "path"))
    assert record.quiz_total == 2 and record.quiz_correct == 1
    assert record.score == round(0.35 * 0.5, 4)  # only quiz evidence so far

    # completing the lesson adds "introduced" (0.15)
    auth_client.post("/api/learning/lessons/linux/filesystem/complete")
    db_session.expire_all()
    record = db_session.scalar(select(MasteryRecord).where(MasteryRecord.concept_slug == "path"))
    assert record.score == round(0.15 + 0.35 * 0.5, 4)


def test_breakdown_always_sums_to_score(auth_client, db_session):
    """The learner-facing explanation must never disagree with the score."""
    auth_client.post("/api/learning/lessons/linux/filesystem/complete")
    auth_client.post("/api/learning/answers", json={"question_id": "linux-fs-q1", "answer": 3})
    for record in db_session.scalars(select(MasteryRecord)):
        parts = mastery.breakdown(record)
        total = sum(p.get("earned", 0.0) for p in parts.values())
        assert abs(total - record.score) < 1e-6


def test_lesson_completion_marks_concepts_introduced(auth_client, db_session):
    auth_client.post("/api/learning/lessons/systems/what-is-a-server/complete")
    slugs = {
        r.concept_slug
        for r in db_session.scalars(select(MasteryRecord).where(MasteryRecord.introduced))
    }
    assert {"server", "client", "host", "hardware", "operating-system"} <= slugs


def test_flashcard_leitner_progression(auth_client):
    r1 = auth_client.post(
        "/api/learning/flashcards/review", json={"card_slug": "card-server", "correct": True}
    ).json()
    assert r1["box"] == 1
    r2 = auth_client.post(
        "/api/learning/flashcards/review", json={"card_slug": "card-server", "correct": True}
    ).json()
    assert r2["box"] == 2
    r3 = auth_client.post(
        "/api/learning/flashcards/review", json={"card_slug": "card-server", "correct": False}
    ).json()
    assert r3["box"] == 0  # a miss resets the box


def test_due_flashcards_appear_after_lesson_completion(auth_client):
    before = auth_client.get("/api/learning/flashcards/due").json()
    assert before == []
    auth_client.post("/api/learning/lessons/systems/what-is-a-server/complete")
    after = auth_client.get("/api/learning/flashcards/due").json()
    slugs = {c["slug"] for c in after}
    assert "card-server" in slugs


def test_progress_summary_shape_and_next_lesson(auth_client):
    p = auth_client.get("/api/learning/progress").json()
    assert p["lessons_completed"] == 0
    assert p["next_lesson"] == "systems/what-is-a-server"
    assert len(p["modules"]) == 31

    auth_client.post("/api/learning/lessons/systems/what-is-a-server/complete")
    p = auth_client.get("/api/learning/progress").json()
    assert p["lessons_completed"] == 1
    assert p["next_lesson"] == "systems/anatomy-of-an-application"
    m0 = next(m for m in p["modules"] if m["id"] == "systems")
    assert m0["lessons_completed"] == 1 and m0["lessons_total"] == 2


def test_progress_survives_reconnection(client, user):
    """Database persistence: state outlives the client session (the 'leave
    and come back later' requirement)."""
    from tests.conftest import TEST_EMAIL, TEST_PASSWORD

    client.post("/api/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    client.post("/api/learning/lessons/linux/filesystem/complete")
    client.post("/api/auth/logout")

    client.post("/api/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    p = client.get("/api/learning/progress").json()
    assert p["lessons_completed"] == 1
