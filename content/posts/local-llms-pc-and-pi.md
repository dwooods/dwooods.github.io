---
title: "Local LLMs on a PC and a Pi: Almost Every Obvious Answer Was Wrong"
date: 2026-09-21
draft: true
tags: ["ai", "llm", "ollama", "raspberry-pi", "self-hosted", "benchmarking"]
description: "Benchmarking open-weight LLMs locally on a Windows PC with a 12GB AMD GPU and a Raspberry Pi 5 — a silent GPU fallback, a VRAM cliff that runs slower than no GPU at all, an eval harness that caught its own judge grading a right answer wrong, six Pi hard crashes, and the one hidden flag that fixed latency more than the hardware ever did."
summary: "I benchmarked open-weight LLMs on a Windows PC and a Raspberry Pi 5, and nearly every obvious answer turned out wrong — a GPU silently running on CPU, a 'bigger' model slower than no GPU at all, a judge model that graded a correct answer wrong. The biggest latency fix wasn't the hardware — it was one hidden flag."
featuredImage: "/images/hero-pc-vs-pi.png"
featuredImagePreview: "/images/hero-pc-vs-pi.png"
---

I've spent the last few years living entirely inside closed models — ChatGPT, Gemini, Claude — and, like most people, never had much reason to look past them. Open-weight models rarely come up in that conversation, mostly because the GPU most people actually own can't run something that competes with what a closed model already gives you for free. I wanted to find out for myself what running an open-weight model entirely on my own hardware actually gets you — no API bill, no cloud dependency, no data leaving the building — and whether it's good enough to be more than a curiosity.

I tested that on two very different machines, and they weren't really answering the same question. On a high-end Windows desktop with a discrete AMD GPU, the question was whether local inference could get close enough to a closed model to be genuinely useful for daily work. On a Raspberry Pi 5, it wasn't a bake-off against the PC at all — it was a feasibility check for a future Pi project: can this hardware even run an open-weight model well enough to build something useful on top of it.

The short version: the PC is genuinely usable for daily work if you tune it right, the Pi can handle narrow, patient tasks but isn't a chat replacement, and even where the hardware clears the bar, the convenience and accuracy of a closed model make a free open-weight model a harder sell than it should be. There are also a handful of gotchas on both sides that cost more time than the actual setup did.

Here's what I found, with real numbers.

*Repo: [github.com/dwooods/local-llm-benchmark](https://github.com/dwooods/local-llm-benchmark) — every promptfoo config, the voice assistant script, and the full `FINDINGS.md` this post distills.*

## The hardware

| | Windows PC ("DavidPC") | Raspberry Pi 5 |
|---|---|---|
| CPU | Intel Core i7-13700K | — |
| RAM | 128GB DDR | 8GB (7.87GB usable) |
| GPU | AMD Radeon RX 6700 XT, 12GB VRAM | None — CPU-only |
| Storage | NVMe SSD | — |
| OS | Windows 11 Home | Debian GNU/Linux 13 ("trixie") 64-bit |
| Runtime | Ollama 0.33.2, exposed on `localhost:11434` | Ollama 0.33.2 |

## Tools & AI assist

The whole project ran inside a Claude Project ("Run Local LLM") using **Claude Cowork** — not Claude Code, just Cowork end to end. Three standing docs (Project Instructions, a Session Log, a Benchmark Log) got maintained as we went, so nothing had to get reconstructed from memory later — this post is largely a distillation of that log.

Cowork wrote every promptfoo config, the voice-assistant pipeline later in this post, and the Pi thermal watchdog script. I ran the actual hardware, watched the thermals, and made the calls on what to try next and when to stop — including a couple of times I overruled where the investigation was headed (more on that in the Pi crash section below).

It also got things wrong, more than once. The GPU env vars below are one example: Cowork's first pass at "optimizing" them cost me a 3x speed regression before we caught it. The Pi thermal watchdog's first version silently didn't work at all. Both are covered in place, where they actually happened, rather than saved up for a highlight reel here.

## Getting the PC's GPU actually used

Ollama's default behavior on my machine was to quietly fall back to the CPU. That's easy to miss — it still generates text, just slowly — and it took a real benchmark run to notice: **6.88 tokens/sec** on `phi4:14b`, which is CPU-bound and painfully slow for anything interactive.

The fix, since the RX 6700 XT is an AMD card and Ollama's GPU detection can be finicky with AMD's ROCm/HIP stack, was three environment variables:

```powershell
[System.Environment]::SetEnvironmentVariable("HSA_OVERRIDE_GFX_VERSION", "10.3.0", "User")
[System.Environment]::SetEnvironmentVariable("OLLAMA_NUM_PARALLEL", "1", "User")
[System.Environment]::SetEnvironmentVariable("OLLAMA_ORIGINS", "*", "User")
```

`HSA_OVERRIDE_GFX_VERSION` tells the ROCm/HIP runtime to target the RX 6700 XT's actual architecture (RDNA2 / Navi 22) instead of guessing wrong and falling back to CPU. `OLLAMA_NUM_PARALLEL=1` stops Ollama from fragmenting the 12GB VRAM buffer across multiple parallel request slots you probably don't need for single-user use. `OLLAMA_ORIGINS=*` opens up CORS so local tools and a browser console can actually talk to the Ollama server. Set as User-scope variables, these survive a reboot with no startup script needed.

**The one that went wrong.** Once those three were confirmed working, Cowork suggested two more as further "optimizations": `OLLAMA_FLASH_ATTENTION=1` and `OLLAMA_KV_CACHE_TYPE=q8_0`, aimed at trimming VRAM usage for the KV cache. Neither had been checked against AMD/Vulkan first — they're more mature on NVIDIA/CUDA — and the very next verbose run showed why that matters: eval rate dropped from 150.39 tok/s to 52.07 tok/s, prompt-eval from 464.14 to 108.60 tok/s. Roughly a 3x regression, not noise. Unsetting both and restarting Ollama brought it straight back to 150.07 tok/s. **Verdict: don't set either one on this card.** Worth remembering next time an "optimization" gets suggested without a "have we actually confirmed this on your specific hardware" attached to it — including, apparently, when the suggestion comes from the thing doing the suggesting.

## The 12GB VRAM cliff

Once the GPU was actually engaged, the difference was dramatic — but only up to a point, and the point matters more than I expected.

| Model | Mode | VRAM | Tokens/sec | vs. CPU baseline |
|---|---|---|---|---|
| `phi4:14b` | CPU only | 0GB | 6.88 | 1.0x (baseline) |
| `qwen2.5:3b` | 100% GPU | ~2.0GB | **138.94** | ~20x |
| `qwen3.5:9b` | 100% GPU | ~4.7GB | **17.98** | ~2.6x |
| `deepseek-r1:14b` | 100% GPU | ~8.9GB | **8.32** | ~1.2x |
| `gpt-oss:20b` | split (GPU+RAM) | >12GB | 11.28 | ~1.6x |
| `gemma4:31b` | split (GPU+RAM) | >12GB | **~5.5** | **0.8x — slower than CPU-only** |

Everything that fits fully inside the 12GB VRAM buffer runs at native VRAM bandwidth (~475GB/s) and is fast, full stop. The moment a model's footprint crosses roughly 11.2GB, though, Ollama starts splitting layers across the PCIe bus into system RAM — and that's not a gentle slowdown. `gpt-oss:20b` still eked out a win over the CPU baseline in split mode, but `gemma4:31b` actually landed *slower* than running a smaller model on CPU alone. The lesson: don't assume a bigger model in "stretch" mode is a safe bet just because it's got more parameters. Test it.

The practical rule that fell out of this: **~13B parameters at Q4_K_M quantization (7–9GB) is the sweet spot** on a 12GB card — big enough to be genuinely useful, small enough to stay fully in VRAM with headroom for context.

One more data point on `deepseek-r1:14b` worth calling out: I ran it against four different prompts to check consistency, and generation speed held steady between 8.05 and 8.58 tok/s the whole time, with prompt-processing (how fast it chews through your input before generating) running much faster, 38–75 tok/s depending on prompt length. No sign of throttling or slowdown across runs — reassuring, since a model that's fast on the first prompt and degrades on the fourth is a much worse product experience than one that's consistently modest.

## Which installed model for which job

Once you've got a handful of models pulled, the "fastest" one isn't always the right default — it's worth matching the model to the task instead of always reaching for whichever benchmarks best. Here's how mine shook out in practice:

| Model | Role | What it's actually good for |
|---|---|---|
| `qwen2.5:3b` | Speed / utility | Terminal scripts, fast completions, basic JSON parsing — near-instant at ~139 tok/s |
| `llama3:latest` | Light general | Quick formatting, light back-and-forth where depth doesn't matter |
| `qwen2.5:latest` | Structured output | Structured JSON generation, general daily coding, multi-language tasks |
| `qwen3.5:9b` | Daily driver | Complex coding, multi-turn reasoning, image/vision tasks — my default for most things |
| `deepseek-r1:14b` | Deep reasoning | Complex algorithm design, step-by-step debugging — worth the ~8.3 tok/s tax when you actually need chain-of-thought |
| `phi4:14b` | Analytical writing | Formal documentation, structured writing, analytical reasoning |
| `gpt-oss:20b` | Heavy analysis | Multi-step agentic execution across a large codebase — usable at ~11 tok/s even split across VRAM and system RAM |

This is informal usage-pattern guidance, not a rigorous quality score for each task — but it's a reasonable starting hypothesis before you burn time benchmarking every model against every workload. I eventually did burn that time, and the results below are a reminder that this table is a hypothesis, not a verdict.

## Testing it properly: what an automated eval harness found

Raw tok/s is the easy number, and it's what most of this post is built on so far. It also tells you nothing about whether a model is actually *right*. To get real pass/fail data instead of vibes, I set up `promptfoo` — a Node-based eval tool — to score models against four workloads (coding, agentic/tool use, structured extraction, chat) plus a fifth I added later for vision, using a fixed judge model (`deepseek-r1:14b`) kept separate from the models under test so nothing could grade its own homework.

![Terminal running npx promptfoo eval on the vision suite, 8 of 12 test cases complete](/images/promptfoo-cli-running.png)
*`npx promptfoo@latest eval -c promptfoo-vision-pc.yaml -j 1 --no-cache` mid-run — `-j 1` so results are directly comparable, `--no-cache` so every case actually re-queries the model instead of replaying a cached response.*

What came back wasn't a clean leaderboard. It was three separate places where the obvious answer — the vendor recommendation, the model I was already trusting to grade the others — turned out to be wrong, plus a fourth on the Pi I'll get to in that section below.

**The "top choice for agentic coding" that can't call tools.** General guidance going in rated `qwen2.5-coder:14b` as the strongest local pick for agentic/tool-calling work — a purpose-built coder model, a reasonable size for the 12GB card, no obvious reason to doubt it. Final score on the agentic suite: 1 out of 4. Pulling the raw, uncaptured output showed why: asked for the weather in Walnut Creek, it replied with `{"name": "get_weather", "arguments": {"location": {"city": "Walnut Creek", "state": "CA"}}}` — a plausible-looking function call that is also plain text. It isn't populating Ollama's actual `tool_calls` API field at all; it's printing a JSON-shaped string into the same content field it'd use to answer "write me a haiku." A system-prompt reminder fixed the surface symptom (the argument shape) but not the underlying issue — a downstream integration reading the real `tool_calls` field, the way any actual agent harness does, would see nothing to execute here regardless. `qwen3.5:9b` and `qwen2.5:latest` — neither marketed as "the coding model" — went a clean 4 for 4 on the same suite. The vendor label never got tested against a real tool-calling harness; once it was, it didn't survive.

**The judge that graded a correct answer wrong.** The coding suite came back 15 out of 16, with the one failure landing on `qwen2.5-coder:14b`'s `parse_duration` function. The terminal output truncated the generated code, so Cowork built an isolated debug run to capture it in full, and we hand-checked it together against the test's own three example inputs. The code was correct on all three — `total_seconds = hours * 3600 + minutes * 60` after a clean split. The judge's stated reason for failing it ("incorrectly processes cases where minutes are present without an 'm' suffix") didn't correspond to anything in the code or the prompt's own examples. Not a borderline call — a wrong grade on a right answer. That bumped the real score to 16 out of 16, but the bigger finding is that an automated judge can produce a single plausible-looking bad verdict sitting quietly inside an otherwise-clean run, with nothing about the raw number giving it away. I spot-checked the other rubric-graded suites by hand afterward and they held up — this looks like an isolated incident, not a systemic problem — but "isolated" is only a conclusion I have because I went and checked.

**The vision showdown: a model that won't stop talking.** I pitted `qwen3-vl:8b` against `glm-ocr` — a general-purpose vision model against a purpose-built OCR specialist — on six real receipt photos, extracting vendor, date, and total into fixed JSON. `qwen3-vl:8b` won clearly: 5 out of 6, 92% weighted. `glm-ocr` — the model actually built for this job — scored 4 out of 6, 83.3% weighted. That number is itself a correction: the original scoring run had it at 3 out of 6, 75%, and the difference wasn't a re-test, it was a bug in my own harness. The scoring assertion extracted JSON by taking the span from the first `{` to the last `}`, which breaks the moment a model re-emits its already-complete answer instead of stopping — exactly what `glm-ocr` does (see below) — because the "last `}`" then belongs to a second, garbled copy of the answer, not the good one. Fixing the extractor to scan for brace-balanced top-level objects and parse from the last complete one backward recovered the case that bug had wrongly failed. A second, smaller harness bug turned up in the same pass: the vendor-name check was a plain substring match, which fails the moment OCR drops an accent — "La Cabaña" read back as "La Cabana" scored as a wrong vendor, even though the model got the name right. The fix was to normalize both strings with Unicode NFD decomposition and strip the combining marks before comparing, so an accent mark stops being load-bearing for a pass/fail grade. I hit this on two different models on two different receipts before I trusted it was a pattern worth fixing generally rather than special-casing one test. Worth sitting with for a second: the model that got dinged hardest by a strict-parsing bug was the one already failing for a real reason, which is exactly the kind of compounding error that makes a single bad number easy to believe without checking. The underlying behavior the corrected score is measuring didn't change: `glm-ocr` hit the exact context-length ceiling on all six test cases, at two different context sizes, every time — not because it ran out of room to answer, but because it re-emits its own already-complete JSON answer in a loop instead of stopping. Doubling the context budget didn't fix the behavior, it just let the loop run twice as long before truncation, and the defect held stable across three separate runs. Separately, on one case `glm-ocr` also mis-extracted the vendor name outright — a Home Depot receipt attributed to the wrong merchant — a distinct failure from the non-termination pattern, not a symptom of it. On the cases where it did terminate normally, its accuracy was fine — the score is measuring "can this model stop talking," not "can it read a receipt." One finding from the same suite didn't budge no matter what I did: one receipt prints both a pre-tax subtotal (€4.24) and a VAT-inclusive grand total (€5.00), and both models, at both context sizes, extracted the pre-tax number every time — even after I explicitly reworded the schema to specify "the final amount actually paid or due... not a pre-tax subtotal." Four independent runs converging on the same wrong-but-explicable number is enough to call this a genuine small-model limitation, not something worth another prompt-wording pass.

![promptfoo eval dashboard showing glm-ocr and qwen3-vl:8b both FAIL(0.50) on the Costa receipt with the identical reason — vendor match=true, total match=false (got 4.24, expected 5) — and both PASS on La Cabaña](/images/promptfoo-dashboard-vision.png)
*The actual promptfoo dashboard, mid-suite: both models fail Costa the same way (4.24 vs. 5, the VAT-vs-net limitation above) and both pass La Cabaña once the diacritic-normalization fix was in — "La Cabana" without the tilde reads as a match now.*

<div style="display:flex; gap:1rem; flex-wrap:wrap; margin:1.5rem 0;">
<figure style="flex:1; min-width:220px; margin:0;">

![Costa Coffee receipt from Malta International Airport, showing a pre-tax subtotal of €4.24 and a VAT-inclusive total of €5.00](/images/receipt-costa-coffee.jpg)
*The Costa Coffee receipt every model extracted wrong the same way: €4.24 (pre-tax) instead of the €5.00 actually paid.*

</figure>
<figure style="flex:1; min-width:220px; margin:0;">

![Home Depot receipt, the one glm-ocr attributed to the wrong vendor](/images/receipt-home-depot.png)
*The Home Depot receipt `glm-ocr` mis-extracted the vendor on — the footer survey URL is the likely culprit.*

</figure>
</div>

**The meta-lesson.** Three of these findings aren't really about the models — they're about how easily a benchmark can lie to you. A tool-calling test can score a false 0% because a config key was nested wrong. A judge can confidently grade a correct answer as wrong. A strict JSON check can fail a model producing perfectly good JSON wrapped in markdown fences it wasn't told to expect. The rule I've landed on: a uniform failure across every model is almost always your harness, not their capability — models fail in different, idiosyncratic ways, a scoring bug fails everyone identically — and any single surprising result is worth pulling the raw output and checking by hand before it goes in a table.

## Config tuning that actually mattered

A few settings made a bigger difference than I expected, mostly around context size:

- **`num_ctx`** — the default context window (32K–128K depending on the model) eats 2–6GB of VRAM just for the KV cache before you've generated a single token. For anything in the 14B range on a 12GB card, dropping this to somewhere between 8192 and 16384 keeps the KV cache from silently pushing model layers out of VRAM and into much slower system RAM.
- **Quantization** — Ollama's default `Q4_K_M` (~4.9 bits/weight) is the right call for most things. Q8_0 is there if you have VRAM to spare and want to test whether it actually changes output quality for your use case — it often doesn't, enough to justify the size.
- **`OLLAMA_MAX_LOADED_MODELS=1`** — if you're running multiple local AI tools at once, this stops VRAM from getting split across simultaneously-loaded models.
- **Repeat penalty** — worth turning on if it's off by default in your client. Qwen models in particular can fall into repetition loops at a repeat penalty of 1 (disabled); 1.05–1.1 clears that up without hurting output quality.
- **Temperature** — 0.8 is a reasonable default for general chat; drop to 0.2–0.3 for coding tasks where you want deterministic, less "creative" output.

## Calling Ollama directly (bypassing the GUI)

Ollama exposes a REST API on `localhost:11434` by default, which is handy for testing or building your own front end. A one-shot request from a browser console or Node script:

```javascript
async function chat(promptText) {
  const response = await fetch('http://localhost:11434/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: "qwen3.5:9b", prompt: promptText, stream: false })
  });
  const data = await response.json();
  console.log(data.response);
}
```

Set `stream: true` and read the response body with `response.body.getReader()` if you want tokens streaming in as they're generated instead of waiting for the whole thing.

**The gotcha:** modern Chromium browsers block a public web page (or even `about:blank`) from fetching `localhost` under Private Network Access (PNA) rules — it treats your local Ollama server as a more-private address space that untrusted origins shouldn't be able to reach. Disabling the relevant `chrome://flags` entry works but is a moving target Chromium keeps deprecating, so it's not a real fix. The actual fix is server-side: start Ollama with both `OLLAMA_ORIGINS="*"` and `OLLAMA_ALLOW_PRIVATE_NETWORKS="true"` set, which makes Ollama respond to the browser's preflight check correctly. The alternative that sidesteps the whole problem is just running your test script in Node instead of a browser console — no CORS, no PNA, no CSP to fight.

One more Windows-specific snag: if you kill and relaunch `ollama serve` to pick up new environment variables and get `bind: Only one usage of each socket address is normally permitted`, a background `ollama_app.exe` process is probably still holding port 11434. `taskkill /F /IM "ollama*"` (note the wildcard) clears both the CLI and the tray-app process; `Get-NetTCPConnection -LocalPort 11434` confirms the port's actually free before you relaunch.

## Ollama Cloud: the option for models too big for your hardware

Some of the largest model tags in Ollama's library — `gemma4:31b`, `gpt-oss:120b`, and similar — are really meant to run on Ollama's cloud compute rather than local hardware, once you've authenticated with `ollama login`. Your prompt gets routed to a remote GPU and tokens stream back, using essentially none of your local VRAM.

Worth knowing the tradeoffs before reaching for this: it needs a stable internet connection (no more fully-offline story), it adds real round-trip latency on top of generation time, your prompts and outputs are leaving your machine, and free-tier usage is presumably subject to whatever rate limits Ollama sets. It's a legitimate way to try a model too big for your rig, but it quietly gives up the two biggest reasons to run local in the first place — privacy and zero ongoing dependency. Worth treating as a "try before you buy more GPU" tool rather than a default.

## The Raspberry Pi 5: CPU-only, and it shows

No GPU means every model lives or dies by CPU throughput and the Pi's ~17GB/s memory bandwidth. The math is straightforward: generation speed is roughly that bandwidth divided by model size, which is why the gap between a 1.5B and an 8B model here is so much larger than the parameter count alone would suggest.

I ran a quick automated pass with the `llm-benchmark` pip package (`pip install llm-benchmark`, then `llm_benchmark run --no-sendinfo`) against its default 7–9B model set, and the results confirmed the Pi is not the machine for mid-size models:

| Model | Tokens/sec |
|---|---|
| `llava:7b` | 2.89 |
| `mistral:7b` | 2.44 |
| `llama3.1:8b` | 2.32 |
| `deepseek-r1:8b` | 2.12 |
| `gemma2:9b` | 2.06 |

All in the same tight 2–2.9 tok/s band — technically it runs, but that's a submit-and-wait experience, not a conversation.

The models actually sized for this hardware are the sub-4B tier, and I initially only had community/vendor estimates for them rather than my own measurements. I've since run all six on the actual hardware, and every single vendor estimate turned out optimistic:

| Model | Size | Estimated speed | Measured speed | Estimate accuracy |
|---|---|---|---|---|
| `llama3.2:1b` | ~1.3GB | ~20–22 tok/s | **8.24 tok/s** | ~37–41% of estimate — the biggest miss |
| `qwen2.5:1.5b` | ~0.99GB | ~15–17 tok/s | **12.08 tok/s — fastest measured** | ~71–80% of estimate |
| `llama3.2:3b` | ~2.0GB | ~8–9 tok/s | **5.55 tok/s** | ~62–69% of estimate |
| `qwen2.5:3b` | ~1.9GB | ~8–9 tok/s | **5.49 tok/s** | ~61–69% of estimate |
| `phi3.5:3.8b` | ~2.4GB | ~6–7 tok/s | **4.87 tok/s — slowest measured** | ~70–81% of estimate |
| `gemma2:2b` | ~1.6GB | 5–10 tok/s | **6.66 tok/s** | within the (wide) estimate band |

One methodology finding fell out of running all six back to back: on-disk GGUF file size, not the nominal parameter count, is what actually predicts speed here. `tok/s × file-size-in-GB` lands in a tight 10.4–11.9 range across all six models — dividing that by the Pi's ~17GB/s memory-bandwidth ceiling shows every model hit roughly 61–70% of theoretical throughput, consistently. That's why `llama3.2:1b` (1.3GB) beats `gemma2:2b` (1.6GB) despite the "smaller" name, and why `qwen2.5:1.5b` (0.99GB, the smallest file of the six) is the outright speed leader.

Which is where it gets interesting, because speed and quality pulled in opposite directions. I ran all six models through the same four-workload eval harness described above, and `qwen2.5:1.5b` — the fastest model by a wide margin — finished dead last or tied for it on every single suite: 1 out of 3 on extraction, 2 out of 4 on the agentic suite, 2 out of 4 on chat, 1 out of 4 on coding. Meanwhile `llama3.2:3b` and `qwen2.5:3b` — both roughly half its speed — are the only two models on the shortlist with a perfect record on every judge-free test they were given: 3/3 on extraction, 4/4 on the full agentic suite. This wasn't a lucky pair of runs I talked myself into; it held across four independent suites run over three separate days, and the gap only got clearer as more data came in.

So despite `qwen2.5:1.5b` looking like the obvious pick from a speed table alone, **`llama3.2:3b` or `qwen2.5:3b` are the actual Pi recommendation** — if you're picking a model by grabbing whatever's fastest, you're optimizing for exactly the wrong variable. `llama3.2:1b` is a reasonable middle-ground pick if you want something faster than the 3B tier without `qwen2.5:1.5b`'s consistent quality gap. Two other models, `gemma2:2b` and `phi3.5:3.8b`, both bottomed out on the agentic suite specifically — but that turned out to be a Pi-only reliability bug, not a capability problem: running six models through a 6-provider matrix on 8GB of RAM (7.87GB usable) forces repeated load/evict cycles, and under that memory pressure a model can return completely empty output even though it works fine when run alone. It's a real caveat for a Pi product that serves multiple models from shared RAM, but not a mark against either model standalone.

A couple of things that'll bite you if you skip them: the Pi's BCM2712 chip is reported to thermal-throttle under sustained inference load, so an active cooler or heatsink+fan is worth having before running anything longer than a quick test — a "slow model" result might just be a hot chip. (This turned out to be the easy half of the thermal story, not the whole thing — see below.) And storage matters more than you'd think: loading a 2GB model off a MicroSD card reportedly takes around 20 seconds, versus 2–4 seconds off an NVMe HAT over PCIe. If you're calling a model repeatedly rather than keeping it loaded, that difference adds up fast.

If CPU-only inference turns out to be the actual bottleneck rather than model choice, Raspberry Pi's own **AI HAT+ 2** ($130) is worth a look — it's a Hailo-10H accelerator with 8GB of *dedicated* RAM (separate from the Pi's own 8GB), supporting 1–1.5B models at genuinely practical speeds without competing with the OS for memory. Not something to buy before you've actually hit the CPU-only ceiling, but the real lever if you do.

## Six crashes and a watchdog: closing out the Pi's vision suite

The Pi's vision suite — the same receipt-extraction workload from the PC showdown above — was supposed to be the last item on the Pi side, a quick coda to the speed and quality tables above. It turned into the most disruptive week of this whole project, because the assumption I walked in with was backwards: an active cooler is not a fix for sustained CPU-bound inference on a Pi 5. It's a mitigation, and there's a real difference between the two.

The Pi in this project has had Raspberry Pi's own Active Cooler — heatsink plus fan — installed since before any benchmarking began, confirmed physically present and spinning every time I checked.

![Raspberry Pi 5 with the official Active Cooler (heatsink and fan) mounted](/images/pi5-active-cooler.png)
*The Pi 5 with its Active Cooler on — present and spinning through all six crashes below. Necessary, it turned out, but not sufficient.*

Running the vision suite's six-case, two-model matrix at sustained CPU load anyway produced six confirmed hard, silent reboots, in two distinct signatures: some were fast, uncaught spikes that reset the board in about a minute with no warning at all, and others were slower cycles of the board visibly throttling, recovering, throttling again, before eventually resetting anyway. My first instinct was that this had to be a power problem — a board browning out under sustained load can look a lot like this from the outside — so I pulled per-rail voltage with `vcgencmd pmic_read_adc` through several of the crashes. Every rail held steady, every time, through every crash. Not a power-supply issue.

The "the cooler fixed it" conclusion I'd half-written after the first couple of crashes didn't survive either, and I want to flag that I did write it down at one point before retracting it, because getting it wrong once is part of the finding. The Active Cooler was installed and its fan was confirmed running through all six crashes — on both multi-model and, notably, single-model runs, so "don't run several models at once" wasn't the fix I'd hoped it was. The board also touched an 80.7°C peak at one point without crashing at all, while other crashes happened in the same rough 79–86°C band — which rules out a clean trip point. Whatever's actually killing the board is probabilistic somewhere near that temperature range, not deterministic, and what distinguishes a crash from a clean run at the same reading is still an open question I don't have an answer to.

After the fourth crash, Cowork asked me directly whether we were actually done here — the honest answer at that point was no, the vision suite still had no trustworthy result. I pushed back on that framing before it went any further: *"This keeps crashing, so not sure we are going to get the results we want. We might want to summarize as not possible to complete unless you have other ideas."* Rather than agreeing to close it out, Cowork came back with three concrete options instead of one: split the two-model matrix into separate single-model runs with checkpointing (cheapest, try it first), build a software watchdog that kills the process and lets the board cool before it hits the danger zone, or swap in a more aggressive third-party cooler. That third option is the one I killed myself, once the data actually ruled it out: the official Active Cooler had failed to prevent five crashes with its fan confirmed spinning for every one of them, which is a reasonable basis for concluding a different air cooler wasn't going to be the lever that mattered — the other two options targeted the actual mechanism (a reaction-time gap between the temperature climb and the firmware's own throttle response), not raw cooling capacity. Standing plan from there: single-model split first since it's basically free, watchdog only if that alone still wasn't enough.

The fix I reached for next, once the single-model split alone wasn't enough, was that watchdog: monitor temperature, kill the inference process before it crossed into the danger zone, let the board cool, resume. Cowork wrote the first version, and it surfaced two bugs of its own worth knowing about if you're scripting anything similar around `promptfoo`. First, a naive PID-based kill didn't actually work — this was Cowork's own script, and it looked complete, but it was silently doing nothing: `npx`-launched processes spawn children (`llama-server`, here) that keep running after you kill the parent PID you captured, so the watchdog had to track and kill by pattern-matching the invocation — `pgrep -f`/`pkill -f` against a distinguishing config filename — instead of a single captured PID. Second, the script's own success/failure logic misclassified a clean kill-and-resume cycle as a failure, which took a second pass to fix by tracking success with an internal flag rather than trusting the process exit code. Once both were fixed, the watchdog worked exactly as designed, mechanically — I could prove it killed and resumed correctly.

It still wasn't usable, for one specific model. `qwen3-vl:2b`'s normal per-case generation time on the Pi turned out to be longer than the watchdog's kill window, so a watchdog tuned to intervene before thermal danger would kill every case before it could ever finish, healthy or not — a working watchdog that was simply incompatible with this model's timing. I abandoned it for that model and fell back to running the remaining cases manually, leaning on `promptfoo`'s own response cache so a mid-suite crash wouldn't cost the cases that had already completed. That fallback approach produced the sixth crash — and, on a later pass, the first fully clean completion of the suite.

One result from that manual run is still sitting open and unreconciled: the same receipt (a Costa Coffee photo), same model, same config, produced an 18.86-minute non-terminating loop on one run and two clean 1–2 minute completions on two later runs. I don't have an explanation for the difference and I'm not pretending to — it's logged as an open item, worth a targeted repeat if this specific case ever becomes decision-relevant, but not worth blocking the suite's closure on.

What I do have a clean answer for is what `qwen3-vl:2b` got right and wrong once a case actually completed: four of six receipts correct on vendor, date, and total, with Costa and Home Depot the two failures. Ground-truthing the Costa failure against the actual receipt showed it was the same pattern I'd already hit twice on the PC's vision suite above — the model extracted the pre-tax subtotal instead of the VAT-inclusive total that was actually due. Third confirmed instance of the same small-model limitation, on a third receipt, on a different model. At that point it's not a coincidence, it's a pattern worth designing around rather than re-prompting away.

With that, I closed the Pi vision suite: `qwen3-vl:2b` at 4 out of 6, 66.67% weighted, and `minicpm-v4.6` at 92% (11 of 12) — the second model's existing partial-run result from the day before, accepted as final rather than re-run clean, my own call once I'd seen what re-running the suite was actually costing in crash risk. As I put it at the time: "Pi vision suite (both models) can be marked closed. I'm good with what we have."

The practical upshot for anything I actually build on this board: active cooling is necessary, but treating it as sufficient was the mistake that cost the week. Any real product running sustained inference on a Pi 5 needs an application-level watchdog and auto-restart designed in from the start — and tuned per-workload, not borrowed wholesale from this one. The exact kill-window mismatch that sidelined the watchdog for `qwen3-vl:2b` here is the reminder: "the watchdog works" and "the watchdog works for this model's timing" are two different claims, and only one of them is the one that matters in production.

## Keeping the stack current

Worth a periodic check rather than a set-and-forget: it's easy for the GPU acceleration to silently regress back to CPU-only after a Windows or AMD driver update, exactly the problem that started all this.

- **Ollama itself:** `ollama --version` to check, then either right-click the Ollama icon in the system tray and choose "Check for Updates," or grab the latest installer from ollama.com/download — it updates the engine in place without touching your downloaded models.
- **Python tooling:** `python -m pip install --upgrade pip` and `pip install --upgrade llm-benchmark` if you're using it for quick speed checks.
- **Models themselves:** `ollama list` to see what's installed, then `ollama pull <model>` again for any tag you want refreshed — upstream fixes, tokenizer corrections, and quantization tweaks do land on existing tags over time.
- **GPU acceleration, after any driver update:** run something like `ollama run qwen2.5:3b --verbose "hi"` and check that `library=Vulkan` (or your platform's equivalent) shows up in the output or in `%LOCALAPPDATA%\Ollama\server.log`. If it's silently gone, you're back to CPU-only until you catch it — and the tok/s difference is large enough that it's worth checking after every driver update, not just once.

## What people are actually building with this

A few patterns kept coming up in projects other people have built on Pi-class hardware, worth stealing ideas from:

- **Fully offline voice assistants** — Whisper for speech-to-text, a local LLM via Ollama for the response, Piper for text-to-speech, no cloud round-trip at all.
- **Natural-language smart home control** — Home Assistant talks to a local Ollama instance so voice or text commands get parsed into device actions on-device. This is a much more realistic "agentic" use case for small models than open-ended tool use — a small, fixed set of possible actions (turn this light off, set that thermostat) is exactly where a 3B model can be reliable, versus open-ended multi-step planning where it usually isn't.

## Building my own voice assistant: three gotchas that ate an afternoon

Talk is cheap until you actually wire up `faster-whisper` → Ollama → Piper and hit record. Cowork built exactly the pattern described above — push-to-talk, `faster-whisper` (`base.en`, CPU, int8) for speech-to-text, Ollama's streaming `/api/chat` for the LLM, `piper-tts` for the voice — specifically to get a real, measured time-to-first-token number instead of the derived estimate I'd been using elsewhere in this project. Three things broke in ways worth writing down.

**Ollama's default 5-minute keep_alive turns every idle gap into a full reload.** The first time I ran the script, the LLM's time-to-first-token was 12.27 seconds — appalling for a model that benchmarks at ~18 tok/s on this card. The second turn, after a few minutes of me reading and reacting to the first result, TTFT jumped to 32.51 seconds — worse, not better. Ollama's default `keep_alive` is 5 minutes; once that clock runs out, the model gets evicted from VRAM, and the next request pays a full reload cost that gets counted as part of "time to first token" even though it has nothing to do with actual inference speed. The fix is a one-line addition to the request payload: `"keep_alive": -1` keeps the model loaded indefinitely for the life of the session. Only after that did TTFT numbers actually reflect inference speed instead of disk I/O.

**A reasoning model can silently starve itself of tokens to answer with.** With `num_ctx` hardcoded at 4096 — a sensible default for most non-reasoning models on this card — one turn crashed outright: the assistant printed nothing, and the script died trying to write an empty WAV file to disk. The cause: `qwen3.5:9b` is a reasoning model that emits a separate `thinking` block before its actual answer — even a trivial "hi" burned 258 tokens on internal reasoning before the visible reply. On a harder question, that thinking process ate the entire 4096-token budget, leaving zero tokens left for the actual answer. This is the exact same failure mode I'd already hit benchmarking vision models earlier in this project (`qwen3-vl:8b` hitting an empty-output wall at the same context size) — doubling `num_ctx` to 8192 fixed it there and fixed it here too. As I found out a few days later running a much longer-context test (see below), this "just double it" fix has limits of its own.

**LLMs write in Markdown by default, and Markdown read aloud sounds ridiculous.** The first clean response I got back was littered with `**bold**` around numbers and facts — a TTS engine has no idea what to do with asterisks, so it just reads them as if they were words. Two fixes, because a system prompt alone isn't reliable enough: first, a system message telling the model explicitly that this is a voice interface and to skip Markdown, bullets, headers, and code blocks entirely; second, a small regex cleanup pass that strips any `**bold**`, `*italic*`, backticks, header markers, and list bullets that get through anyway, before the text ever reaches Piper. Belt and suspenders — models don't follow "no formatting" instructions with 100% reliability, so the pipeline can't assume they will.

**Bonus finding: confident and wrong.** Asked what year the Raspberry Pi 5 came out and how much RAM the base model has, `qwen3.5:9b` nailed the year (2023) but invented product details that don't exist — describing a "Plus" or "higher-end" RAM tier that Raspberry Pi never made (the Pi 5 just ships in 4GB/8GB/16GB configurations of the same board, no branded tiering). It repeated a version of the same invented tiering across two independently-phrased attempts at the question. A useful reminder that a model can nail the easy part of a factual question and confidently fabricate the specific detail sitting right next to it — a failure that's much easier to catch out loud, mid-conversation, than buried in a benchmark spreadsheet.

None of these three are exotic bugs — they're exactly the kind of thing that only shows up once you build the actual end-to-end pipeline instead of just benchmarking the model in isolation. Worth remembering next time "the model" gets blamed for something that's actually the harness around it.

### The actual answer to "what's local TTFT," and it's not what the tok/s numbers implied

Here's the twist: after fixing the context-starvation crash, I ran five more turns through the assistant and time-to-first-token was consistently awful — 14 to 84 seconds, scaling almost exactly with how "hard" the question seemed. Doing the math on the printed latency breakdown made the cause obvious: on every single turn, 83–99% of the model's total generation time happened *before* the first audible word. `qwen3.5:9b` is a hybrid-reasoning model, and its entire chain-of-thought block generates silently before any of the actual answer streams out — Ollama's `/api/chat` doesn't expose that thinking phase as separate timing, so from the outside it just looks like a shockingly slow model, even though the same model benchmarks at ~18 tok/s raw generation speed.

The fix is a single field: adding `"think": false` to the request payload suppresses the reasoning trace entirely. Before and after, same five kinds of question, same warm model:

| | With reasoning (default) | With `think: false` |
|---|---|---|
| TTFT range | 14.4s – 83.6s | 2.39s – 2.47s |
| Total generation | 15.2s – 100.6s | 2.7s – 4.8s |
| "47 × 89?" | 17.0s TTFT | 2.47s TTFT |

That's a 6–30x latency improvement depending on the question, and — at least on the handful of questions I tried — no visible quality regression; if anything the answers came back cleaner and more direct with reasoning off. This is the real, measured answer to "what's local TTFT" that the rest of this project had only ever estimated: it isn't a property of the model or the GPU at all, it's almost entirely a property of whether reasoning is switched on. A benchmark that only measures raw tok/s — which is every speed number earlier in this post — will completely miss this, because reasoning and non-reasoning modes generate at basically the same tok/s; the difference only shows up in how much gets generated invisibly before the part a user actually sees. Anyone building a live voice or chat product on a hybrid-reasoning model needs to know this switch exists, because leaving reasoning on by default is close to a 10-30x hidden latency tax with no warning.

**Then I added a third arm, and it complicated the story in a useful way.** If `think: false` closes most of the gap to a fast model, what happens if you just skip the reasoning model entirely and run something genuinely small and non-reasoning — `qwen2.5:3b`, the same tag that hit 138.94 tok/s on the raw GPU benchmark earlier in this post? Same pipeline, same five questions, same `keep_alive: -1` warm-model setup:

| | Reasoning on (default) | `qwen3.5:9b` + `think: false` | `qwen2.5:3b` (no reasoning mode to disable) |
|---|---|---|---|
| TTFT range | 14.4s – 83.6s | 2.39s – 2.47s | **2.13s – 2.16s** |
| Answers materially wrong | 0 of 5 (one fabricated detail, see above) | 0 of 5 | **2 of 5** |

`qwen2.5:3b` posted the flattest, lowest TTFT of any model or setting tested anywhere in this project — consistently around 2.1s regardless of question difficulty, edging out even the tuned `qwen3.5:9b`. It also got the arithmetic question wrong (47 × 89 is 4,183; it answered 4,103) and gave a genuinely garbled answer on the Raspberry Pi 5 question — first claiming the Pi 5 "didn't come out yet," then in the same breath saying it "was released in 2022" (it's neither; it shipped in 2023), and inventing RAM figures for both the Pi 4 and Pi 5 that don't match either board. It also completely missed the point of a question about my own AMD RX 6700 XT and Ollama setup, describing Ollama as game-rendering software rather than recognizing it as the very runtime serving the conversation. (The first turn of this run also cost 6.63s TTFT before settling into its ~2.14s baseline — the same cold-load-versus-warm-model tax documented above for `qwen3.5:9b`, confirming it's a property of any model's first request, not something specific to reasoning or size.)

So the honest takeaway isn't "use the smallest model for the fastest chat experience" — it's that TTFT and answer quality are separate axes that don't trade off the way that instinct predicts. Dropping a full model-size class below `qwen3.5:9b` bought roughly a quarter-second of additional TTFT headroom and cost two wrong answers out of five, on the exact same battery `qwen3.5:9b` + `think: false` handled cleanly. For a latency-sensitive product, `qwen3.5:9b` with reasoning turned off looks like the better trade than reaching for a smaller model — the "obvious" latency fix (go smaller) turns out to be the wrong lever; the flag was the right one all along.

## How far can you actually push context? A needle in a 32,000-token haystack

The `qwen3.5:9b` tag on Ollama's library advertises a 256K token context window. That number is doing a lot of marketing work, and I wanted an actual measurement instead of taking it on faith — especially after just watching `num_ctx` bite the voice assistant twice above. So I built the standard test for this: bury a single, distinctive fact somewhere inside a much longer block of unrelated filler text, then ask the model to find it. I used an invented "generator override code" (`ZULU-FOXTROT-8841`) that couldn't possibly appear anywhere in the model's training data, planted it at five different positions within the text (right at the start, a quarter of the way through, dead center, three-quarters through, right at the end), and swept the haystack size from roughly 1,000 tokens up to 32,000. Scoring was a simple exact-string check rather than another LLM grading the answer — after already catching my own judge model grading a correct answer wrong earlier in this post, I wasn't about to trust a second model to tell me whether the first one found an exact string.

The headline is almost anticlimactic: **every single test passed.** All 30 combinations of size and position, from 1K tokens to 32K tokens, found the needle every time. If the goal was "prove the 256K claim is fake," this test didn't get there — 32K is still an eighth of the advertised ceiling, and I have no evidence recall would fail anywhere I actually tested.

But recall was never really the interesting number, once I looked at what else moved.

| Context size | Prefill speed | Generation speed | Time to first token (warm) |
|---|---|---|---|
| 1,024 tokens | ~655 tok/s | ~62 tok/s | ~3.7s |
| 4,096 tokens | ~628 tok/s | ~60 tok/s | ~8.4s |
| 8,192 tokens | ~400–470 tok/s | ~33–40 tok/s | ~19–22s |
| 16,384 tokens | ~277 tok/s | ~17.8 tok/s | ~58s |
| 32,768 tokens | ~203 tok/s | ~11.8 tok/s | ~154s |

Generation speed fell by more than 5x over that range, and it happened with the model still fully resident in VRAM the entire time — `ollama ps` confirmed 100% GPU at every single measurement, and VRAM usage barely moved (5.4GB at 1K tokens, 6.6GB at 32K). That's worth sitting with for a second, because it means this is a *different* bottleneck than the 12GB VRAM cliff earlier in this post. The VRAM cliff is about data placement — a model's weights either fit in fast VRAM or they get pushed into slow system RAM, and the penalty comes from shuttling data across the PCIe bus. Nothing here got pushed anywhere. This slowdown is happening entirely inside the GPU's own fast memory, which means it's not a placement problem at all — it's a compute problem. Every token a transformer model generates has to be compared against every token already in its context window; that comparison gets more expensive as the window grows, memory placement aside. By 32K tokens, `qwen3.5:9b`'s generation speed (11.8 tok/s) has fallen to roughly what `deepseek-r1:14b` — a much bigger, dramatically slower reasoning model — manages as its baseline. A long conversation costs about as much throughput as swapping in a model with 50% more parameters.

Time-to-first-token is the number that actually kills a real product idea here. Even fully warm, with the cold-reload penalty from the voice-assistant work already eliminated, TTFT went from under 4 seconds at 1K tokens to about two and a half minutes at 32K. That's stacked on top of, not instead of, the reasoning-mode TTFT tax from the section above — this test ran with `think: false` throughout specifically so it would measure only the context-length cost in isolation. A voice assistant with a 30-turn conversation history behind it, still with reasoning switched off, is not a "hidden latency tax," it's an unusable product. The 256K context number on the model card is a statement about what the model will *accept* without erroring, not a statement about what stays fast enough to build around.

One loose thread I'm flagging rather than pretending is resolved: the two runs I did at the 8,192-token size don't agree with each other. The first pass measured a clean ~400 tok/s prefill and ~40 tok/s generation across three positions. A second pass, run minutes later as part of extending the test to larger sizes, measured a faster ~470 tok/s prefill but a *slower* ~33 tok/s generation, consistently across all five positions that time. Every other size I tested reproduced cleanly between runs. I don't have an explanation for the 8K-specific discrepancy, and I'd rather say so than paper over it with a guess — it's logged as open, and if it ever matters for something I actually ship, it's worth an isolated rerun to chase down.

## Where this leaves me

On the PC, the fast path is clear: get the GPU env vars right, stay under ~13B params at Q4_K_M unless you've specifically tested a bigger model's split-mode performance, and tune `num_ctx` down before you conclude a model is "slow" when it's actually just spilling out of VRAM. `qwen3.5:9b` is my current daily-driver candidate — good balance of speed and capability, comfortably inside the 12GB budget, and the most consistently reliable model across every real eval-harness suite I ran it through — as long as I keep `think: false` on for anything latency-sensitive and keep an eye on how long the conversation has gotten.

On the Pi, both halves of the picture are in now — real speed measurements across the sub-4B tier, and real quality scores across four separate workloads. The two don't point the same direction: the fastest model on the shortlist is also the weakest one, and `llama3.2:3b`/`qwen2.5:3b` are the actual recommendation despite running at less than half the speed.

If you want to run any of this yourself rather than take my numbers on faith, the repo has everything: the promptfoo suites for both machines, the receipt images and encoder script behind the vision tests, the voice assistant script, and a `FINDINGS.md` with the full data behind every table above — the README covers PC and Pi setup separately since the env vars and model lists differ. [github.com/dwooods/local-llm-benchmark](https://github.com/dwooods/local-llm-benchmark)

The bigger lesson threading through both machines, though, is the one from the eval harness section, and the needle-in-haystack test just added a fourth voice to it. The PC's shortlisted best agentic-coding model doesn't reliably call tools at all. The judge grading my own benchmark suite got a right answer wrong. The purpose-built OCR model lost to a generalist because it can't stop repeating itself. The fastest model on the Pi is the one I'd trust least. The fastest TTFT I measured anywhere in this project came from the model that also got two of five answers wrong. And the model whose spec sheet promises 256K tokens of context becomes unusably slow — 40x worse TTFT, 5x worse throughput — at an eighth of that number, with VRAM sitting nearly flat the entire time so it can't even be blamed on running out of memory. None of that shows up until you actually run the test and check the raw output by hand — a fast wrong answer isn't a win on either machine, a big context window isn't the same thing as a usable one, and neither is a plausible-sounding number from a model, a judge, or a spec sheet you haven't verified yourself.
