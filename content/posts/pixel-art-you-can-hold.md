---
title: "Pixel Art You Can Hold"
date: 2026-10-20
draft: true
tags: ["esp32-c3", "esp32", "led", "ws2812", "pixel-art", "3d-printing", "hardware"]
description: "Glow Grid: a browser pixel-art editor, an ESP32-C3 player, and a 3D-printed case for a 16x16 WS2812B LED panel, built by directing Claude through the implementation."
summary: "A 16x16 LED panel looks harsh on its own. This is the story of the editor, the little board that runs it, the case that makes the pixels glow, and a bug hunt that was hardware, hardware, then software."
featuredImage: "/images/hero-glow-grid.jpeg"
featuredImagePreview: "/images/hero-glow-grid.jpeg"
lightgallery: true
---

<p style="font-size:0.75em;opacity:0.7;margin-top:-0.75em;text-align:center;">AI-generated illustration. The real panel is in the video below.</p>

Bare LEDs make bad pixels. A 16x16 WS2812B panel has 256 of them, each a hard little point of light, and a sprite on that panel looks like a sprite drawn with tiny flashlights. I wanted something that looked like a pixel: soft, square, and something I could draw on my phone and put on a desk.

That turned into three things: a pixel editor that runs in a browser, an ESP32-C3 board that plays what you draw and needs no computer at all, and a 3D-printed case with a black grid and a white diffuser cover. All of it is open source, and the case files are on [Printables](https://www.printables.com/model/1884854-glow-grid-16x16-led-panel-case-frame-grid-diffuser).

## Why I built this

This is another hardware project where I've directed Claude through the implementation instead of writing the code myself. The first was an [LED strip controller](/posts/led-strip/). I have a CS degree, but coding was never the part I loved. I like building things and solving problems, and for years the typing ate the time I would have spent on the problem.

The strip was easy: 60 LEDs, wires everywhere, and it lived on my workbench. This time I wanted a real product, something with no wires showing that could sit anywhere in the house, not just on a bench.

I also wanted a better way to make things for it. I didn't want people asking an AI to write code and uploading that. You draw in the editor, or upload an image and let it turn that into a sprite, and that's the whole job. I wanted to build something with the person using it in mind. I also kept picturing someone else printing the case and building on it.

I started on a Raspberry Pi 5 and moved to an ESP32-C3, a small board that sits inside the case. The Pi was how I found out the idea worked at all. A 256-pixel panel was supposed to be the strip with more LEDs: same Pi, same driver. It wasn't, and the way it failed taught me more than anything else in this build.

## What you'll need

The editor runs in any browser, so you can try it without building anything: [dwooods.github.io/glow-grid](https://dwooods.github.io/glow-grid/). For the hardware, the [Printables page](https://www.printables.com/model/1884854-glow-grid-16x16-led-panel-case-frame-grid-diffuser) has the parts list, wiring, assembly order and my slicer profile, so I won't copy them here.

{{< admonition type="info" title="The short version" open=true >}}
A 16x16 WS2812B flexible panel, a 5 V supply rated for addressable LEDs (6 A, and I learned why the hard way, below), an ESP32-C3 SuperMini, a 3D printer and PLA, and a handful of small parts. Measure your panel before printing. The frame pocket is 162 mm square, and panels from different sellers vary.
{{< /admonition >}}

## Hardware, Hardware, Then Software

This happened on the Raspberry Pi prototype, with my first 256-pixel panel, an 8x32. It worked at first, then random pixels lit up in the wrong colors, more of them the more patterns I ran. I tried what you'd try. A series resistor on the data line helped a little. A 74AHCT125 level shifter (a chip that converts the Pi's 3.3 V data signal to 5 V) made things worse, so I took it out. A big capacitor moved around the board fixed nothing, though it did show the noise was at the input end of the panel. Too little power was next: the supply I had ran the 60-LED strip fine, which proved nothing about the 8x32.

Then I overcorrected. I knew nothing about volts and amps (volts are how hard the power pushes, amps are how much of it flows), and I wasn't paying attention to either. The next supply had the wrong voltage and fried the panel: the wires melted and I came close to a fire. I retired it and got a 6 A supply made for LEDs, which later ran the 16x16 too. **Hard lesson: match the supply to the panel before you plug anything in, or you can break the board and start a fire. It cost me money and time, and the panel paid for my education.**

On the 16x16, with the right supply and no breadboard, the same symptoms came back: wrong-colored pixels that changed on every run, missing pixels in the first row and column, red coming out orange. A solid-red fill looked fine for about five seconds, then grew yellow columns at the input end while nothing was touched.

With the power fixed, one cause was left, and it was software:

- The `rpi5-ws2812` library drives the LEDs over SPI (a fast serial link on the Pi's header) and sends one SPI byte per WS2812 data bit. A 256-LED frame is 42 bytes of framing plus 24 per LED: **6,186 bytes**.
- Linux's default `spidev` buffer is **4,096 bytes**, so every frame went out as two writes with a scheduler-dependent pause between them. The split lands 7 bits into LED 168.
- Short pause: the LEDs ride through it. Long pause: they treat it as the end of the frame and re-apply the second half from LED 0. Solid red shifted by a few bits turns green bits on, and red plus green is yellow.

![One 6,186-byte frame split into a 4,096-byte write and a 2,090-byte write, against a 60-LED strip frame that never splits](/images/glow-grid-spi-buffer-split.png)

That is why the same driver worked on my 60-LED strip: 60 LEDs is 1,482 bytes, which never crosses the limit.

{{< admonition type="note" title="The fix" open=true >}}
Append `spidev.bufsiz=65536` to the single line in `/boot/firmware/cmdline.txt` and reboot. Check it with `cat /sys/module/spidev/parameters/bufsiz`. Wire data to GPIO10 (pin 19), share a ground, and power the panel from its own supply, never from the Pi's 5 V. With the buffer fixed, no resistor, capacitor, or level shifter is needed on the Pi.
{{< /admonition >}}

What found it was a 40-line test script: solid red, 256 LEDs hard-coded, none of the application's image, mapping, or gamma code. Then I read the driver and the `spidev` source, which showed the split.

{{< admonition type="tip" title="The lesson to steal" open=true >}}
Before you buy a part to fix flaky hardware, write the smallest control you can and read the driver. If the fault survives with none of your application in it, the application isn't the cause. I spent two evenings on contacts, ground and capacitors before doing either. It works on any project where a library sits between your code and the pins.
{{< /admonition >}}

One caveat: the 8x32 shared the same driver and almost certainly the same 4,096-byte limit, but the power problem damaged it before I found the buffer bug. I never retested it, so I can't say how much each one caused.

That was the Pi. The idea held up, and the rest of this post is what replaced it: the editor, the board and the case.

## The editor

The editor is a web page that runs from GitHub Pages, installs as an app on a phone, and works offline. You draw on a 16x16 grid, add frames to animate, and export a small PNG that carries its own settings (frame count, frame rate, brightness, gamma) inside the file. I'd originally put those in the file name, `knight_4fps_bright0.35_gamma2.2.png`, but the name was ugly and long, and nobody names files that way. If the editor can read the settings from the file's metadata, I couldn't see a reason to put them in the name too.

**Photos and flat art need different imports.** A photo shrunk to 16x16 with the browser's default smoothing doesn't match what the player will do, so the editor does its own resize, checked against [Pillow](https://python-pillow.org/), a standard Python image library, on test images Claude ran, to within one level out of 255. At brightness 0.3, gamma (the curve that makes brightness steps look even) leaves only about 77 distinct LED levels, so dark gradients band unless the editor dithers, mixing neighboring levels to fake the in-between. Flat art needs the opposite: averaging muddies outlines, so that mode picks a few main colors first.

**Test it where people actually use it.** The editor gets used on a PC and on a phone, so I spent a good while building test cases for both and comparing them to make sure it worked on each. My first phone layout still failed on a real iPhone. It was a locked, no-scroll layout with the tools in a bottom dock, and it looked right at three simulated phone sizes. On the real phone, a finger on the grid painted instead of scrolling, and there was no other place to swipe. The fix removed code instead of adding it: the settings sheet became normal cards below the strip, and the page scrolls. I'd rated that layout 7.5 out of 10 while its settings couldn't be reached on a phone. A screenshot can't show you that.

![The Glow Grid editor: pixel grid and tools at the top, the frame strip and panel settings in the middle, and the Board card for sending a drawing to the ESP32-C3 at the bottom](/images/glow-grid-editor-board-card.png "The full editor.")

## What it can show

The sprites that ship with the repo are all drawn as text in a Python file, one character per pixel, so they live in git as source and not as binary images. Four of them, rendered here from that data with a soft glow added (this is a preview render, not a photo of the panel):

<div style="display:flex;gap:8px;justify-content:center;margin:1em 0;">
  <img src="/images/glow-grid-sprite-fireworks.gif" alt="Fireworks: three shells rise, burst, and fade" style="flex:1 1 0;min-width:0;max-width:150px;height:auto;margin:0;">
  <img src="/images/glow-grid-sprite-meteors.gif" alt="Meteors crossing a starry sky on clean diagonals" style="flex:1 1 0;min-width:0;max-width:150px;height:auto;margin:0;">
  <img src="/images/glow-grid-sprite-lightning.gif" alt="A storm cloud, rain, and two lightning strikes" style="flex:1 1 0;min-width:0;max-width:150px;height:auto;margin:0;">
  <img src="/images/glow-grid-sprite-missile-defense.gif" alt="Two incoming missiles caught by interceptors over a small skyline" style="flex:1 1 0;min-width:0;max-width:150px;height:auto;margin:0;">
</div>

The last one, a missile-defense scene, on the real panel, filmed on my phone:

<video autoplay loop muted playsinline controls preload="metadata" width="100%" poster="/images/glow-grid-missile-defense-real-panel.gif" style="max-width:480px;display:block;margin:1em auto;">
  <source src="/images/glow-grid-missile-defense-real-panel.mp4" type="video/mp4">
  <img src="/images/glow-grid-missile-defense-real-panel.gif" alt="The missile-defense sprite playing on the real panel">
</video>

## The ESP32-C3 board

![The editor talks to the ESP32-C3 over Wi-Fi, and the ESP32-C3 drives the 16x16 panel from GPIO6. The Raspberry Pi 5 drove the panel over SPI in the prototype.](/images/glow-grid-architecture.svg)

The ESP32-C3 is the one that lives inside the case. It holds up to 96 sprites in its own flash (40 come preloaded), drives the panel directly, and serves its own copy of the editor over your home Wi-Fi. I wanted it to work from Safari on an iPhone, and a page loaded from GitHub over HTTPS isn't allowed to talk to a plain-HTTP board on your network, so the board hands you its own copy. Bluetooth was the other route; I dropped it, and this was the next option. Two buttons change what's showing: Next, and On/off. Holding On/off for five seconds opens Wi-Fi setup.

**Why 96?** Part arithmetic, part product decision. A frame is 768 bytes (16 × 16 pixels × 3 colors). I capped a sprite at 16 frames, which makes the biggest one about 12 KB. The flash I set aside for sprites is about 1.5 MB, which would fit roughly 400 of them, so flash isn't the limit. The limit is RAM: the board keeps the list of sprite names in memory, and I cap that list. I started at 64, then raised it to 96 once I'd made almost 40 example sprites and the estimates showed there was room. The 16-frame cap was a product call about what a 16×16 panel is for: short loops, not video. It also matches the editor, which lays frames out in two rows of 8. I could have shrunk sprites to fit more of them, or dropped Wi-Fi and the served editor to free room. I kept the features.

### Getting a screenless board onto Wi-Fi

Two problems came with putting a board with no screen on a home network: joining it safely, and telling two of them apart.

**Part 1: joining without leaving a door open.** The 8-digit code started as a security question. A password printed on a label is the same on every unit, so anyone who owns one knows the password for all of them, and I didn't want to hand users a code anyway. But the board has a panel, so it can show the code itself.

When you hold On/off for five seconds, the board creates its own WPA3 network (the current Wi-Fi security standard) with a random name and a random 8-digit password. It draws the digits on the LED panel and keeps them in RAM only, for five minutes at most. If you can read the code, you're standing in front of the device. The setup network exists only for those five minutes, and nobody can join it without seeing the panel. That window was the part worth protecting, because the board is broadcasting a network anyone nearby could try to join, and if I sold these, I'd want buyers to be able to secure their board the same way. Once the board is on your home Wi-Fi, I left it open: anyone on that network can add or delete sprites. A sprite isn't sensitive or harmful, and you should keep your drawings on your computer or phone anyway, so a deleted one can be added back.

![Wi-Fi setup sequence between you, the ESP32-C3 board, and the LED panel: hold On/off for 5 seconds, read the 8 digits drawn on the panel, join the setup network, pick your home Wi-Fi, and the board forgets the setup key and returns to your sprite.](/images/glow-grid-wifi-setup.svg)

I tested setup on a Windows 11 PC and an iPhone. The iPhone opens the setup page by itself; Windows 11 shows an "Action needed" entry you have to click. I haven't tested Android.

**Part 2: giving each board its own name.** Every board originally advertised itself as `glowgrid.local` over mDNS (the system that lets you type a `.local` name instead of an IP address). With two boards on one home Wi-Fi, say two kids in two rooms, they fight over the name, and whoever wins gets the other person's sprites. Now each board names itself `glowgrid-` plus the last two bytes of its own MAC address, so mine is `glowgrid-b274.local`.

## Why the Glow Comes from the Case

![The case: frame, grid, diffuser cover, ESP32-C3 holder, and cradle, rendered from the generator script](/images/glow-grid-enclosure-preview.jpg)

![The printed case from the side, back and front: the 12-degree cradle, the two buttons and barrel jack on the back, and the white diffuser cover, with the panel off](/images/glow-grid-case-real-photos.jpg "The real thing, panel off. The background is AI-replaced; the device is untouched.")

The glow comes from the case, and the case was a list of things I wanted. I wanted the light to look like individual bright squares, a 2D pixel effect, not a smear, so a black grid sits on the panel and gives each LED its own square, and a thin white cover over the grid diffuses each LED into a soft pixel. The cover snaps on, so it's easy to hold in place. I wanted it to sit on a counter with the wires out of sight in the back, so a cradle tips the whole thing back 12 degrees, and I wanted it to look good enough to be a product. The ESP32-C3 gets its own tray in the back, so it stays put and is easy to replace, and the back has two buttons: on/off, and next sprite for when the board runs without the editor. None of the designs I started from had a place for the C3 or buttons.

The parts are generated by a Python script (`enclosure/build.py` in the repo), so changing a hole or a clearance is a one-line edit; the photos are the parts as printed, in the silk PLA I had on hand. The design descends from three CC BY designs on Thingiverse: ["16x16 RGB Matrix"](https://www.thingiverse.com/thing:4127683) by The_Wrench_DIY, its [remix by chummer](https://www.thingiverse.com/thing:4459985), and the [one-part-frame remix by makeitworktech / Make It Work](https://www.thingiverse.com/thing:5737371). I used only the 10 mm pitch and 1 mm grid walls from those designs and built the rest from scratch. The Printables page is CC BY 4.0, and the code, editor, and example sprites are MIT.

### Three millimetres and a gap

The frame went through several versions. The change worth explaining is v7, because it taught me how a small geometry change shows up somewhere you aren't looking.

I made the frame and the cradle 3 mm deeper because the wires on the C3 were sticking up into the back of the LED panel. I hadn't soldered them: I'd pushed each wire into its hole, so they stood up instead of lying flat. Soldering them flat would probably have fixed it, but I'd never soldered before and didn't want to ruin the board, so I fixed a problem I could undo. The lip that holds the grid was fine, so I left it and just made room for the wires. The lesson: a design fits the model of your parts, not your actual wiring, so print it, put everything in it, and expect to change the design after you see how you really wired it. The lip kept the same distance from the front (11.6 mm), which put it 24 mm from the back instead of 21.

![Side sections of frame v6, v7 and v8: the lip stays 11.6 mm from the front, the distance to the back goes from 21 to 24 mm, and the v8 spring fingers are thicker](/images/glow-grid-frame-lip-v6-v7-v8.png)

Four spring fingers on the back plate press the stack forward against the cover. The extra depth made them 3 mm longer, and a longer arm is softer. On the v7 print there was a gap between the grid and the cover. I think the softer fingers let the panel sink onto the lip, but I haven't measured the finger force, so that's a hypothesis, not a finding. v8 makes the fingers 2.0 mm thick instead of 1.6, which by arithmetic is about 1.2 times stiffer. My v8 print doesn't sag, and that's the evidence I have.

The first fix Claude tried was wrong: it moved the lip toward the front, but the distance from the lip to the front had been right all along, and only the distance to the back needed to change. That mistake is why the diagram exists.

### Fifteen versions of a stand

The desk cradle took 15 versions, more than the frame, for a part whose whole job is to sit there. Most of them were me designing something that looks good, not just something that works. Claude's first cradle was bulky, and its front lip covered the bottom row of LEDs; I had it lower the lip and raise the back to compensate. Then I wanted curves, then wording, then a snake, which Claude couldn't get right, or I couldn't explain. What I pictured, what I said, and what came out were three different things, and the only way to close the gap was to look at the print. Seven of my decisions were later reversed.

## What I'd tell you before you build one

The Printables page has the assembly order, the wiring, my print settings, and a longer list of what I haven't verified (spring-finger force, how the cover's friction fit behaves on other printers, the cradle's tape and screws over time). Two things I'd say even if you read nothing else there:

- **The power wiring needs better connectors than mine.** Parts of the power path on my unit use Dupont-style jumpers, which are typically good for 1 to 3 A, well below what a full-white panel draws. I run the panel at brightness 0.3, where a fully white frame draws about 4.7 A on the 6 A supply. For a unit you leave running, solder the 5 V and ground runs or use terminals rated 10 A or more.
- **Flash the ESP32-C3 on the bench before you close the case.** Its BOOT and RST buttons face the panel and can't be reached afterward.

## What's next

Two things. I plan one board per kid, which is what the per-board names were for. I'm also getting a Mac, and when I do I'll see about an iOS app that runs the editor UI. That one is a plan, not a build.

## Try it yourself

**Just want to try it?** Open the [editor](https://dwooods.github.io/glow-grid/) and draw something.

**Want to build it?**

1. Download the [case files](https://www.printables.com/model/1884854-glow-grid-16x16-led-panel-case-frame-grid-diffuser) from Printables.
2. Get the [code](https://github.com/dwooods/glow-grid) for the ESP32-C3 firmware (the Pi player is in there too).
3. Wire it as in the diagram below, flash the board, and print the holder first.

![The ESP32-C3 wiring diagram and build checklist](/images/glow-grid-wiring-checklist.jpg)

If something doesn't work, [open an issue](https://github.com/dwooods/glow-grid/issues). The example sprites are all original, and I'd ask that remixes keep it that way.

## Tools & AI assist

Same arrangement as the strip project, with more rules, because the project is bigger. I describe what I want and test the result on the real device. Claude writes the code, the build script, and the commits. We keep a journal and a feature tracker in a project folder, so a new session can pick up where the last one stopped.

That covers the volume: the editor, the board firmware, the case generator. It did not cover being right. Claude made mistakes along the way, like moving the frame lip the wrong way in v7. So I had it build a test suite and add cases as we went. That caught some of the mistakes; the real phone and the real print caught the rest. The decisions were mine: keeping a sprite's settings inside the file instead of its name, having the board draw its own Wi-Fi password on the panel, and checking the layout on a real iPhone. I could only judge any of it by looking at the real thing.
