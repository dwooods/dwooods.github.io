---
title: "The Scan That Wouldn't Die: ClamAV on a NAS That Only Stays Awake 16 Hours a Day"
date: 2026-09-24
draft: true
tags: ["synology", "clamav", "docker", "self-hosted", "nas", "antivirus", "dsm"]
description: "Building a weekly ClamAV scan for a Synology DS918+ that has to finish before the NAS's nightly shutdown — a silent 100MB scan cap, an hour-long runaway scan killed mid-run, and 29 undocumented internal folders nobody warns you about."
summary: "My NAS goes to sleep at 11PM to save power, which meant my weekly virus scan had a hard deadline. Getting there meant discovering that ClamAV silently skips anything over 100MB, that Synology's own antivirus package doesn't reliably work, and that deleting one blanket exclude rule can turn a 3-minute scan into an hour-long hang nobody notices until it's too late."
---

<!-- TODO: add a featured image before publishing — a Portainer console screenshot showing the SCAN SUMMARY output, or a simple diagram of DSM Task Scheduler → docker exec → the clamav-scanner container's read-only volume mounts, would both work well here. -->

My Synology DS918+ shuts itself off every night at 11PM and doesn't wake back up until 7AM. That's a deliberate power-schedule setting, not a bug — there's no reason to keep a home NAS spinning while everyone's asleep. It also means every scheduled job on that box is working inside a roughly 16-hour window, and my weekly antivirus scan spent a long time not fitting inside it.

This is the story of getting a ClamAV scan, running in Docker, to actually complete — on schedule, unattended, inside that window — and everything that turned out to be in the way: a silent 100MB scan cap, a scan that ran for over an hour before I killed it, and a Synology folder structure that's apparently interesting enough to be almost completely undocumented anywhere public.

## Why I built this

The NAS holds our family's photos and movies — the actual "if this dies we lose it" stuff, not test data. So "eventually get around to scanning it" was never really on the table; I wanted a weekly scan that just runs, on its own, and tells me if something's wrong.

Synology ships two of its own antivirus options in Package Center, and I tried the obvious one first: **Antivirus Essential**, the free package. It stopped updating its virus definitions, with no way to force a manual refresh — which, it turns out, is a documented, known issue, not something specific to my setup. Synology has [its own knowledge-base article](https://kb.synology.com/en-us/DSM/tutorial/I_cannot_update_virus_definitions_in_Antivirus_Essential) titled almost exactly "I cannot update virus definitions in Antivirus Essential," and there's a [community thread](https://community.synology.com/enu/forum/1/post/189641) of other people hitting the same wall. A virus scanner that can't update its own signatures is a smoke detector with the battery pulled.

The other option, **Antivirus by McAfee**, is a genuinely different, separately-licensed product — full subscription, not the free one — and I wasn't going to pay an annual fee to scan a NAS I already own. (These two share enough branding that I spent longer than I'd like to admit being confused about which one was actually free. If you're evaluating this yourself: Essential is the free one, and it's also the one that stopped working for me.)

So: ClamAV, in Docker, driven by DSM's own Task Scheduler. Free, open-source, and — critically — something I could actually see inside of when it went wrong, instead of a GUI toggle that either works or doesn't tell you why.

## Architecture & tech stack

- **NAS**: Synology DS918+ — Celeron J3455, no GPU, DSM 7.x. Two volumes, `/volume1` and `/volume2`.
- **Scanner**: the official `clamav/clamav:latest` Docker image, running as a container named `clamav-scanner`, with both volumes mounted in **read-only** — the container can see everything, and can't write or delete anything, on purpose.
- **Management**: Portainer CE, for a browser-based container console. This mattered for a reason that's really about the next section: I never SSH into the NAS myself for this project, and I never let Claude touch DSM directly either. Portainer's web console gives a shell *inside the container*, scoped to those read-only mounts, without either of us ever holding actual DSM credentials.
- **Scheduling**: DSM's own Task Scheduler, running the `docker exec` command as a User-defined script every Friday at 11:00 AM Pacific — early enough in the ~16-hour window that even a slow run has room to finish before the 11PM shutdown.

### Tools & AI assist

The whole thing ran through **Claude Cowork**, in a single long-running conversation, the same pattern as the [Plex/Tailscale project](/posts/wagging-the-dog-tailscale-plex-vacation/) before it: no local repo, no code files, just a chat window and a browser session into the NAS.

Claude did the actual investigation work: building the exclude-list logic, diagnosing a stuck process by reading its open file descriptors, and driving the Portainer console to test commands. What Claude explicitly does **not** do, by a hard rule I set going in: log into DSM itself, under any circumstance. Every DSM Task Scheduler change — including the final production command this whole project was building toward — had to be typed in by me, by hand, in DSM's own UI, with Claude only ever verifying the result afterward through the container's read-only mount. That's not a minor detail; it's the actual shape of the division of labor on this project. Claude investigated, proposed, and verified. I held the one set of credentials that could actually change something.

Claude also got a few things wrong along the way, worth being honest about rather than editing out. Early on, I told it to skip the `video` and `video2` folders from the scan, and had to explicitly confirm that decision more than once before it stuck. When the browser session into Portainer dropped mid-verification (more on that below), Claude's first instinct was to just retry quietly — which is a reasonable instinct in general and the wrong one here, since a silently-retried browser session is exactly the kind of thing that should surface to a human, not get smoothed over. I told it so directly, and it changed behavior for the rest of the project.

## Key technical challenges

### The 100MB cap nobody tells you about

`clamscan`'s actual defaults — not documented anywhere obvious, only visible by dumping the running binary's real config with `clamconf` — are `MaxFileSize=100MB` and `MaxScanSize=400MB`. Any file over 100MB gets **silently marked clean**. Not flagged, not logged differently from an actually-clean file — just skipped, with the scan reporting success. On a NAS that stores home movies and full-disk backup images, that's most of the interesting content.

```
clamscan --infected --recursive \
  --max-filesize=2000M --max-scansize=4000M \
  ...
```

One gotcha inside the gotcha: `--max-filesize` has a hard internal ClamAV ceiling of 2GiB. Setting it higher doesn't error, it just prints a cosmetic warning on every single run. I set it to exactly `2000M` specifically to make that warning go away rather than stare at it in a weekly log forever.

### `--exclude-dir` doesn't mean what it sounds like it means

Three separate surprises here, each one a real footgun if you don't know about it going in:

It's a **directory-recursion filter, not a file filter** — a pattern that matches `@syslog-ng` as a directory does nothing to a loose file sitting at the volume root named `@syslog-ng.core.gz`. Synology drops a handful of crash-dump files exactly like that at the root of each volume, and every one of them gets scanned regardless of what you've excluded, because they're files, not directories.

It's also a **prefix match, not an exact match** — `--exclude-dir=^/scandir/Plex` matches both `/scandir/Plex` and `/scandir/PlexMediaServer`. Convenient when you want that; a real trap if you assume it only matches the literal name.

And there's **no way to un-exclude a subdirectory**. Once a broad pattern like `--exclude-dir=/@` matches a folder, there's no mechanism to carve out one subdirectory beneath it and scan just that — not even by passing that subdirectory as its own explicit target on the command line. The only fix is dropping the broad pattern entirely and enumerating every single folder you actually want excluded, one at a time. Which is exactly what caused the next problem.

### The scan that wouldn't die

I wanted to add DSM's own package-data folders to the scan scope — the folders behind Container Manager and everything else installed through Package Center — which meant retiring the blanket `--exclude-dir=/@` pattern that had been quietly catching every Synology-internal folder up to that point. I replaced it with a hand-typed list of the "obvious" `@`-prefixed folders, based on what I remembered seeing in earlier `ls` output.

A test run that should have taken about 200 seconds instead ran for **over an hour**, stuck in disk-sleep (`D`) state with no end in sight.

Claude diagnosed it by reading the stuck process's open file descriptors directly — `ls -la /proc/<pid>/fd` shows exactly which file a process has open right now, which is a much more honest answer than anything in a log file:

```
/proc/7192/fd/4 -> /scandir/@synologydrive/@sync/repo/4/...
```

`@synologydrive` — Synology Drive's internal sync chunk-store — had never made it onto the hand-typed exclude list. It wasn't on the "obvious" list because I'd never actually seen it; it had scrolled off-screen during an earlier terminal review, along with a handful of other capitalized folders (`@AntiVirus`, `@SynoDrive`, `@S2S`) that happened to sort below the lowercase ones I did remember.

I killed the process (`kill -9`) and had Claude run a full, unfiltered directory listing instead of trusting anyone's memory of one:

```bash
find /scandir -maxdepth 1 -type d -iname '@*' > /tmp/v1all.txt
```

That turned up **29** distinct `@`-prefixed folders on `/volume1` alone — not the roughly 15 either of us had assumed. The fix wasn't a smarter exclude pattern. It was refusing to hand-type a list a second time, and generating it programmatically instead:

```bash
EXCL=""
for d in $(cat /tmp/v1all.txt) $(cat /tmp/v2all.txt); do
  case "$d" in
    */@appdata|*/@appstore|*/@apphome|*/@appconf|*/@apptemp|*/@config_backup) ;;
    *) EXCL="$EXCL --exclude-dir=^$d";;
  esac
done
```

Six package folders stay in scope; the other 26 get excluded, generated from a real listing instead of a remembered one. The corrected scan finished clean in 53 minutes 55 seconds — 0 infected files, 58,775 files scanned across 8,800 directories. Two days later, the real DSM Task Scheduler job ran the same command unattended, on its actual Friday-11AM schedule, and matched it almost exactly: 53m54s, 0 infected, 58,778 files. First real confirmation the fix holds up without anyone watching it.

### A folder structure that's apparently a secret

Along the way this turned into an accidental audit of Synology's internal `@` folder taxonomy, which — as far as I could find — isn't documented anywhere public in this kind of detail. A few of the more interesting finds:

- `@synologydrive` (lowercase) and `@SynoDrive` (capitalized) are two **completely different** folders — Synology Drive's live sync data versus something else entirely. Case-sensitivity matters on the underlying filesystem, and it's very easy to assume you've seen a folder before when you've actually seen its differently-capitalized sibling.
- Package data isn't in one place. The six folders backing Container Manager and other installed packages exist on **both** volumes independently — 46MB worth on `/volume2`, and 3.6GB on `/volume1`, almost all of it `@appstore` holding full installed-package binaries (including, memorably, a bundled Node.js runtime for one of my installed packages).
- `@eaDir`, Synology's per-folder thumbnail cache and famous for being inode-heavy, was tiny in my case — 33 files, 232KB. Size isn't a reliable predictor of how expensive a folder is to scan; file *count* is, which is exactly what made `@appstore` the slow part later.

## Lessons learned & what's next

The generalizable version of this, for anyone who's never heard of ClamAV and never will: **when you retire a broad safety net, you have to replace it with a verified, complete list — not a remembered one.** The blanket `--exclude-dir=/@` pattern was doing its job by accident; it caught everything, including folders nobody had specifically thought about. The moment I replaced "everything" with "everything I can remember," the gap between those two things became an hour-long hang on a production job. That's not really a ClamAV lesson. It's true of firewall rules, permission allow-lists, feature flags — anywhere a blanket rule gets replaced with an enumerated one, the enumeration has to come from the system itself, not from anyone's memory of the system.

Two things are still genuinely open, not wrapped up neatly for this post:

**Per-folder timing audit.** The corrected scan takes 54 minutes, comfortably inside the window, but I don't yet know which included folder is actually driving that — `@appstore`'s file count is my prime suspect, but "prime suspect" isn't a measurement. The plan is to time each included folder individually, once, as a one-off audit rather than folding it into the weekly job, and decide from real numbers whether `@appstore` earns its place.

**Whether the failure alert actually works.** `clamscan` exits with code `1` when it finds an infected file, and DSM's Task Scheduler can notify only on abnormal termination — but I haven't actually confirmed DSM treats a `1` exit as abnormal, versus something else entirely. The honest way to find out is to drop a standard EICAR test file (a harmless, universally-recognized antivirus test string, not real malware) somewhere in scope and watch whether a real alert shows up. That test hasn't happened yet as of writing this. If you're building something similar and you get to that step before I do, I'd genuinely like to know what you find.

One more thing worth admitting, since undercutting my own competence seems to be a running theme on this blog: partway through this project, Claude gave me the corrected command and told me to go update it in DSM Task Scheduler myself. A few days later I asked "did the job run yesterday and complete," Claude asked whether I'd actually made the update, and I asked "what update" — genuinely having forgotten the conversation from days earlier. We went back and forth restating what needed to happen, and it turned out I'd already done it, before either of us had sorted out the confusion. Not exactly a seamless AI-orchestrated success story. Just two things — my memory and a chat log — briefly out of sync, resolved by checking the actual file on the NAS instead of trusting either one.

---

No GitHub repo to link here — like the Plex/Tailscale project, this was NAS configuration, not code, and the exclude list and Task Scheduler command above are the whole artifact. If you're fighting the same fight: check `clamconf` for your actual running defaults before you trust anything the docs say, and if you ever retire a blanket exclude pattern for a narrower one, generate the replacement list with `find`, not with whatever you remember scrolling past.

Every Friday at 11 in the morning, while nobody in the house knows or cares, the NAS spends 54 minutes checking that years of family photos aren't quietly carrying something they shouldn't. That's not a very exciting sentence to end a blog post on. It's kind of the point — boring is what it's supposed to feel like when it's actually working.
