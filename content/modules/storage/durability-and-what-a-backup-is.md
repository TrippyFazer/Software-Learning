---
module: storage
lesson: durability-and-what-a-backup-is
title: "Durability: RAID Is Not a Backup"
difficulty: intermediate
concepts:
  - raid
  - backup
  - restore-test
prerequisites:
  - storage/space-and-what-eats-it
  - docker/volumes-and-data
quiz: storage/durability-and-what-a-backup-is
flashcards:
  - card-raid-not-backup
  - card-restore-test
  - card-3-2-1
---

## Why this matters

Every storage decision is really a question about *what failure you are
buying protection from*. RAID, snapshots, replicas and backups protect
against different things, and people routinely buy one and believe they
got another.

There is a live example on the very server you are learning on, and it
is worth being blunt about it.

## Mental model

**Beginner mental model:** ask what each mechanism actually survives.

| Mechanism | Survives | Does **not** survive |
|---|---|---|
| RAID mirror | A disk dying | `rm -rf`, a bad migration, ransomware, the building |
| Snapshot | A bad change, if you notice in time | The array being destroyed |
| Replica | The primary host failing | A deletion — it replicates faithfully |
| Backup (off-site) | Nearly all of it | Only being tested by restoring |

**Technical reality:** RAID is an *availability* mechanism. It keeps a
machine serving while a disk is dead. It writes every deletion to both
disks instantly and correctly, because that is its job.

## Vocabulary

| Term | Plain meaning | Why you care |
|------|---------------|--------------|
| **RAID** | Several disks presented as one, with redundancy | Uptime, not history |
| **snapshot** | A point-in-time view of a filesystem or volume | Fast undo; same hardware |
| **backup** | An independent copy, elsewhere | The only thing that survives the machine |
| **restore test** | Actually restoring, and checking the result | The only proof a backup exists |
| **3-2-1** | 3 copies, 2 media, 1 off-site | The rule of thumb worth remembering |

## Deep explanation

**A copy on the same disk is not a backup.** It shares a fate with what
it protects: the disk, the filesystem, the machine, and the `rm -rf`
you typed one directory too high.

**This server's backups are on the disk they protect.**
`~/scripts/backup-databases.sh` writes nightly dumps of both PostgreSQL
databases to `~/backups` — on `/`, the same 77 GB filesystem holding the
databases. That is real protection against a dropped table or a bad
migration, and *none at all* against losing the instance. The script
itself says so in its output, every run.

**And silence is not success.** That script spent nine consecutive
nights discarding a perfectly good Task OS dump because of a bug in how
it validated the file, writing the failure into a log nobody was
reading. The only surviving backup was nine days old. Nothing alerted;
the machine was fine; the data was fine; the *safety net* was gone. A
backup you do not verify is a hypothesis.

**The only test that counts is a restore.** Not "the file exists". Not
"the script exited zero". Restore into a scratch database, count the
rows, look at the newest record's timestamp, then throw the scratch
database away. Do it on a calendar, not when you feel like it — because
the failure modes are all silent: an empty dump, a truncated one, a
correct dump of the wrong database, a dump you cannot decrypt because
the key was only on the machine that died.

**Retention is part of the design.** Keeping only last night's backup
means a corruption you notice on Wednesday has already overwritten
Monday's good copy. Keep a ladder — several dailies, a few weeklies, a
monthly — so there is somewhere to go back *to*.

## Brain Core connection

Brain Core's provenance chain is exactly the kind of data whose value is
cumulative and whose loss is unrecoverable — you cannot re-derive who
measured what, when. It needs off-site backups and a tested restore
before it holds anything anyone relies on, not after.

## Plex / home-server connection

Home servers are where "RAID is not a backup" is learned expensively. A
mirrored array full of irreplaceable photos, with no copy anywhere else,
survives a disk failure and does not survive a mistaken delete, a
lightning strike, or a controller writing garbage to both disks at once.
Media is often re-acquirable; family photos are not. Treat them
differently.

## Interactive example

Two commands on the real host, worth running when you next log in:

```
ls -la ~/backups/*/          # how recent is the newest file, really?
~/scripts/backup-databases.sh --dry-run
```

If the newest backup is older than you expected, you have just learned
something that was true whether or not you looked.

## Practice

No terminal exercise: this one is a policy you write, not a command you
run. The quiz checks that you can tell the mechanisms apart.

## Common mistake

> "It is backed up — there is a nightly job."

The job existing is not the claim that matters. The claims that matter
are: it ran last night, the output is a valid dump, it contains the data
you think it does, a copy is somewhere this machine cannot destroy, and
you have restored from it recently enough to believe it. Every one of
those has failed for somebody, quietly.

## Knowledge check

Quiz below.

## Summary

- RAID is availability, not history. It replicates your mistakes
  faithfully.
- A backup on the same disk protects against operator error only.
- 3-2-1: three copies, two kinds of media, one off-site.
- The only proof a backup works is a restore you actually performed.
- Failures here are silent by nature — assume nothing without checking.
