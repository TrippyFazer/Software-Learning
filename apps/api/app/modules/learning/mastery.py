"""The mastery scoring model — deliberately simple, fully explainable.

A concept's mastery is a weighted sum of independent evidence types
(docs/ARCHITECTURE.md "Mastery model"):

    introduced            0.15   the lesson declaring the concept was completed
    quiz accuracy         0.35   rolling correct/total over quiz answers
    exercise passed       0.30   any terminal exercise touching the concept
    applied passed        0.20   any challenge/boss touching the concept

Retention checks are RECORDED (retention_correct/total on MasteryRecord and
Attempt rows) but carry no weight yet — v0.1 preserves the data a future
spaced-review scheduler will need without pretending to be one (ROADMAP §v0.2).

Do not make this cleverer without updating the lesson content that explains
it to the learner. The learner-facing breakdown in the UI must always match
this table.
"""

from app.modules.learning.models import MasteryRecord

WEIGHTS = {
    "introduced": 0.15,
    "quiz": 0.35,
    "exercise": 0.30,
    "applied": 0.20,
}


def compute_score(record: MasteryRecord) -> float:
    """Pure function: evidence counters -> score in [0, 1]."""
    score = 0.0
    if record.introduced:
        score += WEIGHTS["introduced"]
    if record.quiz_total > 0:
        score += WEIGHTS["quiz"] * (record.quiz_correct / record.quiz_total)
    if record.exercise_passed:
        score += WEIGHTS["exercise"]
    if record.applied_passed:
        score += WEIGHTS["applied"]
    return round(score, 4)


def breakdown(record: MasteryRecord) -> dict:
    """The learner-facing explanation of a score. Must mirror compute_score."""
    return {
        "introduced": {
            "achieved": record.introduced,
            "weight": WEIGHTS["introduced"],
            "earned": WEIGHTS["introduced"] if record.introduced else 0.0,
        },
        "quiz": {
            "correct": record.quiz_correct,
            "total": record.quiz_total,
            "weight": WEIGHTS["quiz"],
            "earned": round(
                WEIGHTS["quiz"] * (record.quiz_correct / record.quiz_total), 4
            )
            if record.quiz_total
            else 0.0,
        },
        "exercise": {
            "achieved": record.exercise_passed,
            "weight": WEIGHTS["exercise"],
            "earned": WEIGHTS["exercise"] if record.exercise_passed else 0.0,
        },
        "applied": {
            "achieved": record.applied_passed,
            "weight": WEIGHTS["applied"],
            "earned": WEIGHTS["applied"] if record.applied_passed else 0.0,
        },
        "retention": {
            "correct": record.retention_correct,
            "total": record.retention_total,
            "weight": 0.0,
            "note": "recorded for future spaced review; no weight in v0.1",
        },
    }
