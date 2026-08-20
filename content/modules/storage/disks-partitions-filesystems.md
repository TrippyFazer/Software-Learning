---
module: storage
lesson: disks-partitions-filesystems
title: "Disks, Partitions, Filesystems, Mounts"
difficulty: beginner
concepts:
  - block-device
  - partition
  - filesystem-format
  - mount-point
prerequisites:
  - linux/filesystem
quiz: storage/disks-partitions-filesystems
flashcards:
  - card-block-device
  - card-mount-point
  - card-partition-vs-filesystem
---

## Why this matters

In Module 1 you learned that everything on Linux lives in one tree
starting at `/`. That was true and deliberately incomplete. The tree is
an *illusion assembled at boot* out of separate physical things, and the
moment you add a second disk, resize a volume, or wonder why `/boot/efi`
shows up in `df`, the illusion stops being helpful.

## Mental model

**Beginner mental model:** four layers, each one built on the one below.

```
  /dev/nvme0n1        the DISK        — a slab of numbered blocks
        │
  /dev/nvme0n1p1      a PARTITION     — "blocks 2048 to the end are mine"
        │
      ext4            a FILESYSTEM    — structure written into those blocks:
        │                               directories, names, permissions
        /             a MOUNT POINT   — where that structure is grafted
                                        into the one visible tree
```

**Technical reality:** a **block device** is anything the kernel can
address in fixed-size blocks — a disk, a partition, a USB stick, a
network volume. It has no idea what a file is. A **partition** is a
declared range of blocks on a device. A **filesystem** is a data
structure *written into* those blocks that turns "block 419,206" into
"a file called `orders.csv`, owned by ubuntu, modified Tuesday". A
**mount point** is a directory where that filesystem's tree is attached
to the visible one.

The key consequence: **`/` and `/boot/efi` on your server are different
filesystems**, on different partitions, formatted differently (ext4 and
vfat). They look like one tree because they were mounted into one.

## Vocabulary

| Term | Plain meaning | Why you care |
|------|---------------|--------------|
| **block device** | A thing the kernel reads in fixed-size blocks | `/dev/nvme0n1` — knows nothing about files |
| **partition** | A declared range of blocks on a device | Why one disk can hold two filesystems |
| **filesystem** (format) | The structure that turns blocks into named files | ext4, vfat, xfs — a *format*, not a place |

> **The same word, twice.** Module 1 used "filesystem" for *the tree
> rooted at `/`*. Here it means *the on-disk format* — ext4, vfat. Both
> usages are standard and you will meet both, often in the same
> sentence: "the root filesystem is an ext4 filesystem." Read it as
> "the tree at `/` is stored using the ext4 format" and the ambiguity
> disappears.
| **mount point** | The directory a filesystem is attached at | `/`, `/boot/efi` |
| **`df`** | Report free space, per filesystem | The first command when something breaks |

## Deep explanation

**Read your own machine.** Three commands, three different questions:

```
lsblk     what physical devices and partitions exist?
mount     which filesystem is attached where, and how?
df -h     how full is each one?
```

`lsblk` on this server shows one 80 GB NVMe device, split into a 79 GB
ext4 partition mounted at `/` and a 99 MB vfat partition at `/boot/efi`.
That tiny vfat partition is not an oddity — UEFI firmware can only read
FAT, so the bootloader has to live somewhere the firmware understands,
before Linux exists to understand anything else.

**Mounting is grafting, and it hides.** Mount a filesystem at
`/mnt/data` and whatever was already in `/mnt/data` becomes invisible —
not deleted, just covered, and it reappears when you unmount. This is a
classic 2am confusion: files that "vanished" are usually underneath a
mount, or were written to the mount point *before* the disk was mounted
and are now hidden beneath it.

**A path belongs to exactly one filesystem — the longest matching
mount.** `/boot/efi/grub.cfg` is on the vfat partition, not on `/`, even
though `/boot/efi` sits inside `/`. That rule is why `df /some/path`
tells you which filesystem a path actually lives on, and why a file can
fail to move with "Invalid cross-device link" when it would have to
cross that boundary.

**Nothing here is about Docker, and everything here is under it.** A
Docker named volume is a directory on some filesystem —
`/var/lib/docker/volumes/<name>/_data`. On your server that is on `/`.
So "the volume is full" and "the disk is full" are the same sentence,
and Task OS's database, this Lab's database, every image layer and every
backup are all competing for the same 77 GB.

## Brain Core connection

Brain Core will hold documents, embeddings and provenance records —
things that grow monotonically. Knowing which filesystem they land on,
and how big it is, is the difference between planned growth and an
outage. "Where does this data physically live" is a question worth
answering before the first write, not after the first alarm.

## Plex / home-server connection

This is where a home server really diverges: a media box has a small
fast disk for the OS and one or more big slow disks for media, mounted
somewhere like `/mnt/media`. Plex's *config* belongs on the fast disk;
the *films* belong on the big one. Getting that mapping wrong is how
people end up with a full boot disk and a nearly empty media array.

## Interactive example

In the exercise, run `lsblk`, then `mount`, then `df -h`, and match the
same partition across all three outputs. Being able to say "this device,
this partition, this filesystem type, this mount point, this much free"
in one breath is the whole lesson.

## Practice

Covered by the next lesson's exercise, which starts from `df` and works
downward.

## Common mistake

> Writing files to a mount point before the disk is mounted.

The directory exists, so the write succeeds — onto the *root*
filesystem, in the space beneath where the real disk will attach. Then
the disk mounts, the files vanish, and `/` is mysteriously fuller than
it should be. `df` on the path is what reveals it: the path reports the
root filesystem, not the disk you expected.

## Knowledge check

Quiz below.

## Summary

- Disk → partition → filesystem → mount point. Four layers, each one
  meaningless without the one below.
- The single tree under `/` is assembled at boot from separate
  filesystems.
- A path belongs to the **longest matching mount**, which is what `df
  <path>` reports.
- Mounting hides whatever was already in the directory; it does not
  delete it.
- Docker volumes are directories on an ordinary filesystem — "volume
  full" and "disk full" are the same problem.
