"""The virtual filesystem: a plain Python tree, JSON-serializable.

SECURITY INVARIANT (docs/SECURITY.md, ADR-0004): this module — and the whole
simterm package — must never import subprocess, os.system, pty, socket, or
anything else capable of touching the host. It manipulates dictionaries.
tests/test_simterm_safety.py enforces this by inspecting the import graph;
if you add an import here, expect that test to interrogate it.

Node shapes:
    {"type": "dir",  "mode": "755", "owner": "learner", "children": {name: node}}
    {"type": "file", "mode": "644", "owner": "learner", "content": str,
     "exec_output": str|None, "exec_creates": {path: content}}

exec_output/exec_creates power failure-driven lessons: a "script" file, when
executed (and executable), prints scripted output and may create files —
all inside the simulation.
"""

HOME = "/home/learner"
USERNAME = "learner"


class VfsError(Exception):
    """A user-visible filesystem error, phrased like the real shell would."""


def make_dir(mode: str = "755") -> dict:
    return {"type": "dir", "mode": mode, "owner": USERNAME, "children": {}}


def make_file(
    content: str = "",
    mode: str = "644",
    exec_output: str | None = None,
    exec_creates: dict | None = None,
    size_mb: int | None = None,
) -> dict:
    node = {
        "type": "file",
        "mode": mode,
        "owner": USERNAME,
        "content": content,
        "exec_output": exec_output,
        "exec_creates": exec_creates or {},
    }
    # Apparent size, for storage lessons. A "6 GB log file" must weigh 6 GB to
    # df and du without the exercise shipping six gigabytes of text.
    if size_mb:
        node["size_mb"] = size_mb
    return node


class VirtualFileSystem:
    def __init__(
        self,
        root: dict | None = None,
        cwd: str = HOME,
        docker: dict | None = None,
        machine: dict | None = None,
    ):
        self.root = root or self._default_root()
        self.cwd = cwd
        # Simulated Docker engine state (images/containers/volumes/networks),
        # carried alongside the filesystem because a container's lifetime is
        # not a file. Deliberately a plain dict with no schema of its own here:
        # docker_sim owns its shape, and this module stays a filesystem.
        # It rides in the same JSON column, so no migration was needed.
        self.docker = docker if docker is not None else {}
        # Simulated hardware and disks (machine_sim). Same reasoning as
        # `docker`: not a filesystem concept, same JSON column, no migration.
        self.machine = machine if machine is not None else {}

    # --- construction / serialization ---------------------------------------

    @staticmethod
    def _default_root() -> dict:
        root = make_dir()
        vfs = VirtualFileSystem.__new__(VirtualFileSystem)
        vfs.root = root
        vfs.cwd = "/"
        vfs.ensure_dir(HOME)
        return root

    @classmethod
    def from_spec(cls, cwd: str, files: dict) -> "VirtualFileSystem":
        """Build from a content Exercise/Challenge initial_files spec:
        path -> VfsFileSpec (file) or None/{} (directory)."""
        vfs = cls(cwd=cwd)
        vfs.ensure_dir(cwd)
        for path, spec in files.items():
            if spec is None:
                vfs.ensure_dir(path)
            else:
                parent = path.rsplit("/", 1)[0] or "/"
                vfs.ensure_dir(parent)
                node = vfs._lookup_parent(path)
                name = path.rsplit("/", 1)[1]
                node["children"][name] = make_file(
                    content=spec.content,
                    mode=spec.mode,
                    size_mb=spec.size_mb,
                    exec_output=spec.exec_output,
                    exec_creates=spec.exec_creates,
                )
        return vfs

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "cwd": self.cwd,
            "docker": self.docker,
            "machine": self.machine,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VirtualFileSystem":
        # Deep copy: the caller often hands us a dict owned by the ORM
        # (a JSON column value). Mutating that in place would corrupt
        # SQLAlchemy's change detection — the "old" value it compares
        # against would mutate along with ours, and updates would silently
        # never be written.
        import copy

        # `.get` for docker, not `[...]`: snapshots written before Module 8
        # existed have no such key, and an exercise in progress must not
        # explode because the engine gained a feature underneath it.
        return cls(
            root=copy.deepcopy(data["root"]),
            cwd=data["cwd"],
            docker=copy.deepcopy(data.get("docker") or {}),
            machine=copy.deepcopy(data.get("machine") or {}),
        )

    # --- path handling -------------------------------------------------------

    def resolve(self, path: str) -> str:
        """Normalize any user path to an absolute one (handles ~, ., ..)."""
        if path == "~" or path.startswith("~/"):
            path = HOME + path[1:]
        if not path.startswith("/"):
            path = self.cwd.rstrip("/") + "/" + path
        parts: list[str] = []
        for part in path.split("/"):
            if part in ("", "."):
                continue
            if part == "..":
                if parts:
                    parts.pop()
            else:
                parts.append(part)
        return "/" + "/".join(parts)

    def _node_at(self, abs_path: str) -> dict | None:
        node = self.root
        if abs_path == "/":
            return node
        for part in abs_path.strip("/").split("/"):
            if node["type"] != "dir" or part not in node["children"]:
                return None
            node = node["children"][part]
        return node

    def get(self, path: str) -> dict | None:
        return self._node_at(self.resolve(path))

    def _lookup_parent(self, path: str) -> dict:
        abs_path = self.resolve(path)
        parent_path = abs_path.rsplit("/", 1)[0] or "/"
        parent = self._node_at(parent_path)
        if parent is None or parent["type"] != "dir":
            raise VfsError(f"cannot access '{path}': No such file or directory")
        return parent

    @staticmethod
    def basename(path: str) -> str:
        return path.rstrip("/").rsplit("/", 1)[-1] or "/"

    # --- operations ----------------------------------------------------------

    def ensure_dir(self, path: str) -> None:
        """mkdir -p semantics; used for setup, not user commands."""
        node = self.root
        abs_path = self.resolve(path)
        if abs_path == "/":
            return
        for part in abs_path.strip("/").split("/"):
            if part not in node["children"]:
                node["children"][part] = make_dir()
            node = node["children"][part]
            if node["type"] != "dir":
                raise VfsError(f"cannot create directory '{path}': Not a directory")

    def mkdir(self, path: str, parents: bool = False) -> None:
        abs_path = self.resolve(path)
        if self._node_at(abs_path) is not None:
            raise VfsError(f"cannot create directory '{path}': File exists")
        if parents:
            self.ensure_dir(abs_path)
            return
        parent = self._lookup_parent(abs_path)
        parent["children"][self.basename(abs_path)] = make_dir()

    def touch(self, path: str) -> None:
        abs_path = self.resolve(path)
        if self._node_at(abs_path) is not None:
            return  # touch on existing path only updates mtime, which we don't model
        parent = self._lookup_parent(abs_path)
        parent["children"][self.basename(abs_path)] = make_file()

    def read_file(self, path: str) -> str:
        node = self.get(path)
        if node is None:
            raise VfsError(f"{path}: No such file or directory")
        if node["type"] == "dir":
            raise VfsError(f"{path}: Is a directory")
        return node["content"]

    def write_file(self, path: str, content: str, append: bool = False) -> None:
        abs_path = self.resolve(path)
        node = self._node_at(abs_path)
        if node is not None and node["type"] == "dir":
            raise VfsError(f"{path}: Is a directory")
        if node is None:
            parent = self._lookup_parent(abs_path)
            node = make_file()
            parent["children"][self.basename(abs_path)] = node
        node["content"] = (node["content"] + content) if append else content

    def remove(self, path: str, recursive: bool = False) -> None:
        abs_path = self.resolve(path)
        if abs_path == "/" or abs_path == HOME:
            raise VfsError(f"cannot remove '{path}': Operation not permitted")
        node = self._node_at(abs_path)
        if node is None:
            raise VfsError(f"cannot remove '{path}': No such file or directory")
        if node["type"] == "dir" and not recursive:
            raise VfsError(f"cannot remove '{path}': Is a directory")
        parent = self._lookup_parent(abs_path)
        del parent["children"][self.basename(abs_path)]
        # If the cwd was inside the removed tree, the real shell keeps a
        # dangling cwd; we simplify by stepping up to the parent.
        if self.cwd.startswith(abs_path):
            self.cwd = abs_path.rsplit("/", 1)[0] or "/"

    def copy(self, src: str, dst: str, recursive: bool = False) -> None:
        import copy as _copy

        src_node = self.get(src)
        if src_node is None:
            raise VfsError(f"cannot stat '{src}': No such file or directory")
        if src_node["type"] == "dir" and not recursive:
            raise VfsError(f"-r not specified; omitting directory '{src}'")
        dst_abs = self.resolve(dst)
        dst_node = self._node_at(dst_abs)
        if dst_node is not None and dst_node["type"] == "dir":
            dst_node["children"][self.basename(self.resolve(src))] = _copy.deepcopy(src_node)
        else:
            parent = self._lookup_parent(dst_abs)
            parent["children"][self.basename(dst_abs)] = _copy.deepcopy(src_node)

    def move(self, src: str, dst: str) -> None:
        src_abs = self.resolve(src)
        src_node = self._node_at(src_abs)
        if src_node is None:
            raise VfsError(f"cannot stat '{src}': No such file or directory")
        self.copy(src, dst, recursive=True)
        parent = self._lookup_parent(src_abs)
        del parent["children"][self.basename(src_abs)]

    def chdir(self, path: str) -> None:
        abs_path = self.resolve(path)
        node = self._node_at(abs_path)
        if node is None:
            raise VfsError(f"{path}: No such file or directory")
        if node["type"] != "dir":
            raise VfsError(f"{path}: Not a directory")
        self.cwd = abs_path

    def listing(self, path: str | None = None, show_all: bool = False) -> list[tuple[str, dict]]:
        target = path or self.cwd
        node = self.get(target)
        if node is None:
            raise VfsError(f"cannot access '{target}': No such file or directory")
        if node["type"] == "file":
            return [(self.basename(self.resolve(target)), node)]
        entries = sorted(node["children"].items())
        if not show_all:
            entries = [(n, v) for n, v in entries if not n.startswith(".")]
        return entries

    def chmod(self, path: str, mode: str) -> None:
        node = self.get(path)
        if node is None:
            raise VfsError(f"cannot access '{path}': No such file or directory")
        node["mode"] = mode

    @staticmethod
    def mode_string(node: dict) -> str:
        """'755' -> 'rwxr-xr-x', prefixed with d/- by the caller."""
        bits = ""
        for digit in node["mode"].rjust(3, "0"):
            n = int(digit)
            bits += ("r" if n & 4 else "-") + ("w" if n & 2 else "-") + ("x" if n & 1 else "-")
        return bits

    @staticmethod
    def is_executable(node: dict) -> bool:
        # owner-execute bit, the one that matters for ./script.sh lessons
        return bool(int(node["mode"].rjust(3, "0")[0]) & 1)
