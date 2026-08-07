"""Simulated terminal: VFS semantics, command behavior, goal grading,
exercise flow, and state persistence."""

from app.modules.content.schema import GoalCheck
from app.modules.simterm import commands, goals
from app.modules.simterm.vfs import VirtualFileSystem


def fresh():
    return VirtualFileSystem()


# --- filesystem semantics ----------------------------------------------------

def test_default_vfs_has_home(capsys):
    vfs = fresh()
    assert vfs.get("/home/learner") is not None
    assert vfs.cwd == "/home/learner"


def test_path_resolution():
    vfs = fresh()
    assert vfs.resolve("~/x") == "/home/learner/x"
    assert vfs.resolve("../..") == "/"
    assert vfs.resolve("./a/./b") == "/home/learner/a/b"
    assert vfs.resolve("/a/b/../c") == "/a/c"


def test_mkdir_touch_write_read_roundtrip():
    vfs = fresh()
    vfs.mkdir("proj")
    vfs.write_file("proj/readme.md", "hello")
    assert vfs.read_file("proj/readme.md") == "hello"
    vfs.write_file("proj/readme.md", " world", append=True)
    assert vfs.read_file("proj/readme.md") == "hello world"


def test_serialization_roundtrip_is_deep_copied():
    vfs = fresh()
    vfs.mkdir("a")
    data = vfs.to_dict()
    restored = VirtualFileSystem.from_dict(data)
    restored.mkdir("b")
    # the source dict must NOT gain 'b' — from_dict deep-copies (ORM safety)
    assert "b" not in data["root"]["children"]["home"]["children"]["learner"]["children"]


# --- command behavior --------------------------------------------------------

def run(vfs, line):
    return commands.run_line(vfs, line)


def test_basic_navigation_commands():
    vfs = fresh()
    assert run(vfs, "pwd") == ["/home/learner"]
    assert run(vfs, "whoami") == ["learner"]
    run(vfs, "mkdir projects")
    run(vfs, "cd projects")
    assert vfs.cwd == "/home/learner/projects"
    assert run(vfs, "cd ..") == []
    assert vfs.cwd == "/home/learner"


def test_unknown_command_bash_style_error():
    assert run(fresh(), "frobnicate") == ["bash: frobnicate: command not found"]


def test_chaining_semicolon_and_and():
    vfs = fresh()
    run(vfs, "mkdir a; mkdir b")
    assert vfs.get("a") and vfs.get("b")
    # && short-circuits on failure
    out = run(vfs, "cd missing && mkdir never")
    assert vfs.get("never") is None
    assert "No such file" in out[0]
    # ; continues despite failure
    run(vfs, "cd missing ; mkdir anyway")
    assert vfs.get("anyway") is not None


def test_echo_redirection():
    vfs = fresh()
    run(vfs, 'echo "line one" > f.txt')
    run(vfs, 'echo "line two" >> f.txt')
    assert vfs.read_file("f.txt") == "line one\nline two\n"
    run(vfs, 'echo "replaced" > f.txt')  # > truncates
    assert vfs.read_file("f.txt") == "replaced\n"


def test_cp_mv_rm():
    vfs = fresh()
    run(vfs, "echo data > a.txt")
    run(vfs, "cp a.txt b.txt")
    run(vfs, "mv a.txt c.txt")
    assert vfs.get("a.txt") is None
    assert vfs.read_file("b.txt") == vfs.read_file("c.txt") == "data\n"
    assert "Is a directory" in run(vfs, "mkdir d; rm d")[0]
    run(vfs, "rm -r d")
    assert vfs.get("d") is None


def test_ls_long_format_shows_permissions():
    vfs = fresh()
    run(vfs, "touch script.sh")
    out = run(vfs, "ls -l")
    assert any("-rw-r--r--" in line and "script.sh" in line for line in out)


def test_chmod_numeric_and_symbolic():
    vfs = fresh()
    run(vfs, "touch s.sh")
    run(vfs, "chmod +x s.sh")
    assert vfs.get("s.sh")["mode"] == "755"
    run(vfs, "chmod 600 s.sh")
    assert vfs.get("s.sh")["mode"] == "600"


def test_script_execution_gated_on_execute_bit():
    from app.modules.simterm.vfs import make_file

    vfs = fresh()
    node = make_file(
        content="#!/bin/bash", mode="644", exec_output="ran!", exec_creates={"/tmp/out": "x"}
    )
    vfs.get("/home/learner")["children"]["s.sh"] = node
    assert run(vfs, "./s.sh") == ["bash: ./s.sh: Permission denied"]
    run(vfs, "chmod +x s.sh")
    assert run(vfs, "./s.sh") == ["ran!"]
    assert vfs.read_file("/tmp/out") == "x"


def test_unsupported_operators_rejected_helpfully():
    out = run(fresh(), "ls | grep x")
    assert "unsupported operator" in out[0]


# --- goal grading: state, not keystrokes -------------------------------------

def test_goals_graded_on_state_not_commands():
    goal = [
        GoalCheck(type="dir_exists", path="/home/learner/p", description="p exists"),
        GoalCheck(type="file_exists", path="/home/learner/p/f", description="f exists"),
    ]
    # route A: step by step
    a = fresh()
    for line in ["mkdir p", "cd p", "touch f"]:
        run(a, line)
    # route B: one-liner, different commands entirely
    b = fresh()
    run(b, "mkdir -p p && echo hi > p/f")
    for vfs in (a, b):
        assert all(g["met"] for g in goals.evaluate(vfs, goal))


def test_goal_types():
    vfs = fresh()
    run(vfs, "mkdir d; echo secret > d/f; chmod 600 d/f; cd d")
    checks = {
        "dir_exists": GoalCheck(type="dir_exists", path="/home/learner/d", description=""),
        "file_contains": GoalCheck(
            type="file_contains", path="/home/learner/d/f", text="secret", description=""
        ),
        "cwd_is": GoalCheck(type="cwd_is", path="/home/learner/d", description=""),
        "mode_is": GoalCheck(type="mode_is", path="/home/learner/d/f", mode="600", description=""),
        "path_absent": GoalCheck(type="path_absent", path="/home/learner/ghost", description=""),
    }
    for name, check in checks.items():
        assert goals.check_goal(vfs, check), name


# --- API flow ----------------------------------------------------------------

def test_exercise_flow_and_completion(auth_client):
    slug = "linux/create-project-structure"
    state = auth_client.post(f"/api/simterm/exercises/{slug}/start").json()
    assert state["completed"] is False
    for line in ["mkdir projects", "cd projects", "mkdir brain-core",
                 "cd brain-core", "touch README.md"]:
        state = auth_client.post(f"/api/simterm/exercises/{slug}/input", json={"line": line}).json()
    assert state["completed"] is True
    assert all(g["met"] for g in state["goals"])


def test_exercise_state_persists_across_requests(auth_client):
    slug = "practice/sandbox"
    auth_client.post(f"/api/simterm/exercises/{slug}/start")
    auth_client.post(f"/api/simterm/exercises/{slug}/input", json={"line": "mkdir persistent"})
    # a separate request sees the directory
    state = auth_client.post(f"/api/simterm/exercises/{slug}/input", json={"line": "ls"}).json()
    assert "persistent/" in state["transcript"][-1]["output"]


def test_exercise_reset_restores_initial_state(auth_client):
    slug = "practice/sandbox"
    auth_client.post(f"/api/simterm/exercises/{slug}/start")
    auth_client.post(f"/api/simterm/exercises/{slug}/input", json={"line": "rm notes.txt"})
    state = auth_client.post(f"/api/simterm/exercises/{slug}/reset").json()
    assert state["transcript"] == []
    out = auth_client.post(f"/api/simterm/exercises/{slug}/input", json={"line": "ls"}).json()
    assert "notes.txt" in out["transcript"][-1]["output"]


def test_exercise_completion_recorded_as_mastery_evidence(auth_client, db_session):
    from sqlalchemy import select

    from app.modules.learning.models import MasteryRecord

    slug = "linux/create-project-structure"
    auth_client.post(f"/api/simterm/exercises/{slug}/start")
    auth_client.post(
        f"/api/simterm/exercises/{slug}/input",
        json={"line": "mkdir -p projects/brain-core && touch projects/brain-core/README.md"},
    )
    record = db_session.scalar(
        select(MasteryRecord).where(MasteryRecord.concept_slug == "filesystem")
    )
    assert record is not None and record.exercise_passed
    assert record.score >= 0.30


def test_challenge_requires_goals_and_questions(auth_client):
    # fix the scenario in the terminal
    auth_client.post("/api/simterm/challenges/server-rookie/start")
    for line in ["chmod 644 /var/www/app/config.yaml", "cd /var/www/app",
                 "chmod +x restart.sh", "./restart.sh"]:
        auth_client.post("/api/simterm/challenges/server-rookie/input", json={"line": line})
    status = auth_client.get("/api/simterm/challenges/server-rookie/status").json()
    assert status["goals_met"] is True
    assert status["completed"] is False  # questions still unanswered

    for qid, ans in [("rookie-q1", 2), ("rookie-q2", 1), ("rookie-q3", "8080"), ("rookie-q4", 1)]:
        auth_client.post("/api/learning/answers", json={"question_id": qid, "answer": ans})
    status = auth_client.get("/api/simterm/challenges/server-rookie/status").json()
    assert status["completed"] is True
    assert status["success_text"]
