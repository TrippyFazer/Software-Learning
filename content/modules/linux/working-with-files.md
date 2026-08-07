---
module: linux
lesson: working-with-files
title: "Making, Moving, and Destroying Things"
difficulty: beginner
concepts:
  - file-operations
  - redirection
prerequisites:
  - linux/filesystem
quiz: linux/working-with-files
exercise: linux/create-project-structure
flashcards:
  - card-mkdir-touch
  - card-cp-mv-rm
  - card-redirection
---

## Why this matters

Reading the tree was passive. Servers are administered by *changing* it:
creating a directory for a deployment, copying a config into place, moving
a log aside, deleting old artifacts. These six commands are the hands you'll
use for everything — and one of them (`rm`) is the first command that can
genuinely hurt you on a real machine.

## Mental model

**Beginner mental model:** six verbs against the tree.

| Verb | Command |
|------|---------|
| make a directory | `mkdir name` |
| make an empty file | `touch name` |
| read a file | `cat name` |
| copy | `cp source destination` |
| move / rename | `mv source destination` |
| delete | `rm name` |

**Technical reality:** these are tiny standalone programs, not features of
the shell. The shell just finds and runs them with your arguments. That's
why they behave identically in scripts, on other distros, and over SSH —
and why `mv` doing both "move" and "rename" isn't weird: renaming *is*
moving to a new path in the tree.

## Vocabulary

| Term | Plain meaning | Why you care |
|------|---------------|--------------|
| **argument** | The words after a command (`mkdir projects` — `projects` is the argument) | How you tell commands what to act on |
| **flag** | A `-x` style option that changes behavior (`ls -l`, `rm -r`) | Same verb, different manner |
| **redirection** | `>` sends a command's output into a file instead of the screen | How files get content from commands |

## Deep explanation

**Creating.** `mkdir projects` makes one directory. `mkdir -p a/b/c` makes
the whole chain at once (`-p` = "parents"). `touch notes.txt` creates an
empty file (its real job is updating timestamps; creating-if-missing is the
side effect everyone actually uses it for).

**Putting content in files.** `echo` prints its arguments; **redirection**
captures them:

```
echo "hello" > greeting.txt     # write (REPLACES the whole file)
echo "again" >> greeting.txt    # append
cat greeting.txt
```

Note the danger built into `>`: it truncates an existing file before
writing. `>` a config file you meant to read and it's gone.

**Copying and moving.** `cp a.txt b.txt` copies; `cp -r dir1 dir2` copies
a directory tree (`-r` = recursive — directories need it). `mv old new`
moves — which is also how you rename. If the destination is an existing
directory, the source goes *into* it: `mv notes.txt docs/`.

**Deleting.** `rm file` removes a file. `rm -r dir` removes a directory
and everything inside. On real Linux there is no trash can and no undo —
`rm` unlinks the data immediately. Treat `rm -r` like a scalpel: look
(`ls`) before you cut, and be suspicious of any `rm` with a path you
didn't just verify. (In this simulator, `rm -rf /` just refuses — on a
real machine as root, it is how servers die.)

## Brain Core connection

Deploying Brain Core will be exactly these verbs in sequence: `mkdir -p`
the app directory, `cp` the environment file into place, `mv` an old
release aside, `rm -r` a stale build. Deployment scripts are these six
commands wearing a trench coat — when you read one, you'll now see the
verbs.

## Plex / home-server connection

Media management is bulk file operations: `mv Downloads/show-s01e01.mkv
/media/tv/Show/Season\ 01/` — and the reason people script it is that
doing it by hand for a thousand episodes is misery. The scripts people
share for this (Sonarr, Radarr, or hand-rolled) are automating precisely
these commands.

## Interactive example

In the sandbox (Practice → Free Practice Sandbox), build something and
tear it down: make a directory, put a file in it with `echo ... > `,
`cat` it back, copy it, rename the copy, then remove the whole directory
with `rm -r`. Watch `ls` between steps.

## Practice

The mission: **Build a Project Skeleton** — create the `projects/brain-core/`
structure with a README inside. Any valid route works: step-by-step with
`cd`, or all-at-once with `mkdir -p` and full paths. The grader only checks
the resulting tree.

## Common mistake

> `rm -r projects` — "wait, no, that was the wrong directory."

There is no undo. The habit that prevents this on real servers: run `ls
<target>` first, *look* at what will be deleted, then reuse the same path
in the `rm`. Never type a fresh path directly into `rm -r`. (Related
classic: `echo "x" > important.conf` when you meant `>>` — the file's old
contents are already gone.)

## Knowledge check

Quiz below.

## Summary

- `mkdir` / `touch` create; `-p` builds whole directory chains.
- `echo text > file` writes (destructively!); `>>` appends; `cat` reads.
- `cp` copies (`-r` for directories); `mv` moves *and* renames.
- `rm` is immediate and permanent on real systems; look before you delete.
- These are programs the shell runs for you — the same everywhere Linux runs.
