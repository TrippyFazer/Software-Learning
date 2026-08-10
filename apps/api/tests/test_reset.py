"""Manual reset: clearing an exercise/challenge completion and honestly
recomputing mastery from the remaining evidence — the sanctioned exception
to the append-only attempt log (e.g. someone else completed a boss on your
account)."""

from sqlalchemy import select

from app.modules.learning.models import Attempt, ExerciseState, MasteryRecord


def _complete_exercise(auth_client, slug="linux/create-project-structure"):
    auth_client.post(f"/api/simterm/exercises/{slug}/start")
    state = auth_client.post(
        f"/api/simterm/exercises/{slug}/input",
        json={"line": "mkdir -p projects/brain-core && touch projects/brain-core/README.md"},
    ).json()
    assert state["completed"] is True
    return slug


def _complete_challenge(auth_client):
    auth_client.post("/api/simterm/challenges/server-rookie/start")
    for line in ["chmod 644 /var/www/app/config.yaml", "cd /var/www/app",
                 "chmod +x restart.sh", "./restart.sh"]:
        auth_client.post("/api/simterm/challenges/server-rookie/input", json={"line": line})
    for qid, ans in [("rookie-q1", 2), ("rookie-q2", 1), ("rookie-q3", "8080"), ("rookie-q4", 1)]:
        auth_client.post("/api/learning/answers", json={"question_id": qid, "answer": ans})
    status = auth_client.get("/api/simterm/challenges/server-rookie/status").json()
    assert status["completed"] is True


def test_reset_exercise_clears_completion_and_mastery(auth_client, db_session):
    slug = _complete_exercise(auth_client)
    record = db_session.scalar(
        select(MasteryRecord).where(MasteryRecord.concept_slug == "filesystem")
    )
    assert record.exercise_passed and record.score >= 0.30

    res = auth_client.post("/api/learning/reset-item", json={"item_slug": slug})
    assert res.status_code == 200

    db_session.expire_all()
    # attempt gone, mastery honestly recomputed
    assert db_session.scalar(select(Attempt).where(Attempt.item_slug == slug)) is None
    record = db_session.scalar(
        select(MasteryRecord).where(MasteryRecord.concept_slug == "filesystem")
    )
    assert record.exercise_passed is False
    assert record.score < 0.30
    # terminal state wiped: a fresh start shows unmet goals, not completed
    state = auth_client.post(f"/api/simterm/exercises/{slug}/start").json()
    assert state["completed"] is False
    assert not any(g["met"] for g in state["goals"])
    assert state["transcript"] == []


def test_reset_challenge_clears_completion_answers_and_applied_mastery(auth_client, db_session):
    _complete_challenge(auth_client)

    res = auth_client.post("/api/learning/reset-item", json={"item_slug": "server-rookie"})
    assert res.status_code == 200

    # status: nothing completed, no questions answered
    status = auth_client.get("/api/simterm/challenges/server-rookie/status").json()
    assert status["completed"] is False
    assert status["questions_correct"] == 0
    assert status["goals_met"] is False  # fresh broken scenario again

    # diagnosis-question attempts are gone too
    db_session.expire_all()
    for qid in ("rookie-q1", "rookie-q2", "rookie-q3", "rookie-q4"):
        assert db_session.scalar(select(Attempt).where(Attempt.item_slug == qid)) is None

    # applied evidence removed from the boss's concepts
    record = db_session.scalar(
        select(MasteryRecord).where(MasteryRecord.concept_slug == "permission")
    )
    assert record is not None and record.applied_passed is False


def test_reset_preserves_unrelated_evidence(auth_client, db_session):
    # unrelated evidence: lesson completion (introduced) + a lesson-quiz answer
    auth_client.post("/api/learning/lessons/linux/users-and-permissions/complete")
    auth_client.post(
        "/api/learning/answers", json={"question_id": "linux-perm-q2", "answer": "755"}
    )
    _complete_challenge(auth_client)

    auth_client.post("/api/learning/reset-item", json={"item_slug": "server-rookie"})

    db_session.expire_all()
    record = db_session.scalar(
        select(MasteryRecord).where(MasteryRecord.concept_slug == "permission")
    )
    # challenge credit gone, but introduction and the lesson-quiz answer survive
    assert record.applied_passed is False
    assert record.introduced is True
    assert record.quiz_total == 1 and record.quiz_correct == 1
    # exercise state row for the challenge is gone
    assert (
        db_session.scalar(
            select(ExerciseState).where(ExerciseState.exercise_slug == "challenge:server-rookie")
        )
        is None
    )


def test_reset_unknown_item_404(auth_client):
    res = auth_client.post("/api/learning/reset-item", json={"item_slug": "ghost/item"})
    assert res.status_code == 404


def test_completed_items_lists_everything_resettable(auth_client):
    empty = auth_client.get("/api/learning/completed-items").json()
    assert empty == {"lessons": [], "exercises": [], "challenges": []}

    auth_client.post("/api/learning/lessons/linux/filesystem/complete")
    _complete_exercise(auth_client)
    _complete_challenge(auth_client)

    items = auth_client.get("/api/learning/completed-items").json()
    assert [x["slug"] for x in items["lessons"]] == ["linux/filesystem"]
    assert [x["slug"] for x in items["exercises"]] == ["linux/create-project-structure"]
    assert [x["slug"] for x in items["challenges"]] == ["server-rookie"]
    assert items["challenges"][0]["title"].startswith("SERVER ROOKIE")


def test_reset_lesson_uncompletes_and_clears_quiz_history(auth_client, db_session):
    auth_client.post("/api/learning/lessons/linux/filesystem/complete")
    auth_client.post("/api/learning/answers", json={"question_id": "linux-fs-q3", "answer": "pwd"})
    record = db_session.scalar(
        select(MasteryRecord).where(MasteryRecord.concept_slug == "working-directory")
    )
    assert record.introduced and record.quiz_total == 1

    res = auth_client.post("/api/learning/reset-lesson", json={"lesson_slug": "linux/filesystem"})
    assert res.status_code == 200

    db_session.expire_all()
    progress = auth_client.get("/api/learning/lessons/progress").json()
    assert "linux/filesystem" not in progress
    record = db_session.scalar(
        select(MasteryRecord).where(MasteryRecord.concept_slug == "working-directory")
    )
    assert record.introduced is False
    assert record.quiz_total == 0
    assert record.score == 0.0


def test_reset_lesson_keeps_introduced_if_another_lesson_covers_concept(auth_client, db_session):
    # "permission" is taught by users-and-permissions AND exercised by the boss;
    # here: complete users-and-permissions, and verify un-completing a DIFFERENT
    # lesson never touches it — while un-completing its own lesson clears it.
    auth_client.post("/api/learning/lessons/linux/users-and-permissions/complete")
    auth_client.post("/api/learning/lessons/linux/filesystem/complete")
    auth_client.post("/api/learning/reset-lesson", json={"lesson_slug": "linux/filesystem"})

    db_session.expire_all()
    record = db_session.scalar(
        select(MasteryRecord).where(MasteryRecord.concept_slug == "permission")
    )
    assert record.introduced is True  # untouched by the other lesson's reset


def test_reset_all_requires_exact_phrase_and_wipes_everything(auth_client, db_session):
    auth_client.post("/api/learning/lessons/linux/filesystem/complete")
    _complete_exercise(auth_client)
    auth_client.post(
        "/api/learning/flashcards/review", json={"card_slug": "card-server", "correct": True}
    )

    # wrong phrase → refused, nothing changes
    res = auth_client.post("/api/learning/reset-all", json={"confirm": "yes"})
    assert res.status_code == 400
    assert auth_client.get("/api/learning/progress").json()["lessons_completed"] == 1

    res = auth_client.post("/api/learning/reset-all", json={"confirm": "reset everything"})
    assert res.status_code == 200

    p = auth_client.get("/api/learning/progress").json()
    assert p["lessons_completed"] == 0
    assert p["concepts_tracked"] == 0
    assert p["due_flashcards"] == 0
    assert auth_client.get("/api/learning/completed-items").json() == {
        "lessons": [], "exercises": [], "challenges": [],
    }
    db_session.expire_all()
    assert db_session.scalar(select(Attempt)) is None
    assert db_session.scalar(select(MasteryRecord)) is None
    assert db_session.scalar(select(ExerciseState)) is None
