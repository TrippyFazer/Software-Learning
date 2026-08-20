"""A simulated Docker engine for the terminal.

Same contract as the rest of `simterm` (docs/SECURITY.md rule 1, ADR-0004):
this manipulates dictionaries. There is no Docker here, no socket, no daemon,
no process. `docker rm -f` in this simulator is as dangerous as deleting a key
from a dict, which is exactly what it does.

WHY SIMULATE DOCKER AT ALL

Module 8 has to teach the two facts that cost people real data:

  * `docker compose down` KEEPS named volumes; `docker compose down -v`
    destroys them.
  * a container that was never given a volume loses everything the moment it
    is removed — and removal is routine.

Both are only learnable by doing them and watching the data vanish. Reading
"be careful with -v" teaches nobody anything; typing it, running `docker
compose up -d` again, and finding an empty database teaches it permanently.
That is the whole "MAKE A MISTAKE → UNDERSTAND WHY" loop, and it cannot be
run against a real engine on a shared host.

STATE SHAPE (JSON-serialisable, stored in ExerciseState.vfs_snapshot)

    {
      "images":     {"postgres:16": {...}},
      "containers": {"db": {...}},
      "volumes":    {"pgdata": {...}},
      "networks":   {"learning-lab_default": {...}},
    }

Containers hold a "data" dict: the bytes a service would have written. It is
what makes durability visible — the learner can `docker exec db ls /var/lib/
postgresql/data` and see rows survive, or not.
"""

import copy

import yaml

DEFAULT_STATE = {
    "images": {},
    "containers": {},
    "volumes": {},
    "networks": {},
    # Which compose projects have had their scenario data seeded already.
    # This lives at ENGINE level so it survives the volume being deleted —
    # without it, `down -v` deletes the volume, the next `up` recreates it,
    # the scenario data is seeded again, and the learner concludes that -v is
    # harmless. That is the exact opposite of the lesson.
    "seeded": {},
}

COMPOSE_NAMES = ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")

# Short ids are cosmetic, but a stable, made-up-looking hex string is part of
# what makes the output read as real docker rather than as a mock.
def _short_id(seed: str) -> str:
    h = 0
    for ch in seed:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFFFFFF
    return f"{h:012x}"


def new_state() -> dict:
    return copy.deepcopy(DEFAULT_STATE)


def _ensure(state: dict) -> dict:
    for key in DEFAULT_STATE:
        state.setdefault(key, {})
    return state


# ---------------------------------------------------------------- formatting

def _table(rows: list[list[str]], headers: list[str]) -> list[str]:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    out = ["   ".join(h.ljust(widths[i]) for i, h in enumerate(headers)).rstrip()]
    for row in rows:
        out.append("   ".join(c.ljust(widths[i]) for i, c in enumerate(row)).rstrip())
    return out


def _ports_text(container: dict) -> str:
    published = container.get("ports") or []
    if not published:
        # The realistic display for an unpublished port: reachable on the
        # container network, not from the host. Module 8 leans on this line.
        exposed = container.get("expose") or []
        return ", ".join(f"{p}/tcp" for p in exposed)
    return ", ".join(f"0.0.0.0:{p['host']}->{p['container']}/tcp" for p in published)


# ------------------------------------------------------------------ commands

def run(vfs, args: list[str]) -> tuple[list[str], bool]:
    """Entry point. Returns (output lines, ok)."""
    state = _ensure(vfs.docker)
    if not args:
        return _usage(), False

    sub, rest = args[0], args[1:]
    handler = {
        "ps": _ps,
        "images": _images,
        "image": _image,
        "pull": _pull,
        "run": _run,
        "stop": _stop,
        "start": _start,
        "rm": _rm,
        "logs": _logs,
        "exec": _exec_in_container,
        "volume": _volume,
        "network": _network,
        "inspect": _inspect,
        "compose": _compose,
        "version": _version,
        "help": lambda *_: (_usage(), True),
    }.get(sub)

    if handler is None:
        return (
            [
                f"docker: '{sub}' is not a docker command.",
                "See 'docker help'. (This simulator implements the subset Module 8 teaches.)",
            ],
            False,
        )
    return handler(vfs, state, rest)


def _usage() -> list[str]:
    return [
        "Usage:  docker COMMAND",
        "",
        "Simulated commands:",
        "  ps [-a]                 list containers (-a includes stopped ones)",
        "  images                  list images on this machine",
        "  pull IMAGE              download an image",
        "  run [-d] [--name N] [-p H:C] [-v VOL:PATH] IMAGE",
        "  start|stop|rm [-f] NAME",
        "  logs NAME               show a container's output",
        "  exec NAME ls PATH       look inside a running container",
        "  inspect NAME",
        "  volume ls|create|rm|inspect",
        "  network ls",
        "  compose up [-d] | down [-v] | ps | logs | config",
    ]


def _version(vfs, state, args) -> tuple[list[str], bool]:
    return (["Docker version 29.7.2 (simulated)", "Docker Compose version v5.4.0 (simulated)"], True)


# --- images -----------------------------------------------------------------

def _images(vfs, state, args) -> tuple[list[str], bool]:
    rows = []
    for ref, img in sorted(state["images"].items()):
        repo, _, tag = ref.partition(":")
        rows.append([repo, tag or "latest", img["id"], img.get("size", "—")])
    if not rows:
        return (_table([], ["REPOSITORY", "TAG", "IMAGE ID", "SIZE"]), True)
    return (_table(rows, ["REPOSITORY", "TAG", "IMAGE ID", "SIZE"]), True)


def _image(vfs, state, args) -> tuple[list[str], bool]:
    if args and args[0] == "ls":
        return _images(vfs, state, args[1:])
    return (["Usage: docker image ls"], False)


def _pull(vfs, state, args) -> tuple[list[str], bool]:
    if not args:
        return (['"docker pull" requires exactly 1 argument.'], False)
    ref = args[0] if ":" in args[0] else f"{args[0]}:latest"
    if ref in state["images"]:
        return ([f"{ref}: Pulling from library", "Image is up to date for {}".format(ref)], True)
    state["images"][ref] = {"id": _short_id(ref), "size": "142MB"}
    return (
        [
            f"{ref.split(':')[1]}: Pulling from library/{ref.split(':')[0]}",
            "Digest: sha256:" + _short_id(ref + "digest"),
            f"Status: Downloaded newer image for {ref}",
        ],
        True,
    )


# --- containers --------------------------------------------------------------

def _ps(vfs, state, args) -> tuple[list[str], bool]:
    show_all = "-a" in args or "--all" in args
    rows = []
    for name, c in sorted(state["containers"].items()):
        if not show_all and c["status"] != "running":
            continue
        status = "Up 2 minutes" if c["status"] == "running" else f"Exited ({c.get('exit_code', 0)}) 1 minute ago"
        rows.append([c["id"], c["image"], name, status, _ports_text(c)])
    return (_table(rows, ["CONTAINER ID", "IMAGE", "NAMES", "STATUS", "PORTS"]), True)


def _parse_run_flags(args: list[str]) -> tuple[dict, str | None, list[str]]:
    opts: dict = {"detach": False, "name": None, "ports": [], "volumes": []}
    image = None
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-d", "--detach"):
            opts["detach"] = True
        elif a in ("--name",) and i + 1 < len(args):
            i += 1
            opts["name"] = args[i]
        elif a in ("-p", "--publish") and i + 1 < len(args):
            i += 1
            host, _, cont = args[i].partition(":")
            opts["ports"].append({"host": host, "container": cont or host})
        elif a in ("-v", "--volume") and i + 1 < len(args):
            i += 1
            src, _, dst = args[i].partition(":")
            opts["volumes"].append({"source": src, "target": dst or src})
        elif not a.startswith("-"):
            image = a
            return opts, image, args[i + 1 :]
        i += 1
    return opts, image, []


def _run(vfs, state, args) -> tuple[list[str], bool]:
    opts, image, _cmd = _parse_run_flags(args)
    if image is None:
        return (['"docker run" requires at least 1 argument.'], False)
    ref = image if ":" in image else f"{image}:latest"
    pulled: list[str] = []
    if ref not in state["images"]:
        pulled, _ = _pull(vfs, state, [ref])
    name = opts["name"] or f"{ref.split(':')[0].replace('/', '_')}_{len(state['containers']) + 1}"
    if name in state["containers"]:
        return (
            pulled
            + [
                f"docker: Error response from daemon: Conflict. The container name "
                f'"/{name}" is already in use.',
                "You have to remove (or rename) that container to be able to reuse that name.",
            ],
            False,
        )
    for vol in opts["volumes"]:
        state["volumes"].setdefault(vol["source"], {"driver": "local", "project": None})
    state["containers"][name] = {
        "id": _short_id(name),
        "image": ref,
        "status": "running",
        "ports": opts["ports"],
        "expose": [],
        "volumes": opts["volumes"],
        "project": None,
        "service": None,
        "logs": [f"{name}: started"],
        "data": {},
    }
    return (pulled + [state["containers"][name]["id"]], True)


def _find(state, name) -> dict | None:
    return state["containers"].get(name)


def _stop(vfs, state, args) -> tuple[list[str], bool]:
    if not args:
        return (['"docker stop" requires at least 1 argument.'], False)
    out, ok = [], True
    for name in args:
        c = _find(state, name)
        if c is None:
            out.append(f"Error response from daemon: No such container: {name}")
            ok = False
            continue
        c["status"] = "exited"
        c["exit_code"] = 0
        out.append(name)
    return (out, ok)


def _start(vfs, state, args) -> tuple[list[str], bool]:
    if not args:
        return (['"docker start" requires at least 1 argument.'], False)
    out, ok = [], True
    for name in args:
        c = _find(state, name)
        if c is None:
            out.append(f"Error response from daemon: No such container: {name}")
            ok = False
            continue
        c["status"] = "running"
        out.append(name)
    return (out, ok)


def _rm(vfs, state, args) -> tuple[list[str], bool]:
    force = "-f" in args or "--force" in args
    names = [a for a in args if not a.startswith("-")]
    if not names:
        return (['"docker rm" requires at least 1 argument.'], False)
    out, ok = [], True
    for name in names:
        c = _find(state, name)
        if c is None:
            out.append(f"Error response from daemon: No such container: {name}")
            ok = False
            continue
        if c["status"] == "running" and not force:
            out.append(
                f"Error response from daemon: cannot remove container \"{name}\": "
                "container is running: stop the container before removing or force remove"
            )
            ok = False
            continue
        # THE LESSON. Everything written inside the container's own writable
        # layer goes with it. Only paths backed by a volume survive, because
        # those bytes were never in the container in the first place.
        _persist_volumes(state, c)
        del state["containers"][name]
        out.append(name)
    return (out, ok)


def _persist_volumes(state, container) -> None:
    """Move the container's data into its volumes before it disappears."""
    for vol in container.get("volumes") or []:
        target = vol["target"]
        volume = state["volumes"].get(vol["source"])
        if volume is None:
            continue
        kept = {p: v for p, v in (container.get("data") or {}).items() if p.startswith(target)}
        volume.setdefault("data", {}).update(kept)


def _restore_volumes(state, container) -> None:
    for vol in container.get("volumes") or []:
        volume = state["volumes"].get(vol["source"]) or {}
        container.setdefault("data", {}).update(volume.get("data") or {})


def _logs(vfs, state, args) -> tuple[list[str], bool]:
    names = [a for a in args if not a.startswith("-")]
    if not names:
        return (['"docker logs" requires exactly 1 argument.'], False)
    c = _find(state, names[0])
    if c is None:
        return ([f"Error response from daemon: No such container: {names[0]}"], False)
    return (list(c.get("logs") or []), True)


def _exec_in_container(vfs, state, args) -> tuple[list[str], bool]:
    """`docker exec NAME ls PATH` — deliberately just enough to look inside.

    Being able to SEE whether the data is still there is what makes the
    volume lesson land; a full shell inside a simulated container is a rabbit
    hole with no teaching value.
    """
    argv = [a for a in args if a not in ("-it", "-i", "-t")]
    if len(argv) < 2:
        return (["Usage: docker exec NAME ls PATH"], False)
    name, cmd, *rest = argv
    c = _find(state, name)
    if c is None:
        return ([f"Error response from daemon: No such container: {name}"], False)
    if c["status"] != "running":
        return ([f"Error response from daemon: container {name} is not running"], False)
    if cmd != "ls":
        return ([f"this simulator only supports 'ls' inside a container (you asked for '{cmd}')"], False)
    path = (rest[0] if rest else "/").rstrip("/") or "/"
    data = c.get("data") or {}
    entries = sorted(
        {p[len(path):].lstrip("/").split("/")[0] for p in data if p.startswith(path)}
    )
    entries = [e for e in entries if e]
    if not entries:
        return ([], True)
    return (entries, True)


def _inspect(vfs, state, args) -> tuple[list[str], bool]:
    if not args:
        return (['"docker inspect" requires at least 1 argument.'], False)
    name = args[0]
    c = _find(state, name)
    if c is not None:
        return (
            [
                f"Name:     {name}",
                f"Image:    {c['image']}",
                f"Status:   {c['status']}",
                f"Ports:    {_ports_text(c) or '(none published)'}",
                "Mounts:   "
                + (", ".join(f"{v['source']} -> {v['target']}" for v in c["volumes"]) or "(none)"),
                f"Network:  {c.get('network') or 'bridge'}",
            ],
            True,
        )
    vol = state["volumes"].get(name)
    if vol is not None:
        return _volume(vfs, state, ["inspect", name])
    return ([f"Error: No such object: {name}"], False)


# --- volumes -----------------------------------------------------------------

def _volume(vfs, state, args) -> tuple[list[str], bool]:
    if not args:
        return (["Usage: docker volume ls|create|rm|inspect"], False)
    sub, rest = args[0], args[1:]
    if sub == "ls":
        rows = [["local", n] for n in sorted(state["volumes"])]
        return (_table(rows, ["DRIVER", "VOLUME NAME"]), True)
    if sub == "create":
        if not rest:
            return (["Usage: docker volume create NAME"], False)
        state["volumes"].setdefault(rest[0], {"driver": "local", "project": None})
        return ([rest[0]], True)
    if sub == "rm":
        out, ok = [], True
        for name in [a for a in rest if not a.startswith("-")]:
            if name not in state["volumes"]:
                out.append(f"Error: No such volume: {name}")
                ok = False
                continue
            in_use = [
                cn
                for cn, c in state["containers"].items()
                if any(v["source"] == name for v in c["volumes"])
            ]
            if in_use:
                out.append(
                    f"Error response from daemon: remove {name}: volume is in use - "
                    f"[{', '.join(in_use)}]"
                )
                ok = False
                continue
            del state["volumes"][name]
            out.append(name)
        return (out, ok)
    if sub == "inspect":
        if not rest or rest[0] not in state["volumes"]:
            return ([f"Error: No such volume: {rest[0] if rest else ''}"], False)
        vol = state["volumes"][rest[0]]
        files = sorted((vol.get("data") or {}).keys())
        return (
            [
                f"Name:       {rest[0]}",
                f"Driver:     {vol.get('driver', 'local')}",
                f"Mountpoint: /var/lib/docker/volumes/{rest[0]}/_data",
                f"Contents:   {len(files)} file(s)" + (f" — {', '.join(files[:4])}" if files else ""),
            ],
            True,
        )
    return ([f"docker volume: unknown command '{sub}'"], False)


def _network(vfs, state, args) -> tuple[list[str], bool]:
    if args and args[0] == "ls":
        rows = [["bridge", "bridge"], ["host", "host"], ["none", "null"]]
        rows += [[n, "bridge"] for n in sorted(state["networks"])]
        return (_table(rows, ["NAME", "DRIVER"]), True)
    return (["Usage: docker network ls"], False)


# --- compose -----------------------------------------------------------------

def _find_compose(vfs) -> tuple[str | None, dict | None, str | None]:
    """Locate and parse a compose file in the current directory."""
    for name in COMPOSE_NAMES:
        node = vfs.get(f"{vfs.cwd.rstrip('/')}/{name}")
        if node is not None and node["type"] == "file":
            try:
                parsed = yaml.safe_load(node.get("content") or "") or {}
            except yaml.YAMLError as e:
                return name, None, f"{name}: invalid YAML — {e}"
            if not isinstance(parsed, dict):
                return name, None, f"{name}: top level must be a mapping"
            return name, parsed, None
    return None, None, (
        "no configuration file provided: not found\n"
        "(docker compose looks for docker-compose.yml in the CURRENT directory)"
    )


def _project_name(vfs, spec: dict) -> str:
    named = spec.get("name")
    if named:
        return str(named)
    # Compose falls back to the directory name — the reason the docs insist on
    # an explicit `name:` in every compose file on this server.
    return (vfs.cwd.rstrip("/").rsplit("/", 1)[-1] or "root").lower()


def _compose(vfs, state, args) -> tuple[list[str], bool]:
    if not args:
        return (["Usage: docker compose up [-d] | down [-v] | ps | logs | config"], False)
    sub, rest = args[0], args[1:]
    fname, spec, err = _find_compose(vfs)
    if spec is None:
        return (err.split("\n"), False)

    project = _project_name(vfs, spec)
    services = spec.get("services") or {}
    if not isinstance(services, dict) or not services:
        return ([f"{fname}: no services defined"], False)

    if sub == "config":
        return (yaml.safe_dump(spec, sort_keys=False).rstrip().split("\n"), True)
    if sub == "up":
        return _compose_up(vfs, state, project, spec, services, rest)
    if sub == "down":
        return _compose_down(vfs, state, project, spec, rest)
    if sub == "ps":
        rows = [
            [n, c["image"], "running" if c["status"] == "running" else "exited", _ports_text(c)]
            for n, c in sorted(state["containers"].items())
            if c.get("project") == project
        ]
        return (_table(rows, ["NAME", "IMAGE", "STATUS", "PORTS"]), True)
    if sub == "logs":
        out = []
        for n, c in sorted(state["containers"].items()):
            if c.get("project") == project:
                out.extend(f"{n}  | {line}" for line in (c.get("logs") or []))
        return (out, True)
    return ([f"docker compose: unknown command '{sub}'"], False)


def _compose_up(vfs, state, project, spec, services, rest) -> tuple[list[str], bool]:
    detach = "-d" in rest or "--detach" in rest
    out: list[str] = []
    network = f"{project}_default"
    if network not in state["networks"]:
        state["networks"][network] = {"driver": "bridge", "project": project}
        out.append(f"Network {network}  Created")

    first_run_done = bool(state.setdefault("seeded", {}).get(project))
    declared_volumes = spec.get("volumes") or {}
    for vol_name in declared_volumes:
        full = f"{project}_{vol_name}"
        if full not in state["volumes"]:
            state["volumes"][full] = {"driver": "local", "project": project, "data": {}}
            out.append(f"Volume {full}  Created")

    for service, sdef in services.items():
        sdef = sdef or {}
        cname = sdef.get("container_name") or f"{project}-{service}-1"
        image = sdef.get("image") or f"{project}-{service}:latest"
        ref = image if ":" in image else f"{image}:latest"
        state["images"].setdefault(ref, {"id": _short_id(ref), "size": "142MB"})

        existing = state["containers"].get(cname)
        if existing is not None and existing["status"] == "running":
            out.append(f"Container {cname}  Running")
            continue

        ports = []
        for p in sdef.get("ports") or []:
            host, _, cont = str(p).partition(":")
            ports.append({"host": host, "container": cont or host})
        expose = [str(e) for e in (sdef.get("expose") or [])]

        mounts = []
        for m in sdef.get("volumes") or []:
            src, _, dst = str(m).partition(":")
            dst = dst.split(":")[0] or src
            # A named volume is one declared in the top-level `volumes:` block.
            # Anything else is a bind mount of a host path — a different thing
            # with different lifetime rules, which the lesson draws out.
            if src in declared_volumes:
                mounts.append({"source": f"{project}_{src}", "target": dst, "kind": "volume"})
            else:
                mounts.append({"source": src, "target": dst, "kind": "bind"})

        container = {
            "id": _short_id(cname),
            "image": ref,
            "status": "running",
            "ports": ports,
            "expose": expose,
            "volumes": [m for m in mounts if m["kind"] == "volume"],
            "binds": [m for m in mounts if m["kind"] == "bind"],
            "project": project,
            "service": service,
            "network": network,
            "logs": [f"{service} ready to accept connections"],
            "data": {},
        }

        scenario = dict(sdef.get("x-sim-initial-data") or {})
        if scenario and not first_run_done:
            # FIRST run of this project only: the data that was "already
            # there" when the scenario begins. Paths under a mounted volume go
            # into the VOLUME; everything else goes into the container's own
            # writable layer, where it will not survive removal.
            for path, value in scenario.items():
                target_volume = None
                for m in container["volumes"]:
                    if path.startswith(m["target"]):
                        target_volume = state["volumes"].get(m["source"])
                        break
                if target_volume is not None:
                    target_volume.setdefault("data", {})[path] = value
                else:
                    container["data"][path] = value

        _restore_volumes(state, container)

        # A database whose data directory is empty initialises a fresh, empty
        # one. Realistic, and it is what the learner sees after `down -v`.
        if scenario and not container["data"]:
            container["logs"].insert(
                0, f"{service}: data directory is empty — initializing a new empty cluster"
            )

        state["containers"][cname] = container
        out.append(f"Container {cname}  {'Started' if detach else 'Created'}")

    state.setdefault("seeded", {})[project] = True

    if not detach:
        out.append("")
        out.append("(attached — in a real terminal this would stream logs until Ctrl+C.")
        out.append(" Use -d to run in the background, which is what servers do.)")
    return (out, True)


def _compose_down(vfs, state, project, spec, rest) -> tuple[list[str], bool]:
    remove_volumes = "-v" in rest or "--volumes" in rest
    out: list[str] = []
    for name in sorted(list(state["containers"])):
        c = state["containers"][name]
        if c.get("project") != project:
            continue
        # Data reaches the volume on the way out. This ordering IS the lesson:
        # the bytes were only ever safe because they lived somewhere the
        # container did not own.
        _persist_volumes(state, c)
        del state["containers"][name]
        out.append(f"Container {name}  Removed")

    network = f"{project}_default"
    if network in state["networks"]:
        del state["networks"][network]
        out.append(f"Network {network}  Removed")

    if remove_volumes:
        for vol_name in sorted(state["volumes"]):
            if state["volumes"][vol_name].get("project") == project:
                del state["volumes"][vol_name]
                out.append(f"Volume {vol_name}  Removed")
    else:
        kept = [v for v, d in state["volumes"].items() if d.get("project") == project]
        if kept:
            out.append("")
            out.append(f"(kept {len(kept)} named volume(s): {', '.join(sorted(kept))}")
            out.append(" `docker compose down` never deletes them. `down -v` does.)")
    return (out, True)
