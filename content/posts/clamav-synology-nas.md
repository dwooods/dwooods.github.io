---
title: "The Scan That Wouldn't Die: ClamAV on a NAS That Only Stays Awake 16 Hours a Day"
date: 2026-09-24
draft: false
tags: ["synology", "clamav", "docker", "self-hosted", "nas", "antivirus", "dsm"]
description: "I had never used Docker. With AI help I built a scheduled ClamAV virus scan on a Synology NAS that has to finish before its nightly shutdown, and learned Docker, ClamAV, and where the AI needed checking along the way."
summary: "I had never used Docker. This is how I used AI to learn it well enough to run a ClamAV virus scan on my Synology NAS, which goes to sleep at 11PM and gives every scan a hard deadline. Along the way: a silent 100MB scan cap, a scan that hung for an hour, and a few places where the AI needed checking."
featuredImage: "/images/hero-clamav-nas.jpeg"
featuredImagePreview: "/images/hero-clamav-nas.jpeg"
---

My Synology DS918+ shuts itself off every night at 11PM and doesn't wake back up until 7AM. That's a deliberate power-schedule setting, not a bug — there's no reason to keep a home NAS spinning while everyone's asleep. It also means every scheduled job on that box is working inside a roughly 16-hour window, and my antivirus scan spent a long time not fitting inside it.

This is the story of getting a ClamAV scan, running in Docker, to actually complete — on schedule, unattended, inside that window — and everything that turned out to be in the way: a silent 100MB scan cap, a scan that ran for over an hour before I killed it, and a Synology folder structure that's apparently interesting enough to be almost completely undocumented anywhere public.

## Why I built this

The NAS holds our music, photos, backups, videos, movies and TV shows. It's the household's everything-drive, so keeping it locked down and free of anything nasty matters more to me than it would on a throwaway hobby server. I hadn't run a virus scan on it in a long while, and that had been bugging me.

Not because I was worried. That's exactly how you end up not scanning for a year. The realistic threat isn't a stranger; it's me installing something I thought was trustworthy and finding out otherwise, on the one box the whole house depends on.

That shaped what the scan is actually for. Photos reach the NAS through Synology's own apps, and music and movies are files I play, not run. What I needed watched was the other category: system files, installed packages, and anything that executes. So the goal was never "scan every byte." It was "scan where software lives and runs, and skip where media just gets played."

I tried Synology's free **Antivirus Essential** first. It stopped updating its virus definitions and I couldn't force a refresh, which turns out to be a known issue: Synology has [its own knowledge-base article](https://kb.synology.com/en-us/DSM/tutorial/I_cannot_update_virus_definitions_in_Antivirus_Essential) titled almost exactly "I cannot update virus definitions in Antivirus Essential," and there's a [community thread](https://community.synology.com/enu/forum/1/post/189641) of other people hitting the same wall. A virus scanner that can't update its own signatures is a smoke detector with the battery pulled.

I didn't give up quickly. The package bundles **ClamAV 0.103.8**, a version the ClamAV project has long since retired, and as far as I can tell that's the root of it: when I enabled SSH and ran `freshclam` by hand, the signature servers answered with HTTP 429 and 403 errors and a cool-down period instead of a database. Downloading the signature files manually and uploading them through DSM got "Incorrect file format" (the links sit behind Cloudflare, so I presumably saved an HTML page instead of a database). Fixing DNS and NTP changed nothing. The other option, Antivirus by McAfee, is a separate paid subscription, and I wasn't going to pay an annual fee to scan a NAS I already own.

{{< image src="/images/clamav-logo.png" alt="ClamAV logo" width="150px" >}}

What stuck with me is that [ClamAV](https://www.clamav.net/), the engine underneath, is free and runs on Windows, macOS and Linux. Getting current signatures onto a Synology shouldn't be harder than getting them onto a Raspberry Pi. I still don't know why Essential stopped updating and I haven't heard Synology's side, so that's a question I need to send them.

So: ClamAV, in Docker, driven by DSM's own Task Scheduler. Free, open-source, and something I could actually see inside of when it went wrong, instead of a GUI toggle that either works or doesn't tell you why.

Now the part that surprised me, and the reason I'm writing any of this down: **I had never installed or run Docker before this project.** Not "rusty." Never. I went in expecting the free route to be *less* technical than the paid one and got a crash course instead: containers, read-only mounts, a management UI, and a long stretch of installing and validating before any scan result meant anything. The free version costs you in knowledge instead of dollars, and it turned out to be a good way to learn, which is what the next two sections are about.

## Docker, for people who think it's for other engineers

{{< image src="/images/docker-logo.png" alt="Docker logo" width="150px" >}}

I used [Docker](https://www.docker.com/) for the first time on my NAS to run ClamAV and Portainer. I had always thought Docker was something engineers used to package and run code, but it turns out to be useful for something much simpler: running software your device doesn't natively support. Docker runs applications in containers, which are isolated environments with the application and everything it needs packaged together. You start with an image, a packaged blueprint for the software, and Docker uses it to create a running container. In my case the NAS's built-in antivirus had stopped updating, so instead of installing a scanner into the NAS operating system, I ran a current ClamAV in its own container, and did the same with Portainer to manage it. Data that has to survive a restart can live in a volume outside the container. (Foreshadowing: I didn't put my virus signatures in one. More on that below.) I still don't fully understand what Docker is doing under the hood, and I definitely needed Claude to walk me through the setup, but I understand the practical value: a relatively clean, isolated way to run software on my own hardware that otherwise wouldn't be available.

Here's the scale of what I actually set up, so it looks less intimidating: one official image, `clamav/clamav`; my two NAS volumes mounted **read-only**, so the scanner can look at everything and change nothing; a name; and a restart policy so it comes back when the NAS boots at 7AM. No Dockerfile, no published ports. The scan itself is a single `docker exec` command that Synology's Task Scheduler runs. If you copy this, note that the mounts cover both whole volumes, so what gets scanned is decided by the paths and excludes in that command, not by the container.

![Synology's own Docker screen, showing the two containers I run: clamav-scanner and portainer](/images/synology-docker-containers-running.png)

## ClamAV, for people who think antivirus is an app

I didn't know ClamAV existed until Synology's own scanner stopped updating, I couldn't get it to refresh manually, and I wasn't going to pay for McAfee. That's when I pivoted. I went in expecting a GitHub repo from some stranger. It isn't. The [ClamAV docs](https://docs.clamav.net/) say it's brought to you by Cisco Systems, and there's real documentation, a [community project ecosystem](https://docs.clamav.net/manual/Installing/Community-projects.html), an updated signature database, and versions for Windows, macOS and Linux.

What I didn't expect is that it isn't an app. The docs call it an open-source anti-virus toolkit, and in practice that's a small set of separate command-line pieces. `clamscan` scans on demand and exits, `clamd` is a background daemon that keeps the signatures loaded in memory, and `freshclam` handles signature updates. In my container `freshclam` runs as a daemon that checks once a day, `clamd` is running (I confirmed it with `ps`), and my scheduled job calls `clamscan`. There's no green checkmark. There's an exit code.

Installing it was the easy part. The hard part was the setup around it: the scripts, what to run, what to exclude, and when. I leaned on Claude for most of that. The docs say it was designed especially for scanning email on mail gateways, which explains why it has plenty of users doing things I haven't thought of. I'm still not sure how else I'd use it.

Two limits worth knowing before you trust it. The docs themselves say ClamAV isn't a traditional anti-virus or endpoint security suite. It only recognizes known malware, so a clean scan means "nothing matched," not "nothing's there." And mine is a scheduled scan, twice a week, not real-time protection.

## Architecture & tech stack

- **NAS**: Synology DS918+ — Celeron J3455, no GPU, DSM 7.x. Two volumes, `/volume1` and `/volume2`.
- **Scanner**: the official `clamav/clamav:latest` image, running as a container named `clamav-scanner`, with both volumes mounted **read-only**: it can see everything and change nothing, on purpose.
- **Management**: Portainer CE, alongside Synology's own Docker package, because the Synology Docker GUI wouldn't let me mount a top-level shared folder and my version had no Project (compose) tab. (Gemini suggested it. Yes, that's yet another container just to manage the first container.) Portainer let me type the host paths directly, create the container from a form (Containers > Add container), read its logs, and open a console inside it. That console became the backbone of the project: it's a shell *inside the container*, scoped to the read-only mounts, so Claude and I never had to share DSM credentials to test anything.
- **Scheduling**: DSM's own Task Scheduler, running the `docker exec` command as a User-defined script every Monday and Friday at 11:00 AM Pacific — early enough in the ~16-hour window that even a slow run has room to finish before the 11PM shutdown.

### Tools & AI assist

Two AI tools were involved. **Gemini** came first: it walked me through the Antivirus Essential dead end and suggested Portainer when Synology's Docker UI ran out of road, and its Nano Banana model drew the hero image from a prompt Claude wrote. Most of the build then ran through **Claude Cowork**, in a single long-running conversation, the same pattern as the [Plex/Tailscale project](/posts/wagging-the-dog-tailscale-plex-vacation/) before it: no local repo, no code files, just a chat window and a browser session into Portainer. Since Docker was brand new to me, that conversation doubled as the tutorial.

Claude did the investigation: building the exclude-list logic, diagnosing a stuck process by reading its open file descriptors, and driving the Portainer console to test commands. What it does **not** do, by a hard rule I set going in, is log into DSM. Every Task Scheduler change, including the final production command, I typed in myself in DSM's own UI, and Claude only verified the result afterward through the container's read-only mount. Claude investigated, proposed and verified. I held the one set of credentials that could change something.

Claude also got things wrong, and I'd rather say so than edit it out. Early on I told it to skip the `video` and `video2` folders and had to confirm that more than once before it stuck. When the browser session into Portainer dropped mid-verification, its first instinct was to retry quietly, which is exactly the kind of thing that should surface to a human. I told it so, and it changed behavior for the rest of the project. And I'd assumed a security job would email me after every run, when Task Scheduler was set to email only on failure. That one wasn't really Claude's miss or mine so much as a misunderstanding: I ticked the box thinking it was what Claude wanted, without checking what it meant for a scan that runs fine.

## Key technical challenges

### The job that kept getting killed at bedtime

My first version scanned everything. It ran all day, the NAS went down for the night, and the scan never finished. Nothing told me: the task didn't fail loudly, there just wasn't a finished result, and I only found out by digging into why the job had stopped each day.

Scanning literally everything, I assume, isn't how a virus scanner is normally used. Real antivirus tools skip what doesn't matter, and I hadn't told mine what didn't matter. It also wasn't only the shutdown: a scan grinding through the whole NAS all day would have dragged it down right when the rest of us use it in the evening.

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

Three surprises, each one bites if you don't see it coming:

It's a **directory filter, not a file filter**. A pattern for `@syslog-ng` does nothing to a loose file named `@syslog-ng.core.gz` at the volume root, and Synology leaves several crash dumps like that, so they get scanned whatever you exclude.

It's a **prefix match, not an exact match**. `--exclude-dir=^/scandir/Plex` also catches `/scandir/PlexMediaServer`.

And there's **no way to un-exclude a subdirectory**. Once a broad pattern like `--exclude-dir=/@` matches a folder, you can't carve one subfolder back in, not even by naming it as a scan target. The only fix is to drop the broad pattern and list every folder you want excluded, one at a time. Which is exactly what caused the next problem.

### The scan that wouldn't die

I wanted to add DSM's package folders, where everything from Package Center lives, to the scan. That meant retiring the blanket `--exclude-dir=/@` pattern, and I replaced it with a hand-typed list of the "obvious" `@` folders, based on what I remembered from earlier `ls` output.

A test run that should have taken a few minutes instead ran for **over an hour**, stuck in disk-sleep (`D`) state with no end in sight.

Claude diagnosed it by checking which file the stuck process had open (`ls -la /proc/<pid>/fd`), a more honest answer than any log file:

```
/proc/7192/fd/4 -> /scandir/@synologydrive/@sync/repo/4/...
```

`@synologydrive`, Synology Drive's internal sync store, wasn't on my list. It had scrolled off-screen during an earlier terminal review, along with a few capitalized folders (`@AntiVirus`, `@SynoDrive`, `@S2S`) I'd never noticed.

I killed the process and had Claude stop guessing and ask the NAS itself what folders existed:

```bash
find /scandir -maxdepth 1 -type d -iname '@*' > /tmp/v1all.txt
```

That turned up **29** `@` folders on `/volume1` alone, not the roughly 15 either of us had assumed. So the exclude list stopped being typed by hand and got generated from that listing instead:

```bash
EXCL=""
for d in $(cat /tmp/v1all.txt) $(cat /tmp/v2all.txt); do
  case "$d" in
    */@appdata|*/@appstore|*/@apphome|*/@appconf|*/@apptemp|*/@config_backup) ;;
    *) EXCL="$EXCL --exclude-dir=^$d";;
  esac
done
```

Six package folders stay in scope on each volume, and every other `@` folder is excluded. The corrected scan finished clean in 53 minutes 55 seconds: 0 infected, 58,775 files. Two days later the real Task Scheduler job ran it unattended in its Friday 11AM slot and matched almost exactly (53m54s, 0 infected, 58,778 files), the first confirmation that the fix holds without anyone watching.

Fifty-four minutes is also well past the roughly 21 I'd estimated from raw megabytes. My best explanation is that scan time follows file count, not size, and the package folders are a huge pile of small files. (More on that in the open items at the end.)

### The finished job

Here's the shape of what runs today, on Mondays and Fridays at 11:00 (why twice a week, and why that's debatable, is near the end). The lines after the scan are for alerting: they keep the scan's exit code, print the summary lines, and exit with the same code, so DSM still sees a failure when there is one.

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

I'd assumed a security job that runs twice a week would tell me how it went. It didn't. I had ticked "send notification only when the script terminates abnormally" myself, thinking that's what the job needed, and I misunderstood what it meant for a scan that runs fine: a clean scan isn't abnormal, so a scan that finished fine sent nothing. I found out by waiting for an email after a run and getting silence, which is also exactly what a job that never ran looks like.

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

The `End Date` line is UTC because it comes from the container, which is why it doesn't match my clock. (This run took 52 minutes on 58,169 files; the earlier runs took 54 minutes on about 58,800. Same job, different days.)

### How to check on it

`--infected` prints nothing until the very end, so an empty results file is ambiguous. These are the three read-only checks I ended up using:

1. **Is it running?** Over SSH, `ps | grep clamscan`. If the only line is the `grep` itself, nothing is running.
2. **Did it finish?** `tail -n 15 /volume1/docker/clamav_scan_results.txt`. A finished run ends with a `SCAN SUMMARY` block; a zero-byte file means it's still running or was cut off (a bedtime shutdown, in my case).
3. **What does DSM say?** Control Panel > Task Scheduler, select the task, Action > View Result: the last run's exit code (0 clean, 1 infected, 2 error) and the wrapper's summary lines. The same summary lands in the task-completion email.

One trap: the timestamps *inside* the results file come from the container, which runs on UTC, so read them against Pacific time and you're off by seven or eight hours depending on daylight saving. (I haven't verified which clock the file's modified time uses.)

### A folder structure that's apparently a secret

Along the way this turned into an accidental audit of Synology's internal `@` folders, which, as far as I could find, aren't documented anywhere public in this kind of detail. Two finds worth knowing. `@synologydrive` (lowercase) and `@SynoDrive` (capitalized) are two **completely different** folders, so it's very easy to think you've seen a folder before when you've seen its differently-capitalized sibling. And size is a poor predictor of scan cost: `@eaDir`, the inode-heavy thumbnail cache, was tiny (33 files, 232KB), while the six package folders that I do scan exist on **both** volumes, 46MB on `/volume2` and 3.6GB on `/volume1`, almost all of it `@appstore` (full installed-package binaries, including, memorably, a bundled Node.js runtime).

## Keeping it running: signatures update themselves, software doesn't

A scan is only as good as its signatures, so once the job was stable I asked the question I should have asked on day one: what keeps this thing current? There are two answers.

**The signatures update on their own.** The official `clamav/clamav` image starts a `freshclam` daemon inside the container, and `clamscan` reads the signature database from disk on every run. I didn't want to just trust the docs, so I checked from the container console:

```sh
clamscan --version      # version + signature DB number and date
ps | grep freshclam     # is the update daemon actually running?
```

The version line came back `ClamAV 1.5.4/28137/Mon Sep 28 06:24:12 2026`: current software, and a signature database built that same morning. The daemon runs with `--checks=1`, one update check per day, which sounds too slow until you remember the 16-hour NAS. It boots at 7AM, freshclam checks a few minutes later, and the 11AM scan runs on signatures at most four hours old. The nightly shutdown accidentally lines up with the update schedule, which is the closest thing to good luck this project has had.

**The software does not update itself.** The image refreshes signatures, never the ClamAV binary. The `latest` tag isn't a subscription, it's a snapshot of whatever was current the day I pulled, and ClamAV's own docs recommend pinning a feature-release tag like `clamav/clamav:1.5` instead. Upgrading means pulling a newer image and recreating the container, and the signatures live in the container's own writable layer, not a volume (Portainer's dashboard says the same from another angle: zero volumes). So a recreate means a full signature re-download unless you add a named volume at `/var/lib/clamav`.

![Portainer's dashboard: 2 containers, 0 stacks, 0 volumes](/images/portainer-dashboard.png)

Neglect isn't free, either. ClamAV eventually blocks signature downloads for end-of-life versions (it did exactly that to 0.103), so a container nobody touches will one day just stop updating. My upkeep plan is a quarterly check of `grep -i outdated /var/log/clamav/freshclam.log`, or any time a scan comes back with a hit.

## Lessons learned & what's next

**The general lesson: when you retire a broad safety net, replace it with a verified, complete list, not a remembered one.** The blanket `--exclude-dir=/@` pattern was doing its job by accident; it caught everything, including folders nobody had specifically thought about. The moment I replaced "everything" with "everything I can remember," the gap between the two became an hour-long hang on a production job. It's true of firewall rules and permission allow-lists too: the enumeration has to come from the system itself, not from anyone's memory of it.

**The other lesson is where the effort went.** Getting ClamAV to run was the easy half. The hard half was deciding what to scan, through repeated rounds of run, measure and adjust. Scan everything and the multi-terabyte media and backup folders blow through the 16-hour window; scan too little and the job is theater. I ended up with the package folders, Drive documents and general content in, and photos, music, Plex, video, backups and most home directories out, partly as a judgment about risk (photos arrive through Synology's own apps, and movies and music get played, not executed) and partly because they don't fit. If you build this, expect the folder list to be the real project.

**What a clean result does and doesn't mean.** The scan works: it runs, it finishes, and it emails me when something's wrong (tested with a fake virus, the only kind I've personally met). It is not a bodyguard. ClamAV compares files against malware it already knows about, so clean means "nothing here matched," not "nothing bad is here." It's a fire inspector who visits on Mondays and Fridays, not a smoke alarm: a file that lands Tuesday and misbehaves Wednesday gets its first look on Friday. The coverage has holes by design: anything that lands in an excluded folder by another route, like a PC saving over SMB or a download, goes unchecked, and `@docker`, where container image layers live, is out because it's impractical to scan, even though it's where the software I installed via containers actually lives. So "scan where software runs" has a hole in it, and I'd rather say so. Files over the size caps get skipped, I'd expect password-protected archives to be sealed envelopes to it (worth confirming in the [ClamAV docs](https://docs.clamav.net/)), and everything is mounted read-only, so a hit gets me a report and an email, not a cleanup. My one end-to-end test used EICAR, a harmless fake virus, so it proves the alert reaches me, not that ClamAV would catch the real thing.

**How often should you run this at all?** It's an open debate, and I'm not sure I'm on the right side of it. The sources I found lean toward "you barely need antivirus on a NAS": [Marius Hosting](https://mariushosting.com/should-i-install-antivirus-package-on-my-synology-nas/) argues you don't and puts patching and careful downloading first, and [Windows Central](https://www.windowscentral.com/do-i-need-antivirus-synology-nas) calls it optional and names ransomware, not viruses, as the real threat. Neither says how often to scan. The one ClamAV schedule I found, in a [ctrl.blog guide](https://www.ctrl.blog/entry/how-to-periodic-clamav-scan.html) for a Linux machine, scans a web directory daily and the whole filesystem monthly, at quiet hours, because scanning is heavy. That's a small sample, not a survey.

My gut agrees with the sources. I'm the only user, not much on this NAS changes, the folders that change most (movies and TV) are excluded anyway, and DSM and everything from Synology's Package Center update themselves. I went years with no working scan at all, so twice a week is already an upgrade, and a regular computer's antivirus doesn't run daily either. But I've also never had a virus take over my computer, and that's exactly how everyone sounds until they do. So: twice a week, cheap insurance I hope never to collect on. I'm concerned, but not over-concerned. The one thing that doesn't update itself is what I installed for this project (containers don't), so the tool I built to watch for trouble is now the one piece of software on the NAS I have to remember to patch, which is the kind of irony I'd love to claim I planned. Most of what goes wrong here will probably be my own doing, plus any door I've left open for someone else, and that's the one thing this scan can't see. If you run yours daily, monthly, or never, tell me why in the comments.

**The AI lesson: let it explain and draft, and check every claim about your own system against the system.** Several of the problems in this post, including the email assumption and the hand-typed exclude list, were plausible answers nobody had checked against the real system yet, and the fix each time was looking at the real thing. The bigger takeaway is simpler. There's always another way to do something, but it isn't always the easy one. Mine took learning a little Docker, some scripting and some terminal commands. If you're not into tech, that may be more than you're willing to try. I was, and I ended up with a virus scan that works, updates itself, is free, and does what I need.

**Still open, not wrapped up neatly:**

- **Per-folder timing.** The scan takes 52 to 54 minutes, comfortably inside the window, but I don't know which included folder drives that. `@appstore`'s file count is my prime suspect, and "prime suspect" isn't a measurement. The plan is to time each included folder once and decide from real numbers whether `@appstore` earns its place.
- **Failure-alert loose ends.** I still haven't seen what a real hit looks like in an email from the wrapper, or whether a shutdown-killed run emails at all. If you get to either before I do, I'd like to hear what you find.

## Tell me what I got wrong

This post is what I know today, plus references where I found them. Some of it is probably wrong, or already answered somewhere I didn't look. If you know better, or you've solved the same problem a cleaner way, say so in the comments. I read them, I'll reply, and I'll fix the post where you're right.

The full Task Scheduler script and a Compose equivalent of my container are in the blog repo: [examples/clamav-synology](https://github.com/dwooods/dwooods.github.io/tree/main/examples/clamav-synology). The exclude list is specific to my NAS, so don't copy mine. If you're fighting the same fight: check `clamconf` for your actual running defaults before you trust the docs, and generate any exclude list with `find`, not with whatever you remember scrolling past.

---

Every Monday and Friday at 11 in the morning, while nobody in the house knows or cares, the NAS spends under an hour checking the places where its own software runs, so the family's photos, music and movies can just sit there being played. That's not a very exciting sentence to end a blog post on. It's kind of the point — boring is what it's supposed to feel like when it's actually working.
