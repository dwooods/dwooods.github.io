---
title: "The Scan That Wouldn't Die: ClamAV on a NAS That Only Stays Awake 16 Hours a Day"
date: 2026-09-24
draft: true
tags: ["synology", "clamav", "docker", "self-hosted", "nas", "antivirus", "dsm"]
description: "I had never used Docker. With AI help I built a scheduled ClamAV virus scan on a Synology NAS that has to finish before its nightly shutdown, and learned Docker, ClamAV, and where the AI needed checking along the way."
summary: "I had never used Docker. This is how I used AI to learn it well enough to run a ClamAV virus scan on my Synology NAS, which goes to sleep at 11PM and gives every scan a hard deadline. Along the way: a silent 100MB scan cap, a scan that hung for an hour, and a few places where the AI needed checking."
featuredImage: "/images/hero-clamav-nas.jpeg"
featuredImagePreview: "/images/hero-clamav-nas.jpeg"
---

My Synology DS918+ shuts itself off every night at 11PM and doesn't wake back up until 7AM. That's a deliberate power-schedule setting, not a bug — there's no reason to keep a home NAS spinning while everyone's asleep. It also means every scheduled job on that box is working inside a roughly 16-hour window, and my antivirus scan spent a long time not fitting inside it.

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

{{< image src="/images/clamav-logo.png" alt="ClamAV logo" width="150px" >}}

What stuck with me is that [ClamAV](https://www.clamav.net/), the engine underneath, is free and runs on Windows, macOS and Linux. Getting current signatures onto a Synology shouldn't be harder than getting them onto a Raspberry Pi. I don't know why Essential stopped updating and I haven't heard Synology's side, so that's a question I still need to send them.

In the meantime, my options were fighting a bundled scanner I couldn't see inside of, or running a current ClamAV myself. So: ClamAV, in Docker, driven by DSM's own Task Scheduler. Free, open-source, and — critically — something I could actually see inside of when it went wrong, instead of a GUI toggle that either works or doesn't tell you why.

Now the part that surprised me, and the reason I'm writing any of this down: **I had never installed or run Docker before this project.** Not "rusty." Never. I went in expecting the free route to be *less* technical than the paid one, and got a crash course instead: containers, read-only mounts, a management UI, and a long stretch of installing and validating before any scan result meant anything. I also had no idea how to set up a recurring job, what to scan, how to check it ran, or how to keep it updated. The free version costs you in knowledge instead of dollars, and it turned out to be a good way to learn, which is what the next section is about.

## Docker, for people who think it's for other engineers

{{< image src="/images/docker-logo.png" alt="Docker logo" width="150px" >}}

I used [Docker](https://www.docker.com/) for the first time on my NAS to run ClamAV and Portainer. I had always thought Docker was something engineers used to package and run code, but it turns out to be useful for something much simpler: running software your device doesn't natively support. Docker runs applications in containers, which are isolated environments with the application and everything it needs packaged together. You start with an image, a packaged blueprint for the software, and Docker uses it to create a running container. In my case the NAS's built-in antivirus had stopped updating, so instead of installing a scanner into the NAS operating system, I ran a current ClamAV in its own container, and did the same with Portainer to manage it. Docker also gives you tools to manage containers: start and stop them, check their status, read logs, and open a console inside the software. Data that has to survive a restart can live outside the container in a volume. (Foreshadowing: I didn't put my virus signatures in one. More on that below.) I still don't fully understand what Docker is doing under the hood, and I definitely needed Claude to walk me through the setup, but I understand the practical value: a relatively clean, isolated way to run software on my own hardware that otherwise wouldn't be available.

Here's the scale of what I actually set up, so it looks less intimidating: one official image, `clamav/clamav`; my two NAS volumes mounted **read-only**, so the scanner can look at everything and change nothing; a name; and a restart policy so it comes back when the NAS boots at 7AM. No Dockerfile, no published ports. The scan itself is a single `docker exec` command that Synology's Task Scheduler runs on a schedule. One thing to know if you copy this: the mounts cover both whole volumes, so what actually gets scanned is decided by the paths and excludes in that command, not by the container.

![Synology's own Docker screen, showing the two containers I run: clamav-scanner and portainer](/images/synology-docker-containers-running.png)

## ClamAV, for people who think antivirus is an app

I didn't know ClamAV existed until Synology's own scanner stopped updating, I couldn't get it to refresh manually, and I wasn't going to pay for McAfee. That's when we pivoted. I went in expecting a GitHub repo from some stranger. It isn't. The [ClamAV docs](https://docs.clamav.net/) say it's brought to you by Cisco Systems, and there's real documentation, a [community project ecosystem](https://docs.clamav.net/manual/Installing/Community-projects.html), an updated signature database, and versions for Windows, macOS and Linux. It was also easy to install and run. The container image is about 240 MB and there's no big service to babysit. (It does hold its virus signatures in memory, so it isn't light on RAM. When I looked, the NAS showed a little over 2 GB in use.)

What I didn't expect is that it isn't an app. The docs call it an open-source anti-virus toolkit, and in practice that's a small set of separate command-line pieces. `clamscan` scans on demand and exits, `clamd` is a background daemon that keeps the signatures loaded in memory, and `freshclam` handles signature updates. In my container `freshclam` runs as a daemon that checks once a day, `clamd` is running (I confirmed it with `ps`), and my scheduled job calls `clamscan`. There's no green checkmark. There's an exit code.

Installing it was the easy part. The hard part was the setup around it: the scripts, what to run, what to exclude, and when. I leaned on Claude for most of that. The docs say it was designed especially for scanning email on mail gateways, which explains why it has plenty of users doing things I haven't thought of. I'm still not sure how else I'd use it.

My PC already has Windows Defender, which should cover most of what I need there. Yet when I tried ClamAV on the PC, it flagged a file in my Downloads folder that Defender never did. I still don't know whether that's a real problem or a false positive, which is its own lesson about getting a second opinion.

Two limits worth knowing before you trust it. The docs themselves say ClamAV isn't a traditional anti-virus or endpoint security suite. It only recognizes known malware, so a clean scan means "nothing matched," not "nothing's there." And as I read the docs, its real-time scanning (a component called ClamOnAcc) is a Linux feature that needs clamd, and I don't use it. Mine is a scheduled scan, twice a week, nothing more.

## Architecture & tech stack

- **NAS**: Synology DS918+ — Celeron J3455, no GPU, DSM 7.x. Two volumes, `/volume1` and `/volume2`.
- **Scanner**: the official `clamav/clamav:latest` Docker image, running as a container named `clamav-scanner`, with both volumes mounted in **read-only** — the container can see everything, and can't write or delete anything, on purpose.
- **Management**: Portainer CE, installed alongside Synology's own Docker package because the Synology Docker GUI kept getting in my way. (Gemini suggested it. Yes, that's yet another container just to manage the first container.) The folder picker for volume mounts drills into subfolders and wouldn't let me select a top-level shared folder to mount, and my version had no Project (compose) tab to define the container as a file. I got as far as a workaround, a root Task Scheduler entry running a raw `docker run ... -v /volume1:/scandir:ro`, before deciding that typing mounts into a scheduler box wasn't a plan. Portainer let me type the host paths directly, create the container from a form (Containers > Add container), read its logs, and open a console inside it. That last one turned out to be the backbone of the whole project. It mattered for a reason that's really about the next section: I never let Claude touch DSM directly, and Portainer's web console gives a shell *inside the container*, scoped to those read-only mounts, without either of us ever holding actual DSM credentials.
- **Scheduling**: DSM's own Task Scheduler, running the `docker exec` command as a User-defined script every Monday and Friday at 11:00 AM Pacific — early enough in the ~16-hour window that even a slow run has room to finish before the 11PM shutdown.

### Tools & AI assist

Two AI tools were involved. **Gemini** came first: it walked me through the Antivirus Essential dead end and is the one that suggested Portainer when Synology's Docker UI ran out of road. Then most of the build ran through **Claude Cowork**, in a single long-running conversation, the same pattern as the [Plex/Tailscale project](/posts/wagging-the-dog-tailscale-plex-vacation/) before it: no local repo, no code files, just a chat window and a browser session into the NAS. Since Docker was brand new to me, that conversation doubled as the tutorial.

Claude did the actual investigation work: building the exclude-list logic, diagnosing a stuck process by reading its open file descriptors, and driving the Portainer console to test commands. What Claude explicitly does **not** do, by a hard rule I set going in: log into DSM itself, under any circumstance. Every DSM Task Scheduler change — including the final production command this whole project was building toward — had to be typed in by me, by hand, in DSM's own UI, with Claude only ever verifying the result afterward through the container's read-only mount. That's not a minor detail; it's the actual shape of the division of labor on this project. Claude investigated, proposed, and verified. I held the one set of credentials that could actually change something.

Claude also got a few things wrong along the way, worth being honest about rather than editing out. Early on, I told it to skip the `video` and `video2` folders from the scan, and had to explicitly confirm that decision more than once before it stuck. When the browser session into Portainer dropped mid-verification, Claude's first instinct was to just retry quietly — which is a reasonable instinct in general and the wrong one here, since a silently-retried browser session is exactly the kind of thing that should surface to a human, not get smoothed over. I told it so directly, and it changed behavior for the rest of the project.

The hero image is AI-made too. I asked Claude for an image prompt, ran it in Gemini's Nano Banana image model, and needed a second round because the first version cut the "SOS" off the edge of the monitor. The fluffy plush viruses are the only part of this project that turned out exactly as planned.

## Key technical challenges

### The job that kept getting killed at bedtime

My first version scanned everything. It ran all day, the NAS went down for the night, and the scan never finished. Nothing told me: the task didn't fail loudly, there just wasn't a finished result, and I only found out by digging into why the job had stopped each day.

Scanning literally everything, I assume, isn't how a virus scanner is normally used. Real antivirus tools skip what doesn't matter, and I hadn't told mine what didn't matter. It also wasn't only about the shutdown. A scan grinding through the whole NAS all day would have been dragging it down right when the rest of us use it in the evening.

So the target changed. It wasn't "scan everything," it was "finish inside a window that ends before the NAS goes to bed and doesn't get in the household's way later in the day." That's when the 16-hour window stopped being trivia and became a design constraint: the scan has to *finish*, not just start. It's also why I turned on email notifications in Task Scheduler (how that went is below). A silent failure is the one thing a security job can't afford, and checking a container's logs by hand every week was never going to happen.

### The 100MB cap nobody tells you about

`clamscan`'s actual defaults — not documented anywhere obvious, only visible by dumping the running binary's real config with `clamconf` — are `MaxFileSize=100MB` and `MaxScanSize=400MB`. Any file over 100MB gets **silently marked clean**. Not flagged, not logged differently from an actually-clean file — just skipped, with the scan reporting success. On a NAS that stores home movies and full-disk backup images, that's most of the interesting content.

```
clamscan --infected --recursive \
  --max-filesize=2000M --max-scansize=4000M \
  ...
```

One gotcha inside the gotcha: `--max-filesize` has a hard internal ClamAV ceiling of 2GiB. Setting it higher doesn't error, it just prints a cosmetic warning on every single run. I set it to exactly `2000M` specifically to make that warning go away rather than stare at it in the scan log forever.

### `--exclude-dir` doesn't mean what it sounds like it means

Three separate surprises here, each one a real footgun if you don't know about it going in:

It's a **directory-recursion filter, not a file filter** — a pattern that matches `@syslog-ng` as a directory does nothing to a loose file sitting at the volume root named `@syslog-ng.core.gz`. Synology drops a handful of crash-dump files exactly like that at the root of each volume, and every one of them gets scanned regardless of what you've excluded, because they're files, not directories.

It's also a **prefix match, not an exact match** — `--exclude-dir=^/scandir/Plex` matches both `/scandir/Plex` and `/scandir/PlexMediaServer`. Convenient when you want that; a real trap if you assume it only matches the literal name.

And there's **no way to un-exclude a subdirectory**. Once a broad pattern like `--exclude-dir=/@` matches a folder, there's no mechanism to carve out one subdirectory beneath it and scan just that — not even by passing that subdirectory as its own explicit target on the command line. The only fix is dropping the broad pattern entirely and enumerating every single folder you actually want excluded, one at a time. Which is exactly what caused the next problem.

### The scan that wouldn't die

I wanted to add DSM's own package-data folders to the scan scope — the folders behind Docker and everything else installed through Package Center — which meant retiring the blanket `--exclude-dir=/@` pattern that had been quietly catching every Synology-internal folder up to that point. I replaced it with a hand-typed list of the "obvious" `@`-prefixed folders, based on what I remembered seeing in earlier `ls` output.

A test run that should have taken a few minutes instead ran for **over an hour**, stuck in disk-sleep (`D`) state with no end in sight.

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

Fifty-four minutes is also well past the roughly 21 I'd estimated from raw megabytes. My best explanation is that scan time follows file count, not size, and the package folders are a huge pile of small files. (More on that in the open items at the end.)

### The finished job

Here's the shape of what runs today, on Mondays and Fridays at 11:00. Why twice a week? Mostly because a regular computer's antivirus scan doesn't run daily either, and a NAS that rarely changes needs it even less. The lines after the scan are for alerting: they keep the scan's exit code, print the summary lines, and exit with the same code, so DSM still sees a failure when there is one.

```sh
docker exec clamav-scanner clamscan \
  --infected --recursive \
  --max-filesize=2000M --max-scansize=4000M \
  --exclude-dir=^/scandir/@database \
  --exclude-dir=^/scandir/@docker \
  --exclude-dir=^/scandir/photo \
  --exclude-dir=^/scandir/homes/<username>/Photos \
  ... one --exclude-dir per folder from your own find listing (mine has 36) ...
  /scandir /scandir2 > /volume1/docker/clamav_scan_results.txt 2>&1
rc=$?
grep -E 'FOUND$|Scanned files|Infected files|Time:|End Date' \
  /volume1/docker/clamav_scan_results.txt | head -n 40
exit $rc
```

### The alert that had nothing to say

I'd assumed a security job that runs twice a week would tell me how it went. It didn't. Task Scheduler had "send notification only when the script terminates abnormally" ticked (I believe that's the default), and a clean scan isn't abnormal, so a scan that finished fine sent nothing. I found out by waiting for an email after a run and getting silence, which is also exactly what a job that never ran looks like.

Did a *hit* count as abnormal? I dropped an EICAR file (a harmless, universally recognized antivirus test string, not real malware) into a scanned folder and ran a test task. `clamscan` exits with code `1` when it finds something, DSM emailed me, and the status read "1 (Interrupted)". So the failure path works. The body was empty, though, because the scan's output goes to a file and not to the terminal, so the email said *something* was found and nothing about what.

Two fixes, both small: the wrapper lines at the end of the script above, which print the summary to standard output, and unticking the failure-only box so clean runs email too. The next run produced this:

```
Task: Create ClamAV Full Volume
Current status: 0 (Normal)
Standard output/error:
Scanned files: 58169
Infected files: 0
Time: 3139.667 sec (52 m 19 s)
End Date: 2026:09:29 22:30:52
```

The email's own start and stop times are labelled GMT but match my local afternoon, so I suspect DSM is stamping local time with a GMT label (I haven't confirmed that). The `End Date` line comes from the container, which runs on UTC. Same email, two clocks.

Two loose ends on alerting. I've seen the clean-run email and the empty-bodied failure email, but not yet a failure email from the new wrapper, so I don't know that an infected file's name shows up in the body. And I don't know whether a run killed by the nightly shutdown sends any email at all.

### How to check on it

The hardest part of a scan you only run twice a week is knowing whether it's running, done, or dead. `--infected` prints nothing until the very end, so an empty results file is ambiguous. These are the four checks I ended up using, all read-only:

1. **Is it running?** Over SSH, `ps | grep clamscan`. If the only line is the `grep` itself, nothing is running.
2. **What did it write?** `tail -n 15 /volume1/docker/clamav_scan_results.txt`. A finished run always ends with a `SCAN SUMMARY` block. A zero-byte file means it's still running or was cut off (a bedtime shutdown, in my case).
3. **What does DSM think?** Control Panel > Task Scheduler, select the task, Action > View Result. It shows the last run's times, exit code (0 clean, 1 infected, 2 error) and standard output, which is where the wrapper's summary lines should show up.
4. **Did the email arrive?** Search for "Task Scheduler has completed a scheduled task" from the NAS. On a clean run the body carries the summary lines from the wrapper.

One trap: the timestamps *inside* the results file come from the container, which runs on UTC. Read them against Pacific time and you're off by seven or eight hours, depending on daylight saving. (I haven't verified which clock the file's modified time uses, so check that before relying on it.)

### A folder structure that's apparently a secret

Along the way this turned into an accidental audit of Synology's internal `@` folder taxonomy, which — as far as I could find — isn't documented anywhere public in this kind of detail. A few of the more interesting finds:

- `@synologydrive` (lowercase) and `@SynoDrive` (capitalized) are two **completely different** folders — Synology Drive's live sync data versus something else entirely. Case-sensitivity matters on the underlying filesystem, and it's very easy to assume you've seen a folder before when you've actually seen its differently-capitalized sibling.
- Package data isn't in one place. The six folders backing Docker and other installed packages exist on **both** volumes independently — 46MB worth on `/volume2`, and 3.6GB on `/volume1`, almost all of it `@appstore` holding full installed-package binaries (including, memorably, a bundled Node.js runtime for one of my installed packages).
- `@eaDir`, Synology's per-folder thumbnail cache and famous for being inode-heavy, was tiny in my case — 33 files, 232KB. Size isn't a reliable predictor of how expensive a folder is to scan; file *count* is, which is exactly what made `@appstore` the slow part later.

## Keeping it running: signatures update themselves, software doesn't

A scheduled scan is only as good as the signatures it's scanning with. Once the production job was stable, I asked the question I should have asked on day one: what actually keeps this thing current? The answer is two different answers, and the difference matters.

**The signatures update on their own.** The official `clamav/clamav` image starts a `freshclam` daemon inside the container, and `clamscan` reads the signature database fresh from disk on every run, so every scan always uses whatever freshclam last downloaded. I didn't want to just trust the docs, so I checked from the container console:

```sh
clamscan --version                       # version + signature DB number and date
ps | grep freshclam                      # is the daemon actually running?
ls -la /var/lib/clamav                   # timestamps on the database files
tail -20 /var/log/clamav/freshclam.log   # look for "OUTDATED" or errors
```

The version line came back `ClamAV 1.5.4/28137/Mon Sep 28 06:24:12 2026`: current software, and a signature database built that same morning. The process list showed the daemon running with `--checks=1`, which means one update check per day. That sounds too slow until you remember the 16-hour NAS. It boots at 7AM, freshclam checks a few minutes later, and the 11AM scan runs on signatures that are at most four hours old. The nightly shutdown accidentally lines up with the update schedule, which is the closest thing to good luck this project has had.

**The software does not update itself.** The image refreshes signatures only, never the ClamAV binary. The `latest` tag isn't a subscription, it's a snapshot of whatever was current the day I pulled. Upgrading means pulling a newer image and recreating the container. ClamAV's own docs recommend pinning a feature-release tag like `clamav/clamav:1.5` instead of `latest`, so a re-pull gives you patches without silently jumping you to a new feature release.

Portainer's image list shows it happening to me: two ClamAV images, the one tagged `latest` (built Sept 6) and an older untagged one that nothing uses (built Aug 30), which I take to be what `latest` pointed to before I pulled again.

![Portainer's image list: two ClamAV images, one tagged latest and an older untagged one](/images/portainer-image-list.png)

Neglecting this isn't free, either. ClamAV eventually blocks signature downloads for end-of-life versions (it did exactly that to 0.103), so a container nobody ever touches will one day just stop getting updates. My upkeep plan is a quarterly check, or any time this comes back with a hit:

```sh
grep -i outdated /var/log/clamav/freshclam.log
```

Two things in that output looked alarming and weren't. The freshclam log ends every update with `WARNING: Clamd was NOT notified`, which only means freshclam couldn't find the clamd daemon to tell it to reload. `clamscan` doesn't use clamd, so it's irrelevant to the scan itself. It does raise a question, which I settled by looking. The container's health check tests clamd, and `ps` in the container console shows exactly that: a `clamd --foreground` process running alongside `freshclam --checks=1 --daemon`, the once-a-day signature updater. So clamd is up and holding the signatures in memory, while the scan I actually schedule uses `clamscan`, which loads its own copy. As I understand it, that means clamd sits idle during my scans and spends RAM for nothing. That's my reading of how the two tools work, not something I measured. And the signature files turned out to live in the container's own writable layer, not a volume: only `daily.cld` was rewritten that morning, while `main.cvd` and `bytecode.cvd` still carried the date of the image pull.

That last detail has a practical consequence. Recreating the container wipes the writable layer, so the next recreate should add a named volume at `/var/lib/clamav`, and it's worth confirming the scheduled command doesn't reference any file *inside* the container (like the `/tmp` lists I generated while troubleshooting) before pulling the trigger.

Portainer's dashboard says the same thing from another angle: zero volumes, and zero stacks.

![Portainer's dashboard: 2 containers, 0 stacks, 0 volumes](/images/portainer-dashboard.png)

## Lessons learned & what's next

The generalizable version of this, for anyone who's never heard of ClamAV and never will: **when you retire a broad safety net, you have to replace it with a verified, complete list — not a remembered one.** The blanket `--exclude-dir=/@` pattern was doing its job by accident; it caught everything, including folders nobody had specifically thought about. The moment I replaced "everything" with "everything I can remember," the gap between those two things became an hour-long hang on a production job. That's not really a ClamAV lesson. It's true of firewall rules, permission allow-lists, feature flags — anywhere a blanket rule gets replaced with an enumerated one, the enumeration has to come from the system itself, not from anyone's memory of the system.

The other lesson is about where the effort actually went. Getting ClamAV to run was the easy half. The hard half was deciding **what to scan**, and it took repeated rounds of run, measure, and adjust to land on a folder set that balanced coverage against run time. Scan everything and the multi-terabyte media and backup folders blow straight through the 16-hour window; scan too little and the scheduled job is theater. Where I ended up follows the rule from the top of this post: the Synology package folders, Drive documents, and general content are in, while photos, music, Plex, the video and backup folders, and most of the home directories are out. Some of that is a judgment call about risk (photos only arrive through Synology's own apps, and movies and music get played, not executed) and some of it is simply that they don't fit. That combination finishes in about 54 minutes, and it got there through actual full runs rather than guesswork (a per-folder breakdown is still on the to-do list below). If you build this, expect the folder list to be the real project.

It's also a choice, not a guarantee. Nothing scans the folders I left out, so anything that lands there by another route (a PC saving over SMB, a download) goes unchecked. I'm comfortable with that trade for now, but it's worth saying out loud.

**What a clean result does and doesn't mean.** The scan works. It runs, it finishes, and it emails me when something's wrong (tested with a fake virus, the only kind I've personally met). It is not a bodyguard. ClamAV compares files against a list of malware it already knows about, so a clean result means "nothing here matched anything on the list," not "nothing bad is here." Anything brand new sails through until someone writes a signature. It's a fire inspector who visits on Mondays and Fridays, not a smoke alarm: a file that lands Tuesday and misbehaves Wednesday gets its first look on Friday, and I'm not running the real-time mode. Files over the size caps I set get skipped, and I'd expect password-protected archives to be sealed envelopes to it (worth confirming in the [ClamAV docs](https://docs.clamav.net/)). The container mounts everything read-only, so a hit gets me a report and an email, not a cleanup. On purpose. And the one end-to-end test I ran used EICAR, a harmless fake virus built for exactly this. It proves the alert reaches me, not that ClamAV would catch the real thing.

I'm concerned about this, but not over-concerned, for reasons specific to my setup. I went years with no working scan at all after Synology's stopped updating, so twice a week is already an upgrade. I'm the only user, not much on this NAS changes, and DSM and everything from Synology's Package Center are set to update themselves. The one exception is the two things I installed for this project. ClamAV and Portainer run as containers, and containers don't update themselves (the virus signatures do, the software doesn't). So the tool I built to watch for trouble is now the one piece of software on the NAS I have to remember to patch, which is the kind of irony I'd love to claim I planned. Most of what goes wrong here will probably be my own doing, plus any door I've left open for someone else, and that's the one thing this scan can't see.

**How often should you run this at all?** It's an open debate, and I'm not sure I'm on the right side of it. The sources I found lean toward "you barely need antivirus on a NAS": [Marius Hosting](https://mariushosting.com/should-i-install-antivirus-package-on-my-synology-nas/) argues you don't, and puts patching and careful downloading ahead of it, and [Windows Central](https://www.windowscentral.com/do-i-need-antivirus-synology-nas) calls it optional and names ransomware, not viruses, as the real NAS threat. Neither says how often to scan. The one ClamAV schedule I found, in a [ctrl.blog guide](https://www.ctrl.blog/entry/how-to-periodic-clamav-scan.html) written for a Linux machine, scans a web directory daily and the whole filesystem monthly, at quiet hours, because scanning is heavy on memory, CPU and disk. That's a small sample, not a survey.

My gut agrees with the sources. Little on this NAS changes, the folders that change most (movies and TV) are excluded from the scan anyway, and everything from Synology updates itself. I feel it isn't needed. But I've also never had a virus take over my computer, and that's exactly how everyone sounds until they do. Running the scan twice a week is hedging my bets that nothing goes wrong, and hedging is cheap right up until the day it isn't, when you're up a creek with no paddle and spending a long time removing something. So: twice a week, cheap insurance I hope never to collect on. If you run yours daily, monthly, or never, tell me why in the comments.

One exclusion deserves a flag because it cuts against my own rule: `@docker`, where Docker keeps container image layers, is out on purpose. I judged it impractical to scan and a poor fit for signature scanning, since it's binary layers. But it's also where the software I installed via containers (Portainer, ClamAV itself) actually lives, so "scan where software runs" has a hole in it, and I'd rather say so than pretend otherwise.

One more thing worth admitting, since undercutting my own competence seems to be a running theme on this blog: partway through this project, Claude gave me the corrected command and told me to go update it in DSM Task Scheduler myself. A few days later I asked "did the job run yesterday and complete," Claude asked whether I'd actually made the update, and I asked "what update" — genuinely having forgotten the conversation from days earlier. We went back and forth restating what needed to happen, and it turned out I'd already done it, before either of us had sorted out the confusion. Not exactly a seamless AI-orchestrated success story. Just two things — my memory and a chat log — briefly out of sync, resolved by checking the actual file on the NAS instead of trusting either one.

Two things are still genuinely open, not wrapped up neatly for this post:

**Per-folder timing audit.** The corrected scan takes 54 minutes, comfortably inside the window, but I don't yet know which included folder is actually driving that — `@appstore`'s file count is my prime suspect, but "prime suspect" isn't a measurement. The plan is to time each included folder individually, once, as a one-off audit rather than folding it into the weekly job, and decide from real numbers whether `@appstore` earns its place.

**Failure-alert loose ends.** Covered above: I still haven't seen what a real hit looks like in an email from the wrapper, or whether a shutdown-killed run emails at all. If you get to either before I do, I'd like to hear what you find.

## Tell me what I got wrong

This post is what I know today, plus references where I found them. Some of it is probably wrong, or already answered somewhere I didn't look. If you know better, or you've solved the same problem a cleaner way, say so in the comments. I read them, I'll reply, and I'll fix the post where you're right.

The full Task Scheduler script and a Compose equivalent of my container are in the blog repo: [examples/clamav-synology](https://github.com/dwooods/dwooods.github.io/tree/main/examples/clamav-synology). The exclude list is specific to my NAS, so generate yours from a real listing rather than copying mine. If you're fighting the same fight: check `clamconf` for your actual running defaults before you trust anything the docs say, and if you ever retire a blanket exclude pattern for a narrower one, generate the replacement list with `find`, not with whatever you remember scrolling past.

---

Every Monday and Friday at 11 in the morning, while nobody in the house knows or cares, the NAS spends 54 minutes checking the places where its own software runs, so the family's photos, music and movies can just sit there being played. That's not a very exciting sentence to end a blog post on. It's kind of the point — boring is what it's supposed to feel like when it's actually working.
