"""Simulated machine inspection: df, du, lsblk, mount, free (Modules 4 and 5).

The Storage module's exercise is the oldest real sysadmin drill there is:
the disk is full, find the culprit, delete it, CONFIRM THE SPACE CAME BACK.
That last step only teaches anything if the numbers genuinely move — a `df`
that prints a fixed string would quietly tell the learner the Lab is a toy.
So the important test here is that deleting a file changes df's output.
"""

from app.modules.simterm import commands, machine_sim
from app.modules.simterm.vfs import VirtualFileSystem, make_file


def run(vfs, line: str) -> str:
    return "\n".join(commands.run_line(vfs, line))


def _with_big_file(size_mb: int = 40000) -> VirtualFileSystem:
    vfs = VirtualFileSystem()
    vfs.ensure_dir("/var/log/webapp")
    vfs._lookup_parent("/var/log/webapp/access.log")["children"]["access.log"] = make_file(
        content="x", size_mb=size_mb
    )
    return vfs


def _use_pct(vfs) -> int:
    row = [ln for ln in run(vfs, "df -h").split("\n") if ln.endswith(" /")][0]
    return int([c for c in row.split() if c.endswith("%")][0].rstrip("%"))


# --- the drill ---------------------------------------------------------------

def test_deleting_a_big_file_frees_space_in_df():
    vfs = _with_big_file()
    before = _use_pct(vfs)
    assert before > 50, f"scenario should start nearly full, got {before}%"
    run(vfs, "rm /var/log/webapp/access.log")
    after = _use_pct(vfs)
    assert after < before - 20, f"df did not move: {before}% -> {after}%"


def test_du_finds_the_culprit_and_reports_apparent_size():
    vfs = _with_big_file()
    out = run(vfs, "du -h /var/log/webapp")
    assert "access.log" in out
    assert "G" in out, out  # reported in gigabytes, not as one byte of content


def test_ls_lh_shows_apparent_size():
    vfs = _with_big_file()
    assert "G" in run(vfs, "ls -lh /var/log/webapp")


def test_du_on_a_missing_path_reports_like_du_does():
    vfs = VirtualFileSystem()
    out = run(vfs, "du -sh /nope")
    assert "cannot access" in out and "No such file or directory" in out


# --- reading the machine -----------------------------------------------------

def test_lsblk_shows_disk_and_partitions_with_mountpoints():
    out = run(VirtualFileSystem(), "lsblk")
    assert "nvme0n1" in out and "nvme0n1p1" in out
    assert "/boot/efi" in out


def test_mount_lists_filesystem_types():
    out = run(VirtualFileSystem(), "mount")
    assert "type ext4" in out and "type vfat" in out


def test_free_reports_available_separately_from_free():
    """The whole point of the lesson: `free` and `available` differ."""
    out = run(VirtualFileSystem(), "free -h")
    assert "available" in out
    header, mem = out.split("\n")[0].split(), out.split("\n")[1].split()
    available = mem[header.index("available") + 1]
    free_col = mem[header.index("free") + 1]
    assert available != free_col


def test_nproc_and_lscpu_disagree_in_the_instructive_way():
    """nproc says 2, lscpu says one core with two threads. Both true."""
    vfs = VirtualFileSystem()
    assert run(vfs, "nproc") == "2"
    out = run(vfs, "lscpu")
    assert "Thread(s) per core:    2" in out
    assert "Core(s) per socket:    1" in out


# --- accounting details ------------------------------------------------------

def test_a_path_belongs_to_the_longest_matching_mount():
    """Bytes under /boot/efi must not be counted against /."""
    vfs = VirtualFileSystem()
    vfs.ensure_dir("/boot/efi")
    vfs._lookup_parent("/boot/efi/big.bin")["children"]["big.bin"] = make_file(size_mb=50)
    root_before = _use_pct(vfs)
    vfs2 = VirtualFileSystem()
    assert root_before == _use_pct(vfs2), "an EFI file changed the root filesystem's usage"


def test_human_sizes_match_the_shape_of_real_output():
    assert machine_sim.human(0) == "0"
    assert machine_sim.human(1536) == "1.5K"
    assert machine_sim.human(40 * 1024**3) == "40G"


def test_machine_state_survives_a_snapshot_round_trip():
    vfs = _with_big_file()
    before = _use_pct(vfs)
    revived = VirtualFileSystem.from_dict(vfs.to_dict())
    assert _use_pct(revived) == before


def test_old_snapshots_without_machine_state_still_work():
    vfs = VirtualFileSystem.from_dict({"root": VirtualFileSystem().root, "cwd": "/home/learner"})
    assert "nvme0n1" in run(vfs, "lsblk")
