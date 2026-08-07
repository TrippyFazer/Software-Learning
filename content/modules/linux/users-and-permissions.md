---
module: linux
lesson: users-and-permissions
title: "Users, Permissions, and Permission Denied"
difficulty: beginner
concepts:
  - user
  - permission
  - owner
  - execute-bit
prerequisites:
  - linux/working-with-files
quiz: linux/users-and-permissions
exercise: linux/fix-the-backup-script
flashcards:
  - card-permissions
  - card-rwx
  - card-chmod
  - card-execute-bit
---

## Why this matters

`Permission denied` is the most common wall every new server administrator
hits — and it's not an error so much as the operating system doing its job.
Once you can *read* permissions, the wall becomes a door with a documented
lock. This lesson ends with a broken script you'll diagnose and fix
yourself.

## Mental model

**Beginner mental model:** every file has an access-control card taped to
it: *who owns this, and what may the owner / the owner's group / everyone
else do with it?* The three doable things are **r**ead, **w**rite, and
e**x**ecute.

Like controlled substances in a lab: the substance (file) has a register
saying who may view the record (r), amend it (w), and actually use it (x).
The register is checked on *every* access, no exceptions — which is
exactly what Linux does.

**Technical reality:** each file carries an owner, a group, and nine
permission bits — three triplets of `rwx` for owner/group/others. `ls -l`
prints them:

```
-rwxr-xr--  1 learner learner  512 Aug  7 12:00 backup.sh
│└┬┘└┬┘└┬┘
│ │   │  └ others: read only
│ │   └ group: read + execute
│ └ owner: read, write, execute
└ file type: - file, d directory
```

## Vocabulary

| Term | Plain meaning | Why you care |
|------|---------------|--------------|
| **user** | An identity the OS tracks; every process runs *as* someone | Explains who may do what — and why services get their own users |
| **permission** | The r/w/x rights on a file for owner, group, others | The lock on every door |
| **owner** | The user a file belongs to | First triplet of rights applies to them |
| **execute bit** | The x permission — required to *run* a file as a program | The classic `./script.sh: Permission denied` cause |
| **root** | The superuser; permission checks don't apply | Power and blast radius — why we don't run things as root |

## Deep explanation

**Numbers.** Each triplet is also a number: r=4, w=2, x=1, summed. So
`rwx`=7, `r-x`=5, `r--`=4, and the whole mode is three digits:
`755` = `rwxr-xr-x` (typical for programs and directories),
`644` = `rw-r--r--` (typical for plain files). You'll see these numbers
everywhere: in `chmod`, in Docker files, in error messages.

**Changing permissions.** `chmod` sets them, two ways:

```
chmod 755 backup.sh    # numeric: set exactly this mode
chmod +x backup.sh     # symbolic: add the execute bit
```

**The execute bit has two jobs.** On a *file*, x means "may be run as a
program" — a script without it produces the famous
`./backup.sh: Permission denied`. On a *directory*, x means "may be
entered" (`cd` into it). A directory you can read but not execute is a
strange half-open state you'll meet eventually.

**Why servers care.** Every process runs as some user, with that user's
permissions. Well-run systems give each service a low-privilege user: the
web server user can read the app's files but not `/etc/shadow`; the
database user owns its data directory and nothing else. When an attacker
compromises a service, the permissions of *that user* are the walls around
the damage. This is exactly why the Learning Lab's own API container runs
as a non-root user — visible in `infra/docker/api.Dockerfile`.

**root** bypasses all of it. That power is needed for administration and
catastrophic in daily use: a typo'd `rm -r` as a normal user hits a wall
of permission denials; as root, nothing pushes back.

## Brain Core connection

Brain Core will have secrets (API keys, database passwords) in files that
must be readable by the service user *only* — mode `600`. It will have
data directories owned by its own service user. When something in its
deployment can't read something, your diagnosis will be this lesson: `ls
-l`, read the triplets, ask "who is the process running as?"

## Plex / home-server connection

The single most common Plex problem on forums: *media doesn't show up*
because the `plex` user can't read the media files — wrong owner or
missing r/x on a directory in the path. You'll be able to diagnose in two
commands what people flail at for hours.

## Interactive example

In the sandbox: `touch script.sh`, then `ls -l script.sh` — note `644`.
Try `./script.sh` → denied. `chmod +x script.sh`, `ls -l` again — watch
the x's appear — then `./script.sh`.

## Practice

Mission: **Fix the Backup Script.** It's failing. Your job is to find out
why (the tools are `ls -l` and this lesson) and make it run successfully.

## Common mistake

> "Permission denied, so… `chmod 777` — it works now!"

`777` means *everyone* may read, write, and execute. It "fixes" every
permission error by removing all protection — including from other
processes and, on shared systems, other people. It's the antibiotic-for-
a-virus of Linux administration: superficially effective, actually harmful.
The right fix is always specific: identify *who* needs *what* access, and
grant exactly that (`755` for programs, `644` for data, `600` for secrets).

## Knowledge check

Quiz below.

## Summary

- Every file has an owner and three rwx triplets: owner / group / others.
- `ls -l` shows them; r=4, w=2, x=1 sum into modes like 755 and 644.
- The execute bit gates running files as programs and entering directories.
- Every process runs as a user; that user's permissions are the blast
  radius when things go wrong — hence dedicated low-privilege service users.
- `chmod 777` is surrender, not a fix; grant the minimum that works.
