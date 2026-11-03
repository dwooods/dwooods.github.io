---
title: "I Built a Smoke Alarm for My Internet (and Then Muted It)"
date: 2026-11-03
draft: true
tags: ["docker", "synology", "portainer", "networking", "cable-modem", "monitoring", "python", "self-hosted"]
description: "A Python container on my Synology NAS that logs my cable modem's signal, built after three modems, three tech visits and a year of drops."
summary: "My internet had been dropping for a year and nothing would tell me when. So Claude and I built a monitor on my NAS, which then recorded nothing at all for half of what I built it to watch."
featuredImage: "/images/hero-modem-monitor-synology.jpeg"
featuredImagePreview: "/images/hero-modem-monitor-synology.jpeg"
---

At 6:54 PM on a Sunday, my internet died. At 6:54 PM on Monday, it died again, to the minute. Claude's first question was whether something was spiking the power at that exact minute. Then it floated interference from a cell tower. Both theories were dead by midweek.

None of this was new. I've had Astound for over a year, and the connection has always dropped now and then, rarely enough that I shrugged and rebooted something. Over the last couple of months it got worse, with longer outages. I'm also job hunting, which means video interviews from home, and an outage in the middle of one is the kind of thing you rehearse at 3 a.m.

The real problem was that I never knew when it dropped or how often. As far as I could tell, nothing on my modem, my router or the provider's side would tell me, so unless I happened to be using the connection, an outage didn't exist. My evidence was my memory, which is not a measuring instrument.

So I did what I do these days: I opened a chat with Claude and built a smoke alarm. It's a small Python program in a Docker container on my Synology NAS that checks the internet every minute, reads the modem's own signal numbers every five minutes, writes everything to files, draws a dashboard, and, for about four days, tapped my phone when something looked wrong.

This post is about how that went: three modems, three tech visits, a monitor that spent four days recording nothing for half of what it was built to watch, and a result I'd like to trust more than I do.

![The monitor's dashboard, 7-day view: status tiles, two outages on October 29, and signal-loss events by hour](/images/modem-monitor-dashboard.jpeg)

## Why I Built This

The week before I built it was a blur of changes. On Sunday, October 25, I put in a new Netgear modem, and my ASUS router refused to see the internet until I power-cycled the modem. The cause was me. I'd plugged my laptop into the new modem first to test it, and cable modems, as far as I understand, tie themselves to the first device they meet until they're restarted.

A tech came Monday, fixed the outside connector where the line meets the house, and updated the connectors inside. He also mentioned that Netgear modems sometimes have trouble with Astound, which I'm passing along as what he said, not something I can prove. It dropped again that evening.

Tuesday's tech replaced the outside connector again, redid the cables, and added a 3-way splitter to the line feeding the modem. The reason, as he put it to me, was to dampen the signal more, so apparently the line was too strong at the modem, not too weak. He also suggested the power block in my wiring box, which fed the router, the modem, a switch and a door-opener Wi-Fi unit, might be causing interference. I wasn't sure I bought it, but I pulled it out that afternoon, because that was cheaper than being right. Around then my notes had the errors following one channel when the modem moved it to a different frequency, which was enough to kill the cell-tower theory.

![The wiring box: the coax line that feeds the modem runs in from the top and across, with the 3-way splitter the tech added in the middle of the frame](/images/wiring-box-splitter.jpeg)
*The coax that feeds the modem, with the tech's 3-way splitter in the middle, after the cleanup.*

That same Tuesday I ordered an ARRIS SB6190 as a controlled test, and it went in on Wednesday. I had also bought a used Motorola modem, until a tech told me never to use a used one (he said they heat up inside and wear out over time), and I'm sending it back unopened. The first tech told me the SB6190 was the one to get and that Astound supports it. The rule I took from that: new modems only, and ones your provider recommends.

Every one of those fixes was a guess made without data. Each ended with "let's see if it holds," and the only way I could see was to be online when it didn't. So I wanted a witness, not a fix: something that would sit on the network, log the connection every minute, read the modem's own numbers, and tell me when something happened. I wanted to hand a tech a timeline instead of a feeling.

I also had a place to run it. My NAS already ran Docker, which is a way of packaging a small program with everything it needs so it behaves the same anywhere, so one more small container was cheap.

## Architecture & Tech Stack

A cable modem is the box that turns the coax line from the street into Ethernet, and it keeps a tiny web page about itself that nobody reads (on most modems it lives at 192.168.100.1). That page lists the channels the modem listens on (downstream, 32 on mine) and talks on (upstream, 2 on mine), each channel's signal strength, and a running count of uncorrectable errors, which are chunks of data the modem couldn't repair. It also has an event log, and the entry I came to know best is "No Ranging Response received - T3 time-out," which means the modem asked the provider's equipment for an adjustment and got silence. That page is the whole data source.

![Diagram: the modem's page and three internet checks feed a Python container on the NAS, which writes CSV files, serves a dashboard, sends queued alerts through ntfy and Gmail, and pings healthchecks.io](/images/modem-monitor-synology-architecture.svg)

| Piece | What it does |
|---|---|
| Python script, standard library only | Checks three public addresses every 60 seconds and calls an outage after two failed rounds; reads the modem page and event log every five minutes |
| Six CSV files | Outages, issues, events, polls, per-channel readings and connectivity checks, kept for later analysis |
| Dashboard | Charts drawn on the server as SVG, so it still loads while the internet is down |
| [ntfy](https://ntfy.sh) and Gmail | A push to my phone and an email, queued while offline and sent when the connection returns |
| [healthchecks.io](https://healthchecks.io) | A heartbeat for when the internet is down and the NAS can't send anything: the pings stop, so an outside service tells me |

It runs in a `python:3.12-slim` container on my DS918+, deployed as a stack in [Portainer](https://www.portainer.io), a web dashboard for managing containers. The alerts queue because the thing that notices an outage can't report it over the connection that just died. The dashboard's "no CDN" detail means it doesn't borrow code from third-party servers (a CDN, in web-speak), so it still loads when the thing that's broken is the internet. And each five-minute poll writes a summary row plus one row per channel, which is why the per-channel file is the one that grows.

### Tools & AI Assist

Claude wrote the original monitor in an earlier chat and tested it against a simulated modem, which is how it shipped a bug that only appears when a real Gmail login fails: the phone push repeated every minute. In this chat Claude reproduced it (five failed email sends, five pushes) and fixed it with a three-line flag. It also walked me through deployment, read the modem's pages, wrote the patches and ran the CSV analysis that found the bug in the third challenge below.

The misses: it assumed my NAS ran Container Manager, guessed wrong about why Google blocked my app password, set up a 24/7 heartbeat without noticing the NAS sleeps at night, told me a CSV contained data it didn't, and tied the power block to a dip in signal using the wrong date. No other AI tools. It was Claude from start to finish.

## Key Challenges

### Claude assumed the wrong NAS, and Google said no

The original README walked through Container Manager, Synology's newer container app. My NAS runs the older Docker package with Portainer. Different tools, different steps, so Claude redid the deployment as a Portainer stack. That redo exposed two details. Portainer's web editor wants absolute folder paths on the NAS instead of relative ones, and it passes the variables you type into its form through a file called `stack.env`, so the compose file has to point at it.

Then, alerts. I wanted to reuse my NAS's own email notifications so the monitor wouldn't need another credential. It can't: DSM signs in to Google with OAuth, a token handshake a container can't borrow. So the monitor needed a Gmail app password, and Google's page for those said "setting not available." Claude guessed Advanced Protection and sent me to a URL that returned a 404. The real cause was on my screen the whole time. 2-Step Verification was off, and the page said "Turn on." I turned it on, made the password, and the first alert landed a few minutes later. That first alert was about an event from before the monitor existed: the modem keeps its own log, and the monitor reads it on startup. A later restart didn't repeat it, so the monitor remembers what it has already seen. The ntfy pushes only showed up after I pulled to refresh the phone app, and I never found out why.

The alarm earned its keep fast. Around 5:30 PM, less than an hour after I deployed it, the modem logged "RCS Partial Service," which I read as it losing some of its channels, and the error count jumped by 63,704 between two polls. My phone buzzed. It was the first time the monitor told me something I couldn't have known.

### The heartbeat that would have paged me every night

The monitor has a blind spot: when the internet is down, it can't tell me, because ntfy and Gmail are on the far side of the outage. So I added a dead-man's switch. Every loop the script pings a URL at healthchecks.io, but only while the internet is up. If the pings stop, that service, which lives outside my network, emails me and pushes a notification. It's the one alert that still works when my connection is the thing that died, and as a side effect it also catches the monitor itself dying.

Claude set it up to run around the clock. My NAS powers off at 11 PM and back on at 7 AM, so left alone it would have declared the monitor dead every night. Claude caught that late, as a reminder tacked onto the end of an answer ("don't forget the healthchecks cron change before 23:00 tonight"), and I asked why it hadn't said so earlier. Fair question. The fix was a schedule instead of a fixed interval:

```
Schedule:   */2 7-22 * * *    (every second minute, 07:00 through 22:59)
Time zone:  America/Los_Angeles
Grace:      10 minutes
```

The time zone matters, because without it the service reads the schedule in UTC and the quiet hours land mid-afternoon. The grace window gives the NAS time to boot at 7 before anyone panics.

I tested it the only way that counts, by stopping the container on purpose. The email arrived. The phone push needed its own integration and a test message ("TEST is DOWN") before it showed up, and I never saw the matching "UP" on the phone. An alarm you've never set off is a hope.

That's the design. Here's where it caught me instead. That same evening, healthchecks emailed that the monitor was back up after 1 hour and 11 minutes of downtime. The file running on my NAS wasn't the one I thought. A different version, with a feature I didn't have and without the heartbeat, had replaced mine, so the pings had stopped. Most likely I'd uploaded an old copy over the new one, which is easy to do when a file has been through this many chats and downloads. Claude merged the two into one file and tested it, and I uploaded it. A dead-man's switch catches your mistakes too, and mine caught one on day one.

### Four days of blank columns

The monitor had columns for upstream power, how loudly the modem has to shout to be heard by the provider. High upstream power is one classic sign of trouble on the line, so it was the number I most wanted. Four days in, I asked Claude to analyze the CSV for a before-and-after. It opened `polls.csv`, 763 polls, and found `us_locked` was 0 on every row and both upstream power columns were empty. The monitor had never recorded a single upstream reading. And Claude had told me, earlier, that the file would contain upstream power. It had read the column names in the code and assumed.

Nothing complained, because a scraper that finds nothing doesn't raise an error. It writes a blank. To find out why, I needed the raw page, so Claude asked me to save the modem's page source and told me to press Cmd+U. On a Mac in Chrome that's Option+Cmd+U, and Cmd+U does nothing useful. It's a tiny miss, but I'm keeping a list. Once Claude had the saved page, it spotted the cause: the modem's HTML leaves out the closing row tags in the upstream table.

```html
<tr><td>1</td><td> Locked </td> ... <td>46.50 dBmV</td><tr><td>2</td> ... <td>45.75 dBmV</td>
</table>
```

Browsers shrug and render that fine, which is why I could see the numbers myself the whole time. My parser trusted closing tags, so each new `<tr>` meant "throw away the unfinished row," and the last row vanished at `</table>`. Two rows in, zero out. Before changing anything, Claude ran the old parser against the saved page and got zero upstream rows, which is the only way to know a fix is fixing the thing you think it is. The fix is to close the open row whenever a new one starts or the table ends:

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

I tested it against the real page. The old parser found 0 upstream rows and the fixed one found 2 (46.5 and 45.75 dBmV), downstream still read 32, and well-formed tables still parsed. The cost is that the upstream history for those four days is gone. All I have are two readings from screenshots: 44.5 and 43.25 dBmV on the evening of October 28, and 46.5 and 45.75 four days later. That's about 2 dB higher, from two readings, which is not a trend. The running container confirms it: since 7:37 AM on November 1, all 430 polls (to this afternoon) show both upstream channels locked, at 45.75 and 46.5 dBmV, and those two numbers haven't moved.

There's one more thing in that data I can't explain. The dashboard's outage table has two entries, both on the morning of October 29: 35 minutes starting at 8:38 AM and 15 minutes starting at 9:19 AM, 50.6 minutes in all, logged as the modem being unreachable. The modem's uptime counter kept counting through both, and the seven-day view shows zero modem restarts, so the modem itself never rebooted. A tech visit was scheduled for that day between 8 AM and noon, so the likeliest explanation is that he was working on the line, though I haven't confirmed it.

## Lessons Learned & What's Next

The first evening the monitor ran, about six hours, it logged 72,241 uncorrectable errors, 63,704 of them in a single six-minute window around 5:30 PM. On October 29 it logged 12 critical events by 10:36 AM and then none, which fits the tech finishing somewhere between 10 and 11 that morning, as best I remember. From noon that day until the morning of November 1 (650 polls) it logged 61 uncorrectable errors and no critical events, and all 32 downstream channels stayed locked on every poll.

It didn't stay quiet. On the afternoon of November 1 the line came back: by my count of the dashboard's bars, four signal-loss events between about 1:50 and 5:25 PM, including an "RCS Partial Service" and a "T3 time-out," and one check at 1:51 PM that added about 5,400 uncorrectable errors. On November 3 it logged two more, a partial-service warning at 9:29 AM and a T3 time-out at 11:58 AM. The three-day totals on the dashboard read 14,246 new uncorrectable errors and six signal-loss events, with zero outages, zero modem restarts and 32 of 32 channels locked. That's far below the first evening's 72,241, and it is not nothing. Over the whole seven-day view the dashboard shows 88,228 uncorrectable errors, 21 signal-loss events, two outages and no restarts, so about 82 percent of the week's errors landed in the first six hours. All of it happened after I muted the alerts.

![The dashboard's color-coded event log: two signal-loss events on November 3 and November 1, with a DHCP renewal notice between them, MAC addresses masked](/images/modem-monitor-events.jpeg)
*The event log as the dashboard shows it, newest first: red is critical, amber is a warning, blue is a notice. The modem and provider hardware addresses are masked.*

That was the good news for a while, and the whole record is the timeline I wanted to hand a tech: what changed, what the line did before, and what it did after. A tech can argue with a feeling. It's harder to argue with a few thousand polls. Here's the honest version. My "before" is six hours and a morning, because the monitor didn't exist for the first two tech visits. I changed at least five things in a week (the outside connector twice, the cables, the power block, the modem and finally the outside line), so I can't tell you which one mattered. And four quiet days couldn't promise a fifth, and didn't deliver one.

The lesson I'd hand to anyone with a different project: zero is not the same as quiet. A sensor that fails silently looks exactly like a calm system, so before you trust a clean chart, find one row where the thing you care about has an actual number in it. If I'd opened the CSV on day one and looked for a single upstream reading, I'd have saved four days. The better version is a monitor that shouts about its own blind spots. An alert for "this column has been empty for an hour" would take a few lines, and I haven't written them yet. The other lesson is about timing. Get the logging running before the people with the wrenches arrive, because I got mine going on the evening of day four, after two of the three visits.

The AI lesson sits next to that one. Claude did the typing: the parser, the alert rules, the container, the diagram. It also told me the upstream columns would hold data, going only by their names, and I believed it. Claude was fast at going from "here's the file" to "here's the missing tag," and equally fast at describing a column it had never seen filled. The second one was mine to catch, and I didn't, until the data was already four days old.

A few days in, I turned the alerts off and went back to reading the dashboard. Nothing seemed to need alerting on, the tech fixes looked like they had worked, and I wanted to keep the server off at night. I figured I could check the monitor if I needed to. The Gmail app password is revoked and the heartbeat is paused, which seems like the right amount of caution for a monitor that spent four days not looking at half its data. The monitor keeps recording. The per-channel file trims itself at 60 days, since it was growing by about half a megabyte a day. What I still don't have is the thing I wanted at the start: as far as I can tell, no one will tell me when the line goes bad. I'll just have the timeline.

## Try This Yourself

The script, the Portainer stack file and a template for the settings are in [examples/modem-monitor](https://github.com/dwooods/dwooods.github.io/tree/main/examples/modem-monitor) in this blog's repo. If you want to try the idea, open your modem's own page, look at the event log and the uncorrectable errors, and see whether anything is writing them down for you. With a home server, a small container that reads that page every few minutes is an evening's work, and a heartbeat from [healthchecks.io](https://healthchecks.io) costs nothing at this scale. If your modem's page is shaped differently, or you find a fifth thing that makes a parser lie, I'd like to hear about it.

---

Friday, October 30: 259 polls, zero uncorrectable errors, zero events, all 32 channels locked every time. It's the dullest day of data I own, and I'd like a few hundred more.
