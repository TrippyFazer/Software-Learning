"""Goal evaluation: grade the STATE of the virtual filesystem, not the
commands typed. `mkdir -p a/b` and `mkdir a; cd a; mkdir b` earn the same
credit (ADR-0004)."""

from app.modules.content.schema import GoalCheck
from app.modules.simterm.vfs import VirtualFileSystem


def check_goal(vfs: VirtualFileSystem, goal: GoalCheck) -> bool:
    node = vfs.get(goal.path)
    match goal.type:
        case "dir_exists":
            return node is not None and node["type"] == "dir"
        case "file_exists":
            return node is not None and node["type"] == "file"
        case "path_absent":
            return node is None
        case "file_contains":
            return (
                node is not None
                and node["type"] == "file"
                and (goal.text or "") in node.get("content", "")
            )
        case "cwd_is":
            return vfs.cwd == vfs.resolve(goal.path)
        case "mode_is":
            return (
                node is not None
                and node["mode"].rjust(3, "0") == (goal.mode or "").rjust(3, "0")
            )
    return False


def evaluate(vfs: VirtualFileSystem, goals: list[GoalCheck]) -> list[dict]:
    return [{"description": g.description, "met": check_goal(vfs, g)} for g in goals]
