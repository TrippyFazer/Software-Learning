"""The command interpreter for the simulated terminal.

Learner input is tokenized by shlex (TOKENIZATION ONLY — nothing here spawns
a process; there is no shell anywhere in this path) and dispatched to
handlers that mutate a VirtualFileSystem. Unknown commands get a bash-style
error. Supported syntax beyond single commands:

    cmd1 ; cmd2      run both
    cmd1 && cmd2     run cmd2 only if cmd1 succeeded
    echo text > f    write, echo text >> f   append
    ./script.sh      "execute" a file: requires the x bit, then prints the
                     file's scripted exec_output — the vehicle for
                     failure-driven permission lessons

Deliberate simplifications (taught explicitly in lessons): no pipes, no
globbing, no environment variables. Permissions are displayed and enforced
for execution only.
"""

import shlex

from app.modules.simterm.vfs import HOME, USERNAME, VfsError, VirtualFileSystem

MAX_LINE_LENGTH = 500
MAX_TOKENS = 50


class CommandResult:
    def __init__(self, lines: list[str] | None = None, ok: bool = True):
        self.lines = lines or []
        self.ok = ok


def run_line(vfs: VirtualFileSystem, line: str) -> list[str]:
    """Execute one input line (possibly several ; / && chained commands).
    Returns output lines. Never raises: all errors become shell-style text."""
    line = line.strip()
    if not line:
        return []
    if len(line) > MAX_LINE_LENGTH:
        return ["input too long"]

    try:
        lexer = shlex.shlex(line, posix=True, punctuation_chars=";&")
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError as e:
        return [f"syntax error: {e}"]
    if len(tokens) > MAX_TOKENS:
        return ["too many arguments"]

    # split into chained commands on ; and &&
    commands: list[tuple[str, list[str]]] = []  # (joiner, argv)
    current: list[str] = []
    joiner = ";"
    for tok in tokens:
        if tok in (";", "&&"):
            if current:
                commands.append((joiner, current))
            current, joiner = [], tok
        elif tok in ("&", "|", "||", ";;"):
            return [f"unsupported operator '{tok}' — the simulator keeps to ; and && (lessons explain the rest)"]
        else:
            current.append(tok)
    if current:
        commands.append((joiner, current))

    output: list[str] = []
    last_ok = True
    for join, argv in commands:
        if join == "&&" and not last_ok:
            continue
        result = _dispatch(vfs, argv)
        output.extend(result.lines)
        last_ok = result.ok
    return output


def _dispatch(vfs: VirtualFileSystem, argv: list[str]) -> CommandResult:
    cmd, *args = argv

    # ./script.sh execution
    if cmd.startswith("./") or cmd.startswith("/") and not _is_builtin(cmd):
        return _execute_file(vfs, cmd)

    handler = _HANDLERS.get(cmd)
    if handler is None:
        return CommandResult([f"bash: {cmd}: command not found"], ok=False)
    try:
        return handler(vfs, args)
    except VfsError as e:
        return CommandResult([f"{cmd}: {e}"], ok=False)


def _is_builtin(cmd: str) -> bool:
    return cmd in _HANDLERS


def _split_flags(args: list[str]) -> tuple[set[str], list[str]]:
    flags: set[str] = set()
    rest: list[str] = []
    for a in args:
        if a.startswith("-") and len(a) > 1 and not a.startswith("--"):
            flags.update(a[1:])
        else:
            rest.append(a)
    return flags, rest


# --- handlers ----------------------------------------------------------------

def _pwd(vfs: VirtualFileSystem, args: list[str]) -> CommandResult:
    return CommandResult([vfs.cwd])


def _whoami(vfs: VirtualFileSystem, args: list[str]) -> CommandResult:
    return CommandResult([USERNAME])


def _cd(vfs: VirtualFileSystem, args: list[str]) -> CommandResult:
    target = args[0] if args else "~"
    try:
        vfs.chdir(target)
    except VfsError as e:
        return CommandResult([f"cd: {e}"], ok=False)
    return CommandResult()


def _ls(vfs: VirtualFileSystem, args: list[str]) -> CommandResult:
    flags, paths = _split_flags(args)
    targets = paths or [None]
    lines: list[str] = []
    ok = True
    for i, target in enumerate(targets):
        try:
            entries = vfs.listing(target, show_all="a" in flags)
        except VfsError as e:
            lines.append(f"ls: {e}")
            ok = False
            continue
        if len(targets) > 1 and target:
            if i:
                lines.append("")
            lines.append(f"{target}:")
        if "l" in flags:
            for name, node in entries:
                prefix = "d" if node["type"] == "dir" else "-"
                size = len(node.get("content", "")) if node["type"] == "file" else 4096
                display = name + ("/" if node["type"] == "dir" else "")
                lines.append(
                    f"{prefix}{vfs.mode_string(node)} 1 {node['owner']} {node['owner']} "
                    f"{size:>6} Aug  7 12:00 {display}"
                )
        else:
            lines.extend(
                name + ("/" if node["type"] == "dir" else "") for name, node in entries
            )
    return CommandResult(lines, ok=ok)


def _mkdir(vfs: VirtualFileSystem, args: list[str]) -> CommandResult:
    flags, paths = _split_flags(args)
    if not paths:
        return CommandResult(["mkdir: missing operand"], ok=False)
    for p in paths:
        vfs.mkdir(p, parents="p" in flags)
    return CommandResult()


def _touch(vfs: VirtualFileSystem, args: list[str]) -> CommandResult:
    if not args:
        return CommandResult(["touch: missing file operand"], ok=False)
    for p in args:
        vfs.touch(p)
    return CommandResult()


def _cat(vfs: VirtualFileSystem, args: list[str]) -> CommandResult:
    if not args:
        return CommandResult(["cat: missing file operand (the simulator has no stdin)"], ok=False)
    lines: list[str] = []
    ok = True
    for p in args:
        try:
            content = vfs.read_file(p)
            lines.extend(content.split("\n") if content else [""])
        except VfsError as e:
            lines.append(f"cat: {e}")
            ok = False
    return CommandResult(lines, ok=ok)


def _echo(vfs: VirtualFileSystem, args: list[str]) -> CommandResult:
    # handle redirection: echo text > file / >> file
    if ">" in args or ">>" in args:
        op = ">>" if ">>" in args else ">"
        i = args.index(op)
        text = " ".join(args[:i])
        rest = args[i + 1 :]
        if len(rest) != 1:
            return CommandResult([f"syntax error near '{op}'"], ok=False)
        vfs.write_file(rest[0], text + "\n", append=(op == ">>"))
        return CommandResult()
    return CommandResult([" ".join(args)])


def _cp(vfs: VirtualFileSystem, args: list[str]) -> CommandResult:
    flags, paths = _split_flags(args)
    if len(paths) != 2:
        return CommandResult(["cp: expected source and destination"], ok=False)
    vfs.copy(paths[0], paths[1], recursive="r" in flags or "R" in flags)
    return CommandResult()


def _mv(vfs: VirtualFileSystem, args: list[str]) -> CommandResult:
    _, paths = _split_flags(args)
    if len(paths) != 2:
        return CommandResult(["mv: expected source and destination"], ok=False)
    vfs.move(paths[0], paths[1])
    return CommandResult()


def _rm(vfs: VirtualFileSystem, args: list[str]) -> CommandResult:
    flags, paths = _split_flags(args)
    if not paths:
        return CommandResult(["rm: missing operand"], ok=False)
    for p in paths:
        vfs.remove(p, recursive="r" in flags or "R" in flags)
    return CommandResult()


def _chmod(vfs: VirtualFileSystem, args: list[str]) -> CommandResult:
    _, rest = _split_flags([a for a in args if not (a.startswith("+") or a.startswith("-"))])
    symbolic = [a for a in args if a.startswith("+") or (a.startswith("-") and not a[1:].isdigit() and len(a) > 1 and a[1] in "rwx")]
    numeric = [a for a in rest if a.isdigit()]
    paths = [a for a in rest if not a.isdigit()]

    if not paths or (not numeric and not symbolic):
        return CommandResult(["chmod: usage: chmod <mode|+x|-x> <file>"], ok=False)
    for p in paths:
        node = vfs.get(p)
        if node is None:
            return CommandResult([f"chmod: cannot access '{p}': No such file or directory"], ok=False)
        if numeric:
            mode = numeric[0]
            if len(mode) != 3 or any(c not in "01234567" for c in mode):
                return CommandResult([f"chmod: invalid mode: '{mode}'"], ok=False)
            node["mode"] = mode
        else:
            for spec in symbolic:
                add = spec[0] == "+"
                for ch in spec[1:]:
                    bit = {"r": 4, "w": 2, "x": 1}.get(ch)
                    if bit is None:
                        return CommandResult([f"chmod: invalid mode: '{spec}'"], ok=False)
                    digits = [int(d) for d in node["mode"].rjust(3, "0")]
                    # apply to user/group/other alike — the common beginner usage
                    digits = [(d | bit) if add else (d & ~bit) for d in digits]
                    node["mode"] = "".join(str(d) for d in digits)
    return CommandResult()


def _help(vfs: VirtualFileSystem, args: list[str]) -> CommandResult:
    return CommandResult(
        [
            "Simulated shell — available commands:",
            "  pwd ls cd mkdir touch cat cp mv rm echo whoami chmod help clear",
            "  chaining: cmd1 ; cmd2   or   cmd1 && cmd2",
            "  redirection: echo text > file   echo text >> file",
            "  run a script: ./script.sh (needs the execute bit — try ls -l)",
            "This is a safe simulation: nothing you type touches a real machine.",
        ]
    )


def _clear(vfs: VirtualFileSystem, args: list[str]) -> CommandResult:
    # The frontend interprets this control marker and clears the scrollback.
    return CommandResult(["\x00clear"])


def _execute_file(vfs: VirtualFileSystem, path: str) -> CommandResult:
    node = vfs.get(path)
    name = path if path.startswith("./") else path
    if node is None:
        return CommandResult([f"bash: {name}: No such file or directory"], ok=False)
    if node["type"] == "dir":
        return CommandResult([f"bash: {name}: Is a directory"], ok=False)
    if not vfs.is_executable(node):
        # The classic teaching moment (curriculum §13).
        return CommandResult([f"bash: {name}: Permission denied"], ok=False)
    lines = (node.get("exec_output") or "").split("\n") if node.get("exec_output") else []
    for target, content in (node.get("exec_creates") or {}).items():
        parent = target.rsplit("/", 1)[0] or "/"
        vfs.ensure_dir(parent)
        vfs.write_file(target, content)
    return CommandResult(lines)


_HANDLERS = {
    "pwd": _pwd,
    "whoami": _whoami,
    "cd": _cd,
    "ls": _ls,
    "mkdir": _mkdir,
    "touch": _touch,
    "cat": _cat,
    "echo": _echo,
    "cp": _cp,
    "mv": _mv,
    "rm": _rm,
    "chmod": _chmod,
    "help": _help,
    "clear": _clear,
}
