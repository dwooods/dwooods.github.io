---
title: "Someone in Russia Tried My NAS Password: A Security Audit I Didn't Plan"
date: 2026-09-28
draft: true
tags: ["synology", "security", "tailscale", "firewall", "ssh", "nas", "dsm", "self-hosted"]
description: "A failed admin login from Russia turned into an audit of my Synology NAS: a firewall that was switched off, four default rules that allow every service from every IP, an SSH warning whose official fix is the weakest one, and why Tailscale ended up being the real answer."
summary: "One Synology Active Insight email about a failed login from Russia sent me digging through DSM's security settings. What I found was a disabled firewall, four rules that allowed nearly everything from anywhere, and a whole afternoon of confusing my LAN IP with my public one. This is the audit, the mistakes (mine and the AI's), and the parts I haven't finished yet."
---

<!-- TODO: add a featured image before publishing — a screenshot of the DSM firewall rule list with the bundled-services tooltip open would be the strongest option (redact anything identifying), or a simple diagram: internet → router → NAS, with Tailscale as the only door. -->

The email arrived at 1:41 in the afternoon, from Synology Active Insight: a failed login attempt on my NAS, user `admin`, over HTTP/HTTPS, from Russia. Advisory: "Verify if the failed login was not malicious."

I did not, at the time, feel qualified to verify that. What I did feel qualified to do was open a chat window and start asking questions, which is how a single email turned into an afternoon-long audit of every security setting on the box. This post is what I found, what I got wrong, and, because I refuse to pretend otherwise, what I still haven't finished.

## Why I built this

I didn't. That's the honest answer: nobody plans a security audit for a home NAS. The NAS holds our family's photos and movies, plus a few Docker containers I've been using for other projects (like [the virus scan that wouldn't die](/posts/clamav-synology-nas/)). It sits on a home network, and until that email, my security model was roughly "it's behind my router, so it's fine."

That model has a hole big enough to drive a botnet through: I hadn't actually checked what was reachable from outside the router, or what DSM was doing about it if something was. An email about a failed login is the mildest possible version of finding out. Nothing got in. But it made me ask what would have happened if the password had been guessed instead of failed.

## Architecture & tech stack

- **NAS**: Synology DS918+ running DSM 7.x, with the usual suspects installed: Synology Drive, Docker, and Plex in a container.
- **Container management**: Portainer, which I installed because Synology's own Docker UI wasn't as useful. Worth noting for this post: every extra web console is another login page, and Portainer's (port 9000) has to be scoped in the firewall like everything else.
- **Remote access**: Tailscale, installed directly on the NAS and acting as a subnet router, so devices on my tailnet can reach the home network from anywhere.
- **The alerting**: Synology Active Insight, the cloud service that sent the email. It also let me mute noisy events, which I'm mentioning only because it's the fastest way to make the problem *appear* solved without solving it.

### Tools & AI assist

Same setup as my other NAS projects: a long-running Claude Cowork conversation, no repo, no scripts. I pasted in the email and, later, screenshots of every DSM settings screen I opened, and we worked through them one at a time. The standing rule from the other projects still applies: Claude never logs into DSM. Every setting in this post was changed by me, by hand, following instructions.

Claude also got things wrong along the way, and some of those mistakes are the useful parts of the story, so they're staying in. Early on it told me to grab my public IP address for the Auto Block allow-list, which is the wrong IP for the job (more on that below). And when I showed it the firewall rules, its first read was that Synology had auto-generated a mess of default rules; it turned out I had built the last one myself by ticking more boxes than I'd been told to. Two people, one bad rule. I'll take my share of the blame.

## Key technical challenges

### What the email actually means

A failed `admin` login from an unfamiliar country sounds alarming and is, statistically, background noise. Synology admin panels get scanned constantly, and `admin` is the first username every scanner tries. One failed attempt is a bot testing the door, not a person targeting my photos.

The real question the email should trigger isn't "who is this?" but "why can this reach me at all?" If the DSM login page is reachable from the public internet (through a port forward, QuickConnect, or a DDNS setup), then it's exposed to every scanner on earth, and no amount of alerting changes that. If it isn't, the attempt should have been dead on arrival. I'll get to which one applies to me, because I didn't know at first, and it took a firewall screenshot to find out.

### The SSH warning, and why the official fix is the weakest one

While I was in Security Advisor, it flagged something else with a scary label: **High** severity, "SSH port has not been changed from default value." The recommended action is to change the port from 22 to something else.

That advice is real, but it's the weakest available move. Changing the port hides SSH from scanners that only check port 22. It does nothing against anyone who scans all ports, and it doesn't touch the actual problem, which is that SSH accepts passwords. The options I actually ranked, best first:

1. **Turn SSH off** if you don't use it. Zero attack surface beats any hardening. (Control Panel → Terminal & SNMP.)
2. **Key-based authentication with password login disabled.** A password can be guessed or stuffed from a leaked list; a private key that never leaves your machine can't. Even a correct guess of your password gets nothing, because the server won't accept a password at all.
3. **Don't expose SSH to the internet.** Route it through a VPN so the port only answers to trusted networks.
4. **Change the port.** Fine as an extra layer, not as the fix.

Here's the gotcha nobody mentions: DSM's Terminal & SNMP screen has an "Advanced Settings" button, and I assumed that's where the password toggle lived. It isn't. That dialog only sets the *cipher strength* (High/Medium/Low), and the setting that disables password login exists only in `/etc/ssh/sshd_config`. You can paste your public key into the user's profile through the DSM GUI, but turning off passwords means editing that file over an SSH session:

```sh
# 1. On your PC: generate a keypair (modern and short)
ssh-keygen -t ed25519

# 2. Paste the .pub file into the user's SSH Public Key field in DSM,
#    then test key login BEFORE the next step.

# 3. Only after key login works, in /etc/ssh/sshd_config:
PasswordAuthentication no
```

The order matters. Turn passwords off before confirming the key works and you've locked yourself out of SSH (recoverable through the DSM GUI, but annoying). Also worth knowing: DSM updates can quietly revert hand-edited config like this, so it's worth re-checking after major version bumps.

I have not done this yet. More on that in a moment.

### Auto Block, and the detour where I confused two IP addresses

DSM's Auto Block bans an IP after too many failed logins. Mine was already on, at 6 attempts within 3 minutes with no expiry, and I left it alone: tight enough to stop a fast brute force, loose enough that a couple of my own typos won't lock me out. The no-expiry part means bans are permanent until I clear them, which for a home NAS is exactly what I want.

The catch is that Auto Block can't tell you mistyping your own password from an attacker. It just counts. So it has an Allow list, and adding your own trusted addresses is how you avoid banning yourself. That's where I went off the rails.

I asked how to find my IP so I could allow-list it. The reply was to check a "what's my IP" service, which I did from PowerShell, where `curl` is secretly an alias for `Invoke-WebRequest`, so instead of an IP I got a wall of parsed HTML and a security warning about script execution. The fix, if you ever hit this, is one line that returns plain text:

```powershell
Invoke-RestMethod -Uri "https://api.ipify.org"
```

That got me my public IP, and it was the wrong one. When I'm at home talking to the NAS, the traffic never leaves my network, so DSM sees my PC's *private* address (192.168.x.x), not the public IP my ISP hands out. The public IP is what the internet sees; it's irrelevant to LAN traffic. And my ISP assigns a dynamic address anyway, so any rule pinned to it would silently stop matching the next time it changed.

The fix was to allow-list *ranges*, not addresses, and there are two networks I actually trust. I added my LAN subnet (a `/24`, so every device at home is covered) and Tailscale's address range (`100.64.0.0/10`), which covers every device on my tailnet no matter where it physically is. The Add IP address dialog wants a subnet and a mask (or a prefix length like `24`), and it does not care which you pick.

Someone also asked whether there's a public blocklist I should paste into the Block list. There isn't a good way to use one here: reputation lists like Spamhaus DROP run to thousands of entries and change constantly, and this dialog takes them one at a time with no import. The thing that fills that need is GeoIP blocking, which lives in the *Firewall* screen. Which brings me to the actual bombshell.

### The firewall that was off

When I opened Control Panel → Security → Firewall, "Enable firewall" was unchecked. Everything I'd tuned so far, Auto Block included, is *reactive*: it reacts to failed logins. With the firewall off, there was no packet-level filtering at all. GeoIP blocking, port rules, source restrictions: none of it could work.

I didn't just flip it on, because a deny-by-default firewall with the wrong rules is a great way to lock yourself out of your own NAS. I opened the rule list first, and this is what a default DSM profile looks like after a few years of installing packages: four rules, all set to **Source IP: All**, all set to **Allow**.

The rule names are truncated in the table, and the tooltips are where it gets interesting. Between them, those four rules bundled:

- Rule 1: Windows ODX, WS-Discovery, UPnP, DLNA, Synology Drive Server, Video Station, FTP, Windows file server (SMB), Network Backup, UPS Server, **and "Encrypted terminal service", which is SSH**.
- Rule 3: Synology Storage Console, WS-Discovery, Synology Drive Server, Video Station again.
- Rule 4: File Station, Synology Drive, **Management UI (that's the DSM admin login)**, Audio Station, Surveillance Station, Download Station, CMS, Web Station and Web Mail, Tailscale VPN, Bonjour.

Every one of those, DSM admin and SSH included, allowed from any IP on the internet. And the way DSM's list works ("rules at the top have higher priorities") means the first match wins, so adding a tidy, narrowly scoped rule for, say, Plex on top of that pile would have accomplished nothing: the broad rule would catch the traffic first. You can't out-narrow a broader rule sitting in the same list. You have to edit the broad ones.

Rule 4, it turned out, was mine. I had been walking through the "Select Built-in Applications" list and had ticked considerably more boxes than the three I meant to (Management UI, Synology Drive, Tailscale). File Station, Web Station, Audio Station, Surveillance Station and Download Station all came along for the ride, for services I don't even run. Lesson, freely offered: every checkbox in a firewall dialog is a port you're opening, and "select all the ones that look relevant" is not a security posture.

And there's one more rule I still can't explain: `33400,33443`, TCP, Source IP: All. It's not in Synology's built-in list, so it wasn't auto-added by a package. Somebody made it by hand, and I don't remember doing so. It could be a leftover from a reverse proxy or a container port mapping. It's also an unidentified port, open to the whole internet, which is the kind of thing you delete first and ask questions about later.

### Tailscale is the real answer, with a catch

If you've been paying attention, the throughline here is that scoping firewall rules to "my LAN plus my Tailscale range" only works if remote access actually goes *through* Tailscale. It does. The NAS runs Tailscale as a subnet router, my devices are enrolled, and remote access to DSM, SSH, Portainer, and Plex was already meant to go through the tailnet rather than a port forward. The audit just turned that intent into something the firewall can enforce.

A few things worth knowing:

- **The trade-off is a habit.** If DSM is only reachable from LAN or Tailscale, then the Synology mobile apps only work away from home when Tailscale is switched on. That's the point, not a bug: the alternative is leaving the admin ports open to the world so the app "just works."
- **Tailscale has no 2FA of its own.** It delegates login to your identity provider and inherits that provider's multi-factor setup. If you sign in with Google, 2-Step Verification on the Google account is your 2FA. Given that the tailnet includes a route into your home network, that account deserves the strongest login you own.
- **Prune stale devices.** My machine list had two entries for the same phone, one last seen five months earlier: a leftover from a reinstall. Every enrolled device is a trusted door into the house. Remove the ones you don't use.

## Lessons learned & what's next

The generalizable lesson is one I keep relearning on this NAS: **a default-permissive configuration doesn't announce itself.** Nothing was broken. Nothing warned me. The firewall was off, four rules allowed everything from everywhere, and the whole thing hummed along until an email from Russia made me look. The scary part isn't the attempted login. It's how long the system would have kept saying "all good" if I hadn't.

A short version for anyone in the same spot: turn SSH off or make it key-only, put remote access behind a VPN like Tailscale instead of port forwards, allow-list ranges instead of addresses, and read your firewall rule tooltips. The truncated names hide the interesting part.

And now the honest part, because I said I'd be honest. **This audit isn't finished.** As of writing:

- The firewall is still off. The four broad rules still say Source IP: All, and I haven't yet scoped them down to my LAN and Tailscale ranges. I'm deliberately not enabling anything until the rule set is right, because turning on a deny-by-default firewall with the wrong rules is how you lock yourself out of your own NAS.
- The `33400,33443` rule is still a mystery.
- SSH is still on port 22, and I haven't yet chosen between turning it off and setting up keys.
- I haven't yet confirmed 2-Step Verification is on for the Google account behind my Tailscale login, which is, embarrassingly, the check that matters most.

I'll write up how it ends. If you get to the firewall step before I do and find out what `33400` was, I'd like to hear about it.

---

No GitHub repo to link here, because, again, this was NAS configuration rather than code. If you take one thing from it, make it this: don't wait for the email. Open your firewall screen today and check whether it's actually turned on.
