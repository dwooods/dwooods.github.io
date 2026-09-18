---
title: "Wagging the Dog: Convincing Plex My Vacation Home Is My Actual Home"
date: 2026-09-18
draft: false
tags: ["tailscale", "plex", "synology", "networking", "self-hosted", "vpn", "wireguard"]
description: "Setting up Tailscale on a Synology NAS so a vacation-home TV thinks it's sitting on my home network — no port forwarding, no Remote Watch Pass, and a deep dive into why Plex quietly deleted the one setting that used to make this easy."
summary: "My movie library lives on a NAS at home. Plex decided watching it from vacation should cost extra. Here's how I taught my NAS to lie about its address — with a lot of help from Claude and one deeply misleading grep match."
featuredImage: "/images/plex-marketing-stream-anywhere.png"
featuredImagePreview: "/images/plex-marketing-stream-anywhere.png"
---

We don't have Netflix. We don't have Hulu, Max, or whatever streaming service currently has the show everyone's talking about. What we have is a NAS in a closet with a few hundred movies and TV seasons on it, a Plex server, and — as of a few weeks ago — a genuine grudge against Plex's product team.

Here's the problem: those movies live at our permanent address. We watch them on vacation, at a house that is very much not our permanent address, on someone else's Wi-Fi, with zero access to their router. Historically, Plex treated any device connected back to your home network as local, full stop — tunneling in with a VPN to make your own TV look like it never left the house was a known, if slightly nerdy, trick. Then sometime in the 2025–2026 window, Plex turned that into a subscription feature and started actively enforcing against it.

I don't actually blame them for wanting recurring revenue. Plex runs infrastructure and payroll, and a lifetime Plex Pass isn't exactly a subscription business model. Charging a few dollars a month for remote streaming is a reasonable way to monetize it. I just happen to already own the media and the server it lives on, so I'd rather spend an evening rerouting my own network traffic than pay a subscription for a feature I already had.

This is the story of how I un-decided that, mostly by asking Claude a lot of increasingly specific questions from an SSH session.

<p align="center"><img src="/images/tailscale-plex-flow.svg" alt="The full path a movie takes from my NAS to a vacation-home TV" style="max-width:100%;"></p>

## Why I Built This

We rely entirely on our own library — no subscriptions, no "well we could just watch something on Netflix instead." So when the TV at the vacation house flatly refused to play a movie I own, on a server I own, that's not a minor inconvenience, that's the entertainment plan for the week collapsing.

The actual message wasn't even honest about what was happening — it just acted like the content wasn't available, the same as if the file had been deleted. It took some digging to learn Plex has been actively enforcing a subscription requirement for remote streaming of personal media since late 2025, rolling it out to TV platforms first. Unless the server owner or the viewer has an active Plex Pass, or the viewer buys a "Remote Watch Pass," remote playback is just blocked. Not throttled, not watermarked — blocked.

<p align="center"><img src="/images/plex-remote-watch-pass-paywall.png" alt="Plex's &quot;you need a Remote Watch Pass&quot; paywall, shown here as a deliberate test with Tailscale turned off" style="max-width:340px; width:100%;"></p>

My first instinct was "I already pay for a VPN, can't I just use that?" I already pay Private Internet Access for exactly this kind of thing. Claude's answer was fast and a little deflating: no, and not almost-no, structurally no. A commercial VPN like PIA solves the opposite problem — it routes your traffic *out* through someone else's servers so the internet can't tell where you really are. I needed the reverse: I needed a device six hundred miles from home to convincingly pretend it *was* home. Different job entirely. That's one subscription I now know I'm paying for something it was never going to do.

The other constraint that shaped everything: none of our TVs can run a VPN client, and neither can most smart TVs in general — no Tailscale app for webOS, Tizen, or Roku. Whatever fixes this has to live upstream of the TV, on hardware I control. Which meant: a travel router.

## The Setup

The hardware side of this is almost embarrassingly simple: a Synology DS918+ NAS that's been quietly running Plex for years, and is now the entire reason this project exists. Onto it I installed Tailscale — a mesh VPN built on WireGuard, installed as the official Synology package — and configured it as a *subnet router* that advertises the home LAN out to a private network of my own devices (a "tailnet").

At the vacation house, a GL.iNet Opal (GL-SFT1200) travel router — ordered, not yet in hand — will run the Tailscale client and hand the TV a completely normal-looking Wi-Fi network. The router handles the tunnel; the TV never knows it exists.

Plex Media Server is the one component in this entire chain that spent the whole project actively working against me.

I looked at Synology's own VPN Server package first, since it was already sitting in Package Center, free, zero new accounts. Two things killed it: it only speaks OpenVPN/L2TP/PPTP, not WireGuard, and OpenVPN topped out around 11–12 Mbps on the router hardware I compared — fine for a phone, not great for a TV. Worse, reaching it from outside means forwarding a port on the home router, which requires either a static IP or dynamic DNS, and simply doesn't work at all if the home ISP uses CGNAT. Tailscale needs none of that — no ports, and its relay fallback can ride over ordinary HTTPS, which makes it much more tolerant of restrictive networks — including hotel networks that hate you.

### Tools & AI Assist

No repo for this one. This wasn't code — it was network plumbing — so there's no VS Code, no Claude Code CLI, no pull request to point at. The entire thing happened in one long-running conversation with Claude (Claude Cowork), which is a pretty accurate description of how I now do most home-infrastructure work: open a chat, SSH into the NAS in another window, paste output back and forth.

This wasn't me handing Claude the problem and collecting a finished answer — most of it was me running into something broken, describing exactly what I was seeing, and the two of us figuring out what was actually going on together. I already had a VPN subscription through PIA, so my first move was asking whether I could just use that; Claude explained fast why the answer was no, before I burned an evening finding out the hard way myself. When Tailscale looked installed and configured but nothing actually worked, I described the symptom and we tracked it down together to a cryptic "TUN Mode: No" line buried on the device page, then worked out the exact Task Scheduler boot script needed to fix it. When the GUI setting I needed had mysteriously vanished, I didn't even know Plex had an API to check — Claude walked me through the right `curl` syntax and how to pull a full preference dump so I could go look for myself instead of taking anyone's word for it.

**What Claude got wrong, credit where due:**

The setting at the center of all this is Plex's **LAN Networks** option — it lets you tell Plex "treat this IP range as local no matter where it physically is," which is the exact loophole the whole project depends on. It wasn't showing up in the GUI anymore, but a missing menu item doesn't prove much by itself — Plex hides plenty of settings behind an "Advanced" toggle. So instead of trusting the settings page, I pulled the server's actual live preferences straight from Plex's own API with `curl` and grepped the raw file for anything mentioning "lan," to see what Plex's backend really had stored rather than what its interface felt like showing me. My first attempt at that came back with nothing, which looked like confirmation the setting was truly gone. In reality, it was a formatting mismatch: the entire preference file was sitting on one enormous unbroken line, so a pattern expecting normal line breaks silently matched zero lines of everything. We only caught it by checking the raw file size directly.

Going in, I'd told Claude my actual theory: Plex hadn't just buried this setting somewhere behind an "Advanced" toggle, they'd pulled it because it was the exact loophole letting people dodge the new Remote Watch Pass charge. That theory decided which project I was actually building. If LAN Networks still existed in Plex's data model and was only hidden from the GUI, I could probably set it directly through the API and skip Tailscale, the travel router, all of it — a five-minute `curl` command instead of a weekend project. If it had been stripped out of the backend entirely, there was no shortcut, and the network-level trick was the only path left. So this wasn't just confirming a hunch — it was the fork in the road for the rest of the project, which is exactly why a false negative from a broken grep pattern was dangerous: it would have told me "gone" when the file just hadn't been searched correctly.

Round two, with simpler search terms, went better right up until one of the promising-looking hits turned out to be the word **"blank"** — b-l-a-n-k — which, if you're doing a case-insensitive substring search for "lan," absolutely contains "lan." Claude does not typically expect to be out-detectived by the word "blank." And yet.

That was probably the best lesson of the whole project. Claude was very good at turning a symptom into the next thing to investigate — broken grep, cryptic TUN Mode line, missing GUI setting, hand it a symptom and it had a next step. It was less good at knowing when the evidence actually proved the conclusion. A zero-match grep looked exactly as conclusive as a real one, right up until it wasn't, and I still had to go look at the raw data myself and ask "does this actually say what we think it says?" AI can accelerate the debugging. It can't do the part where you check whether the result means what it looks like it means.

## Key Technical Challenges

### Synology quietly disables the one thing Tailscale needs

Tailscale's Synology package installs clean, signs in fine, looks done. It is not done. Buried in the machine's detail page in the Tailscale admin console was a line reading `TUN Mode: No` — DSM's package sandboxing blocks Tailscale from creating a TUN network device by default, which silently breaks subnet routing. Nothing errors. It just doesn't work, and you have no way of knowing why until you go looking for that one line.

The fix is a Task Scheduler entry that runs at every boot:

```
Control Panel → Task Scheduler → Create → Triggered Task → User-defined script
User: root · Trigger: Boot-up
Script:
/var/packages/Tailscale/target/bin/tailscale configure-host; synosystemctl restart pkgctl-Tailscale.service
```

`configure-host` re-grants the TUN permission DSM strips away, and restarting the package makes it stick without a full reboot. Run it once manually to apply immediately, and it survives every reboot after that.

The second small trap, once TUN was fixed:

```bash
sudo tailscale up --advertise-routes=192.168.X.X/24 --reset
```

`tailscale up` demands you restate *every* non-default flag on every invocation or it silently clears them — the `--reset` flag isn't optional decoration, it's what makes the command actually apply the route instead of erroring. Annoying, but I'll take "errors loudly" over "silently clears your config" any day.

### The setting that used to make this easy just isn't there anymore

The actual plan was simple: Plex has (had) a **LAN Networks** setting where you list IP ranges that should be treated as local, regardless of where they geographically are. Add my home subnet and Tailscale's CGNAT range, and a tunneled device should look exactly as local as the living room TV.

It's gone. Not hidden behind "Show Advanced" — gone from the server's entire preference set. I confirmed this the hard way, by pulling the server's live preferences directly and searching them:

```bash
curl -s "http://192.168.X.X:32400/:/prefs?X-Plex-Token=YOUR_TOKEN" -o /tmp/prefs.xml
grep -oi '.\{50\}lan.\{50\}' /tmp/prefs.xml
```

(That's the "blank" incident from above — the raw `grep -io "lan"` looked like a hit, and only printing 50 characters of context on either side revealed it was nothing.) No trace of anything resembling LAN Networks anywhere in the file. Plex didn't just hide this setting. They deleted it from the backend entirely, conveniently removing the exact mechanism this project would have depended on.

So if that setting doesn't exist, what's actually convincing Plex a tunneled device is local? Nothing on Plex's side — it's how Tailscale hands the traffic off before Plex ever sees it. A Tailscale subnet router source-NATs (masquerades) traffic by default before forwarding it onto the real LAN, so by the time a request reaches the NAS, it arrives with a source address inside `192.168.X.X/24` — the same subnet as the living room TV. Plex never sees a Tailscale address, a CGNAT address, or anything to be suspicious of; the packet looks exactly like it came from a device plugged into the router downstairs. That's also why the Windows and Pixel tests below worked with zero Plex-side configuration — there was nothing to configure, because as far as Plex could tell, it was never talking to anything but an ordinary local IP.

Step by step, that's:

1. **Phone or TV connects to the travel router's Wi-Fi** — a completely ordinary local network at the vacation house.
2. **The travel router tunnels that traffic home over Tailscale** — WireGuard-encrypted, riding over ordinary HTTPS when a direct connection isn't possible.
3. **The NAS's Tailscale subnet router source-NATs it onto the home LAN** — the request now carries an address inside `192.168.X.X/24`, same as the living room TV.
4. **Plex Media Server only ever sees that local address** — no Tailscale IP, no CGNAT range, nothing to flag — and serves the stream as "Local."
5. **The movie streams back down the same path**, in reverse, to whichever screen asked for it.

To be clear, I'm not the one who figured this out. It's sitting in the open on Plex's own community forums. A thread called ["Support for Tailscale"](https://forums.plex.tv/t/support-for-tailscale/936755) has a reply from a longtime, highly-trusted community member spelling out this exact mechanism: "Tailscale itself provides a means of allowing remotely connected devices to appear as though they are local (see subnet routers)... you can already allow any Tailscale client device to appear as it were on your local network without modification to Plex." That post has been up since February, with Plex Pass users openly discussing it. I just went and confirmed it on my own setup instead of taking a forum reply's word for it.

I didn't just take my own word for it either. I pulled up Plex's Now Playing panel while streaming to my phone over the tunnel, away from home Wi-Fi, and there it was: `Local (192.168.X.X) — 2 Mbps`. Not a Tailscale address, not a CGNAT address — Plex itself labeling the session "Local," at the exact IP the subnet router hands out. Mechanism confirmed.

<p align="center"><img src="/images/plex-now-playing-local-proof.png" alt="Plex's server dashboard labeling a phone streaming over cellular data, miles from home Wi-Fi, as &quot;Local (192.168.X.X) — 2 Mbps&quot;" style="max-width:293px; width:100%;"></p>

## Lessons Learned & What's Next

The generalizable version of this, for anyone reading this who has never heard of Plex and never will: before you build a workaround around any system's rule — a paywall, a rate limiter, an app-store policy — the question that matters isn't "how do I get around this," it's "what is this thing actually checking, and how likely is that specific check to still exist in six months." Plex was checking a source IP range, which is a genuinely fragile way to define "local." I built an entire project on the bet that fragility would hold. So far it has. That is not the same thing as it being a good bet, and I wrote down four different ways Plex could patch it out from under me, mostly so future-me can feel smug about having seen it coming, right before panicking.

The other lesson wasn't really about networking. It was about using AI for infrastructure work. Claude can move incredibly quickly from "here's what I'm seeing" to "here's what we should try next," which is exactly what I wanted. But speed makes bad assumptions easier to miss. The broken grep was a perfect example: the answer looked right until I checked the raw data. AI was useful for getting me to the evidence; I still had to decide whether the evidence actually supported the conclusion.

The honest scorecard, tested with no Plex Pass and no Remote Watch Pass active: a Windows laptop off the home network, tunneled in through Tailscale, played media in Plex Web with zero paywall. A Pixel phone, on cellular data only, Wi-Fi fully off, played media in the actual Plex mobile app with zero paywall. Both work today. The phone test isn't just a lab condition, either — it's already my actual commute: riding public transit to work, watching something on my phone, nowhere near either network's Wi-Fi, and Plex has no idea there's anything to charge me for.

What hasn't been tested is the one thing that actually matters for the trip: the smart TV itself. Plex's enforcement reportedly targeted TV platforms first, which means a browser and a phone passing is not proof a TV app will. That test happens once the GL.iNet router arrives, gets configured, and gets planted in front of whatever TV is waiting for us at the vacation house — which is a problem for a future post, not this one.

One thing worth being straight about, now that I've actually checked: [Plex's Terms of Service](https://www.plex.tv/about/privacy-legal/plex-terms-of-service/) prohibit "obtaining Plex Pass functionality without a valid Plex Pass," and Remote Watch Pass gates exactly the functionality this project unlocks. On a literal reading, that's this. I'm not touching anyone else's content or breaking into anything — this is my own server and my own media — but "it's my own stuff" and "it's within the contract I agreed to" are two different questions, and I'd rather say that plainly than pretend I found a free loophole with no fine print attached. The actual consequence Plex spells out for a Terms violation is account suspension or termination, not a lawsuit. Whether they'd ever bother enforcing that against someone running their own homelab for personal use — versus the kinds of use cases Plex may have been trying to prevent — I don't know.

Also worth admitting: I have now spent, conservatively, several hours of my life engineering around a $2.99-a-month charge. My hourly rate for problems nobody is paying me to solve remains extremely reasonable.

## Try This Yourself

No GitHub repo to link here — it's a NAS, a $30 travel router, and one very long chat, not code. If you're fighting the same fight, Tailscale's own docs for the Synology package and subnet routers are genuinely good, and the GL.iNet Opal (GL-SFT1200) is the router I landed on for the price and its WireGuard throughput ceiling over the smaller Mango. Worth a read too: the ["Support for Tailscale"](https://forums.plex.tv/t/support-for-tailscale/936755) thread on Plex's own community forums, where this exact subnet-router trick is already laid out in the replies — I didn't invent anything here, I just went and checked that it actually works. Whether the actual TV cooperates is a problem for a future post — right now the whole thing has been proven on a laptop and a phone, which is a very fancy way of saying "it works, probably, we'll see." If your setup breaks in a way I haven't listed, or you find a fifth way Plex could close this off, I'd like to know before their engineers tell me by breaking it.

---

But the phone test is the one that actually matters: it means that six hundred miles from home, on somebody else's Wi-Fi, without paying Plex a second time for movies I already own, I can hand my kid a phone and let him finish what he started watching at home.

That's the whole point. Everything above — the TUN mode, the vanished preference, the word "blank" pretending to be a security researcher — was just the toll booth.
