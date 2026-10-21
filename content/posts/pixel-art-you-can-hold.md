---
title: "Pixel Art You Can Hold"
date: 2026-10-20
draft: true
tags: ["esp32-c3", "esp32", "led", "ws2812", "pixel-art", "3d-printing", "hardware"]
description: "Glow Grid: a browser pixel-art editor, an ESP32-C3 player, and a 3D-printed case for a 16x16 WS2812B LED panel, built by directing Claude through the implementation."
summary: "A 16x16 LED panel looks harsh on its own. This is the story of the editor, the little board that runs it, the case that makes the pixels glow, and the one bug that looked like hardware and wasn't."
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

It turned out to be a lot more than the strip. There were 256 LEDs instead of 60, soldering, Wi-Fi setup with a password you read off the panel, buttons, and real design work on the 3D prints. It took far more time.

I started on a Raspberry Pi 5 and moved to an ESP32-C3, a small board that sits inside the case. The Pi was how I found out the idea worked at all. A 256-pixel panel was supposed to be the strip with more LEDs: same Pi, same driver. It wasn't, and the way it failed taught me more than anything else in this build.

## What you'll need

The editor runs in any browser, so you can try it without building anything. For the hardware, the [Printables page](https://www.printables.com/model/1884854-glow-grid-16x16-led-panel-case-frame-grid-diffuser) has the full parts list, wiring, assembly order and my slicer profile, and I'd rather keep that in one place than copy it here.

The short version: a 16x16 WS2812B flexible panel, a 5 V supply rated for addressable LEDs (6 A, and I learned why the hard way, below), an ESP32-C3 SuperMini, a 3D printer and PLA, and a handful of small parts. Measure your panel before printing. The frame pocket is 162 mm square, and panels from different sellers vary.

## The bug that looked like hardware

This happened on the Raspberry Pi prototype. My first 256-pixel panel was an 8x32. It worked at first, then random pixels started lighting up in the wrong colors, more of them as I ran more patterns. I did what you'd do. I added a series resistor, which helped a little. I added a 74AHCT125 level shifter (a chip that converts the Pi's 3.3 V data signal to 5 V), which made things worse, and I took it out. I moved a big capacitor around the board. I worked out that the noise was at the input end of the panel, not the far end, which ruled out one theory and pointed at nothing in particular.

What I eventually blamed was the power supply. Something was wrong with the panel's power: it got hot enough that the wires melted and I came close to a fire, so I retired it. I replaced the adapter with a 6 A supply made for LEDs, which was the right call for the 16x16 too. Check an adapter's voltage and rating before you plug anything in.

It wasn't the whole story. When I moved to the 16x16 panel with the proper supply, no breadboard and a resistor on the data line, the same symptoms came back. A static check pattern was mostly right but had different wrong pixels on every run. A solid-red fill of all 256 LEDs looked fine for about five seconds and then grew yellow columns at the input end while nothing was touched.

The symptoms pointed at the electronics, and the cause was in software. The library that drives the panel, `rpi5-ws2812`, talks to the LEDs over SPI, a fast serial link on the Pi's header, and sends one SPI byte for every WS2812 data bit, so a frame for 256 LEDs is 42 preamble bytes plus 24 bytes per LED, which is **6,186 bytes**. Linux's default `spidev` buffer is **4,096 bytes**. Every frame went out as two separate writes with a scheduler-dependent pause between them, landing 7 bits into LED 168. Depending on the length of that pause, the LEDs either rode through it or treated it as the end of the frame and re-applied the second half from LED 0. Solid red shifted by a few bits turns green bits on, and red plus green is yellow.

![One 6,186-byte frame split into a 4,096-byte write and a 2,090-byte write, against a 60-LED strip frame that never splits](/images/glow-grid-spi-buffer-split.png)

That is why the same driver worked on my 60-LED strip: 60 LEDs is 1,482 bytes, which never crosses the limit.

{{< admonition type="note" title="The fix" open=true >}}
Append `spidev.bufsiz=65536` to the single line in `/boot/firmware/cmdline.txt` and reboot. Check it with `cat /sys/module/spidev/parameters/bufsiz`. Wire data to GPIO10 (pin 19), share a ground, and power the panel from its own supply, never from the Pi's 5 V. With the buffer fixed, no resistor, capacitor, or level shifter is needed on the Pi.
{{< /admonition >}}

What found it was a 40-line test script: solid red, 256 LEDs hard-coded, none of the application's image, mapping, or gamma code. If the fault survived in that, the application wasn't the cause. Then I read the driver and the `spidev` source, which showed the split.

{{< admonition type="tip" title="The lesson to steal" open=true >}}
Before you buy a part to fix flaky hardware, write the smallest control you can and read the driver. If the fault survives with none of your application in it, the application isn't the cause. I spent two evenings on contacts, ground and capacitors before doing either. It works on any project where a library sits between your code and the pins.
{{< /admonition >}}

One thing I can't fully say. The 8x32 shared the same driver, the same frame size and almost certainly the same 4,096-byte limit, but it was damaged by a power problem before I found the buffer bug, so I never retested it. I can't say how much each one caused.

That was the Pi. The panel worked, the idea held up, and the rest of this post is about what replaced it: the editor, the board and the case.

## The editor

The editor is a web page. It runs from GitHub Pages, installs as an app on a phone, and works offline: [dwooods.github.io/glow-grid](https://dwooods.github.io/glow-grid/). You draw on a 16x16 grid, add frames to animate, and export a small PNG that carries its own settings (frame count, frame rate, brightness, gamma) inside the file instead of in the file name. I'd originally put those in the name, `knight_4fps_bright0.35_gamma2.2.png`, until I asked why a file needed a name to know how fast to play.

**Photos and flat art need different imports.** A photo shrunk to 16x16 with the browser's default smoothing doesn't match what the player will do, so the editor does its own resize, checked against Pillow to within one level out of 255. Gamma is the curve that makes brightness steps look even to the eye, and at brightness 0.3 it leaves only about 77 distinct LED levels, so dark gradients band unless the editor dithers, mixing neighboring levels pixel by pixel to fake the in-between. Flat art needs the opposite: averaging blends outlines into muddy colors, so that mode picks a few main colors first.

**A phone layout I got wrong.** I built a locked, no-scroll layout with the tools in a bottom dock. It looked right at three simulated phone sizes. On a real iPhone, a finger on the grid painted instead of scrolling, and there was no other place to swipe. The fix removed code instead of adding it: the settings sheet became normal cards below the strip, and the page scrolls. I'd rated that layout 7.5 out of 10 while its settings couldn't be reached on a phone. A screenshot can't show you that.

![The Glow Grid editor: pixel grid and tools at the top, the frame strip and panel settings in the middle, and the Board card for sending a drawing to the ESP32-C3 at the bottom](/images/glow-grid-editor-board-card.png "The full editor. Click to enlarge.")

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

The ESP32-C3 is the one that lives inside the case. It has room for 96 sprites in its own flash (40 come preloaded), drives the panel directly, and serves its own copy of the editor over your home Wi-Fi. That isn't a convenience: a page loaded from GitHub over HTTPS isn't allowed to talk to a plain-HTTP board on your network, so the board hands you its own copy, and you can open it from a phone without a computer. Two buttons change what's showing: Next, and On/off. Holding On/off for five seconds opens Wi-Fi setup.

The chip is tight. The board holds the player, Wi-Fi, a web server, the setup network and a compressed copy of the whole editor in 1.3 MB of flash, and one firmware version used 97% of it.

The Pi player is still in the repo, but the C3 is the product.

### Getting a screenless board onto Wi-Fi

The setup network is the part I thought about longest: a board with no screen has nowhere to show a password, and a password printed on a label is the same on every unit. So the board creates a new WPA3 network (the current Wi-Fi security standard) with a random name and a random 8-digit password, draws the digits on the LED panel (if you can read them, you're standing in front of the device), and keeps them in RAM only, for five minutes at most.

![Wi-Fi setup sequence between you, the ESP32-C3 board, and the LED panel: hold On/off for 5 seconds, read the 8 digits drawn on the panel, join the setup network, pick your home Wi-Fi, and the board forgets the setup key and returns to your sprite.](/images/glow-grid-wifi-setup.svg)

I tested it on a Windows 11 PC and an iPhone. The iPhone opens the setup page by itself. On Windows 11 you get an "Action needed" entry and have to click it. I haven't tested Android, so I don't claim it works there.

The first real run of the setup page showed "Loading..." forever, on both the PC and the iPhone. I assumed the new WPA3 network was the culprit and built a WPA2 comparison version to prove it. It wasn't. The F12 console on the PC showed a JavaScript syntax error: an apostrophe inside a single-quoted string had stopped the entire page script from running. That bug had shipped for four firmware versions, and every test had passed because the tests compared the page's text instead of running its code. Three days of debugging, one character of fix. The test that prevents it runs `node --check` on the page script. The new feature was the suspect, and old unchanged code was guilty.

### One name per board

Every board called itself `glowgrid` and advertised `glowgrid.local` over mDNS (the system that lets you type a `.local` name instead of an IP address). With one board that's a nice address. With two boards on the same home Wi-Fi (two kids, two rooms) they fight over the name, and whoever wins the race gets the other person's sprites. One hard-coded `#define`, a single constant in the firmware, was the whole problem.

Now each board names itself `glowgrid-` plus the last two bytes of its own MAC address, so mine is `glowgrid-b274.local`. The editor learns the name when the board joins Wi-Fi, the setup page prints it, and the board refuses requests addressed to any other name. I couldn't check the byte order of the MAC without hardware, so the first thing I did after flashing was compare the board's name to the MAC the flash tool printed. They matched. The follow-up defect only showed up on a real upgrade: my installed copy of the editor still offered the old `glowgrid.local`, because nothing had told it the board was renamed. Now the editor asks a board on USB for its name and drops the stale one.

## The case

![The case: frame, grid, diffuser cover, ESP32-C3 holder, and cradle, rendered from the generator script](/images/glow-grid-enclosure-preview.jpg)

The glow comes from the case. A black grid sits on the panel so each LED gets its own square, and a thin white cover over the grid diffuses each LED into a soft pixel. A frame holds the stack, a small tray holds the ESP32-C3 inside the back, and a cradle tips the whole thing back 12 degrees on a desk.

The parts are generated by a Python script (`enclosure/build.py` in the repo), so changing a hole or a clearance is a one-line edit. The design descends from three CC BY designs on Thingiverse: ["16x16 RGB Matrix"](https://www.thingiverse.com/thing:4127683) by The_Wrench_DIY, its [remix by chummer](https://www.thingiverse.com/thing:4459985), and the [one-part-frame remix by makeitworktech / Make It Work](https://www.thingiverse.com/thing:5737371). I used only the 10 mm pitch and 1 mm grid walls from those designs and built the rest from scratch. The Printables page is CC BY 4.0, and the code, editor, and example sprites are MIT.

### Three millimetres and a gap

The frame went through several versions. The change worth explaining is v7, because it taught me how a small geometry change shows up somewhere you aren't looking.

I made the frame 3 mm deeper because the wires soldered to the C3's pin tips were touching the back of the LED panel. All the numbers moved with the extra depth. The lip that holds the grid kept the same distance from the front (11.6 mm, as before), which put it 24 mm from the back instead of 21.

![Side sections of frame v6, v7 and v8: the lip stays 11.6 mm from the front, the distance to the back goes from 21 to 24 mm, and the v8 spring fingers are thicker](/images/glow-grid-frame-lip-v6-v7-v8.png)

Four spring fingers on the back plate press the stack forward against the cover. The extra depth made them 3 mm longer, and a longer arm is softer. On the v7 print there was a gap between the grid and the cover. I think the softer fingers let the panel sink onto the lip, but I haven't measured the finger force, so that's a hypothesis, not a finding. v8 keeps the same geometry and makes the fingers 2.0 mm thick instead of 1.6, which by arithmetic puts them about 1.2 times stiffer than the original. My v8 print doesn't sag, and that's the evidence I have.

The first fix Claude tried was wrong: it moved the lip toward the front, but the distance from the lip to the front had been right all along, and only the distance to the back needed to change. That mistake is why the diagram exists.

### Fifteen versions of a stand

The desk cradle took 15 versions, more than the frame, for a part whose whole job is to sit there. Its first design had no front hook because the hook covered the bottom row of LEDs. Then it needed one to hold the panel, so a 1.8 mm hook came back, low enough to stay below the first row. I started with screws into the desk, then removed the desk holes. Two loose feet became two feet joined by a curved bar. Seven of my design decisions were later reversed by a newer one, and I kept both entries in the log instead of editing the first away. My print settings are on the Printables page.

## What I'd tell you before you build one

The Printables page has the assembly order, the wiring, my print settings, and a longer list of what I haven't verified (spring-finger force, how the cover's friction fit behaves on other printers, the cradle's tape and screws over time). Two things I'd say even if you read nothing else there:

- **The power wiring needs better connectors than mine.** Parts of the power path on my unit use Dupont-style jumpers, which are typically good for 1 to 3 A, well below what a full-white panel draws. I run the panel at brightness 0.3, where a fully white frame draws about 4.7 A on the 6 A supply. For a unit you leave running, solder the 5 V and ground runs or use terminals rated 10 A or more.
- **Flash the ESP32-C3 on the bench before you close the case.** Its BOOT and RST buttons face the panel and can't be reached afterward.

## What's next

Two things. I plan one board per kid, which is what the per-board names were for. And Android is the other gap: I've only tested the Wi-Fi setup on Windows 11 and an iPhone. I'm also getting a Mac, and when I do I'll see about an iOS app that runs the editor UI. That one is a plan, not a build.

## Try it yourself

1. Open the [editor](https://dwooods.github.io/glow-grid/) and draw something.
2. Download the [case files](https://www.printables.com/model/1884854-glow-grid-16x16-led-panel-case-frame-grid-diffuser) from Printables.
3. Get the [code](https://github.com/dwooods/glow-grid) for the ESP32-C3 firmware (the Pi player is in there too).
4. Wire it as in the diagram below, flash the board, and print the holder first.

![The ESP32-C3 wiring diagram and build checklist](/images/glow-grid-wiring-checklist.jpg)

If something doesn't work, [open an issue](https://github.com/dwooods/glow-grid/issues). The example sprites are all original, and I'd ask that remixes keep it that way.

## Tools & AI assist

Same arrangement as the strip project, with more rules, because the project is bigger. I describe what I want and test the result on the real device. Claude writes the code, the build script, and the commits. We keep a journal and a feature tracker in a project folder, so a new session can pick up where the last one stopped.

That covers the volume: the editor, the board firmware, the case generator. It did not cover being right. Claude moved the frame lip the wrong way in v7, and it wrote a setup page whose tests all passed while the page itself didn't run. The decisions were mine: asking why a file needed its name to know how fast to play, having the board draw its own Wi-Fi password on the panel, and checking the layout on a real iPhone. I could only judge any of it by looking at the real thing.

The better prompt isn't a cleverer instruction, it's a person holding the device.
