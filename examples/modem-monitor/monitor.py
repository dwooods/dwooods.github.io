#!/usr/bin/env python3
"""
Cable modem monitor for the ARRIS SB6190 (DOCSIS 3.0).

Runs forever. Every CHECK_SECONDS it tests internet reachability; every
MODEM_POLL_SECONDS it scrapes the modem's Status, Product Information and
Event Log pages. Everything is appended to CSV files in DATA_DIR, and a small
web dashboard is served on DASHBOARD_PORT.

Alerts go to ntfy (push) and email. Alerts raised while the internet is down
are queued and sent as soon as it comes back.

Standard library only: no pip installs needed.
"""

import csv
import html
import json
import os
import re
import smtplib
import socket
import threading
import time
import traceback
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta
from email.message import EmailMessage
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

# --------------------------------------------------------------------------
# Configuration (environment variables)
# --------------------------------------------------------------------------

def env(name, default=""):
    v = os.environ.get(name, default)
    return v.strip() if isinstance(v, str) else v

MODEM_URL = env("MODEM_URL", "http://192.168.100.1").rstrip("/")
DATA_DIR = env("DATA_DIR", "/data")
CHECK_SECONDS = int(env("CHECK_SECONDS", "60"))
MODEM_POLL_SECONDS = int(env("MODEM_POLL_SECONDS", "300"))
DOWN_AFTER_FAILURES = int(env("DOWN_AFTER_FAILURES", "2"))
CHECK_TARGETS = [t.strip() for t in env("CHECK_TARGETS", "1.1.1.1:443,8.8.8.8:53,9.9.9.9:443").split(",") if t.strip()]
UNCORR_ALERT_THRESHOLD = int(env("UNCORR_ALERT_THRESHOLD", "1000"))
ALERT_COOLDOWN_MIN = int(env("ALERT_COOLDOWN_MIN", "30"))
DASHBOARD_PORT = int(env("DASHBOARD_PORT", "8088"))
DASHBOARD_URL = env("DASHBOARD_URL", "")  # optional, included in alerts
HEALTHCHECK_URL = env("HEALTHCHECK_URL")  # optional dead-man ping (healthchecks.io)
CHANNELS_RETENTION_DAYS = int(env("CHANNELS_RETENTION_DAYS", "60"))  # per-channel rows only; 0 = keep everything

NTFY_URL = env("NTFY_URL", "https://ntfy.sh").rstrip("/")
NTFY_TOPIC = env("NTFY_TOPIC")
NTFY_TOKEN = env("NTFY_TOKEN")

SMTP_HOST = env("SMTP_HOST")
SMTP_PORT = int(env("SMTP_PORT", "587"))
SMTP_SECURITY = env("SMTP_SECURITY", "starttls").lower()  # starttls | ssl | none
SMTP_USER = env("SMTP_USER")
SMTP_PASS = env("SMTP_PASS")
EMAIL_FROM = env("EMAIL_FROM") or SMTP_USER
EMAIL_TO = [e.strip() for e in env("EMAIL_TO").split(",") if e.strip()]

HTTP_TIMEOUT = 10
CRITICAL_PRIORITIES = ("critical", "error", "emergency", "alert")

# --------------------------------------------------------------------------
# Logging helpers
# --------------------------------------------------------------------------

def now():
    return datetime.now().replace(microsecond=0)

def ts(dt=None):
    return (dt or now()).strftime("%Y-%m-%d %H:%M:%S")

def log(msg):
    print(f"{ts()} {msg}", flush=True)

# --------------------------------------------------------------------------
# CSV storage
# --------------------------------------------------------------------------

FILES = {
    "connectivity": ["time", "internet_ok", "modem_reachable", "targets_ok", "latency_ms"],
    "polls": ["time", "uptime_minutes", "modem_rebooted", "ds_locked", "ds_total", "us_locked",
              "ds_power_min", "ds_power_max", "snr_min", "us_power_min", "us_power_max",
              "corrected_total", "uncorrectable_total", "corrected_delta", "uncorrectable_delta",
              "worst_channel", "worst_channel_uncorr_delta", "new_events", "new_critical_events"],
    "channels": ["time", "direction", "channel", "lock_status", "modulation", "channel_id",
                 "frequency_mhz", "power_dbmv", "snr_db", "corrected", "uncorrectables"],
    "events": ["first_seen", "modem_time", "priority", "description"],
    "outages": ["start", "end", "duration_minutes", "kind", "detail"],
    "issues": ["time", "kind", "detail"],
}

_lock = threading.Lock()

def path(name):
    return os.path.join(DATA_DIR, f"{name}.csv")

def append(name, rows):
    if not rows:
        return
    p = path(name)
    with _lock:
        new = not os.path.exists(p)
        with open(p, "a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(FILES[name])
            for r in rows:
                w.writerow([r.get(k, "") for k in FILES[name]])

def read(name):
    p = path(name)
    if not os.path.exists(p):
        return []
    with _lock:
        with open(p, newline="") as f:
            return list(csv.DictReader(f))

def prune(name, days):
    """Drop rows older than `days` (first column is the timestamp). Rewrites the file atomically while holding
    the same lock the writers use. Rows whose first column is not a timestamp are kept. Returns rows dropped."""
    if days <= 0:
        return 0
    p = path(name)
    cutoff = ts(now() - timedelta(days=days))
    with _lock:
        if not os.path.exists(p):
            return 0
        with open(p, newline="") as f:
            rows = list(csv.reader(f))
        if len(rows) < 2:
            return 0
        head, body = rows[0], rows[1:]
        keep = [r for r in body if not r or not r[0][:4].isdigit() or r[0] >= cutoff]
        dropped = len(body) - len(keep)
        if dropped:
            tmp = p + ".tmp"
            with open(tmp, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(head)
                w.writerows(keep)
            os.replace(tmp, p)
        return dropped

def issue(kind, detail):
    append("issues", [{"time": ts(), "kind": kind, "detail": detail}])

# --------------------------------------------------------------------------
# HTML table parsing (SB6190 pages are plain tables)
# --------------------------------------------------------------------------

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables, self._stack, self._row, self._cell = [], [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._stack.append([])
        elif tag == "tr" and self._stack:
            self._flush_row()  # the SB6190 upstream table leaves </tr> out; keep the unclosed row
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row.append(re.sub(r"\s+", " ", "".join(self._cell)).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None and self._stack:
            self._stack[-1].append(self._row)
            self._row = None
        elif tag == "table" and self._stack:
            self._flush_row()
            self.tables.append(self._stack.pop())

    def _flush_row(self):
        if self._row is not None and self._stack:
            if self._cell is not None:
                self._row.append(re.sub(r"\s+", " ", "".join(self._cell)).strip())
                self._cell = None
            if self._row:
                self._stack[-1].append(self._row)
        self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

def tables(page_html):
    p = TableParser()
    p.feed(page_html)
    return p.tables

def find_table(all_tables, title):
    for t in all_tables:
        for row in t[:2]:
            if row and title.lower() in row[0].lower():
                return t
    return None

def num(s):
    m = re.search(r"-?\d+(?:\.\d+)?", s or "")
    return float(m.group()) if m else None

def fetch(url_path):
    req = urllib.request.Request(MODEM_URL + url_path, headers={"User-Agent": "modem-monitor"})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
        return r.read().decode("utf-8", "replace")

def parse_status(page):
    t = tables(page)
    ds, us = [], []
    dst = find_table(t, "Downstream Bonded Channels")
    if dst:
        for r in dst:
            if len(r) >= 9 and r[0].isdigit():
                ds.append({"channel": r[0], "lock_status": r[1], "modulation": r[2], "channel_id": r[3],
                           "frequency_mhz": num(r[4]), "power_dbmv": num(r[5]), "snr_db": num(r[6]),
                           "corrected": int(num(r[7]) or 0), "uncorrectables": int(num(r[8]) or 0)})
    ust = find_table(t, "Upstream Bonded Channels")
    if ust:
        for r in ust:
            if len(r) >= 7 and r[0].isdigit():
                us.append({"channel": r[0], "lock_status": r[1], "modulation": r[2], "channel_id": r[3],
                           "frequency_mhz": num(r[5]), "power_dbmv": num(r[6])})
    if not ds:
        raise ValueError("No downstream channel table found on the status page")
    return ds, us

def parse_uptime_minutes(page):
    text = re.sub(r"<[^>]+>", " ", page)
    text = html.unescape(re.sub(r"\s+", " ", text))
    m = re.search(r"Up\s*Time\s*:?\s*(\d+)\s*d(?:ays?)?\s*:?\s*(\d+)\s*h\s*:?\s*(\d+)\s*m", text, re.I)
    if m:
        d, h, mi = map(int, m.groups())
        return d * 1440 + h * 60 + mi
    m = re.search(r"Up\s*Time\s*:?\s*(\d+)\s*days?\s*(\d+)h:(\d+)m", text, re.I)
    if m:
        d, h, mi = map(int, m.groups())
        return d * 1440 + h * 60 + mi
    return None

def is_critical(priority):
    """SB6190 logs priority as a bare number ("3"); Netgear as "Critical (3)". 1-3 = critical or worse."""
    p = priority.lower()
    if any(w in p for w in CRITICAL_PRIORITIES):
        return True
    m = re.search(r"\d+", p)
    return bool(m) and int(m.group()) <= 3

SIGNAL_KEYWORDS = ("rcs partial service", "mdd timeout", "mdd message timeout", "loss of sync",
                   "sync timing", "t3 time", "t4 time", "lock failure")

def is_signal_event(description):
    """Signal-loss events the SB6190 logs at warning priority (5) but that matter."""
    d = description.lower()
    return any(k in d for k in SIGNAL_KEYWORDS)

def parse_events(page):
    t = tables(page)
    out = []
    for table in t:
        if table and table[0][:1] and table[0][0].lower() == "time":
            for r in table[1:]:
                if len(r) >= 3 and r[2]:
                    out.append({"modem_time": r[0], "priority": r[1], "description": r[2]})
    return out

# --------------------------------------------------------------------------
# Alerts (queued while offline)
# --------------------------------------------------------------------------

_queue = []
_last_alert = defaultdict(lambda: datetime.min)

def queue_alert(title, body, priority="default", key=None, cooldown=True):
    if key and cooldown:
        if now() - _last_alert[key] < timedelta(minutes=ALERT_COOLDOWN_MIN):
            log(f"alert suppressed by cooldown: {title}")
            return
        _last_alert[key] = now()
    if DASHBOARD_URL:
        body = f"{body}\n\nDashboard: {DASHBOARD_URL}"
    _queue.append({"title": title, "body": body, "priority": priority, "queued": ts()})
    log(f"alert queued: {title}")

def send_ntfy(a):
    if not NTFY_TOPIC:
        return True
    body = a["body"]
    if a["queued"] != ts():
        body = f"(raised {a['queued']})\n{body}"
    req = urllib.request.Request(f"{NTFY_URL}/{NTFY_TOPIC}", data=body.encode("utf-8"), method="POST")
    req.add_header("Title", a["title"].encode("ascii", "replace").decode())
    req.add_header("Priority", a["priority"])
    req.add_header("Tags", "satellite_antenna")
    if NTFY_TOKEN:
        req.add_header("Authorization", f"Bearer {NTFY_TOKEN}")
    urllib.request.urlopen(req, timeout=HTTP_TIMEOUT).read()
    return True

def send_email(batch):
    if not (SMTP_HOST and EMAIL_TO):
        return True
    msg = EmailMessage()
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(EMAIL_TO)
    msg["Subject"] = batch[0]["title"] if len(batch) == 1 else f"Modem monitor: {len(batch)} alerts"
    parts = [f"[{a['queued']}] {a['title']}\n{a['body']}" for a in batch]
    msg.set_content("\n\n---\n\n".join(parts))
    cls = smtplib.SMTP_SSL if SMTP_SECURITY == "ssl" else smtplib.SMTP
    with cls(SMTP_HOST, SMTP_PORT, timeout=20) as s:
        if SMTP_SECURITY == "starttls":
            s.starttls()
        if SMTP_USER:
            s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
    return True

def flush_alerts():
    global _queue
    if not _queue:
        return
    batch = list(_queue)
    try:
        for a in batch:
            if not a.get("ntfy_done"):
                send_ntfy(a)
                a["ntfy_done"] = True  # don't re-push if only the email leg fails
        send_email(batch)
        _queue = _queue[len(batch):]
        log(f"sent {len(batch)} alert(s)")
    except Exception as e:
        log(f"alert send failed, will retry: {e}")

# --------------------------------------------------------------------------
# Connectivity checks
# --------------------------------------------------------------------------

def ping_healthcheck():
    """Tell the external dead-man service we're alive. Silent on failure."""
    if not HEALTHCHECK_URL:
        return
    try:
        urllib.request.urlopen(urllib.request.Request(HEALTHCHECK_URL, headers={"User-Agent": "modem-monitor"}),
                               timeout=5).read()
    except Exception as e:
        log(f"healthcheck ping failed: {e}")

def tcp_ok(target):
    host, _, port = target.rpartition(":")
    start = time.monotonic()
    try:
        with socket.create_connection((host, int(port)), timeout=3):
            return (time.monotonic() - start) * 1000
    except OSError:
        return None

def modem_reachable():
    try:
        fetch("/cgi-bin/swinfo")
        return True
    except Exception:
        return False

class Monitor:
    def __init__(self):
        self.failures = 0
        self.down_since = None
        self.down_modem_unreachable = False
        self.last_poll = None
        self.prev = None          # previous status snapshot
        self.prev_uptime = None
        self.boot_id = 0
        self.seen_events = set()
        for e in read("events"):
            self.seen_events.add(self._event_key(e))
        polls = read("polls")
        if polls:
            last = polls[-1]
            try:
                self.prev_uptime = int(float(last["uptime_minutes"])) if last["uptime_minutes"] else None
            except ValueError:
                pass

    @staticmethod
    def _event_key(e):
        return f"{e['modem_time']}|{e['priority']}|{e['description']}"

    # ---- connectivity -------------------------------------------------
    def check(self):
        results = [tcp_ok(t) for t in CHECK_TARGETS]
        ok = [r for r in results if r is not None]
        internet = bool(ok)
        reach = modem_reachable()
        append("connectivity", [{"time": ts(), "internet_ok": int(internet), "modem_reachable": int(reach),
                                 "targets_ok": f"{len(ok)}/{len(results)}",
                                 "latency_ms": round(min(ok), 1) if ok else ""}])
        if internet:
            if self.down_since:
                self._recovered()
            self.failures = 0
        else:
            self.failures += 1
            if self.failures == 1:
                self._first_failure = now() - timedelta(seconds=CHECK_SECONDS // 2)
                self._first_failure_unreachable = not reach
            if self.failures >= DOWN_AFTER_FAILURES and not self.down_since:
                self.down_since = self._first_failure
                self.down_modem_unreachable = self._first_failure_unreachable or not reach
                where = "modem not responding" if self.down_modem_unreachable else "modem up, no internet"
                log(f"INTERNET DOWN since {ts(self.down_since)} ({where})")
                issue("internet_down", where)
                queue_alert("Internet DOWN",
                            f"No internet since about {self.down_since:%-I:%M %p} ({where}). "
                            "You will get this when the connection is back.", "high")
        return internet

    def _recovered(self):
        end = now()
        mins = round((end - self.down_since).total_seconds() / 60, 1)
        kind = "modem_unreachable" if self.down_modem_unreachable else "internet_down"
        append("outages", [{"start": ts(self.down_since), "end": ts(end), "duration_minutes": mins,
                            "kind": kind, "detail": ""}])
        issue("internet_restored", f"after {mins} min")
        log(f"INTERNET RESTORED after {mins} min")
        queue_alert("Internet restored",
                    f"Outage from {self.down_since:%-I:%M %p} to {end:%-I:%M %p} ({mins} min). "
                    "Check the modem event log and Status page.", "high", cooldown=False)
        self.down_since = None
        self.poll_modem()  # capture what the modem saw right away

    # ---- modem scrape ---------------------------------------------------
    def poll_modem(self):
        self.last_poll = time.monotonic()
        t = now()
        try:
            ds, us = parse_status(fetch("/cgi-bin/status"))
        except Exception as e:
            log(f"status scrape failed: {e}")
            issue("modem_scrape_failed", str(e)[:200])
            return
        uptime = None
        try:
            uptime = parse_uptime_minutes(fetch("/cgi-bin/swinfo"))
        except Exception as e:
            log(f"uptime scrape failed: {e}")
        events = []
        try:
            events = parse_events(fetch("/cgi-bin/eventlog"))
        except Exception as e:
            log(f"event log scrape failed: {e}")

        rebooted = uptime is not None and self.prev_uptime is not None and uptime < self.prev_uptime
        if rebooted:
            self.boot_id += 1
            issue("modem_rebooted", f"uptime reset to {uptime} min")
            queue_alert("Modem restarted",
                        f"The modem's uptime reset to {uptime} minutes, so it restarted on its own or lost power.",
                        "high", key="reboot")
        if uptime is not None:
            self.prev_uptime = uptime

        # channel rows
        stamp = ts(t)
        rows = [dict(c, time=stamp, direction="down") for c in ds]
        rows += [dict(c, time=stamp, direction="up", snr_db="", corrected="", uncorrectables="") for c in us]
        append("channels", rows)

        # deltas per downstream channel
        cur = {c["channel_id"]: (c["corrected"], c["uncorrectables"]) for c in ds}
        corr_delta = unc_delta = 0
        worst, worst_d = "", 0
        if self.prev is not None:
            for cid, (co, un) in cur.items():
                pco, pun = self.prev.get(cid, (0, 0))
                dco = co - pco if co >= pco else co
                dun = un - pun if un >= pun else un
                corr_delta += dco
                unc_delta += dun
                if dun > worst_d:
                    worst, worst_d = cid, dun
        self.prev = cur

        # events
        new_events, new_crit = [], []
        for e in events:
            key = self._event_key(e)
            if "not established" in e["modem_time"].lower():
                key += f"|boot{self.boot_id}"
            if key in self.seen_events:
                continue
            self.seen_events.add(key)
            new_events.append({"first_seen": stamp, **e})
            if is_critical(e["priority"]) or is_signal_event(e["description"]):
                new_crit.append(e)
        append("events", new_events)

        locked = [c for c in ds if c["lock_status"].lower() == "locked"]
        powers = [c["power_dbmv"] for c in ds if c["power_dbmv"] is not None]
        snrs = [c["snr_db"] for c in ds if c["snr_db"] is not None]
        uspow = [c["power_dbmv"] for c in us if c["power_dbmv"] is not None]
        append("polls", [{
            "time": stamp, "uptime_minutes": uptime if uptime is not None else "", "modem_rebooted": int(rebooted),
            "ds_locked": len(locked), "ds_total": len(ds),
            "us_locked": len([c for c in us if c["lock_status"].lower() == "locked"]),
            "ds_power_min": min(powers) if powers else "", "ds_power_max": max(powers) if powers else "",
            "snr_min": min(snrs) if snrs else "",
            "us_power_min": min(uspow) if uspow else "", "us_power_max": max(uspow) if uspow else "",
            "corrected_total": sum(c["corrected"] for c in ds),
            "uncorrectable_total": sum(c["uncorrectables"] for c in ds),
            "corrected_delta": corr_delta, "uncorrectable_delta": unc_delta,
            "worst_channel": worst, "worst_channel_uncorr_delta": worst_d,
            "new_events": len(new_events), "new_critical_events": len(new_crit),
        }])

        if unc_delta >= UNCORR_ALERT_THRESHOLD:
            issue("uncorrectable_spike", f"{unc_delta} new uncorrectables (worst channel ID {worst}: {worst_d})")
            queue_alert("Uncorrectable errors spiking",
                        f"{unc_delta:,} new uncorrectable codewords since the last check "
                        f"(worst: channel ID {worst}, {worst_d:,}).", key="uncorr")
        if len(locked) < len(ds):
            issue("channels_unlocked", f"{len(ds) - len(locked)} of {len(ds)} downstream channels not locked")
        if new_crit:
            for e in new_crit:
                issue("critical_event", f"{e['priority']}: {e['description'][:150]}")
            lines = "\n".join(f"- {e['modem_time']}: {e['description'][:160]}" for e in new_crit[:8])
            more = f"\n(+{len(new_crit) - 8} more)" if len(new_crit) > 8 else ""
            queue_alert(f"Modem logged {len(new_crit)} signal-loss event(s)", lines + more, key="critical")
        log(f"poll: {len(locked)}/{len(ds)} locked, +{unc_delta} uncorr, {len(new_events)} new events, uptime {uptime}")

    def run(self):
        log(f"monitor started: modem {MODEM_URL}, data in {DATA_DIR}, dashboard port {DASHBOARD_PORT}")
        if NTFY_TOPIC or (SMTP_HOST and EMAIL_TO):
            queue_alert("Modem monitor started",
                        f"Watching {MODEM_URL}. Alerts: "
                        f"{'ntfy ' if NTFY_TOPIC else ''}{'email' if SMTP_HOST and EMAIL_TO else ''}".strip(),
                        "low", cooldown=False)
        last_prune = None
        while True:
            started = time.monotonic()
            try:
                if last_prune is None or time.monotonic() - last_prune >= 86400:
                    last_prune = time.monotonic()
                    n = prune("channels", CHANNELS_RETENTION_DAYS)
                    if n:
                        log(f"retention: dropped {n} channels.csv rows older than {CHANNELS_RETENTION_DAYS} days")
                internet = self.check()
                if self.last_poll is None or time.monotonic() - self.last_poll >= MODEM_POLL_SECONDS:
                    self.poll_modem()
                if internet:
                    ping_healthcheck()
                    flush_alerts()
            except Exception:
                log("loop error:\n" + traceback.format_exc())
            time.sleep(max(1, CHECK_SECONDS - (time.monotonic() - started)))

# --------------------------------------------------------------------------
# Dashboard (self-contained: works even while the internet is down)
# --------------------------------------------------------------------------

DASHBOARD_HTML = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="300">
<title>Modem Monitor</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--fg:#1b2230;--muted:#5d6676;--line:#dde2e9;--bad:#c0392b;--warn:#c27c0e;--ok:#1e7a46;--accent:#2a62b8;--err:#d9480f}
@media (prefers-color-scheme:dark){:root{--bg:#12161d;--card:#1a2029;--fg:#e4e8ef;--muted:#9aa4b4;--line:#2b3442;--bad:#ef8579;--warn:#e8b04a;--ok:#6fcf97;--accent:#80aef0;--err:#f08a4b}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 48px;display:flex;flex-direction:column;gap:22px}
h1{margin:0;font-size:1.5rem}h2{margin:0 0 10px;font-size:1.05rem}
.sub{color:var(--muted)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px}
.tile b{display:block;font-size:1.5rem;font-variant-numeric:tabular-nums}
.tile span{color:var(--muted);font-size:.78rem;text-transform:uppercase;letter-spacing:.05em}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:16px}
svg{width:100%;height:auto;display:block}
svg text{fill:var(--muted);font-size:13px;font-family:inherit}
.grid{stroke:var(--line)}
.s0{fill:var(--bad)}.s1{fill:var(--warn)}.s2{fill:var(--accent)}.w0{fill:var(--warn)}.w1{fill:var(--accent)}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:.85rem;color:var(--muted);margin-top:6px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:-1px}
table{border-collapse:collapse;width:100%;font-size:.88rem;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:600;font-size:.75rem;text-transform:uppercase}
.scroll{overflow-x:auto;max-height:420px;overflow-y:auto}
.bad{color:var(--bad)}.ok{color:var(--ok)}
nav{margin-top:6px}nav a{color:var(--accent);margin-right:12px}
.pri{font-weight:600;white-space:nowrap}
tr.sev-crit td{background:color-mix(in srgb,var(--bad) 9%,transparent)}
tr.sev-crit td:first-child{box-shadow:inset 4px 0 var(--bad)}
tr.sev-err td:first-child{box-shadow:inset 4px 0 var(--err)}
tr.sev-warn td:first-child{box-shadow:inset 4px 0 var(--warn)}
tr.sev-info td:first-child{box-shadow:inset 4px 0 var(--accent)}
tr.sev-crit .pri{color:var(--bad)}tr.sev-err .pri{color:var(--err)}tr.sev-warn .pri{color:var(--warn)}tr.sev-info .pri{color:var(--accent)}
</style></head><body><main>
<header><h1>Modem Monitor</h1><div class="sub">__SUBTITLE__</div>
<nav>Range: <a href="?days=1">1 day</a><a href="?days=3">3 days</a><a href="?days=7">7 days</a><a href="?days=30">30 days</a></nav>
<nav>Download CSV: <a href="/csv/outages.csv">outages</a><a href="/csv/issues.csv">issues</a><a href="/csv/events.csv">events</a><a href="/csv/polls.csv">polls</a><a href="/csv/channels.csv">channels</a><a href="/csv/connectivity.csv">connectivity</a></nav></header>
<section class="tiles">__TILES__</section>
<section class="card"><h2>Minutes without internet (per hour)</h2>__CHART1__</section>
<section class="card"><h2>Modem problems (per hour)</h2>__CHART3__
<div class="legend"><span><i style="background:var(--warn)"></i>Signal-loss events (T3/T4, sync loss, partial service)</span><span><i style="background:var(--accent)"></i>Modem restarts</span></div></section>
<section class="card"><h2>New uncorrectable errors per check</h2>__CHART2__</section>
<section class="card"><h2>Outages</h2><div class="scroll">__OUTAGES__</div></section>
<section class="card"><h2>Modem events (newest first)</h2><div class="legend" style="margin:0 0 10px"><span><i style="background:var(--bad)"></i>Critical (1-3)</span><span><i style="background:var(--err)"></i>Error (4)</span><span><i style="background:var(--warn)"></i>Warning (5)</span><span><i style="background:var(--accent)"></i>Notice / info (6+)</span></div><div class="scroll">__EVENTS__</div></section>
</main></body></html>"""

def parse_ts(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def nice_max(v):
    if v <= 0:
        return 1
    mag = 10 ** (len(str(int(v))) - 1)
    for m in (1, 2, 2.5, 5, 10):
        if v <= m * mag:
            return m * mag
    return 10 * mag

def bar_chart(labels, series, height=260, classes=None):
    """Stacked bar chart as inline SVG. series = list of lists (same length as labels)."""
    W, H, L, R, T, B = 1000, height, 70, 10, 10, 34
    n = max(1, len(labels))
    totals = [sum(s[i] for s in series) for i in range(len(labels))] or [0]
    top = nice_max(max(totals))
    if 1 <= top < 40 and top % 4:
        top = int(-(-top // 4) * 4)  # whole-number gridlines for small counts
    pw, ph = W - L - R, H - T - B
    bw = pw / n
    out = [f'<svg viewBox="0 0 {W} {H}" role="img">']
    for k in range(5):
        v = top * k / 4
        y = T + ph - ph * k / 4
        label = f"{v:,.0f}" if v == int(v) else f"{v:,.2f}".rstrip("0")
        out.append(f'<line class="grid" x1="{L}" x2="{W - R}" y1="{y:.1f}" y2="{y:.1f}"/>'
                   f'<text x="{L - 6}" y="{y + 4:.1f}" text-anchor="end">{label}</text>')
    for i in range(len(labels)):
        base = 0.0
        for si, s in enumerate(series):
            v = s[i]
            if v <= 0:
                continue
            h = ph * v / top
            y = T + ph - ph * base / top - h
            cls = classes[si] if classes else f"s{si}"
            out.append(f'<rect class="{cls}" x="{L + i * bw + bw * 0.12:.2f}" y="{y:.2f}" '
                       f'width="{max(bw * 0.76, 1):.2f}" height="{h:.2f}"><title>{html.escape(labels[i])}: {v:,.1f}</title></rect>')
            base += v
    step = max(1, -(-n // 6))  # at most about 6 axis labels so they never overlap
    for i in range(0, len(labels), step):
        x = L + i * bw + bw / 2
        out.append(f'<text x="{x:.1f}" y="{H - 12}" text-anchor="middle">{html.escape(labels[i])}</text>')
    out.append("</svg>")
    return "".join(out)

def table_html(rows, cols, empty):
    if not rows:
        return f"<p class='sub'>{empty}</p>"
    head = "".join(f"<th>{html.escape(c)}</th>" for c in cols)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(r.get(c, '')))}</td>" for c in cols) + "</tr>" for r in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

SEV_LABELS = {1: "Emergency", 2: "Alert", 3: "Critical", 4: "Error", 5: "Warning", 6: "Notice", 7: "Info", 8: "Debug"}

def severity(priority):
    """Map a modem priority ("3" on the SB6190, "Critical (3)" on the Netgear) to (css class, label)."""
    p = (priority or "").strip().lower()
    m = re.search(r"\d+", p)
    n = int(m.group()) if m else None
    if n is None:
        for k, label in SEV_LABELS.items():
            if label.lower() in p:
                n = k
                break
    if n is None:
        return "sev-info", priority or "?"
    cls = "sev-crit" if n <= 3 else "sev-err" if n == 4 else "sev-warn" if n == 5 else "sev-info"
    return cls, f"{n} - {SEV_LABELS.get(n, 'Info')}"

def clock12(s, fmt):
    """12-hour display; anything unparseable (e.g. "Time Not Established") is shown as-is."""
    try:
        return datetime.strptime(s, fmt).strftime("%b %-d, %-I:%M:%S %p")
    except (ValueError, TypeError):
        return s or ""

def events_html(rows):
    if not rows:
        return "<p class='sub'>No modem events in this range.</p>"
    head = "".join(f"<th>{c}</th>" for c in ("Seen (NAS time)", "Modem clock", "Priority", "Description"))
    body = []
    for r in rows:
        cls, label = severity(r.get("priority", ""))
        body.append(f"<tr class='{cls}'>"
                    f"<td>{html.escape(clock12(r.get('first_seen', ''), '%Y-%m-%d %H:%M:%S'))}</td>"
                    f"<td>{html.escape(clock12(r.get('modem_time', ''), '%a %b %d %H:%M:%S %Y'))}</td>"
                    f"<td><span class='pri'>{html.escape(label)}</span></td>"
                    f"<td>{html.escape(r.get('description', ''))}</td></tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"

def build_dashboard(days):
    end = now()
    since = end - timedelta(days=days)
    hours = []
    h = since.replace(minute=0, second=0)
    while h <= end:
        hours.append(h)
        h += timedelta(hours=1)
    idx = {x: i for i, x in enumerate(hours)}
    offline = [0.0] * len(hours)
    critical = [0] * len(hours)
    reboots = [0] * len(hours)

    outages = [o for o in read("outages") if (parse_ts(o["end"]) or since) >= since]
    spans = [(parse_ts(o["start"]), parse_ts(o["end"])) for o in outages]
    # an outage still in progress is not in outages.csv yet; derive it from connectivity
    conn = read("connectivity")
    ongoing_start = None
    for row in reversed(conn):
        if row["internet_ok"] == "1":
            break
        ongoing_start = parse_ts(row["time"])
    if ongoing_start:
        spans.append((ongoing_start, end))
    for s, e in spans:
        if not s or not e:
            continue
        cur = max(s, since)
        while cur < e:
            hb = cur.replace(minute=0, second=0)
            nxt = min(e, hb + timedelta(hours=1))
            if hb in idx:
                offline[idx[hb]] += round((nxt - cur).total_seconds() / 60, 1)
            cur = nxt
    for i in read("issues"):
        t = parse_ts(i["time"])
        if not t or t < since:
            continue
        hb = t.replace(minute=0, second=0)
        if hb not in idx:
            continue
        if i["kind"] == "critical_event":
            critical[idx[hb]] += 1
        elif i["kind"] == "modem_rebooted":
            reboots[idx[hb]] += 1

    polls = [p for p in read("polls") if (parse_ts(p["time"]) or since) >= since]
    events = [e for e in read("events") if (parse_ts(e["first_seen"]) or since) >= since]
    last_conn = conn[-1] if conn else {}
    last_poll = polls[-1] if polls else {}

    total_off = round(sum(offline), 1)
    unc = sum(int(float(p["uncorrectable_delta"] or 0)) for p in polls)
    status_now = "Online" if last_conn.get("internet_ok") == "1" else ("Offline" if last_conn else "No data yet")
    cls = "ok" if status_now == "Online" else "bad"
    tiles = [
        (f"<b class='{cls}'>{status_now}</b>", f"Checked {last_conn.get('time', '-')[11:16]}"),
        (f"<b>{len(outages) + (1 if ongoing_start else 0)}</b>", f"Outages, last {days} d"),
        (f"<b>{total_off:g}</b>", "Minutes offline"),
        (f"<b>{unc:,}</b>", "New uncorrectables"),
        (f"<b>{sum(critical)}</b>", "Signal-loss events"),
        (f"<b>{sum(reboots)}</b>", "Modem restarts"),
        (f"<b>{last_poll.get('ds_locked', '-')}/{last_poll.get('ds_total', '-')}</b>", "Downstream locked"),
    ]
    tiles_html = "".join(f"<div class='tile'>{v}<span>{l}</span></div>" for v, l in tiles)
    hour_labels = [(x.strftime("%-I%p") if days == 1 else f"{x.month}/{x.day} " + x.strftime("%-I%p")).lower()
                   .replace("am", "a").replace("pm", "p") for x in hours]
    chart1 = bar_chart(hour_labels, [offline], height=200)
    chart3 = bar_chart(hour_labels, [critical, reboots], height=200, classes=["w0", "w1"])
    if polls:
        def short(t):
            d = parse_ts(t)
            if not d:
                return t
            hm = d.strftime("%-I:%M%p").lower().replace("am", "a").replace("pm", "p")
            return hm if days == 1 else f"{d.month}/{d.day} {hm}"
        chart2 = bar_chart([short(p["time"]) for p in polls],
                           [[int(float(p["uncorrectable_delta"] or 0)) for p in polls]], height=220)
    else:
        chart2 = "<p class='sub'>No modem checks in this range yet.</p>"
    return (DASHBOARD_HTML
            .replace("__SUBTITLE__", html.escape(f"{MODEM_URL} · last {days} day(s) · updated {ts()} · refreshes every 5 min"))
            .replace("__TILES__", tiles_html)
            .replace("__CHART1__", chart1)
            .replace("__CHART2__", chart2)
            .replace("__CHART3__", chart3)
            .replace("__OUTAGES__", table_html(list(reversed(outages)), FILES["outages"], "No outages recorded in this range."))
            .replace("__EVENTS__", events_html(list(reversed(events))[:300])))

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urlparse(self.path)
        if u.path.startswith("/csv/"):
            name = os.path.basename(u.path)[:-4] if u.path.endswith(".csv") else ""
            if name in FILES and os.path.exists(path(name)):
                with _lock:
                    with open(path(name), "rb") as f:
                        data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", f'attachment; filename="{name}.csv"')
                self.end_headers()
                self.wfile.write(data)
                return
            self.send_error(404)
            return
        if u.path in ("/", "/index.html"):
            try:
                days = max(1, min(365, int(parse_qs(u.query).get("days", ["3"])[0])))
            except ValueError:
                days = 3
            try:
                body = build_dashboard(days).encode("utf-8")
            except Exception:
                log("dashboard error:\n" + traceback.format_exc())
                self.send_error(500)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

def serve():
    ThreadingHTTPServer(("0.0.0.0", DASHBOARD_PORT), Handler).serve_forever()

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    threading.Thread(target=serve, daemon=True).start()
    Monitor().run()
