# Modem monitor: example files

Companion files for the blog post "I Built a Smoke Alarm for My Internet (and Then Muted It)".

- `monitor.py`: the whole monitor, standard library only. It checks three public addresses every minute, reads an ARRIS SB6190's status page and event log every five minutes, writes six CSV files, serves a dashboard on port 8088, and sends queued alerts through ntfy and Gmail.
- `modem-monitor-compose.yml`: the Portainer stack I run. I checked it against the stack editor in Portainer, so this is the file I deployed, with host paths under `/volume1/docker/modem-monitor`.
- `stack.env.example`: every setting with its default. Secrets are blank. In Portainer you type these into the stack's Environment variables form instead of keeping a file.

Things to know before you copy anything:

- The parser was written against an SB6190. Other modems format their pages differently, so expect to change `parse_status`. On this one, the upstream table leaves out its closing `</tr>` tags, which is why the parser flushes an open row when a new one starts.
- An outage is two checks in a row where all three addresses (`1.1.1.1:443`, `8.8.8.8:53`, `9.9.9.9:443`) refuse a 3-second TCP connection. Change them with `CHECK_TARGETS` and the count with `DOWN_AFTER_FAILURES`. They are raw IPs, so a DNS failure on its own doesn't trip it, and the first successful check ends the outage.
- Gmail needs 2-Step Verification on and an app password, not your normal password.
- The healthchecks.io heartbeat is sent only while the internet is up. A missing ping means the connection or the monitor is down, and the check's schedule has to match when your server is on. Mine is `*/2 7-22 * * *` in my time zone, because the NAS is off from 11 PM to 7 AM.
- To mute a channel, rename its key to `OFF_<KEY>`. Alerts are skipped when `NTFY_TOPIC` or `SMTP_HOST` is unset.
- `channels.csv` grows by about half a megabyte a day, so it is trimmed to `CHANNELS_RETENTION_DAYS` (default 60).
- The ntfy topic is effectively a password: anyone who knows it can read it. Pick a long random one and never commit it.
- Put the real values in Portainer's variables form. Nothing in this folder contains credentials.
