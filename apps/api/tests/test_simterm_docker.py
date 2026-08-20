"""The simulated Docker engine (Module 8).

These tests exist because the module's central lesson is a DESTRUCTIVE one:
`docker compose down` keeps named volumes and `down -v` destroys them. If the
simulator gets that backwards — or quietly re-seeds the data after -v — it
teaches the opposite of the truth, confidently, and the learner finds out on
a real database.
"""

from app.modules.simterm import commands
from app.modules.simterm.vfs import VirtualFileSystem, make_file

COMPOSE = """name: shop
services:
  db:
    image: postgres:16
    volumes:
      - pgdata:/var/lib/postgresql/data
    x-sim-initial-data:
      /var/lib/postgresql/data/orders.tbl: "1200 rows"
  cache:
    image: redis:7
    x-sim-initial-data:
      /data/session.cache: "warm"
  web:
    image: nginx:alpine
    ports:
      - "8080:80"
volumes:
  pgdata:
"""


def _stack(compose: str = COMPOSE) -> VirtualFileSystem:
    vfs = VirtualFileSystem()
    vfs.ensure_dir("/home/learner/shop")
    vfs.cwd = "/home/learner/shop"
    vfs._lookup_parent("/home/learner/shop/docker-compose.yml")["children"][
        "docker-compose.yml"
    ] = make_file(content=compose)
    return vfs


def run(vfs, line: str) -> str:
    return "\n".join(commands.run_line(vfs, line))


# --- the lesson --------------------------------------------------------------

def test_named_volume_survives_down_and_up():
    vfs = _stack()
    run(vfs, "docker compose up -d")
    assert "orders.tbl" in run(vfs, "docker exec shop-db-1 ls /var/lib/postgresql/data")
    run(vfs, "docker compose down")
    run(vfs, "docker compose up -d")
    assert "orders.tbl" in run(vfs, "docker exec shop-db-1 ls /var/lib/postgresql/data")


def test_data_without_a_volume_dies_with_the_container():
    vfs = _stack()
    run(vfs, "docker compose up -d")
    assert "session.cache" in run(vfs, "docker exec shop-cache-1 ls /data")
    run(vfs, "docker compose down")
    run(vfs, "docker compose up -d")
    assert run(vfs, "docker exec shop-cache-1 ls /data") == ""


def test_down_dash_v_destroys_the_volume_and_the_data_does_not_come_back():
    """The regression that would silently invert the whole module.

    An earlier version re-seeded the scenario data on every `up`, so after
    `down -v` the orders reappeared and -v looked harmless.
    """
    vfs = _stack()
    run(vfs, "docker compose up -d")
    run(vfs, "docker compose down -v")
    assert "shop_pgdata" not in run(vfs, "docker volume ls")
    run(vfs, "docker compose up -d")
    assert run(vfs, "docker exec shop-db-1 ls /var/lib/postgresql/data") == ""
    assert "empty cluster" in run(vfs, "docker logs shop-db-1")


def test_plain_down_reports_that_it_kept_the_volumes():
    vfs = _stack()
    run(vfs, "docker compose up -d")
    out = run(vfs, "docker compose down")
    assert "kept 1 named volume" in out
    assert "never deletes them" in out


# --- ports and networks ------------------------------------------------------

def test_published_port_is_shown_and_unpublished_is_not():
    vfs = _stack()
    run(vfs, "docker compose up -d")
    ps = run(vfs, "docker ps")
    assert "0.0.0.0:8080->80/tcp" in ps
    db_line = [ln for ln in ps.split("\n") if "shop-db-1" in ln][0]
    assert "->" not in db_line


def test_compose_creates_a_project_network():
    vfs = _stack()
    run(vfs, "docker compose up -d")
    assert "shop_default" in run(vfs, "docker network ls")
    run(vfs, "docker compose down")
    assert "shop_default" not in run(vfs, "docker network ls")


# --- lifecycle ---------------------------------------------------------------

def test_running_container_cannot_be_removed_without_force():
    vfs = VirtualFileSystem()
    run(vfs, "docker run -d --name web nginx:alpine")
    assert "container is running" in run(vfs, "docker rm web")
    assert "web" in run(vfs, "docker ps")
    run(vfs, "docker stop web")
    run(vfs, "docker rm web")
    assert "web" not in run(vfs, "docker ps -a")


def test_duplicate_container_name_is_refused():
    vfs = VirtualFileSystem()
    run(vfs, "docker run -d --name web nginx:alpine")
    assert "already in use" in run(vfs, "docker run -d --name web nginx:alpine")


def test_image_survives_its_containers():
    """The point of lesson 1: templates outlive instances."""
    vfs = VirtualFileSystem()
    run(vfs, "docker run -d --name a nginx:alpine")
    run(vfs, "docker stop a")
    run(vfs, "docker rm a")
    assert "nginx" in run(vfs, "docker images")


def test_volume_in_use_cannot_be_removed():
    vfs = _stack()
    run(vfs, "docker compose up -d")
    assert "volume is in use" in run(vfs, "docker volume rm shop_pgdata")


# --- failure modes -----------------------------------------------------------

def test_compose_outside_the_project_directory_explains_itself():
    vfs = _stack()
    vfs.cwd = "/home/learner"
    out = run(vfs, "docker compose up -d")
    assert "no configuration file provided" in out
    assert "CURRENT directory" in out


def test_unknown_docker_subcommand_does_not_crash():
    vfs = VirtualFileSystem()
    out = run(vfs, "docker swarm init")
    assert "not a docker command" in out


def test_malformed_compose_file_reports_yaml_error():
    vfs = _stack(compose="services:\n  db:\n   image: [unclosed\n")
    out = run(vfs, "docker compose up -d")
    assert "invalid YAML" in out


def test_docker_state_survives_a_snapshot_round_trip():
    """Exercise state is persisted as JSON between requests; engine state has
    to travel with the filesystem or every command would start from nothing."""
    vfs = _stack()
    run(vfs, "docker compose up -d")
    revived = VirtualFileSystem.from_dict(vfs.to_dict())
    assert "shop-db-1" in run(revived, "docker ps")
    assert "orders.tbl" in run(revived, "docker exec shop-db-1 ls /var/lib/postgresql/data")


def test_old_snapshots_without_docker_state_still_load():
    """Backward compatibility: exercises in progress before Module 8 existed
    have no `docker` key, and must not explode."""
    vfs = VirtualFileSystem.from_dict({"root": VirtualFileSystem().root, "cwd": "/home/learner"})
    assert run(vfs, "docker ps") != ""  # header row only, but no exception
