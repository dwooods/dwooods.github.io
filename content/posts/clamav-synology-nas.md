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

The NAS holds our music, photos, backups, videos, movies and TV shows. It's the household's everything-drive, so keeping it locked down, limited-access and free of anything nasty matters more to me than it would on a throwaway hobby server. I hadn't run a virus scan on it in a long while, and that had been bugging me.

Not because I was worried. That's exactly how you end up not scanning for a year. The realistic threat isn't a stranger; it's me installing something I thought was trustworthy and finding out otherwise, on the one box the whole house depends on.

That shaped what the scan is actually for. Photos reach the NAS through Synology's own apps, and music and movies are files I play, not run. What I needed watched was the other category: system files, installed packages, and anything that executes. So the goal was never "scan every byte." It was "scan where software lives and runs, and skip where media just gets played."

Synology ships two of its own antivirus options in Package Center, and I tried the obvious one first: **Antivirus Essential**, the free package. It stopped updating its virus definitions, with no way to force a manual refresh — which, it turns out, is a documented, known issue, not something specific to my setup. Synology has [its own knowledge-base article](https://kb.synology.com/en-us/DSM/tutorial/I_cannot_update_virus_definitions_in_Antivirus_Essential) titled almost exactly "I cannot update virus definitions in Antivirus Essential," and there's a [community thread](https://community.synology.com/enu/forum/1/post/189641) of other people hitting the same wall. A virus scanner that can't update its own signatures is a smoke detector with the battery pulled.

I assumed the fix would be trivial: update the virus dictionary. I couldn't even do that by hand.

I didn't give up on it quickly, either. Here's what the troubleshooting looked like, in case you're staring at the same error:

- The package bundles **ClamAV 0.103.8**, a version the ClamAV project has long since retired. As far as I can tell, that's the root of the problem: when I enabled SSH and ran `freshclam` by hand, the signature servers answered with HTTP 429 and 403 errors and a cool-down period, rather than a database.
- Downloading the `.cvd` signature files manually and uploading them through DSM didn't work either. The download links sit behind Cloudflare, and what I ended up with was presumably an HTML page rather than a database, which DSM rejects with "Incorrect file format." Which is fair. It isn't a signature file.
- Fixing DNS and NTP on the NAS, the usual suspects for update failures, changed nothing.

The other option, **Antivirus by McAfee**, is a genuinely different, separately-licensed product — full subscription, not the free one — and I wasn't going to pay an annual fee to scan a NAS I already own. (These two share enough branding that I spent longer than I'd like to admit being confused about which one was actually free. If you're evaluating this yourself: Essential is the free one, and it's also the one that stopped working for me.)

What stuck with me is that ClamAV, the engine underneath, is free and runs on Windows, macOS and Linux. Getting current signatures onto a Synology shouldn't be harder than getting them onto a Raspberry Pi. I don't know why Essential stopped updating and I haven't heard Synology's side, so that's a question I still need to send them.

In the meantime, my options were fighting a bundled scanner I couldn't see inside of, or running a current ClamAV myself. So: ClamAV, in Docker, driven by DSM's own Task Scheduler. Free, open-source, and — critically — something I could actually see inside of when it went wrong, instead of a GUI toggle that either works or doesn't tell you why.

Now the part that surprised me, and the reason I'm writing any of this down: **I had never installed or run Docker before this project.** Not "rusty." Never. And I went in expecting the free route to be *less* technical than the paid one: pick a tool, point it at my folders, set a schedule, done. What I got was a crash course in containers, read-only mounts, and a management UI I had to install just to see what was going on inside the thing, followed by a long stretch of installing, testing, and validating before any scan result meant anything. I also had no idea how to set up a recurring job, what to scan, how to check whether it ran, or how to keep it updated, because none of that is a normal non-engineer way to run software. If you're picturing "set up a virus scan" as an afternoon of clicking through a wizard, budget for a lot more than that. The free version costs you in knowledge instead of dollars.

## Architecture & tech stack

- **NAS**: Synology DS918+ — Celeron J3455, no GPU, DSM 7.x. Two volumes, `/volume1` and `/volume2`.
- **Scanner**: the official `clamav/clamav:latest` Docker image, running as a container named `clamav-scanner`, with both volumes mounted in **read-only** — the container can see everything, and can't write or delete anything, on purpose.
- **Management**: Portainer CE, installed alongside Synology's own Docker package because the Synology Docker GUI kept getting in my way. (Gemini suggested it. Yes, that's yet another container just to manage the first container.) The folder picker for volume mounts drills into subfolders and wouldn't let me select a top-level shared folder to mount, and my version had no Project (compose) tab to define the container as a file. I got as far as a workaround, a root Task Scheduler entry running a raw `docker run ... -v /volume1:/scandir:ro`, before deciding that typing mounts into a scheduler box wasn't a plan. Portainer let me type the host paths directly, define the container as a Stack, read its logs, and open a console inside it. That last one turned out to be the backbone of the whole project. It mattered for a reason that's really about the next section: I never let Claude touch DSM directly, and Portainer's web console gives a shell *inside the container*, scoped to those read-only mounts, without either of us ever holding actual DSM credentials.
- **Scheduling**: DSM's own Task Scheduler, running the `docker exec` command as a User-defined script every Friday at 11:00 AM Pacific — early enough in the ~16-hour window that even a slow run has room to finish before the 11PM shutdown.

### Tools & AI assist

Two AI tools were involved. **Gemini** came first: it walked me through the Antivirus Essential dead end and is the one that suggested Portainer when Synology's Docker UI ran out of road. Then most of the build ran through **Claude Cowork**, in a single long-running conversation, the same pattern as the [Plex/Tailscale project](/posts/wagging-the-dog-tailscale-plex-vacation/) before it: no local repo, no code files, just a chat window and a browser session into the NAS. Since Docker was brand new to me, that conversation doubled as the tutorial.

Claude did the actual investigation work: building the exclude-list logic, diagnosing a stuck process by reading its open file descriptors, and driving the Portainer console to test commands. What Claude explicitly does **not** do, by a hard rule I set going in: log into DSM itself, under any circumstance. Every DSM Task Scheduler change — including the final production command this whole project was building toward — had to be typed in by me, by hand, in DSM's own UI, with Claude only ever verifying the result afterward through the container's read-only mount. That's not a minor detail; it's the actual shape of the division of labor on this project. Claude investigated, proposed, and verified. I held the one set of credentials that could actually change something.

Claude also got a few things wrong along the way, worth being honest about rather than editing out. Early on, I told it to skip the `video` and `video2` folders from the scan, and had to explicitly confirm that decision more than once before it stuck. When the browser session into Portainer dropped mid-verification, Claude's first instinct was to just retry quietly — which is a reasonable instinct in general and the wrong one here, since a silently-retried browser session is exactly the kind of thing that should surface to a human, not get smoothed over. I told it so directly, and it changed behavior for the rest of the project.

## Key technical challenges

### The job that kept getting killed at bedtime

The NAS powers off at 11PM, and an early version of the job was still running when it did. The shutdown stopped it. Every day. Nothing told me: the task didn't fail loudly, there just wasn't a finished result, and I only found out by digging into why it kept stopping.
<!-- TODO (David): how long did the early full scan run, how many days before you noticed, and where did you find the cause? A real number here is what makes the 16-hour window feel earned. -->

That's when the 16-hour window stopped being trivia and became a design constraint: the scan has to *finish*, not just start. It's also why I set up email notifications in Task Scheduler. A silent failure is the one thing a security job can't afford, and checking a container's logs by hand every week was never going to happen.

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

I wanted to add DSM's own package-data folders to the scan scope — the folders behind Docker and everything else installed through Package Center — which meant retiring the blanket `--exclude-dir=/@` pattern that had been quietly catching every Synology-internal folder up to that point. I replaced it with a hand-typed list of the "obvious" `@`-prefixed folders, based on what I remembered seeing in earlier `ls` output.

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

Six package folders stay in scope on each volume; everything else with an `@` gets excluded, generated from a real listing instead of a remembered one. The corrected scan finished clean in 53 minutes 55 seconds — 0 infected files, 58,775 files scanned across 8,800 directories. Two days later, the real DSM Task Scheduler job ran the same command unattended, on its actual Friday-11AM schedule, and matched it almost exactly: 53m54s, 0 infected, 58,778 files. First real confirmation the fix holds up without anyone watching it.

### A folder structure that's apparently a secret

Along the way this turned into an accidental audit of Synology's internal `@` folder taxonomy, which — as far as I could find — isn't documented anywhere public in this kind of detail. A few of the more interesting finds:

- `@synologydrive` (lowercase) and `@SynoDrive` (capitalized) are two **completely different** folders — Synology Drive's live sync data versus something else entirely. Case-sensitivity matters on the underlying filesystem, and it's very easy to assume you've seen a folder before when you've actually seen its differently-capitalized sibling.
- Package data isn't in one place. The six folders backing Docker and other installed packages exist on **both** volumes independently — 46MB worth on `/volume2`, and 3.6GB on `/volume1`, almost all of it `@appstore` holding full installed-package binaries (including, memorably, a bundled Node.js runtime for one of my installed packages).
- `@eaDir`, Synology's per-folder thumbnail cache and famous for being inode-heavy, was tiny in my case — 33 files, 232KB. Size isn't a reliable predictor of how expensive a folder is to scan; file *count* is, which is exactly what made `@appstore` the slow part later.

## Keeping it running: signatures update themselves, software doesn't

A weekly scan is only as good as the signatures it's scanning with. Once the production job was stable, I asked the question I should have asked on day one: what actually keeps this thing current? The answer is two different answers, and the difference matters.

**The signatures update on their own.** The official `clamav/clamav` image starts a `freshclam` daemon inside the container, and `clamscan` reads the signature database fresh from disk on every run, so Friday's scan always uses whatever freshclam last downloaded. I didn't want to just trust the docs, so I checked from the container console:

```sh
clamscan --version                       # version + signature DB number and date
ps | grep freshclam                      # is the daemon actually running?
ls -la /var/lib/clamav                   # timestamps on the database files
tail -20 /var/log/clamav/freshclam.log   # look for "OUTDATED" or errors
```

The version line came back `ClamAV 1.5.4/28137/Mon Sep 28 06:24:12 2026`: current software, and a signature database built that same morning. The process list showed the daemon running with `--checks=1`, which means one update check per day. That sounds too slow until you remember the 16-hour NAS. It boots at 7AM, freshclam checks a few minutes later, and the 11AM scan runs on signatures that are at most four hours old. The nightly shutdown accidentally lines up with the update schedule, which is the closest thing to good luck this project has had.

**The software does not update itself.** The image refreshes signatures only, never the ClamAV binary. The `latest` tag isn't a subscription, it's a snapshot of whatever was current the day I pulled. Upgrading means pulling a newer image and recreating the container. ClamAV's own docs recommend pinning a feature-release tag like `clamav/clamav:1.5` instead of `latest`, so a re-pull gives you patches without silently jumping you to a new feature release.

Neglecting this isn't free, either. ClamAV eventually blocks signature downloads for end-of-life versions (it did exactly that to 0.103), so a container nobody ever touches will one day just stop getting updates. My upkeep plan is a quarterly check, or any time this comes back with a hit:

```sh
grep -i outdated /var/log/clamav/freshclam.log
```

Two things in that output looked alarming and weren't. The freshclam log ends every update with `WARNING: Clamd was NOT notified`, which only means freshclam couldn't find the clamd daemon to tell it to reload. `clamscan` doesn't use clamd, so it's irrelevant here (and if clamd isn't running at all, that's over a gigabyte of RAM a small NAS never has to spend). And the signature files turned out to live in the container's own writable layer, not a volume: only `daily.cld` was rewritten that morning, while `main.cvd` and `bytecode.cvd` still carried the date of the image pull.

That last detail has a practical consequence. Recreating the container wipes the writable layer, so the next recreate should add a named volume at `/var/lib/clamav`, and it's worth confirming the scheduled command doesn't reference any file *inside* the container (like the `/tmp` lists I generated while troubleshooting) before pulling the trigger.

## Lessons learned & what's next

The generalizable version of this, for anyone who's never heard of ClamAV and never will: **when you retire a broad safety net, you have to replace it with a verified, complete list — not a remembered one.** The blanket `--exclude-dir=/@` pattern was doing its job by accident; it caught everything, including folders nobody had specifically thought about. The moment I replaced "everything" with "everything I can remember," the gap between those two things became an hour-long hang on a production job. That's not really a ClamAV lesson. It's true of firewall rules, permission allow-lists, feature flags — anywhere a blanket rule gets replaced with an enumerated one, the enumeration has to come from the system itself, not from anyone's memory of the system.

The other lesson is about where the effort actually went. Getting ClamAV to run was the easy half. The hard half was deciding **what to scan**, and it took repeated rounds of run, measure, and adjust to land on a folder set that balanced coverage against run time. Scan everything and the multi-terabyte media and backup folders blow straight through the 16-hour window; scan too little and the weekly job is theater. Where I ended up follows the rule from the top of this post: the Synology package folders, documents, and Drive data are in, while the video folders, the backup folder, and the full home directories are out. Some of that is a judgment call about risk (photos only arrive through Synology's own apps, and movies and music get played, not executed) and some of it is simply that they don't fit. That combination finishes in about 54 minutes, and it got there through actual full runs rather than guesswork (a per-folder breakdown is still on the to-do list below). If you build this, expect the folder list to be the real project.

It's also a choice, not a guarantee. Nothing scans the folders I left out, so anything that lands there by another route (a PC saving over SMB, a download) goes unchecked. I'm comfortable with that trade for now, but it's worth saying out loud.
<!-- TODO (David): confirm the Docker image/container storage folder (@docker on Synology, I believe) is actually in scope. It's where the software you installed via containers runs, and my exclude loop only keeps the six @app* folders. Check in the Portainer console: ls -d /scandir/@docker* /scandir/docker* -->

Two things are still genuinely open, not wrapped up neatly for this post:

**Per-folder timing audit.** The corrected scan takes 54 minutes, comfortably inside the window, but I don't yet know which included folder is actually driving that — `@appstore`'s file count is my prime suspect, but "prime suspect" isn't a measurement. The plan is to time each included folder individually, once, as a one-off audit rather than folding it into the weekly job, and decide from real numbers whether `@appstore` earns its place.

**Whether the failure alert actually works.** `clamscan` exits with code `1` when it finds an infected file, and DSM's Task Scheduler can notify only on abnormal termination — but I haven't actually confirmed DSM treats a `1` exit as abnormal, versus something else entirely. The honest way to find out is to drop a standard EICAR test file (a harmless, universally-recognized antivirus test string, not real malware) somewhere in scope and watch whether a real alert shows up. That test hasn't happened yet as of writing this. If you're building something similar and you get to that step before I do, I'd genuinely like to know what you find.

One more thing worth admitting, since undercutting my own competence seems to be a running theme on this blog: partway through this project, Claude gave me the corrected command and told me to go update it in DSM Task Scheduler myself. A few days later I asked "did the job run yesterday and complete," Claude asked whether I'd actually made the update, and I asked "what update" — genuinely having forgotten the conversation from days earlier. We went back and forth restating what needed to happen, and it turned out I'd already done it, before either of us had sorted out the confusion. Not exactly a seamless AI-orchestrated success story. Just two things — my memory and a chat log — briefly out of sync, resolved by checking the actual file on the NAS instead of trusting either one.

---

No GitHub repo to link here — like the Plex/Tailscale project, this was NAS configuration, not code, and the exclude list and Task Scheduler command above are the whole artifact. If you're fighting the same fight: check `clamconf` for your actual running defaults before you trust anything the docs say, and if you ever retire a blanket exclude pattern for a narrower one, generate the replacement list with `find`, not with whatever you remember scrolling past.

Every Friday at 11 in the morning, while nobody in the house knows or cares, the NAS spends 54 minutes checking the places where its own software runs, so the family's photos, music and movies can just sit there being played. That's not a very exciting sentence to end a blog post on. It's kind of the point — boring is what it's supposed to feel like when it's actually working.
