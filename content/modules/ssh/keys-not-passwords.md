---
module: ssh
lesson: keys-not-passwords
title: "Keys, Not Passwords"
difficulty: beginner
concepts:
  - public-key
  - private-key
  - authorized-keys
  - known-hosts
prerequisites:
  - ssh/what-is-ssh
  - linux/users-and-permissions
quiz: ssh/keys-not-passwords
exercise: ssh/inspect-dot-ssh
flashcards:
  - card-keypair
  - card-authorized-keys
  - card-known-hosts
  - card-key-permissions
---

## Why this matters

Password logins on an internet-facing server lose to patient robots
eventually. Key authentication is both more secure and more convenient —
and it's what your Lightsail host uses from day one. But it only stops
being magic when you know which file is which, which one is secret, and
which machine holds what.

## Mental model

**Beginner mental model:** a key pair is a matched set — a **public key**
you can hand out freely (a lock you give away) and a **private key** that
never leaves your machine (the only key that opens that lock). The server
holds your lock; you hold your key; login is proving you hold it —
without ever sending it.

The biomedical version: the public key is like an antibody's published
*binding profile* — anyone can know it. The private key is the actual
molecule. Publishing the profile doesn't let anyone synthesize the
molecule; deriving the private key from the public one is the
computationally infeasible step that the whole scheme rests on.

**Technical reality:** asymmetric cryptography (Ed25519 today). At login
the server sends a challenge; your client *signs* it with the private
key; the server verifies the signature against the stored public key. The
private key is never transmitted — there is nothing to intercept.

## Vocabulary

| Term | Plain meaning | Why you care |
|------|---------------|--------------|
| **public key** | The shareable half; goes ON servers | What you paste into Lightsail |
| **private key** | The secret half; stays on YOUR machine, never shared, never copied casually | Whoever holds it *is* you |
| **authorized_keys** | Server-side file listing public keys allowed to log in as that user | How the server knows your lock |
| **known_hosts** | Client-side file remembering each server's fingerprint | How your machine detects impostor servers |
| **passphrase** | Optional encryption on the private key file itself | A stolen key file alone isn't enough |

## Deep explanation

**Where each file lives.** This is the part worth over-learning:

```
YOUR machine (client)                    THE SERVER
~/.ssh/id_ed25519         private key    ~/.ssh/authorized_keys
~/.ssh/id_ed25519.pub     public key         └ contains your PUBLIC key
~/.ssh/known_hosts        server fingerprints
```

`ssh-keygen` creates the pair on your machine. You copy the *.pub*
contents into the server's `authorized_keys` (or paste it into
Lightsail's console before the instance exists). The private key never
moves. One key pair can open many servers; many people's public keys can
sit in one `authorized_keys`.

**known_hosts is the other direction.** First connection: the client
records the *server's* fingerprint. Every later connection checks it. The
scary `REMOTE HOST IDENTIFICATION HAS CHANGED` warning means "this
machine isn't presenting the identity I remember" — usually a rebuilt
server, occasionally something worth stopping for.

**Permissions are enforced, not suggested.** SSH refuses to use a
private key that other users could read: `~/.ssh` must be `700`, private
keys `600`. This is Module 1's permission system doing real security
work — and the error message (`UNPROTECTED PRIVATE KEY FILE`) is a
rite of passage. The exercise below reproduces it.

**Why keys, concretely.** Passwords can be guessed at scale (port 22's
background radiation), reused across sites, and phished. A key can't be
brute-forced meaningfully, exists nowhere but your disk, and — with a
passphrase — is useless even if the file leaks. That's why hardening
step one on any new server is: keys work → disable password login
(`PasswordAuthentication no`, as docs/DEPLOYMENT.md does).

## Brain Core connection

Beyond logging into hosts: *deploy keys* let CI systems pull Brain
Core's repo; your `git push` to GitHub authenticates with exactly this
mechanism. When an AI tool says "add this to authorized_keys" or
generates deployment automation, you now know precisely which side of
the trust relationship it's touching — and which file must never appear
in a repo or a chat log.

## Plex / home-server connection

The closet server: your laptop's public key goes in its
`authorized_keys` once, and forever after `ssh server` just works —
password prompts gone. Add your desktop's key too: `authorized_keys` is
a list.

## Interactive example

The exercise below puts you in a home directory with a `.ssh` folder in
a realistic-but-wrong state. (Everything in it is placeholder text — no
real key material ever appears in this Lab.)

## Practice

Mission: **Inspect ~/.ssh** — explore the directory, identify each file's
role, and fix the classic permission problem you'll find there.

## Common mistake

> Pasting a private key into a chat, a repo, or a server's
> authorized_keys "to make it work."

The private key never travels. If it has ever been pasted anywhere —
including to an AI assistant — treat it as burned: generate a new pair,
update `authorized_keys`, delete the old one. (Note the asymmetry: the
*.pub* file is genuinely public; sharing it is the intended workflow.
The naming is your safety rail — trust it.)

## Knowledge check

Quiz below.

## Summary

- Key pair: public = shareable lock (goes on servers), private = the key
  (never leaves your machine, never transmitted — logins are signatures).
- `authorized_keys` (server) lists who may enter; `known_hosts` (client)
  remembers which servers are themselves.
- SSH enforces permissions: `~/.ssh` 700, private keys 600 — Module 1 in
  action.
- Keys beat passwords against scanning, reuse, and phishing; disable
  password login once keys work.
- A private key that has ever been shared is burned — rotate it.
