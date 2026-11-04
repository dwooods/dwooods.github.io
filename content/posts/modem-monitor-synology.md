---
title: "I Built a Smoke Alarm for My Internet (and Then Muted It)"
date: 2026-11-04
draft: false
tags: ["docker", "synology", "portainer", "networking", "cable-modem", "monitoring", "python", "self-hosted"]
description: "A Python container on my Synology NAS that logs my cable modem's signal, built after three modems, three tech visits and a year of drops."
summary: "My internet had been dropping for a year and nothing would tell me when. So Claude and I built a monitor on my NAS, which then recorded nothing at all for half of what I built it to watch."
featuredImagePreview: "/images/hero-modem-monitor-framed.jpeg"
images: ["/images/modem-monitor-dashboard.jpeg"]
---

The modem's own log says my internet went down at 6:54 PM on Sunday, October 25, and again at 6:54 PM on Monday, the same minute. Nothing was watching, so the log was the only witness.

I've had Astound for over a year, and the connection has always dropped now and then, rarely enough that I shrugged and rebooted something. Over the last couple of months it got worse, with longer outages. I'm also job hunting, which means video interviews from home, and an outage in the middle of one is the kind of thing you rehearse at 3 a.m.

The real problem was that I never knew when it dropped or how often. The modem's log is a page nobody reads, and it wipes itself on a reboot, so unless I happened to be using the connection, an outage didn't exist. My evidence was my memory, which is not a measuring instrument.

So I did what I do these days: I opened a chat with Claude and built a smoke alarm. It's a small Python program in a Docker container on my Synology NAS that checks the internet every minute, reads the modem's own signal numbers every five minutes, writes everything to files, draws a dashboard, and, for about four days, tapped my phone when something looked wrong.

This post is about how that went: three modems, three tech visits, a monitor that spent four days recording nothing for half of what it was built to watch, and a result I'd like to trust more than I do.

<div style="max-width: 640px; margin: 0 auto;">

![Dashboard of the modem monitor, 3-day view](/images/modem-monitor-dashboard.jpeg "The monitor's dashboard, 3-day view on November 4: status tiles, no outages, signal-loss events by hour, uncorrectable errors per check, and the event log with hardware addresses masked")

</div>

## Why I Built This

The week before I built it was a blur of changes. On Sunday, October 25, I put in a new Netgear modem, and my ASUS router refused to see the internet until I power-cycled the modem. The cause was me. I'd plugged my laptop into the new modem first to test it, and cable modems, as far as I understand, tie themselves to the first device they meet until they're restarted.

Two tech visits followed, Monday and Tuesday. Between them they replaced the outside connector twice, redid the inside connectors and cables, and added a 3-way splitter to the line feeding the modem. The splitter was the visit that changed the plan: as the tech put it to me, the point was to dampen the signal, so apparently the line was too strong at the modem, not too weak. The first tech also told me the ARRIS SB6190 was the modem to get and that Astound supports it, so I ordered one as a controlled test, and it went in on Wednesday.

![The wiring box: the coax line that feeds the modem runs in from the top and across, with the 3-way splitter the tech added in the middle of the frame](/images/wiring-box-splitter.jpeg "The coax that feeds the modem, with the tech's 3-way splitter in the middle, after the cleanup.")

Every one of those fixes was a guess made without data. Each ended with "let's see if it holds," and the only way I could see was to be online when it didn't. The monitor didn't exist yet for the first two visits; it started logging at 4:49 PM that Wednesday. So I wanted a witness, not a fix: something that would sit on the network, log the connection every minute, read the modem's own numbers, and tell me when something happened. I wanted to hand a tech a timeline instead of a feeling.

I also had a place to run it. My NAS already ran Docker, which is a way of packaging a small program with everything it needs so it behaves the same anywhere, so one more small container was cheap.

## Architecture & Tech Stack

A cable modem is the box that turns the coax line from the street into Ethernet, and it keeps a tiny web page about itself that nobody reads (on most modems it lives at 192.168.100.1). That page lists the channels the modem listens on (downstream, 32 on mine) and talks on (upstream, 2 on mine), each channel's signal strength, and a running count of uncorrectable errors, which are chunks of data the modem couldn't repair. It also has an event log, and the entry I came to know best is "No Ranging Response received - T3 time-out," which means the modem asked the provider's equipment for an adjustment and got silence. That page is the whole data source.

![Diagram: the modem's page and three internet checks feed a Python container on the NAS, which writes CSV files, serves a dashboard, sends queued alerts through ntfy and Gmail, and pings healthchecks.io](/images/modem-monitor-synology-architecture.svg)

| Piece | What it does |
|---|---|
| Python script, standard library only | Checks three public addresses every 60 seconds and calls an outage after two rounds in a row where all three fail; reads the modem page and event log every five minutes |
| Six CSV files | Outages, issues, events, polls, per-channel readings and connectivity checks, kept for later analysis |
| Dashboard | Charts drawn on the server as SVG, so it still loads while the internet is down |
| [ntfy](https://ntfy.sh) and Gmail | A push to my phone and an email, queued while offline and sent when the connection returns |
| [healthchecks.io](https://healthchecks.io) | A heartbeat for when the internet is down and the NAS can't send anything: the pings stop, so an outside service tells me |

It runs in a `python:3.12-slim` container on my DS918+, deployed as a stack in [Portainer](https://www.portainer.io), a web dashboard for managing containers. The alerts queue because the thing that notices an outage can't report it over the connection that just died. The dashboard doesn't rely on third-party servers for its code, so it still loads when the thing that's broken is the internet. And each five-minute poll writes a summary row plus one row per channel, which is why the per-channel file is the one that grows.

### Tools & AI Assist

Claude wrote the original monitor in an earlier chat and tested it against a simulated modem, which is how it shipped a bug that only appears when a real Gmail login fails: the phone push repeated every minute. In this chat Claude reproduced it (five failed email sends, five pushes) and fixed it with a three-line flag. It also walked me through deployment, read the modem's pages, wrote the patches and ran the CSV analysis that found the bug in the third challenge below.

The misses: it assumed my NAS ran Container Manager, guessed wrong about why Google blocked my app password, set up a 24/7 heartbeat without noticing the NAS sleeps at night, and told me a CSV contained data it didn't. No other AI tools. It was Claude from start to finish.

## Key Challenges

### Claude assumed the wrong NAS, and Google said no

The original README walked through Container Manager, Synology's newer container app. My NAS runs the older Docker package with Portainer. Different tools, different steps, so Claude redid the deployment as a Portainer stack.

Then, alerts. I wanted to reuse my NAS's own email notifications so the monitor wouldn't need another credential. It can't: the NAS signs in to Google through OAuth, and the container can't reuse that login. So the monitor needed a Gmail app password, and Google's page for those said "setting not available." Claude guessed Advanced Protection and sent me to a URL that returned a 404. The real cause was on my screen the whole time. 2-Step Verification was off, and the page said "Turn on." I turned it on, made the password, and the first alert landed a few minutes later. That first alert was about an event from before the monitor existed: the modem keeps its own log, and the monitor reads it on startup. A later restart didn't repeat it, so the monitor remembers what it has already seen.

The alarm earned its keep fast. Around 5:30 PM, less than an hour after I deployed it, the modem logged "RCS Partial Service," which I read as it losing some of its channels, and the error count jumped by 63,704 between two polls. My phone buzzed. It was the first time the monitor told me something I couldn't have known.

### The heartbeat that would have paged me every night

The monitor has a blind spot: when the internet is down, it can't tell me, because ntfy and Gmail are on the far side of the outage. So I added a dead-man's switch. Every loop the script pings a URL at healthchecks.io, but only while the internet is up. If the pings stop, that service, which lives outside my network, emails me and pushes a notification. It's the one alert that still works when my connection is the thing that died, and as a side effect it also catches the monitor itself dying.

Claude set it up to run around the clock. My NAS powers off at 11 PM and back on at 7 AM, so left alone it would have declared the monitor dead every night. Claude caught that late, as a reminder tacked onto the end of an answer ("don't forget the healthchecks cron change before 23:00 tonight"), and I asked why it hadn't said so earlier. Fair question. The fix was a schedule instead of a fixed interval:

```
Schedule:   */2 7-22 * * *    (every second minute, 07:00 through 22:59)
Time zone:  America/Los_Angeles
Grace:      10 minutes
```

The time zone matters, because without it the service reads the schedule in UTC and the quiet hours land mid-afternoon. The grace window gives the NAS time to boot at 7 before anyone panics. That's the everyday setup. For the nights of October 29 and 30 I turned the NAS shutdown off so the monitor could watch overnight, and both nights were quiet: about 86 polls each, no events, no new uncorrectable errors, all 32 downstream channels locked.

I tested it the only way that counts, by stopping the container on purpose. The email arrived. The phone push needed its own integration and a test message ("TEST is DOWN") before it showed up, and I never saw the matching "UP" on the phone. An alarm you've never set off is a hope.

That's the design. Here's where it caught me instead. That same evening, healthchecks emailed that the monitor was back up after 1 hour and 11 minutes of downtime. The file running on my NAS wasn't the one I thought. A different version, with a feature I didn't have and without the heartbeat, had replaced mine, so the pings had stopped. Most likely I'd uploaded an old copy over the new one, which is easy to do when a file has been through this many chats and downloads. Claude merged the two into one file and tested it, and I uploaded it. A dead-man's switch catches your mistakes too, and mine caught one on day one.

### Four days of blank columns

The monitor had columns for upstream power: how loudly the modem has to shout to be heard by the provider, in dBmV (higher means louder). It's a classic sign of line trouble and the number I most wanted. Four days in, I asked Claude to analyze the CSV. All 763 polls had `us_locked`, the count of locked upstream channels, at 0, and both upstream power columns were empty. The monitor had never recorded a single upstream reading. Claude had told me earlier the file would contain one; it had read the column names in the code and assumed. That one was mine to catch, and I didn't until the data was four days old.

Nothing complained, because a scraper that finds nothing writes a blank instead of raising an error. Claude had me save the modem's page source (Option+Cmd+U on a Mac; it first said Cmd+U, which does nothing useful, a tiny miss, but I'm keeping a list) and spotted the cause: the upstream table leaves out its closing row tags.

```html
<tr><td>1</td><td> Locked </td> ... <td>46.50 dBmV</td><tr><td>2</td> ... <td>45.75 dBmV</td>
</table>
```

Browsers render that fine, which is why I could see the numbers myself the whole time. My parser trusted closing tags, so each new `<tr>` threw away the unfinished row, and the last row vanished at `</table>`. Claude ran the old parser against the saved page first and got zero upstream rows, which is the only way to know a fix fixes the thing you think it does. The fix closes the open row whenever a new one starts or the table ends:

```python
elif tag == "tr" and self._stack:
    self._flush_row()  # the SB6190 upstream table leaves </tr> out; keep the unclosed row
    self._row = []
...
elif tag == "table" and self._stack:
    self._flush_row()
    self.tables.append(self._stack.pop())

def _flush_row(self):
    if self._row is not None and self._stack:
        if self._cell is not None:      # a cell can be unclosed too
            self._row.append(re.sub(r"\s+", " ", "".join(self._cell)).strip())
            self._cell = None
        if self._row:
            self._stack[-1].append(self._row)
    self._row = None
```

What the fix did and didn't recover:

- **Test on the saved page:** the old parser found 0 upstream rows and the fixed one found 2 (46.5 and 45.75 dBmV). Downstream still read 32, and well-formed tables still parsed.
- **Lost:** the first four days of upstream history. All I have are two readings from screenshots, 44.5 and 43.25 dBmV on the evening of October 28 and 46.5 and 45.75 four days later. About 2 dB higher, from two readings, is not a trend.
- **Since November 1, 7:37 AM:** all 430 polls show both upstream channels locked at 45.75 and 46.5 dBmV, and those numbers haven't moved.

The monitor's only outages are on the morning of October 29: 35 minutes from 8:38 AM and 15 minutes from 9:19 AM. Those were the Thursday tech visit, with the outside drop replaced in the first window and the inside components in the second. The modem never rebooted.

## Lessons Learned & What's Next

Here is what the monitor recorded from the first poll on Wednesday, October 28 to the afternoon of Tuesday, November 3, counted from the raw polls file. These are the modem's own counts of line trouble, not a count of dropped connections.

| Period | Polls | New uncorrectable errors | Signal-loss events |
|---|---|---|---|
| Oct 28, first six hours | 67 | 72,241 | 3 |
| Oct 29, midnight to noon | 45 | 1,680 | 12 |
| Oct 29 noon to Nov 1, 7:30 AM | 652 | 61 | 0 |
| Nov 1, 7:30 AM to Nov 3, 3:20 PM | 430 | 14,246 | 6 |
| Whole week (the dashboard's total) | 1,195 | 88,228 | 21 |

What happened when:

- **Oct 29 morning:** the events stop after 10:36, which fits the tech finishing somewhere between 10 and 11, as best I remember. One last burst of 1,680 errors came at 11:53.
- **Oct 29 noon to Nov 1:** quiet. All 32 downstream channels stayed locked on every poll.
- **Nov 1, 1:50 to 5:25 PM:** four signal-loss events, including an "RCS Partial Service" and a "T3 time-out," and one check at 1:51 PM that added about 5,400 errors.
- **Nov 3:** a partial-service warning at 9:29 AM and a T3 time-out at 11:58 AM.

That is far below the first evening, and it is not nothing: about 82 percent of the week's errors landed in the first six hours, and the monitor has logged no outages or modem restarts since October 29. Every one of the November events came after I muted the alerts that morning.

The whole record is the timeline I wanted to hand a tech, with limits. My "before" is six hours and a morning, and I changed at least five things in a week (the connectors, the cables, a splitter, the power block in my wiring box and the modem), so I can't tell you which one mattered. And four quiet days couldn't promise a fifth, and didn't deliver one. Whether the timeline helps is still open: when I texted the last tech about the November 1 errors, he said it happens, and that he was looking for an outage longer than five minutes, which the monitor hasn't logged since October 29.

The lesson I'd hand to anyone with a different project: zero is not the same as quiet. A sensor that fails silently looks exactly like a calm system, so before you trust a clean chart, find one row where the thing you care about has an actual number in it. One look at the CSV on day one would have saved four days. The better version is a monitor that shouts about its own blind spots; an alert for "this column has been empty for an hour" would take a few lines, and I haven't written it yet. The other lesson is about timing: get the logging running before the people with the wrenches arrive.

A few days in, I turned the alerts off and went back to reading the dashboard. Nothing was reaching me, or anyone else in the house. The modem still logs the occasional complaint, counted in the table above, but the monitor hasn't logged a dropped connection since the morning of October 29. This is a home connection, not a server room, and a phone that buzzes about errors the internet absorbed on its own is a smoke alarm going off when I make toast. The monitor keeps recording, and the per-channel file trims itself at 60 days. What I still don't have is the thing I wanted at the start: as far as I can tell, no one will tell me when the line goes bad.

## Try This Yourself

The script, the Portainer stack file and a template for the settings are in [examples/modem-monitor](https://github.com/dwooods/dwooods.github.io/tree/main/examples/modem-monitor) in this blog's repo. If you want to try the idea, open your modem's own page, look at the event log and the uncorrectable errors, and see whether anything is writing them down for you. With a home server, a small container that reads that page every few minutes is an evening's work, and a heartbeat from [healthchecks.io](https://healthchecks.io) costs nothing at this scale. If your modem's page is shaped differently, or you find a fifth thing that makes a parser lie, I'd like to hear about it.

---

Friday, October 30: 259 polls, zero uncorrectable errors, zero events, all 32 channels locked every time. It's the dullest day of data I own, and I'd like a few hundred more.
