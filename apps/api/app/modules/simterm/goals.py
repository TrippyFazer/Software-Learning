"""Goal evaluation: grade the STATE of the virtual filesystem, not the
commands typed. `mkdir -p a/b` and `mkdir a; cd a; mkdir b` earn the same
credit (ADR-0004)."""

from app.modules.content.schema import DOCKER_GOAL_TYPES, GoalCheck
from app.modules.simterm.vfs import VirtualFileSystem


def _docker_goal(vfs: VirtualFileSystem, goal: GoalCheck) -> bool:
    """Assertions about the simulated Docker engine rather than the VFS.

    Same principle as everything else here: grade the resulting STATE. Whether
    the learner reached it with `docker compose down` or by stopping and
    removing each container by hand is not the Lab's business — both mean they
    understood what a container's lifetime is.
    """
    state = vfs.docker or {}
    containers = state.get("containers") or {}
    volumes = state.get("volumes") or {}
    name = goal.name or ""
    match goal.type:
        case "container_running":
            c = containers.get(name)
            return c is not None and c.get("status") == "running"
        case "container_absent":
            return name not in containers
        case "volume_exists":
            return name in volumes
        case "volume_absent":
            return name not in volumes
        case "volume_contains":
            data = (volumes.get(name) or {}).get("data") or {}
            needle = goal.text or ""
            return any(needle in path for path in data)
    return False


def check_goal(vfs: VirtualFileSystem, goal: GoalCheck) -> bool:
    if goal.type in DOCKER_GOAL_TYPES:
        return _docker_goal(vfs, goal)
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
