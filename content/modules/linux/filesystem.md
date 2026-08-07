---
module: linux
lesson: filesystem
title: "The Filesystem: One Tree, Everything In It"
difficulty: beginner
concepts:
  - filesystem
  - path
  - directory
  - working-directory
prerequisites:
  - systems/anatomy-of-an-application
quiz: linux/filesystem
exercise: linux/explore-the-filesystem
flashcards:
  - card-filesystem
  - card-path
  - card-working-directory
  - card-home-directory
---

## Why this matters

Every server task — deploying Brain Core, finding a log, fixing a broken
service — starts with the same question: *where is the thing?* Linux answers
with one structure, used identically on your Lightsail host, a Raspberry Pi,
and a thousand-node cluster. Learn the tree once and every machine becomes
navigable.

## Mental model

**Beginner mental model:** the filesystem is one upside-down tree. The root
is written `/`, and every single thing — programs, logs, your files, even
attached drives — hangs somewhere under it.

A **path** is directions through the tree: `/home/learner/projects` means
"from the root, into `home`, into `learner`, into `projects`."

If you've worked with a well-organized lab notebook system: `/` is the
archive room, directories are binders within binders, and a path is the
retrieval instruction that finds one exact page.

**Technical reality:** there are no drive letters (no `C:`). Additional
disks are *mounted* onto directories in the same tree (Module 4). The tree
is also mostly conventional: `/home` for users' files, `/etc` for
configuration, `/var/log` for logs, `/usr/bin` for programs. Those
conventions are why an experienced admin can find things on a machine
they've never seen.

## Vocabulary

| Term | Plain meaning | Why you care |
|------|---------------|--------------|
| **filesystem** | The tree of all directories and files | Everything on a server lives in it |
| **path** | An address in the tree, like `/var/log/app.log` | Every command takes them |
| **directory** | A container for files and other directories (a "folder") | The tree's branches |
| **working directory** | The directory your shell is currently "standing in" | Relative paths start from here |
| **home directory** | Your personal directory, `/home/<user>`, abbreviated `~` | Where your session begins |

## Deep explanation

The shell always has a **working directory** — you are always *somewhere*
in the tree. Three commands make that concrete:

```
pwd     # print working directory — "where am I?"
ls      # list — "what's here?"
cd      # change directory — "go there"
```

Paths come in two forms, and confusing them causes most beginner errors:

- **Absolute** paths start with `/` and work from anywhere:
  `cd /home/learner/projects`
- **Relative** paths start from the working directory: if you're in
  `/home/learner`, then `cd projects` goes to the same place.

Two special names exist in every directory: `.` (this directory) and
`..` (the parent). So `cd ..` steps up one level, and `../notes.txt`
means "notes.txt in my parent directory." And `~` always expands to your
home directory: `cd ~` from anywhere brings you home.

`ls` has flags worth knowing immediately: `ls -a` also shows *hidden*
entries (names starting with `.`, used for configuration), and `ls -l`
shows the long listing — permissions, owner, size — which becomes central
in the permissions lesson.

## Brain Core connection

Brain Core's deployment will be paths all the way down: its code in
something like `/srv/brain-core`, its configuration in a dotfile, its
uploads on a mounted volume, its logs under `/var/log` or a Docker
volume. When an AI tool writes `open("./data/uploads.db")`, you can now ask
the critical question: *relative to which working directory?* — a genuinely
common source of production bugs.

## Plex / home-server connection

A Plex server is largely a filesystem-organization exercise:
`/media/movies`, `/media/tv`, named and structured the way Plex's scanner
expects. When a movie doesn't appear in Plex, the first diagnostic is
pure Module 1: does the path exist, is it where the library expects, can
the Plex user reach it?

## Interactive example

The terminal exercise below drops you into a small filesystem. Before any
mission: run `pwd`, then `ls`, then wander with `cd` and `ls` until the
tree feels like a place. Getting "lost" is impossible — `cd ~` always
brings you home, and this is a simulation.

## Practice

Open the exercise: **Explore the Filesystem**. Somewhere in the tree a
file is waiting with instructions inside it. Find it, read it, do what it
says.

## Common mistake

> `cat notes.txt` → `cat: notes.txt: No such file or directory` — "but I
> can SEE it in the other window!"

The file exists — in a *different directory* than your working directory.
A relative path is always resolved from where you are standing, not from
where you are looking. Habit to build: when a file isn't found, run `pwd`
first, then `ls`. Nine times out of ten, you aren't where you think you
are.

## Knowledge check

Quiz below — commit before revealing.

## Summary

- Everything lives in one tree rooted at `/`; there are no drive letters.
- A path is an address; absolute paths start with `/`, relative paths
  start from the working directory.
- `pwd`, `ls`, `cd` are the "where am I / what's here / go there" trio.
- `..` is the parent, `.` is here, `~` is home.
- Standard locations (`/etc`, `/var/log`, `/home`) are conventions that
  make every Linux machine navigable.
