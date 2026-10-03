---
title: "Local LLMs on a PC and a Pi: Almost Every Obvious Answer Was Wrong"
date: 2026-09-21
draft: false
tags: ["ai", "llm", "ollama", "raspberry-pi", "self-hosted", "benchmarking"]
description: "Open-weight LLMs on a 12GB AMD PC and a Raspberry Pi 5: a silent GPU fallback, a VRAM cliff, a judge that graded a right answer wrong, six Pi crashes, and the verdict."
summary: "I benchmarked open-weight LLMs on a Windows PC and a Raspberry Pi 5, and nearly every obvious answer turned out wrong: a GPU silently running on CPU, a 'bigger' model slower than no GPU at all, a judge model that graded a correct answer wrong. Local earned its place for narrow, lightweight work. It isn't yet a replacement for the closed models I use every day, and I didn't put them through the same tests."
featuredImage: "/images/hero-pc-vs-pi.jpeg"
featuredImagePreview: "/images/hero-pc-vs-pi.jpeg"
---

I got laid off this month, and my closed-model subscription suddenly looked less like a convenience and more like a bill. So I tried running open-weight models on my own hardware, a Windows desktop with a 12GB AMD GPU and a Raspberry Pi 5 with no GPU at all, to see whether that's more than a curiosity.

Almost every obvious answer turned out to be wrong. The model I thought was on the GPU was quietly running on the CPU. A bigger model ran slower than no GPU at all. The judge model grading the answers failed one that was right.

The short version: the PC can do real work if you tune it right, the Pi can handle narrow, patient tasks, and the honest answer to "more than a curiosity?" is: only for the lightweight stuff.

## Why I built this

I'd spent the past two years living inside closed models (ChatGPT, Gemini, Claude) and never had much reason to look past them. Most people haven't: the GPU you own probably can't compete with what a closed model gives you for free. Free time changed the math. I wanted to know what running a model on my own hardware actually gets you — no API bill, no data leaving the building — and I'm the kind of person who turns free time into a hobby project anyway. I'd also been meaning to start writing about what I build; this post is the first real attempt.

The two machines weren't answering the same question. The PC was a test of whether local inference could get close enough to a closed model for daily work. The Pi wasn't a bake-off at all: I just wanted to know whether it could run anything useful.

## The hardware

| | Windows PC ("DavidPC") | Raspberry Pi 5 |
|---|---|---|
| CPU | Intel Core i7-13700K | Broadcom BCM2712, 4× Cortex-A76 |
| RAM | 128GB DDR | 8GB (7.87GB usable) |
| GPU | AMD Radeon RX 6700 XT, 12GB VRAM | None — CPU-only |
| Storage | NVMe SSD | NVMe |
| OS | Windows 11 Home | Raspberry Pi OS (Debian 13 "trixie"), 64-bit |
| Runtime | Ollama 0.34.1, exposed on `localhost:11434` | Ollama 0.34.1 |

If you only read one section, read the one about the judge grading a right answer wrong, because that's the one that changed how I read every other number in this post.

## The PC

Everything in this section runs on the Windows desktop, the i7-13700K and the RX 6700 XT.

### Getting the GPU actually used

Ollama's default behavior on my machine was to quietly fall back to the CPU. That's easy to miss (it still generates text, just slowly), and it took a real benchmark run to notice: **6.88 tokens/sec** on `phi4:14b`, which is CPU-bound and painfully slow for anything interactive.

The fix, since Ollama's GPU detection on AMD cards can be finicky, was three environment variables, set together:

```powershell
[System.Environment]::SetEnvironmentVariable("HSA_OVERRIDE_GFX_VERSION", "10.3.0", "User")
[System.Environment]::SetEnvironmentVariable("OLLAMA_NUM_PARALLEL", "1", "User")
[System.Environment]::SetEnvironmentVariable("OLLAMA_ORIGINS", "*", "User")
```

`OLLAMA_NUM_PARALLEL=1` stops Ollama from fragmenting VRAM across parallel request slots you don't need for single-user use; `OLLAMA_ORIGINS=*` opens CORS so local tools can talk to the server. Both are User-scope variables that survive a reboot with no startup script needed. One caveat: a Windows or AMD driver update can silently knock GPU acceleration back to CPU-only, so after any driver update it's worth a quick `ollama run qwen2.5:3b --verbose "hi"` to confirm `library=Vulkan` still shows up in the output.

**Correction, caught in review.** My first draft said `HSA_OVERRIDE_GFX_VERSION` tells ROCm to target the RX 6700 XT, then told you to verify the fix by looking for `library=Vulkan`. Those can't both be right: that variable is ROCm-only, and Vulkan never reads it. Claude flagged the contradiction, so I checked the actual server log:

```
msg="dropping integrated GPU; to enable, set OLLAMA_IGPU_ENABLE=1" library=Vulkan compute=0.0 name=Vulkan1 description="Intel(R) UHD Graphics 770"
msg="inference compute" library=Vulkan compute=0.0 name=Vulkan0 description="AMD Radeon RX 6700 XT" type=discrete total="12.0 GiB" available="11.2 GiB"
```

Vulkan, not ROCm. (That `available="11.2 GiB"` is exactly where the next section's VRAM cliff sits.) The wrong explanation came from the Gemini session where I first fixed the GPU, and I carried it into this draft without checking. A small lesson about where confident-sounding paragraphs come from.

So which variable actually fixed it? I don't know. I set all three at once, plus a restart, and never isolated one. My bet is `OLLAMA_NUM_PARALLEL=1`, because Ollama decides GPU vs. CPU from predicted memory need and fewer parallel slots shrink that estimate; `OLLAMA_ORIGINS` is pure CORS and can't be it. That's a hypothesis, so check `library=` in your own server log before crediting any of them.

{{< admonition type="warning" title="FYI: two settings that made it worse" open=true >}}
Claude later suggested two more "optimizations," `OLLAMA_FLASH_ATTENTION=1` and `OLLAMA_KV_CACHE_TYPE=q8_0`, to save VRAM. Neither had been tested on AMD/Vulkan, and together they dropped generation from 150 to 52 tok/s until I unset them, so test any optimization on your own hardware, even when the AI is the one suggesting it.
{{< /admonition >}}

### The 12GB VRAM cliff

Once the GPU was engaged, the difference was dramatic, but only up to a point, and the point matters more than I expected. (The last column compares every model to `phi4:14b`'s CPU-only number, the one CPU baseline I measured; read it for the ordering, not the decimals.)

| Model | Mode | VRAM | Tokens/sec | vs. CPU baseline |
|---|---|---|---|---|
| `phi4:14b` | CPU only | 0GB | 6.88 | 1.0x (baseline) |
| `qwen2.5:3b` | 100% GPU | ~2.0GB | **138.94** | ~20x |
| `qwen3.5:9b` | 100% GPU | ~4.7GB | **17.98** | ~2.6x |
| `deepseek-r1:14b` | 100% GPU | ~8.9GB | **8.32** | ~1.2x |
| `gpt-oss:20b` | split (GPU+RAM) | >12GB | 11.28 | ~1.6x |
| `gemma4:31b` | split (GPU+RAM) | >12GB | **~5.5** | **0.8x — slower than CPU-only** |
| `qwen2.5-coder:32b` | split (GPU+RAM) | ~19GB | **4.25** | **0.6x — the new worst** |

![Horizontal bar chart of generation speed for five models on the RX 6700 XT, colored by whether the model fits in 12GB VRAM or splits into system RAM, with a dashed CPU-only baseline at 6.88 tok/s; gemma4:31b and qwen2.5-coder:32b fall below the baseline](/images/chart-vram-cliff.png)
*The same numbers as a picture. `qwen2.5:3b` (138.94 tok/s) is left off so the split-mode bars stay readable; the point is the two 31B+ models landing to the left of the no-GPU line.*

Everything that fits in the 12GB of VRAM is fast. Past roughly 11.2GB, Ollama starts splitting layers into system RAM over the PCIe bus, and the slowdown isn't gentle: `gpt-oss:20b` still beat the CPU baseline in split mode, but `gemma4:31b` ran slower than a smaller model on CPU alone.

`qwen2.5-coder:32b` settled an argument with someone else's AI. Gemini had called a 32B model on this rig a reasonable "CPU/RAM hybrid," since 128GB of RAM would "easily handle" the overflow, just "slightly slower." One quick run said otherwise: 4.25 tok/s, worse than CPU-only and the worst split-mode number in the whole project.

What I took from it:

- **~13B parameters at Q4_K_M (7–9GB) is the sweet spot** on a 12GB card. Q4_K_M is a common 4-bit compressed format; at that size a model is big enough to be useful and small enough to stay in VRAM. Anything bigger, test before you trust it.
- **Watch `num_ctx`.** The default context window can eat 2–6GB of VRAM before generating a token, enough to quietly push a 14B model out of VRAM. The README has my settings; the one that matters later is `OLLAMA_MAX_LOADED_MODELS=1`, which comes back to bite me on the Pi.
- **Fully in VRAM means steady.** `deepseek-r1:14b` held 8.05–8.58 tok/s across four different prompts with no slowdown, which matters more in a real product than a fast first answer.

### Testing it properly: what an automated eval harness found

Raw tok/s tells you nothing about whether a model is *right*. So I set up `promptfoo`, a Node-based eval tool, to score models on five workloads (tool use, coding, vision, extraction, and chat), with a separate judge model (`deepseek-r1:14b`) grading the open-ended answers so nothing graded its own homework.

One caveat: these suites are small, three to sixteen cases each. That's enough to catch a model that can't do something, or a harness that's grading wrong, which is what this section is about. It's not enough to rank models, so read "4 out of 4" as "passed the smoke test," not "the best." The configs and cases are in the repo linked at the end.

![Terminal running npx promptfoo eval on the vision suite, 8 of 12 test cases complete](/images/promptfoo-cli-running.png)
*`npx promptfoo@latest eval -c promptfoo-vision-pc.yaml -j 1 --no-cache` mid-run: `-j 1` so results are directly comparable, `--no-cache` so every case re-queries the model instead of replaying a cached response.*

Five suites, five surprises:

| Suite | What I assumed | What actually happened | Whose mistake |
|---|---|---|---|
| Tool use | The coding model is the best agent | `qwen2.5-coder:14b` went 1 for 4: it prints a tool call as plain text and never fills Ollama's `tool_calls` field. Two "chat" models went 4 for 4. | The model's reputation |
| Coding | The judge's 15/16 was right | The one "fail" was correct code. Real score: 16/16. | The judge |
| Vision | The OCR model wins at OCR | `glm-ocr` won't stop repeating its answer. The generalist `qwen3-vl:8b` won, 5 of 6. | The model, plus two bugs in my scorer |
| Extraction | A miss means wrong data | Every field was right; the model tacked extra text on after the JSON. 8 of 9. | The model, for ignoring "JSON only" |
| Chat | A substring check is good enough | A wrong answer contained the right words and passed. Real score: 10/12, not 11/12. | My test |

Two of these deserve the full story.

**The judge that graded a correct answer wrong.** The coding suite came back 15 out of 16, with the one failure landing on `qwen2.5-coder:14b`'s `parse_duration` function. The terminal output truncated the generated code, so Claude built an isolated debug run to capture it in full, and we hand-checked it together against the test's own three example inputs. The code was correct on all three: `total_seconds = hours * 3600 + minutes * 60` after a clean split. The judge's stated reason for failing it ("incorrectly processes cases where minutes are present without an 'm' suffix") didn't correspond to anything in the code or the prompt's own examples. Not a borderline call — a wrong grade on a right answer. That bumped the real score to 16 out of 16, but the bigger finding is that an automated judge can produce a single plausible-looking bad verdict sitting quietly inside an otherwise-clean run, with nothing about the raw number giving it away. I spot-checked the other rubric-graded suites by hand afterward and they held up, so this looks like an isolated incident rather than a systemic problem, but "isolated" is only a conclusion I have because I went and checked.

**The vision showdown: a model that won't stop talking.** Six real receipt photos, with vendor, date, and total pulled out as JSON. Weighted scores give half credit when a receipt is partly right, which put the generalist at 92%. `glm-ocr`'s 4 of 6 took fixing two bugs in my own scorer first: a JSON extractor that grabbed a garbled second copy when a model repeated its answer, and a vendor check that failed "La Cabaña" read back as "La Cabana." The model hit hardest by my bugs was the one already failing for a real reason, which is exactly how a bad number gets believed. That real reason: `glm-ocr` repeats its finished answer until it hits the context limit, every time, and doubling the limit just doubled the loop. When it did stop, it read receipts fine.

One receipt beat both models. A Costa Coffee receipt with a €4.24 pre-tax subtotal and a €5.00 total came back as €4.24 every time, even after I rewrote the instructions to ask for "the final amount actually paid." That's a small-model limitation, not a wording problem.

![promptfoo eval dashboard showing glm-ocr and qwen3-vl:8b both FAIL(0.50) on the Costa receipt with the identical reason — vendor match=true, total match=false (got 4.24, expected 5) — and both PASS on La Cabaña](/images/promptfoo-dashboard-vision.png)
*The actual promptfoo dashboard, mid-suite: both models fail Costa the same way (4.24 vs. 5, the VAT-vs-net limitation above) and both pass La Cabaña once the diacritic-normalization fix was in; "La Cabana" without the tilde reads as a match now.*

<div style="display:flex; gap:1rem; flex-wrap:wrap; margin:1.5rem 0;">
<figure style="flex:1; min-width:220px; margin:0;">

![Costa Coffee receipt from Malta International Airport, showing a pre-tax subtotal of €4.24 and a VAT-inclusive total of €5.00](/images/receipt-costa-coffee.jpg)
*The Costa Coffee receipt every model extracted wrong the same way: €4.24 (pre-tax) instead of the €5.00 actually paid.*

</figure>
<figure style="flex:1; min-width:220px; margin:0;">

![Home Depot receipt, the one glm-ocr attributed to the wrong vendor](/images/receipt-home-depot.png)
*The Home Depot receipt `glm-ocr` mis-extracted the vendor on; the footer survey URL is the likely culprit.*

</figure>
</div>

**The meta-lesson.** Most of these findings aren't about the models; they're about how easily a benchmark can lie to you. The rule I've landed on: a failure that hits every model identically is almost always your harness, because models fail in different, idiosyncratic ways and a scoring bug fails everyone the same. And any single surprising result is worth pulling the raw output and checking by hand before it goes in a table.

### Building my own voice assistant: three gotchas that ate an afternoon

A fully offline voice assistant is one of the most common things people build on hardware like this, and talk is cheap until you wire one up and hit record. Claude built one for me: push-to-talk, `faster-whisper` to turn speech into text, a local model through Ollama to answer, and `piper-tts` to speak the answer, with no cloud round-trip anywhere. The point was a real, measured time to first token (TTFT: how long you wait before the first word of the answer arrives) instead of the estimate I'd been using. Three things broke in ways worth writing down.

| Gotcha | What it looked like | Fix |
|---|---|---|
| Default 5-minute `keep_alive` | 12.27s TTFT on turn one, 32.51s on turn two — the model was being evicted from VRAM and reloaded every idle gap | `"keep_alive": -1` in the request payload |
| Reasoning model starves itself of tokens | One turn returned nothing and the script crashed writing an empty WAV — the hidden thinking block ate the whole 4096-token `num_ctx` | `num_ctx: 8192` |
| LLMs write Markdown; TTS reads the asterisks aloud | First clean answer was full of `**bold**`, which Piper pronounces | A "voice interface, no formatting" system prompt, plus a regex strip pass as backup |

Two details the table can't hold. A slower second turn is the tell for the `keep_alive` problem: a warm-up issue would make the first turn slow, but a reload penalty hits whichever turn follows an idle gap. And the hidden thinking isn't small: even "hi" burned 258 tokens before `qwen3.5:9b` said a word. The Markdown fix has two layers on purpose, because models don't follow "no formatting" every time.

**Bonus finding: confident and wrong.** Asked when the Raspberry Pi 5 came out and how much RAM it has, `qwen3.5:9b` got the year right (2023), then invented a "Plus" RAM tier that Raspberry Pi never made, in two differently worded attempts. The easy fact was right; the detail sitting next to it was made up.

### The real answer to "what's local TTFT" is a flag, not a GPU

With the voice assistant finally working, time to first word was awful: 14 to 84 seconds, worse the harder the question. `qwen3.5:9b` is a hybrid-reasoning model, and it does all its thinking silently before it says anything. The fix is one field in the request, `"think": false`. I also tried skipping reasoning models entirely with the small, fast `qwen2.5:3b`. Same five questions, same warm model:

| | `qwen3.5:9b`, reasoning on (default) | `qwen3.5:9b` + `think: false` | `qwen2.5:3b` (no reasoning) |
|---|---|---|---|
| Time to first word | 14.4s – 83.6s | 2.39s – 2.47s | **2.13s – 2.16s** |
| Answers materially wrong | 0 of 5 (one fabricated detail, see above) | 0 of 5 | **2 of 5** |

A second, easier batch of questions shows where the time goes:

![Stacked bar chart: five questions, each run against qwen3.5:9b with think:true and think:false at num_ctx 8192. The think:true bars are 81–99% invisible reasoning time; the think:false bars are 40–63% invisible and all under 5.5 seconds total.](/images/chart-think-stacked.png)
*Blue is time you spend staring at nothing. With reasoning on, it's 81–99% of every turn; with it off, the bar shrinks and most of what's left is the answer actually streaming.*

What to take from this:

- **Most of the wait is invisible thinking.** With reasoning on, 81–99% of every turn happened before the first word. The model itself generates at a normal ~18 tok/s.
- **One field fixes it.** `"think": false` cut time to first word 6–30x, with no quality drop I could see on the questions I tried.
- **Speed benchmarks won't catch this.** Reasoning and non-reasoning modes generate at the same tok/s, so every tok/s number earlier in this post misses it. The difference is how much gets generated before you see anything.
- **Going smaller isn't the fix.** `qwen2.5:3b` had the fastest time to first word in the whole project, but only by a quarter second, and it got two of the five answers wrong, arithmetic included. The flag was the right lever, not the model size.
- **The model still needs room to think.** At the old 4096 `num_ctx`, one question spent its whole budget reasoning and never answered, so the 8192 setting from the gotchas table isn't optional.

### How far can you actually push context? A needle in a 32,000-token haystack

The `qwen3.5:9b` tag on Ollama advertises a 256K-token context window, and after `num_ctx` bit the voice assistant twice, I wanted a measurement instead of a marketing number. So I ran the standard needle-in-a-haystack test: bury one invented fact (a "generator override code," `ZULU-FOXTROT-8841`, that can't be in any training data) at five positions in a block of filler text, from the very start to the very end, and double the haystack from about 1,000 tokens up to 32,000. Scoring was an exact-string match, not another model; after catching my judge grading a right answer wrong, I wasn't giving it a second chance.

The headline is almost anticlimactic: **every test passed.** Forty-two runs across every size and position, zero misses. That doesn't prove the 256K claim, since 32K is only an eighth of it, but recall never failed anywhere I tested.

Recall wasn't the interesting number, though.

| Context size | Prefill speed | Generation speed | Time to first token (warm) |
|---|---|---|---|
| 1,024 tokens | ~655 tok/s | ~62 tok/s | ~3.7s |
| 2,048 tokens | ~656 tok/s | ~61 tok/s | ~5.2s |
| 4,096 tokens | ~628 tok/s | ~60 tok/s | ~8.4s |
| 8,192 tokens | ~400–470 tok/s | ~33–40 tok/s | ~19–22s |
| 16,384 tokens | ~277 tok/s | ~17.8 tok/s | ~58s |
| 32,768 tokens | ~203 tok/s | ~11.8 tok/s | ~154s |

![Line chart on a log scale with prefill speed, generation speed, and time to first token for qwen3.5:9b, each indexed to its 1,024-token value as 100; the two speed lines decay to 31 and 19 while time to first token climbs to 4,162](/images/chart-needle-in-haystack.png)
*All three metrics indexed to their 1,024-token value (=100) on a log scale, because they don't share units. Throughput decays gently; TTFT goes near-vertical, and the model was 100% GPU-resident the whole way.*

Generation speed fell more than 5x with the model 100% in VRAM the whole time (5.4GB at 1K tokens, 6.6GB at 32K). So this isn't the VRAM cliff from earlier, where weights spill into slow system RAM. Nothing spilled. It's a compute problem: every new token gets compared against every token already in the window, and that gets more expensive as the window grows. At 32K, `qwen3.5:9b` generated at 11.8 tok/s, almost exactly what `gpt-oss:20b` managed while spilling out of VRAM. A long conversation costs about as much as the cliff itself.

Time to first word is what kills the product: under 4 seconds at 1K tokens, about two and a half minutes at 32K, with `think: false` on the whole time. That's a second, separate tax on top of the reasoning one. A voice assistant with a 30-turn conversation behind it wouldn't be slow, it'd be unusable. The 256K on the model card is what the model will *accept*, not what stays fast enough to build on.

One loose thread: my two runs at 8K disagree (~400 vs. ~470 tok/s prefill, ~40 vs. ~33 tok/s generation), while every other size reproduced cleanly. I don't have an explanation, so it's logged as open rather than guessed at.

## The Raspberry Pi 5

Everything in this section runs on the Pi 5: 8GB RAM, no discrete GPU, CPU-only inference.

### CPU-only, and it shows

No GPU means every model lives or dies by the Pi's ~17GB/s memory bandwidth, so speed comes down to how big the model file is. Five 7–9B models all landed at 2–2.9 tok/s: technically running, but submit-and-wait, not a conversation. The usable tier is under 4B, so that's where I measured six models for speed and then ran them through the same quality suites as the PC. One setup note: the Pi can't hold the 14B judge model, so Claude's fix was to keep generation on the Pi and send only the grading call across the LAN to the PC.

![Architecture diagram: the model, promptfoo, and the llm-rubric grading assertion all run on the Raspberry Pi 5; only the grading call crosses the LAN to the PC's deepseek-r1:14b judge model, whose verdict text returns to the Pi, where llm-rubric turns it into a pass/fail score.](/images/chart-lan-judge-diagram.png)
*Everything runs on the Pi except the judge model itself. `llm-rubric` is a promptfoo assertion, so it's the Pi that sends the grading prompt across the LAN and the Pi that turns the verdict that comes back into a score.*

![Scatter plot: measured generation speed against aggregate pass rate across all four quality suites for the six Pi shortlist models. qwen2.5:1.5b sits far right at 12.08 tok/s and 40%; llama3.2:3b and qwen2.5:3b cluster near 5.5 tok/s at 73–80%, the best on the shortlist.](/images/chart-pi-speed-vs-quality.png)
*All six shortlist models, one dot each: the fastest model and the two best-scoring models sit in opposite corners. Hatched dots are the two whose agentic score was zeroed by the memory-pressure bug, not by the model. 15 cases per model.*

What I'd want someone to know before testing their own Pi:

- **Don't trust the published speeds.** Every vendor estimate was optimistic; real speeds landed at 37–81% of the number on the box.
- **File size predicts speed, not parameter count.** Tokens per second times file size in GB came out at roughly 11 for all six models, so the smallest file (`qwen2.5:1.5b`, 0.99GB) was the fastest, ahead of a "1B" model.
- **The fastest model was the weakest.** `qwen2.5:1.5b` came last or tied for last on every quality suite. `llama3.2:3b` and `qwen2.5:3b`, at about half its speed (~5.5 tok/s), were the only two that didn't drop a case on the judge-free tests, so they're my picks.
- **One model at a time.** Six models through 8GB of RAM forced constant load/evict cycles, and under that pressure a model can return completely empty output even though it works fine alone. `OLLAMA_MAX_LOADED_MODELS=1`, the setting I said would come back to bite me, had never been set on the freshly reinstalled Pi, and without it the first run stalled with two models loaded at once. If you set it with `systemctl edit`, include the `[Service]` header, or systemd silently ignores the line.

The full speed tables, the per-suite results and the memory-pressure details are in the repo's `FINDINGS.md`. Run your own models through it rather than taking my six as the answer.

### Six crashes and a watchdog: closing out the Pi's vision suite

The Pi's vision suite, the same receipt-extraction workload from the PC showdown above, was supposed to be a quick coda to the speed and quality tables. It turned into the most disruptive week of the whole project, because the assumption I walked in with was backwards: an active cooler is not a fix for sustained CPU-bound inference on a Pi 5. It's a mitigation, and there's a real difference.

The Pi has had Raspberry Pi's own Active Cooler (heatsink plus fan) installed since before any benchmarking began, confirmed present and spinning every time I checked.

![Raspberry Pi 5 with the official Active Cooler (heatsink and fan) mounted](/images/pi5-active-cooler.jpeg)
*The Pi 5 with its Active Cooler on, present and spinning through all six crashes below. Necessary, it turned out, but not sufficient.*

Running the six-case, two-model matrix anyway produced six hard, silent reboots: some fast and with no warning, some after cycles of visible throttling. My first guess was power, so I logged per-rail voltage with `vcgencmd pmic_read_adc` through several crashes; every rail held steady. My second guess, that the cooler had this covered, I'd half-written into a draft before retracting it: the fan was spinning through all six crashes, single-model runs included. And since the board survived an 80.7°C peak while other runs died in the same 79–86°C band, there was no clean trip point. My best read at the time: crashes were probabilistic near that range, and I didn't know what separated a crash from a clean run.

After the fourth crash, Claude asked me directly whether we were done; the honest answer was no, the vision suite still had no trustworthy result. I pushed back before it went further: *"This keeps crashing, so not sure we are going to get the results we want. We might want to summarize as not possible to complete unless you have other ideas."* Rather than agreeing to close it out, Claude came back with three options: split the two-model matrix into single-model runs with checkpointing (cheapest, try first), build a software watchdog that kills the process and lets the board cool before the danger zone, or swap in a more aggressive third-party cooler. That third one I killed myself, and not on technical grounds: I wasn't going to spend money on a different cooler for a hobby project. The postscript below says that was probably the right lever. It was still not happening. Plan: single-model split first since it's basically free, watchdog only if that wasn't enough.

It wasn't enough, so: the watchdog. Monitor temperature, kill the inference process before the danger zone, let the board cool, resume. Claude's first version shipped with two bugs worth knowing about if you're scripting anything similar around `promptfoo`: a naive PID kill that missed the child processes `npx` actually spawns, and a success/failure check that misclassified a clean kill-and-resume cycle as a failure (both are written up in the repo's `FINDINGS.md`). With both fixed, the watchdog worked exactly as designed; I could prove it killed and resumed correctly.

It still wasn't usable for `qwen3-vl:2b`: that model's normal time per case was longer than the watchdog's kill window, so it killed healthy cases before they could finish. I ran the rest by hand, leaning on `promptfoo`'s cache so a crash wouldn't cost the cases already done, which produced the sixth crash and then a clean pass. Final scores: `minicpm-v4.6` at 5.5 of 6 weighted (92%, a partial run I accepted rather than risk another crash re-running it) and `qwen3-vl:2b` at 4 of 6. As I put it at the time: "I'm good with what we have." Costa failed the same way it had on the PC, the pre-tax subtotal instead of the total: third time, third model, so it's a pattern to design around, not re-prompt away. One case is still unexplained: that same Costa receipt looped for 18.86 minutes on one run and finished in 1–2 minutes on two others.

**Postscript, September 22 — I went back and crashed it on purpose.** That was where I left it when I wrote the section above: probabilistic, cause unknown. I wasn't happy leaving it as an open question, so I reran the vision suite with a logger Claude wrote for the occasion. Once a second it recorded the chip's temperature, whether the firmware was throttling, the voltage and current on every power rail, the CPU speed and the fan speed, and it forced each line onto the disk immediately, so the last second before a reset would survive it. It crashed on the first try, three minutes and ten seconds in, and this time I have the whole thing.

![Four stacked time-series panels over the 191 seconds before the Pi reset, one sample per second: SoC temperature, fan RPM, SoC core current, and 5 V input voltage. A vertical line marks the model swap from minicpm-v4.6 to qwen3-vl:2b; a dashed line marks the last sample before the reset.](/images/chart-pi-crash-timeline.png)
*The 29 seconds that mattered, one sample per second. Pink bands on the top panel are the seconds the firmware's temperature limit kicked in. The dashed line is the last row the logger wrote; the next one came 3 minutes 48 seconds later, after the reboot, at 47°C.*

The story the one-second data tells is not the one I'd been telling. `minicpm-v4.6` ran first, and the board didn't care: the main chip (the SoC) drew about 6.8 amps at 67°C, with the fan at 6,400 RPM, for a minute and a half. Then the suite swapped to `qwen3-vl:2b`, and the chip went from 60°C to 80°C in six seconds (twenty degrees in the time it takes to read this sentence), then settled at 11.5 amps, roughly 12 W, with the fan pinned at its maximum of 8,774 RPM and the firmware's temperature limit switching on and off for 11 of the last 24 seconds. Twenty-nine seconds after the swap, the last row. Peak 84.5°C.

The power was steady. The 5 V input stayed between 4.97 and 5.32 V the whole run (the low-voltage warning trips at 4.63), and the chip's core supply held 1.0 V while delivering 12 amps. Memory wasn't the problem either: 3.5 GB free, nothing pushed out to disk. Not the power supply, not memory — the same conclusion as before, now with numbers attached. And the finding that reframed this section for me: the highest current of the entire run, 15.2 amps, was `minicpm-v4.6`'s load spike at the one-minute mark, and the board shrugged it off. What killed it was `qwen3-vl:2b` holding 12 W for half a minute. Not a spike — a sustained load about 70% higher than the other model in the same suite, on a cooler whose ceiling sits somewhere between the two.

![htop on the Raspberry Pi at 00:51:36 uptime: all four CPU cores at 100%, four llama-server processes at the top of the process list, the thermal logger script a few rows below them.](/images/pi-htop-at-reset.png)
*`htop` at 00:51:36 uptime, which works out to the last second in the CSV. The board reset before the next refresh.*

So "probabilistic near that range" was me not having enough data. It's closer to deterministic than that: this cooler holds about 7 W indefinitely and does not hold about 12 W, and which of your models is the 12-watt one is not something the model card tells you.

Two things I'm leaving open, because they are. First, Linux reported the CPU still at full speed, 3000 MHz, in every second the temperature limit was on, when it should have been slowing down. Either the firmware hadn't reacted yet, or Linux's speed reading lags behind what the firmware actually did. I don't know which; asking the firmware directly (`vcgencmd measure_clock arm`) is the next test. Second, the system log has no trace of the reset at all: Raspberry Pi OS keeps that log in memory by default, so a hard reset wipes it. The only record of those 29 seconds exists because the logger forced every line onto the disk as it went. If you're going to crash a Pi on purpose, do that, and make the system log permanent first (`sudo mkdir -p /var/log/journal`).

The practical upshot for anything I build on this board: active cooling is necessary, but treating it as sufficient was the mistake that cost the week. Any real product running sustained inference on a Pi 5 needs an application-level watchdog and auto-restart designed in from the start, tuned per-workload, not borrowed from this one, and with the per-model power draw measured first, since the postscript says the difference between "fine indefinitely" and "dead in 29 seconds" was which model was loaded. The kill-window mismatch that sidelined the watchdog for `qwen3-vl:2b` is the reminder: "the watchdog works" and "the watchdog works for this model's timing" are two different claims, and only one matters in production.

There's no Pi project waiting on any of this, for what it's worth — I wanted to know what the board could do, and now I do.

## Tools & AI assist

I did the whole project with **Claude**, keeping three running docs as we went (instructions, a session log and a benchmark log), so nothing had to be reconstructed from memory later. This post is mostly a distillation of that log.

Claude wrote every promptfoo config, the voice-assistant pipeline, the Pi thermal watchdog script, and the one-second crash logger in the postscript. It also made every chart in this post from the run data, plus the LAN-judge diagram, and it did the pre-publication review pass that compared this post against the repo's raw files. I generated the hero image with Gemini (Nano Banana). I ran the actual hardware, watched the thermals, and made the calls on what to try next and when to stop, including a couple of times I overruled where the investigation was headed, like the Pi crash section above.

Claude also got things wrong, more than once. The GPU env vars earlier in this post are one example: its first pass at "optimizing" them cost me a 3x speed regression before we caught it. The Pi thermal watchdog's first version silently didn't work at all. And three summary numbers in early drafts of this post and the repo's `FINDINGS.md` didn't match the CSV they were summarizing, which nobody noticed until the review pass opened the CSV instead of comparing one paragraph to another. All of it is covered in place, where it happened, rather than saved up for a highlight reel here.

## Lessons learned & what's next

If you want one pick per machine: `qwen3.5:9b` with `think: false` on the PC, and `llama3.2:3b` or `qwen2.5:3b` on the Pi. The lesson threading through both is the one from the eval-harness section: none of this shows up until you run the test and check the raw output by hand. Here's the whole post as the table it turned out to be:

| What I assumed | What the test found |
|---|---|
| The GPU just needs the right env var | Three vars and a restart fixed it; which one did the work is still unknown |
| Bigger model, better answers | Past 12GB, a 31B model ran slower than no GPU at all |
| The coding model is the agent model | It never populates `tool_calls`; the "chat" models went 4 for 4 |
| An automated judge is objective | It failed a correct function, and nothing about the score gave it away |
| The OCR model wins at OCR | It can't stop talking; the generalist won |
| Smaller model, faster and good enough | Fastest TTFT in the project, two wrong answers out of five |
| 256K context means 256K usable | 40x worse TTFT and 5x worse throughput at an eighth of that, with VRAM flat |
| The fastest Pi model is the pick | It was the weakest on every quality suite |
| Active cooler, problem solved | It holds 7 W indefinitely and not 12 W, and which model draws 12 W isn't on the model card |
| The watchdog works, so it's fixed | It works; it kills this model's normal cases before they finish |

If you want to run any of this yourself rather than take my numbers on faith, the repo has everything: the promptfoo suites for both machines, the receipt images and encoder script behind the vision tests, the voice assistant script, and a `FINDINGS.md` with the full data behind every table above; the README covers PC and Pi setup separately since the env vars and model lists differ. The one-second thermal/power logger and the actual crash data behind the postscript above live in `benchmarks/pi-crash-capture/`. [github.com/dwooods/local-llm-benchmark](https://github.com/dwooods/local-llm-benchmark)

**So — more than a curiosity?** Not really. Not as a replacement for the closed models I started this post living inside of, and not on the hardware most people have. A 12GB card is a perfectly respectable GPU by any non-AI standard, and it caps you at roughly 13B parameters; a 13B model is a long way from ChatGPT or Claude on anything open-ended (that's two years of daily use talking, not a suite I ran), and the price of "free" is a tuning tax (env vars, `num_ctx`, `think: false`, a driver update that can silently undo all of it) plus a model that, asked a simple factual question, invented a Raspberry Pi product tier that doesn't exist.

Where local does earn its place is the lightweight, narrow stuff: the receipt-extraction pipeline from this post, pointed at a folder of scanned invoices instead of six test photos, running on a Pi with no API bill and no data leaving the house, or a voice assistant that only has to answer short questions, or a small fixed set of actions on a Pi. Work where "good enough, and no data leaves the building" beats "best possible answer."

I didn't put the closed models through the same suites, and that's the obvious next test: the one comparison this post talks about and doesn't measure. And I haven't found a job for an open model yet: I'm still paying for Claude, because it's the best fit for what I do right now, and that stays true until something I can run locally can compete with it.
