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
