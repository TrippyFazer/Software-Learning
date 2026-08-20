"""Simulated machine inspection: df, du, lsblk, mount, free, nproc, lscpu.

Same contract as the rest of simterm (docs/SECURITY.md rule 1, ADR-0004):
dictionaries, never the host. `df` here reports on a fictional disk; it cannot
see the real one, and that is the point — the learner is meant to fill a disk
and recover it without anybody's server being involved.

WHY `df` AND `du` ARE COMPUTED, NOT SCRIPTED

The Storage module's central exercise is the oldest real sysadmin task there
is: a disk is full, find what is eating it, delete it, confirm the space came
back. That only teaches anything if the numbers MOVE — if `df` still says 100%
after the learner deletes the culprit, they have learned nothing except that
the Lab is fake.

So `du` is summed live from the virtual filesystem, and `df` is a per-mount
baseline PLUS whatever the VFS currently holds under that mount. Delete a 6 GB
log and the used figure genuinely drops.

APPARENT SIZE

A VFS file's size is normally its content length, which makes a "6 GB log"
awkward. `VfsFileSpec.size_mb` declares an apparent size instead, so an
exercise can ship a huge file without shipping huge content.
"""

MB = 1024 * 1024
GB = 1024 * MB

# A machine that is deliberately recognisable: it is the Lightsail host this
# Lab runs on. Lessons refer to these numbers and so does `~/documentation`.
DEFAULT_MACHINE = {
    "cpu": {
        "model": "Intel(R) Xeon(R) Platinum 8259CL CPU @ 2.50GHz",
        "cores": 2,
        "threads_per_core": 2,
        "physical_cores": 1,
        "arch": "x86_64",
    },
    "memory": {"total_mb": 3832, "used_mb": 1500, "swap_total_mb": 2048, "swap_used_mb": 0},
    "disks": [
        {
            "name": "nvme0n1",
            "size": "80G",
            "partitions": [
                {
                    "name": "nvme0n1p1",
                    "size": "79G",
                    "fstype": "ext4",
                    "mount": "/",
                    "total_gb": 77,
                    "baseline_used_gb": 9,
                },
                {"name": "nvme0n1p15", "size": "99M", "fstype": "vfat", "mount": "/boot/efi",
                 "total_gb": 0.1, "baseline_used_gb": 0.006},
            ],
        }
    ],
    "tmpfs": [{"mount": "/run", "total_gb": 0.38, "used_gb": 0.001}],
}


def new_machine() -> dict:
    import copy

    return copy.deepcopy(DEFAULT_MACHINE)


def _ensure(vfs) -> dict:
    if not vfs.machine:
        vfs.machine = new_machine()
    return vfs.machine


# ------------------------------------------------------------------ sizing

def node_size_bytes(node: dict) -> int:
    """Apparent size of one node. `size_mb` wins so an exercise can ship a
    6 GB log file without shipping 6 GB."""
    if node["type"] == "dir":
        return 4096
    declared = node.get("size_mb")
    if declared:
        return int(declared) * MB
    return len(node.get("content", ""))


def tree_size_bytes(node: dict) -> int:
    if node is None:
        return 0
    if node["type"] == "file":
        return node_size_bytes(node)
    total = 4096
    for child in node.get("children", {}).values():
        total += tree_size_bytes(child)
    return total


def human(num_bytes: float) -> str:
    """Match `-h` output: one decimal under 10, none above, K/M/G/T."""
    value = float(num_bytes)
    for unit in ("", "K", "M", "G", "T"):
        if value < 1024 or unit == "T":
            if unit == "":
                return f"{int(value)}"
            return f"{value:.1f}{unit}" if value < 10 else f"{value:.0f}{unit}"
        value /= 1024
    return f"{value:.0f}T"


def _mount_for(path: str, mounts: list[str]) -> str:
    """Longest matching mount point — the same rule the kernel uses."""
    best = "/"
    for m in mounts:
        if path == m or path.startswith(m.rstrip("/") + "/"):
            if len(m) > len(best):
                best = m
    return best


def _vfs_bytes_under(vfs, mount: str, mounts: list[str]) -> int:
    """Bytes the VFS holds that belong to this mount (not a sub-mount)."""
    node = vfs.get(mount)
    if node is None:
        return 0

    def walk(n, path):
        if n["type"] == "file":
            return node_size_bytes(n)
        total = 0
        for name, child in n.get("children", {}).items():
            child_path = f"{path.rstrip('/')}/{name}"
            if child["type"] == "dir" and child_path in mounts and child_path != mount:
                continue  # belongs to a different filesystem
            total += walk(child, child_path)
        return total

    return walk(node, mount)


# ----------------------------------------------------------------- commands

def df(vfs, args: list[str]) -> tuple[list[str], bool]:
    machine = _ensure(vfs)
    human_flag = any(a in ("-h", "-H", "--human-readable") for a in args)
    parts = [p for d in machine["disks"] for p in d["partitions"] if p.get("mount")]
    mounts = [p["mount"] for p in parts] + [t["mount"] for t in machine.get("tmpfs", [])]

    rows = []
    for p in parts:
        total = p["total_gb"] * GB
        used = p["baseline_used_gb"] * GB + _vfs_bytes_under(vfs, p["mount"], mounts)
        used = min(used, total)
        avail = total - used
        pct = f"{round(used / total * 100)}%" if total else "-"
        dev = f"/dev/{p['name']}"
        if human_flag:
            rows.append([dev, human(total), human(used), human(avail), pct, p["mount"]])
        else:
            rows.append([dev, str(int(total // 1024)), str(int(used // 1024)),
                         str(int(avail // 1024)), pct, p["mount"]])
    for t in machine.get("tmpfs", []):
        total = t["total_gb"] * GB
        used = t["used_gb"] * GB
        pct = f"{round(used / total * 100)}%" if total else "-"
        if human_flag:
            rows.append(["tmpfs", human(total), human(used), human(total - used), pct, t["mount"]])
        else:
            rows.append(["tmpfs", str(int(total // 1024)), str(int(used // 1024)),
                         str(int((total - used) // 1024)), pct, t["mount"]])

    headers = ["Filesystem", "Size" if human_flag else "1K-blocks",
               "Used", "Avail", "Use%", "Mounted on"]
    return _table(rows, headers), True


def du(vfs, args: list[str]) -> tuple[list[str], bool]:
    human_flag = any("h" in a for a in args if a.startswith("-"))
    summarise = any("s" in a for a in args if a.startswith("-"))
    paths = [a for a in args if not a.startswith("-")] or ["."]

    lines, ok = [], True
    for raw in paths:
        target = vfs.resolve(raw)
        node = vfs.get(target)
        if node is None:
            lines.append(f"du: cannot access '{raw}': No such file or directory")
            ok = False
            continue

        def emit(n, path):
            size = tree_size_bytes(n)
            lines.append(f"{human(size) if human_flag else int(size // 1024)}\t{path}")

        if summarise or node["type"] == "file":
            emit(node, raw)
        else:
            # Children first, then the total — the order real du prints in,
            # and the reason `du -h | sort -h | tail` is a habit.
            for name, child in sorted(node.get("children", {}).items()):
                emit(child, f"{raw.rstrip('/')}/{name}")
            emit(node, raw)
    return lines, ok


def lsblk(vfs, args: list[str]) -> tuple[list[str], bool]:
    machine = _ensure(vfs)
    rows = []
    for disk in machine["disks"]:
        rows.append([disk["name"], "259:0", "0", disk["size"], "0", "disk", ""])
        for i, p in enumerate(disk["partitions"]):
            rows.append([f"└─{p['name']}" if i == len(disk["partitions"]) - 1 else f"├─{p['name']}",
                         f"259:{i + 1}", "0", p["size"], "0", "part", p.get("mount", "")])
    return _table(rows, ["NAME", "MAJ:MIN", "RM", "SIZE", "RO", "TYPE", "MOUNTPOINTS"]), True


def mount_cmd(vfs, args: list[str]) -> tuple[list[str], bool]:
    machine = _ensure(vfs)
    lines = []
    for disk in machine["disks"]:
        for p in disk["partitions"]:
            if p.get("mount"):
                lines.append(f"/dev/{p['name']} on {p['mount']} type {p['fstype']} (rw,relatime)")
    for t in machine.get("tmpfs", []):
        lines.append(f"tmpfs on {t['mount']} type tmpfs (rw,nosuid,nodev)")
    if not args:
        lines.append("")
        lines.append("(this simulator lists mounts; it does not attach new filesystems)")
    return lines, True


def free(vfs, args: list[str]) -> tuple[list[str], bool]:
    machine = _ensure(vfs)
    mem = machine["memory"]
    human_flag = any(a in ("-h", "--human") for a in args)

    def fmt(mb):
        if not human_flag:
            return str(mb * 1024)
        # real `free -h` prints a bare "0B" rather than "0i"
        return "0B" if mb == 0 else human(mb * MB) + "i"

    total, used = mem["total_mb"], mem["used_mb"]
    # buff/cache is the number that confuses everyone: it looks like "used"
    # but is reclaimable. `available` is the figure that actually matters.
    cache = max(0, total - used - 200)
    rows = [
        ["Mem:", fmt(total), fmt(used), fmt(200), fmt(36), fmt(cache), fmt(total - used)],
        ["Swap:", fmt(mem["swap_total_mb"]), fmt(mem["swap_used_mb"]),
         fmt(mem["swap_total_mb"] - mem["swap_used_mb"]), "", "", ""],
    ]
    headers = ["", "total", "used", "free", "shared", "buff/cache", "available"]
    return _table(rows, headers), True


def nproc(vfs, args: list[str]) -> tuple[list[str], bool]:
    return [str(_ensure(vfs)["cpu"]["cores"])], True


def lscpu(vfs, args: list[str]) -> tuple[list[str], bool]:
    cpu = _ensure(vfs)["cpu"]
    return (
        [
            f"Architecture:          {cpu['arch']}",
            f"CPU(s):                {cpu['cores']}",
            f"Thread(s) per core:    {cpu['threads_per_core']}",
            f"Core(s) per socket:    {cpu['physical_cores']}",
            "Socket(s):             1",
            f"Model name:            {cpu['model']}",
        ],
        True,
    )


def _table(rows: list[list[str]], headers: list[str]) -> list[str]:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    out = ["  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)).rstrip()]
    for row in rows:
        out.append("  ".join(c.ljust(widths[i]) for i, c in enumerate(row)).rstrip())
    return out
