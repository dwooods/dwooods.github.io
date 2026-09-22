---
title: "Local LLMs on a PC and a Pi: Almost Every Obvious Answer Was Wrong"
date: 2026-09-21
draft: true
tags: ["ai", "llm", "ollama", "raspberry-pi", "self-hosted", "benchmarking"]
description: "Benchmarking open-weight LLMs locally on a Windows PC with a 12GB AMD GPU and a Raspberry Pi 5 — a silent GPU fallback, a VRAM cliff that runs slower than no GPU at all, an eval harness that caught its own judge grading a right answer wrong, six Pi hard crashes and a watchdog, and the honest verdict on whether local can replace a closed model."
summary: "I benchmarked open-weight LLMs on a Windows PC and a Raspberry Pi 5, and nearly every obvious answer turned out wrong — a GPU silently running on CPU, a 'bigger' model slower than no GPU at all, a judge model that graded a correct answer wrong. The verdict: local earns its place for narrow, lightweight work, not as a stand-in for the closed models I've used for two years."
featuredImage: "/images/hero-pc-vs-pi.png"
featuredImagePreview: "/images/hero-pc-vs-pi.png"
---

I've spent the past two years living entirely inside closed models — ChatGPT, Gemini, Claude — and, like most people, never had much reason to look past them. Open-weight models rarely come up in that conversation, mostly because the GPU most people own can't run something that competes with what a closed model already gives you for free.

What actually got this started: I got laid off this month. Suddenly I had real free time, and a closed-model subscription started looking less like a convenience and more like a bill — when you don't have a job, you go looking for the cheaper option. I'm also the kind of person who turns free time into a hobby project anyway, curious enough about how these models actually work under the hood that I wanted an excuse to dig in instead of just prompting them from the outside. And I've been meaning to actually start writing about the stuff I build for a while — this post is the first real attempt at that, too.

I wanted to find out for myself what running an open-weight model entirely on my own hardware gets you — no API bill, no cloud dependency, no data leaving the building, and the ability to actually see and change the configuration instead of trusting whatever a closed API decided to do — and whether it's good enough to be more than a curiosity.

I tested that on two very different machines, and they weren't really answering the same question. On a high-end Windows desktop with a discrete AMD GPU, the question was whether local inference could get close enough to a closed model to be useful for daily work. On a Raspberry Pi 5, it wasn't a bake-off against the PC at all — I just wanted to know whether that hardware can run an open-weight model well enough to build anything useful on top of it.

The short version: the PC can do real work if you tune it right but doesn't replace a closed model, the Pi can handle narrow, patient tasks but isn't a chat replacement, and the honest answer to "more than a curiosity?" turned out to be: only for the lightweight stuff. I'll come back to that at the end. There are also a handful of gotchas on both sides that cost more time than the actual setup did.

*Repo: [github.com/dwooods/local-llm-benchmark](https://github.com/dwooods/local-llm-benchmark) — every promptfoo config, the voice assistant script, and the full `FINDINGS.md` this post distills.*

## The hardware

| | Windows PC ("DavidPC") | Raspberry Pi 5 |
|---|---|---|
| CPU | Intel Core i7-13700K | — |
| RAM | 128GB DDR | 8GB (7.87GB usable) |
| GPU | AMD Radeon RX 6700 XT, 12GB VRAM | None — CPU-only |
| Storage | NVMe SSD | NVMe |
| OS | Windows 11 Home | Debian GNU/Linux 13 ("trixie") 64-bit |
| Runtime | Ollama 0.34.1, exposed on `localhost:11434` | Ollama 0.34.1 |

## The PC

Everything in this section runs on the Windows desktop — the i7-13700K and the RX 6700 XT.

### Getting the GPU actually used

Ollama's default behavior on my machine was to quietly fall back to the CPU. That's easy to miss — it still generates text, just slowly — and it took a real benchmark run to notice: **6.88 tokens/sec** on `phi4:14b`, which is CPU-bound and painfully slow for anything interactive.

The fix, since Ollama's GPU detection on AMD cards can be finicky, was three environment variables, set together:

```powershell
[System.Environment]::SetEnvironmentVariable("HSA_OVERRIDE_GFX_VERSION", "10.3.0", "User")
[System.Environment]::SetEnvironmentVariable("OLLAMA_NUM_PARALLEL", "1", "User")
[System.Environment]::SetEnvironmentVariable("OLLAMA_ORIGINS", "*", "User")
```

`OLLAMA_NUM_PARALLEL=1` stops Ollama from fragmenting the 12GB VRAM buffer across multiple parallel request slots you probably don't need for single-user use. `OLLAMA_ORIGINS=*` opens up CORS so local tools and a browser console can talk to the Ollama server. Set as User-scope variables, these survive a reboot with no startup script needed. One caveat: a Windows or AMD driver update can silently knock GPU acceleration back to CPU-only, so after any driver update it's worth a quick `ollama run qwen2.5:3b --verbose "hi"` to confirm `library=Vulkan` still shows up in the output.

**Correction, caught in review before this went up.** The first draft of this section said `HSA_OVERRIDE_GFX_VERSION` "tells the ROCm/HIP runtime to target the RX 6700 XT's actual architecture," and then, one paragraph later, told you to verify the fix by looking for `library=Vulkan`. Those can't both be right. `HSA_OVERRIDE_GFX_VERSION` is a ROCm/HSA runtime variable; Ollama's Vulkan backend talks to the GPU through the Vulkan driver and never reads it. Cowork (Claude's agent mode, which wrote the configs and scripts on this project; full credits at the end) flagged the contradiction in a review pass, so I went back to the actual Ollama server log from this machine instead of guessing:

```
msg="dropping integrated GPU; to enable, set OLLAMA_IGPU_ENABLE=1" library=Vulkan compute=0.0 name=Vulkan1 description="Intel(R) UHD Graphics 770"
msg="inference compute" library=Vulkan compute=0.0 name=Vulkan0 description="AMD Radeon RX 6700 XT" type=discrete total="12.0 GiB" available="11.2 GiB"
```

Vulkan, not ROCm. So the verify step was right and the explanation above it was wrong. (That `available="11.2 GiB"` is also exactly where the next section's VRAM cliff sits, which is not a coincidence.) The explanation wasn't mine, strictly: the GPU fix predates this project, it came out of a Gemini session, and Gemini's account of *why* it worked got carried into this draft unchecked. Its own small lesson about where a confident-sounding paragraph comes from. What I can't tell you is which of the three variables, or the Ollama restart that came bundled with setting them, actually flipped the model from CPU to GPU. I set all three at once and confirmed the fix by the before/after tok/s jump, never one variable at a time, and there's no "before" server log to compare against. If I had to bet: `OLLAMA_NUM_PARALLEL=1`, because Ollama's scheduler decides GPU-versus-CPU placement from predicted memory need (its logs elsewhere in this project say things like `model predicted to exceed available memory, evicting`), and cutting the parallel slots to one shrinks that prediction. `OLLAMA_ORIGINS` is pure CORS and can't be it. That's a hypothesis, not a result. If you hit the same silent fallback, check `library=` in your own server log before deciding which variable gets the credit.

**The one that went wrong.** Once those three were confirmed working, Cowork suggested two more as further "optimizations": `OLLAMA_FLASH_ATTENTION=1` and `OLLAMA_KV_CACHE_TYPE=q8_0`, aimed at trimming VRAM usage for the KV cache. Neither had been checked against AMD/Vulkan first — they're more mature on NVIDIA/CUDA — and the very next verbose run showed why that matters: eval rate dropped from 150.39 tok/s to 52.07 tok/s, prompt-eval from 464.14 to 108.60 tok/s. Roughly a 3x regression, not noise. Unsetting both and restarting Ollama brought it straight back to 150.07 tok/s. **Verdict: don't set either one on this card.** Worth remembering next time an "optimization" gets suggested without a "have we actually confirmed this on your specific hardware" attached to it — including, apparently, when the suggestion comes from the thing doing the suggesting.

### The 12GB VRAM cliff

Once the GPU was actually engaged, the difference was dramatic — but only up to a point, and the point matters more than I expected.

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
*The same numbers as a picture. `qwen2.5:3b` (138.94 tok/s) is left off so the split-mode bars stay readable — the point is the two 31B+ models landing to the left of the no-GPU line.*

Everything that fits fully inside the 12GB VRAM buffer runs at native VRAM bandwidth (~384GB/s) and is fast, full stop. The moment a model's footprint crosses roughly 11.2GB, though, Ollama starts splitting layers across the PCIe bus into system RAM — and that's not a gentle slowdown. `gpt-oss:20b` still eked out a win over the CPU baseline in split mode, but `gemma4:31b` actually landed *slower* than running a smaller model on CPU alone. The lesson: don't assume a bigger model in "stretch" mode is a safe bet just because it's got more parameters. Test it.

`qwen2.5-coder:32b` pushed the same pattern further, and it settled an argument I'd been having with someone else's AI. A generic recommendation — from Gemini, not Cowork — had called a 32B model on this rig a reasonable "CPU/RAM hybrid" option, on the logic that 128GB of system RAM and a high-end CPU would "easily handle" the overflow, just "slightly slower." A quick manual check (`ollama run qwen2.5-coder:32b --verbose "hi"`, ~19GB pulled at Q4) put that claim out of its misery: 4.25 tok/s — worse than the plain CPU baseline (6.88 tok/s) and worse than the previous worst split-mode result, `gemma4:31b`'s 5.5 tok/s. Not "slightly slower." The worst split-mode number measured anywhere in this project. `qwen2.5-coder:32b` moved from "stretch tier, untested" straight to "ruled out," next to `gemma4:31b`. (Same caveat as elsewhere: single `"hi"` prompt, 10 completion tokens — a spot-check, not a full run — though the gap here isn't close enough for that caveat to matter much.)

The practical rule that fell out of this: **~13B parameters at Q4_K_M quantization (7–9GB) is the sweet spot** on a 12GB card — big enough to be useful, small enough to stay fully in VRAM with headroom for context.

The other half of staying inside that budget is `num_ctx`: the default context window eats 2–6GB of VRAM in KV cache before generating a single token, and on a 12GB card that's enough to push a 14B model's layers out of VRAM without any warning. The README has the settings I landed on; the one that matters for the rest of this post is `OLLAMA_MAX_LOADED_MODELS=1`, which comes back to bite me on the Pi later.

One more data point on `deepseek-r1:14b`: I ran it against four different prompts to check consistency, and generation speed held steady between 8.05 and 8.58 tok/s the whole time, with prompt-processing (how fast it chews through your input before generating) running much faster, 38–75 tok/s depending on prompt length. No sign of throttling or slowdown across runs — reassuring, since a model that's fast on the first prompt and degrades on the fourth is a much worse product experience than one that's consistently modest.

### Testing it properly: what an automated eval harness found

Raw tok/s is the easy number, and it's what most of this post is built on so far. It also tells you nothing about whether a model is actually *right*. To get real pass/fail data instead of vibes, I set up `promptfoo` — a Node-based eval tool — to score models against four workloads (coding, agentic/tool use, structured extraction, chat) plus a fifth I added later for vision, using a fixed judge model (`deepseek-r1:14b`) kept separate from the models under test so nothing could grade its own homework.

One caveat that applies to every score below: these suites are small — three to sixteen cases each. That's enough to catch a model that can't do something at all, or a harness that's grading wrong, and it's what the findings here are about. It is not enough to rank models against each other, and a "4 out of 4" should be read as "didn't fail the smoke test," not "the best." (Every suite mentioned in this post — configs and cases both — is in the repo linked at the end, if you want to check any of this yourself.)

![Terminal running npx promptfoo eval on the vision suite, 8 of 12 test cases complete](/images/promptfoo-cli-running.png)
*`npx promptfoo@latest eval -c promptfoo-vision-pc.yaml -j 1 --no-cache` mid-run — `-j 1` so results are directly comparable, `--no-cache` so every case re-queries the model instead of replaying a cached response.*

**The "top choice for agentic coding" that can't call tools.** General guidance going in rated `qwen2.5-coder:14b` as the strongest local pick for agentic/tool-calling work — a purpose-built coder model, a reasonable size for the 12GB card, no obvious reason to doubt it. Final score on the agentic suite: 1 out of 4. Pulling the raw, uncaptured output showed why: asked for the weather in Walnut Creek, it replied with `{"name": "get_weather", "arguments": {"location": {"city": "Walnut Creek", "state": "CA"}}}` — a plausible-looking function call that is also plain text. It isn't populating Ollama's actual `tool_calls` API field at all; it's printing a JSON-shaped string into the same content field it'd use to answer "write me a haiku." A system-prompt nudge fixed the argument shape but not the real problem: any actual agent harness reads the `tool_calls` field, and there's nothing there to execute. `qwen3.5:9b` and `qwen2.5:latest` — neither marketed as "the coding model" — went 4 for 4 on the same suite. The vendor label just hadn't been tested against a real harness.

**The judge that graded a correct answer wrong.** The coding suite came back 15 out of 16, with the one failure landing on `qwen2.5-coder:14b`'s `parse_duration` function. The terminal output truncated the generated code, so Cowork built an isolated debug run to capture it in full, and we hand-checked it together against the test's own three example inputs. The code was correct on all three — `total_seconds = hours * 3600 + minutes * 60` after a clean split. The judge's stated reason for failing it ("incorrectly processes cases where minutes are present without an 'm' suffix") didn't correspond to anything in the code or the prompt's own examples. Not a borderline call — a wrong grade on a right answer. That bumped the real score to 16 out of 16, but the bigger finding is that an automated judge can produce a single plausible-looking bad verdict sitting quietly inside an otherwise-clean run, with nothing about the raw number giving it away. I spot-checked the other rubric-graded suites by hand afterward and they held up — this looks like an isolated incident, not a systemic problem — but "isolated" is only a conclusion I have because I went and checked.

**The vision showdown: a model that won't stop talking.** I pitted `qwen3-vl:8b` against `glm-ocr` — a general-purpose vision model against a purpose-built OCR specialist — on six real receipt photos, extracting vendor, date, and total into fixed JSON. `qwen3-vl:8b` won: 5 of 6 receipts fully right, 5.5 of 6 weighted (92%) — "weighted" meaning each receipt earns half credit for getting just the vendor or just the total right, rather than needing both to count at all. `glm-ocr`, the model built for this job, scored 4 out of 6 — and that number is itself a correction. The first run had it at 3 out of 6, and the difference wasn't a re-test, it was two bugs in my own harness. The JSON extractor grabbed everything from the first `{` to the last `}`, which breaks the moment a model re-emits its already-complete answer instead of stopping — exactly what `glm-ocr` does — because the "last `}`" then belongs to a garbled second copy, not the good one. And the vendor-name check was a plain substring match, so "La Cabaña" read back as "La Cabana" scored as a wrong vendor even though the model got it right; normalizing the accents out of both strings before comparing fixed that. Notice that the model hit hardest by a strict-parsing bug was the one already failing for a real reason — the kind of compounding error that makes a bad number easy to believe without checking.

The corrected score didn't change what it's measuring. `glm-ocr` hit the context-length ceiling on all six cases at two different context sizes — not because it ran out of room, but because it loops its own finished JSON answer instead of stopping, and doubling the context budget just let the loop run twice as long. On one case it also attributed a Home Depot receipt to the wrong merchant outright. Where it did terminate normally, its accuracy was fine: the score measures "can this model stop talking," not "can it read a receipt." One finding wouldn't budge for either model, though: a receipt printing both a pre-tax subtotal (€4.24) and a VAT-inclusive total (€5.00) got the pre-tax number every time, at both context sizes, even after I reworded the schema to say "the final amount actually paid or due... not a pre-tax subtotal." Four runs converging on the same wrong-but-explicable answer is a genuine small-model limitation, not a prompt-wording problem.

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

**The 8/9 that came down to one extra sentence.** Extraction scored well across the board — `qwen2.5:latest`, `qwen3.5:9b`, and `gemma4:12b` all landed 8 out of 9 — and the one miss wasn't a data problem at all. `qwen2.5:latest`'s failure was otherwise-correct JSON with extra hallucinated text tacked on after the closing brace, which broke a strict JSON-only contract the same way a syntax error would, even though every field inside the JSON itself was right. Unlike the vision-showdown harness bugs above, this one really is the model's fault, not the scorer's — an instruction-adherence gap ("return only JSON, nothing else") rather than a comprehension gap.

**The assertion that let a wrong answer through.** Chat's real score is 10 out of 12 — `qwen3.5:9b`, `phi4:14b`, and `gpt-oss:20b` all in the mix — but it took a second pass to get there. `phi4:14b` really does fail two questions: it denies the Raspberry Pi 5 has been officially released, and its answer for the Pi's idle RAM usage (~7.5GB) reflects the same stale-knowledge gap. The first of those originally passed. The test's assertion was a plain `contains-any` substring check, and `phi4:14b`'s wrong answer happened to contain a right-looking substring — a false PASS that inflated the score to 11 out of 12 until I swapped that assertion for `llm-rubric` (and, while I was in there, turned a placeholder multi-turn test into an actual 5-turn exchange). Same shape of problem as the vision-showdown scorer above: a strict, literal check passing or failing by accident rather than on whether the answer was actually right. I went back afterward and hand-verified all six `llm-rubric` grades in the chat suite against the model's actual text — every one held up. One unrelated wrinkle logged along the way: `phi4:14b`'s summarization answer ran three sentences instead of the requested two and passed anyway, because the rubric never checked sentence count — a small assertion-design gap, not a grading error, and not worth re-running over.

**The meta-lesson.** Most of these findings aren't really about the models — they're about how easily a benchmark can lie to you. A substring check can pass a wrong answer because it happens to contain the right words. A judge can confidently grade a correct answer as wrong. A JSON extractor can fail a model that gave the right answer and then kept talking. The rule I've landed on: a uniform failure across every model is almost always your harness, not their capability — models fail in different, idiosyncratic ways, a scoring bug fails everyone identically — and any single surprising result is worth pulling the raw output and checking by hand before it goes in a table.

### Building my own voice assistant: three gotchas that ate an afternoon

Fully offline voice assistants — Whisper for speech-to-text, a local LLM via Ollama for the response, Piper for text-to-speech, no cloud round-trip at all — are one of the more common patterns people build on Pi-class hardware, and talk is cheap until you wire one up and hit record. Cowork built exactly that pattern — push-to-talk, `faster-whisper` (`base.en`, CPU, int8) for speech-to-text, Ollama's streaming `/api/chat` for the LLM, `piper-tts` for the voice — specifically to get a real, measured time-to-first-token number instead of the derived estimate I'd been using elsewhere in this project. Three things broke in ways worth writing down.

| Gotcha | What it looked like | Fix |
|---|---|---|
| Default 5-minute `keep_alive` | 12.27s TTFT on turn one, 32.51s on turn two — the model was being evicted from VRAM and reloaded every idle gap | `"keep_alive": -1` in the request payload |
| Reasoning model starves itself of tokens | One turn returned nothing and the script crashed writing an empty WAV — the hidden thinking block ate the whole 4096-token `num_ctx` | `num_ctx: 8192` |
| LLMs write Markdown; TTS reads the asterisks aloud | First clean answer was full of `**bold**`, which Piper pronounces | A "voice interface, no formatting" system prompt, plus a regex strip pass as backup |

Two details the table can't hold. The second turn being *worse* than the first is the tell for the `keep_alive` one: a reload penalty shows up as TTFT on whichever turn follows an idle gap, which is exactly backwards from what a warm-up problem looks like. And the reasoning block is not small: even a trivial "hi" burned 258 tokens of hidden thinking before `qwen3.5:9b` said a word, which is why "just double `num_ctx`" worked here and, as a much longer-context test below found, only works up to a point. The Markdown fix is two layers on purpose; models don't follow "no formatting" with 100% consistency, so the regex pass catches what the system prompt lets through.

**Bonus finding: confident and wrong.** Asked what year the Raspberry Pi 5 came out and how much RAM the base model has, `qwen3.5:9b` nailed the year (2023) but invented product details that don't exist — describing a "Plus" or "higher-end" RAM tier that Raspberry Pi never made (the Pi 5 just ships in 4GB/8GB/16GB configurations of the same board, no branded tiering). It repeated a version of the same invented tiering across two independently-phrased attempts at the question. A useful reminder that a model can nail the easy part of a factual question and confidently fabricate the specific detail sitting right next to it — a failure that's much easier to catch out loud, mid-conversation, than buried in a benchmark spreadsheet.

### The real answer to "what's local TTFT" is a flag, not a GPU

Here's the twist: after fixing the context-starvation crash, I ran five more turns through the assistant and time-to-first-token was consistently awful — 14 to 84 seconds, scaling almost exactly with how "hard" the question seemed. Doing the math on the printed latency breakdown made the cause obvious: on every single turn, 83–99% of the model's total generation time happened *before* the first audible word. `qwen3.5:9b` is a hybrid-reasoning model, and its entire chain-of-thought block generates silently before any of the actual answer streams out — Ollama's `/api/chat` doesn't expose that thinking phase as separate timing, so from the outside it just looks like a shockingly slow model, even though the same model benchmarks at ~18 tok/s raw generation speed.

The fix is a single field: adding `"think": false` to the request payload suppresses the reasoning trace entirely. Before and after, same five kinds of question, same warm model:

| | With reasoning (default) | With `think: false` |
|---|---|---|
| TTFT range | 14.4s – 83.6s | 2.39s – 2.47s |
| Total generation | 15.2s – 100.6s | 2.7s – 4.8s |
| "47 × 89?" | 17.0s TTFT | 2.47s TTFT |

That's a 6–30x latency improvement depending on the question, and — at least on the handful of questions I tried — no visible quality regression; if anything the answers came back cleaner and more direct with reasoning off. This is the real, measured answer to "what's local TTFT" that the rest of this project had only ever estimated: it isn't a property of the model or the GPU at all, it's almost entirely a property of whether reasoning is switched on. A benchmark that only measures raw tok/s — which is every speed number earlier in this post — will completely miss this, because reasoning and non-reasoning modes generate at basically the same tok/s; the difference only shows up in how much gets generated invisibly before the part a user sees. Anyone building a live voice or chat product on a hybrid-reasoning model needs to know this switch exists, because leaving reasoning on by default is close to a 10-30x hidden latency tax with no warning.

To see that per turn rather than as a range, I ran a fresh batch of five questions against `qwen3.5:9b` later on, once with reasoning on and once with `think: false`, timestamping the moment the first *visible* token arrived against the moment the whole turn finished. Same `keep_alive: -1`, same `num_ctx: 8192` — but different, easier questions than the original table, so read it as a second measurement of the same effect, not a re-run.

![Stacked bar chart: five questions, each run against qwen3.5:9b with think:true and think:false at num_ctx 8192. The think:true bars are 81–99% invisible reasoning time; the think:false bars are 40–63% invisible and all under 5.5 seconds total.](/images/chart-think-stacked.png)
*Blue is time you spend staring at nothing. With reasoning on, it's 81–99% of every turn; with it off, the bar shrinks and most of what's left is the answer actually streaming.*

The seconds are smaller than the table above because the questions were easier, but the share isn't: 81–99% of each reasoning-on turn was invisible, with the lowest share landing, unsurprisingly, on the question with the longest answer to say out loud (the Fahrenheit conversion). One thing worth flagging: an earlier pass at this same batch, run at the pipeline's original `num_ctx: 4096`, reproduced the context-starvation failure from the gotchas table exactly — one question burned its entire budget on reasoning and never streamed an answer at all. Not a new bug, the same one, and confirmation that the 8192 fix is load-bearing for this model rather than optional.

**Then I added a third arm, and it complicated the story in a useful way.** If `think: false` closes most of the gap to a fast model, what happens if you just skip the reasoning model entirely and run something small and non-reasoning — `qwen2.5:3b`, the same tag that hit 138.94 tok/s on the raw GPU benchmark earlier in this post? Same pipeline, the original five questions from the table above (not the easier batch from the chart), same `keep_alive: -1` warm-model setup:

| | Reasoning on (default) | `qwen3.5:9b` + `think: false` | `qwen2.5:3b` (no reasoning mode to disable) |
|---|---|---|---|
| TTFT range | 14.4s – 83.6s | 2.39s – 2.47s | **2.13s – 2.16s** |
| Answers materially wrong | 0 of 5 (one fabricated detail, see above) | 0 of 5 | **2 of 5** |

`qwen2.5:3b` posted the flattest, lowest TTFT of any model or setting tested anywhere in this project — consistently around 2.1s regardless of question difficulty, edging out even the tuned `qwen3.5:9b`. It also got the arithmetic question wrong (47 × 89 is 4,183; it answered 4,103) and gave a genuinely garbled answer on the Raspberry Pi 5 question — first claiming the Pi 5 "didn't come out yet," then in the same breath saying it "was released in 2022" (it's neither; it shipped in 2023), and inventing RAM figures for both the Pi 4 and Pi 5 that don't match either board. It also completely missed the point of a question about my own AMD RX 6700 XT and Ollama setup, describing Ollama as game-rendering software rather than recognizing it as the very runtime serving the conversation. (The first turn of this run also cost 6.63s TTFT before settling into its ~2.14s baseline — the same cold-load-versus-warm-model tax documented above for `qwen3.5:9b`, confirming it's a property of any model's first request, not something specific to reasoning or size.)

So the honest takeaway isn't "use the smallest model for the fastest chat experience" — it's that TTFT and answer quality are separate axes that don't trade off the way that instinct predicts. Dropping a full model-size class below `qwen3.5:9b` bought roughly a quarter-second of additional TTFT headroom and cost two wrong answers out of five, on the exact same battery `qwen3.5:9b` + `think: false` handled cleanly. For a latency-sensitive product, `qwen3.5:9b` with reasoning turned off looks like the better trade than reaching for a smaller model — the "obvious" latency fix (go smaller) turns out to be the wrong lever; the flag was the right one all along.

### How far can you actually push context? A needle in a 32,000-token haystack

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

![Line chart on a log scale with prefill speed, generation speed, and time to first token for qwen3.5:9b, each indexed to its 1,024-token value as 100; the two speed lines decay to 31 and 19 while time to first token climbs to 4,162](/images/chart-needle-in-haystack.png)
*All three metrics indexed to their 1,024-token value (=100) on a log scale, because they don't share units. Throughput decays gently; TTFT goes near-vertical — and the model was 100% GPU-resident the whole way.*

Generation speed fell by more than 5x over that range, and it happened with the model still fully resident in VRAM the entire time — `ollama ps` confirmed 100% GPU at every single measurement, and VRAM usage barely moved (5.4GB at 1K tokens, 6.6GB at 32K).

That matters, because it means this is a *different* bottleneck than the 12GB VRAM cliff earlier in this post. The VRAM cliff is about data placement — a model's weights either fit in fast VRAM or they get pushed into slow system RAM, and the penalty comes from shuttling data across the PCIe bus. Nothing here got pushed anywhere. This slowdown is happening entirely inside the GPU's own fast memory, which means it's not a placement problem at all — it's a compute problem. Every token a transformer model generates has to be compared against every token already in its context window; that comparison gets more expensive as the window grows, memory placement aside. By 32K tokens, `qwen3.5:9b`'s generation speed (11.8 tok/s) has fallen to roughly what `deepseek-r1:14b` — a much bigger, dramatically slower reasoning model — manages as its baseline. A long conversation costs about as much throughput as swapping in a model with 50% more parameters.

Time-to-first-token is the number that actually kills a real product idea here. Even fully warm, with the cold-reload penalty from the voice-assistant work already eliminated, TTFT went from under 4 seconds at 1K tokens to about two and a half minutes at 32K. That's stacked on top of, not instead of, the reasoning-mode TTFT tax from the section above — this test ran with `think: false` throughout specifically so it would measure only the context-length cost in isolation. A voice assistant with a 30-turn conversation history behind it, still with reasoning switched off, is not a "hidden latency tax," it's an unusable product. The 256K context number on the model card is a statement about what the model will *accept* without erroring, not a statement about what stays fast enough to build around.

One loose thread I'm flagging rather than pretending is resolved: the two runs I did at the 8,192-token size don't agree with each other. The first pass measured a clean ~400 tok/s prefill and ~40 tok/s generation across three positions. A second pass, run minutes later as part of extending the test to larger sizes, measured a faster ~470 tok/s prefill but a *slower* ~33 tok/s generation, consistently across all five positions that time. Every other size I tested reproduced cleanly between runs. I don't have an explanation for the 8K-specific discrepancy, and I'd rather say so than paper over it with a guess — it's logged as open, and if it ever matters for something I ship, it's worth an isolated rerun to chase down.

## The Raspberry Pi 5

Everything in this section runs on the Pi 5 — 8GB RAM, no discrete GPU, CPU-only inference.

### CPU-only, and it shows

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

One methodology finding fell out of running all six back to back: on-disk GGUF file size, not the nominal parameter count, is what predicts speed here. `tok/s × file-size-in-GB` lands in a tight 10.4–11.9 range across all six models — dividing that by the Pi's ~17GB/s memory-bandwidth ceiling shows every model hit roughly 61–70% of theoretical throughput, consistently. That's why `llama3.2:1b` (1.3GB) beats `gemma2:2b` (1.6GB) despite the "smaller" name, and why `qwen2.5:1.5b` (0.99GB, the smallest file of the six) is the outright speed leader.

One methodology note before the quality numbers: the Pi can't fit `deepseek-r1:14b` — the judge model used for every rubric-graded suite in this post — locally, so the three suites that need a judge (chat, coding, agentic) don't grade themselves on-device. Cowork's fix: generation stays on the Pi, and only the `llm-rubric` grading call crosses the LAN to the PC's judge model — the diagram below has the wiring. The one open question it settled: whether `num_ctx` passes through an `openai:chat:` provider the same way it does for a native `ollama:chat:` one. It does — confirmed by checking `ollama ps` on the PC mid-run and seeing `deepseek-r1:14b` loaded at 100% GPU with `CONTEXT 4096`, an exact match to what was configured.

![Architecture diagram: the model, promptfoo, and the llm-rubric grading assertion all run on the Raspberry Pi 5; only the grading call crosses the LAN to the PC's deepseek-r1:14b judge model, whose verdict text returns to the Pi, where llm-rubric turns it into a pass/fail score.](/images/chart-lan-judge-diagram.png)
*Everything runs on the Pi except the judge model itself. `llm-rubric` is a promptfoo assertion, so it's the Pi that sends the grading prompt across the LAN and the Pi that turns the verdict that comes back into a score.*

Then the quality numbers came in, and speed and quality pulled in opposite directions. I ran all six models through the same four-workload eval harness described above, and `qwen2.5:1.5b` — the fastest model by a wide margin — finished dead last or tied for it on every single suite: 1 out of 3 on extraction, 2 out of 4 on the agentic suite, 2 out of 4 on chat, 1 out of 4 on coding. Meanwhile `llama3.2:3b` and `qwen2.5:3b` — both roughly half its speed — are the only two models on the shortlist that didn't drop a single case on the judge-free tests: 3/3 on extraction, 4/4 on the agentic suite — small suites, per the caveat above, but a clean pass where the faster model kept failing. This wasn't a lucky pair of runs I talked myself into; it held across four independent suites run over three separate days, and the gap only got clearer as more data came in.

So despite `qwen2.5:1.5b` looking like the obvious pick from a speed table alone, **`llama3.2:3b` or `qwen2.5:3b` are the actual Pi recommendation** — if you're picking a model by grabbing whatever's fastest, you're optimizing for exactly the wrong variable. `llama3.2:1b` is a reasonable middle-ground pick if you want something faster than the 3B tier without `qwen2.5:1.5b`'s consistent quality gap. Two other models, `gemma2:2b` and `phi3.5:3.8b`, both bottomed out on the agentic suite specifically — but that turned out to be a Pi-only reliability bug, not a capability problem: running six models through a 6-provider matrix on 8GB of RAM (7.87GB usable) forces repeated load/evict cycles, and under that memory pressure a model can return completely empty output even though it works fine when run alone. It's a real caveat for a Pi product that serves multiple models from shared RAM, but not a mark against either model standalone.

![Scatter plot: measured generation speed against aggregate pass rate across all four quality suites for the six Pi shortlist models. qwen2.5:1.5b sits far right at 12.08 tok/s and 40%; llama3.2:3b and qwen2.5:3b cluster near 5.5 tok/s at 73–80%, the best on the shortlist.](/images/chart-pi-speed-vs-quality.png)
*All six shortlist models, one dot each: the fastest model and the two best-scoring models sit in opposite corners. Hatched dots are the two whose agentic score was zeroed by the memory-pressure bug, not by the model. Small suites, per the caveat in the harness section — 15 cases total per model.*

The run that produced those numbers almost didn't happen. The first attempt at the LAN-judge setup stalled hard — the terminal sat at "0% | 0/24" for several minutes with nothing moving. `ollama ps` showed two models loaded on the Pi at once, and `htop` showed why: two or three `llama-server` processes pinned near 99% CPU across all four cores, swap climbing. `OLLAMA_MAX_LOADED_MODELS=1` — the setting from the config-tuning section earlier in this post — had only ever been set on the PC; the Pi's Ollama install, freshly reinstalled a few days earlier, never had it set at all, so it was happily trying to hold multiple models in 8GB of RAM at once. Cowork walked through the `ollama ps`/`htop` output with me to narrow that down and drafted the fix: `sudo systemctl edit ollama.service` with an `Environment=` line.

That did nothing on the first try — the drop-in was missing its `[Service]` header, and systemd doesn't error on a headerless `Environment=` line, it just silently ignores it, which looks a lot like "the fix didn't take" rather than "the fix was malformed." `systemctl show ollama --property=Environment` coming back empty looked at first like pager truncation; `sudo systemctl cat ollama` is what confirmed the header was missing. Once it was in, one model loaded at a time, and the suite ran clean.

### Six crashes and a watchdog: closing out the Pi's vision suite

The Pi's vision suite — the same receipt-extraction workload from the PC showdown above — was supposed to be a quick coda to the speed and quality tables. It turned into the most disruptive week of the whole project, because the assumption I walked in with was backwards: an active cooler is not a fix for sustained CPU-bound inference on a Pi 5. It's a mitigation, and there's a real difference.

The Pi has had Raspberry Pi's own Active Cooler — heatsink plus fan — installed since before any benchmarking began, confirmed present and spinning every time I checked.

![Raspberry Pi 5 with the official Active Cooler (heatsink and fan) mounted](/images/pi5-active-cooler.png)
*The Pi 5 with its Active Cooler on — present and spinning through all six crashes below. Necessary, it turned out, but not sufficient.*

Running the six-case, two-model matrix at sustained CPU load anyway produced six confirmed hard, silent reboots, in two signatures: fast, uncaught spikes that reset the board in about a minute with no warning, and slower cycles of visible throttling, recovering, throttling again, before resetting anyway. My first instinct was a power problem — a board browning out under load looks a lot like this from the outside — so I pulled per-rail voltage with `vcgencmd pmic_read_adc` through several crashes. Every rail held steady, every time. Not the power supply.

The "the cooler fixed it" conclusion I'd half-written after the first couple of crashes didn't survive either — and I did write it down before retracting it, because getting it wrong once is part of the finding. The fan was confirmed running through all six crashes, on multi-model and, notably, single-model runs, so "don't run several models at once" wasn't the fix I'd hoped for. The board also touched an 80.7°C peak without crashing while other crashes landed in the same rough 79–86°C band, which rules out a clean trip point. Whatever's killing the board is probabilistic near that range, not deterministic, and what separates a crash from a clean run at the same reading is still an open question.

**Postscript, September 22 — I went back and crashed it on purpose.** I wasn't happy leaving that as an open question, so I reran the vision suite with a logger Cowork wrote for the occasion: once a second, the `vcgencmd` temperature, the throttle flags, every PMIC rail, the CPU clock, and fan RPM off the cooler's tachometer, each row `fsync`'d to disk so the last second before a reset would survive it. It crashed on the first try, three minutes and ten seconds in, and this time I have the whole thing.

![Four stacked time-series panels from the 191 seconds before the reset: SoC temperature climbing from 60°C to 80°C in six seconds after qwen3-vl:2b loads, then flapping across the 80°C soft-limit line until the last sample at 82.9°C; fan RPM rising to its 8,774 RPM ceiling; SoC core current stepping from about 7 A under minicpm-v4.6 to about 12 A under qwen3-vl:2b; and the 5 V input rail flat between 4.97 and 5.32 V the whole time](/images/chart-pi-crash-timeline.png)
*The 29 seconds that mattered, one sample per second. Pink bands on the top panel are the seconds the firmware's soft-temperature limit was set. The dashed line is the last row the logger wrote; the next one came 3 minutes 48 seconds later, after the reboot, at 47°C.*

The story the one-second data tells is not the one I'd been telling. `minicpm-v4.6` ran first, and the board didn't care: about 6.8 A into the SoC, 67°C, fan at 6,400 RPM, for a minute and a half. Then the suite swapped to `qwen3-vl:2b`, and the chip went from 60°C to 80°C in six seconds — twenty degrees in the time it takes to read this sentence — then settled at 11.5 A, roughly 12 W, with the fan pinned at 8,774 RPM, its ceiling, and the soft-temperature limit flapping on and off for 11 of the last 24 seconds. Twenty-nine seconds after the swap, the last row. Peak 84.5°C.

The rails were flat. The 5 V input stayed between 4.97 and 5.32 V the whole run (the under-voltage warning trips at 4.63), and VDD_CORE held 1.0 V while delivering 12 A. Free memory was 3.5 GB with zero swap. Not the power supply, not memory — the same conclusion as before, now with numbers attached. And the finding that reframed this section for me: the highest current of the entire run, 15.2 A, was `minicpm-v4.6`'s load spike at the one-minute mark, and the board shrugged it off. What killed it was `qwen3-vl:2b` holding 12 W for half a minute. Not a spike — a sustained load about 70% higher than the other model in the same suite, on a cooler whose ceiling sits somewhere between the two.

![htop on the Pi at 00:51:36 uptime, the last second the logger recorded: all four cores at 100%, four llama-server threads at 97–100% CPU with qwen3-vl:2b resident at 3.6 GB, load average 4.24, the thermal logger itself visible three rows down](/images/pi-htop-at-reset.png)
*`htop` at 00:51:36 uptime — which works out to the last second in the CSV. The board reset before the next refresh.*

So "probabilistic near that range" was me not having enough data. It's closer to deterministic than that: this cooler holds about 7 W indefinitely and does not hold about 12 W, and which of your models is the 12-watt one is not something the model card tells you.

Two things I'm leaving open, because they are. The kernel reported 3000 MHz in every one of the seconds the soft limit was set — the clock is supposed to be coming down at that point, and either it hadn't yet, which would be the reaction-time gap captured in a single number, or `scaling_cur_freq` lags what the firmware actually did. I don't know which; sampling `vcgencmd measure_clock arm` instead is the next test. And there is no kernel-side trace of the reset at all: Raspberry Pi OS keeps the journal in RAM by default, so the previous boot's log went with it. The only record of those 29 seconds exists because a script was writing a CSV once a second and calling `fsync` after every line. If you're going to crash a Pi on purpose, do that first — and `sudo mkdir -p /var/log/journal` before the run, so the journal survives too.

After the fourth crash, Cowork asked me directly whether we were done — the honest answer was no, the vision suite still had no trustworthy result. I pushed back before it went further: *"This keeps crashing, so not sure we are going to get the results we want. We might want to summarize as not possible to complete unless you have other ideas."* Rather than agreeing to close it out, Cowork came back with three options: split the two-model matrix into single-model runs with checkpointing (cheapest, try first), build a software watchdog that kills the process and lets the board cool before the danger zone, or swap in a more aggressive third-party cooler. That third one I killed myself: the official cooler had failed to prevent five crashes with its fan confirmed spinning for every one, which is reason enough to conclude a different air cooler wasn't the lever — the other two targeted the actual mechanism, a reaction-time gap between the temperature climb and the firmware's own throttle response, not raw cooling capacity. Plan: single-model split first since it's basically free, watchdog only if that wasn't enough.

It wasn't enough, so: the watchdog. Monitor temperature, kill the inference process before the danger zone, let the board cool, resume. Cowork wrote the first version, and it surfaced two bugs worth knowing about if you're scripting anything similar around `promptfoo`. First, a naive PID-based kill silently did nothing — the script looked complete, but `npx`-launched processes spawn children (`llama-server`, here) that keep running after you kill the parent PID, so the watchdog had to kill by pattern-matching the invocation with `pkill -f` against a distinguishing config filename instead. Second, the script's success/failure logic misclassified a clean kill-and-resume cycle as a failure, fixed by tracking success with an internal flag rather than trusting the exit code. With both fixed, the watchdog worked exactly as designed — I could prove it killed and resumed correctly.

It still wasn't usable for one model. `qwen3-vl:2b`'s normal per-case generation time on the Pi is longer than the watchdog's kill window, so a watchdog tuned to intervene before thermal danger would kill every case before it could finish, healthy or not — a working watchdog incompatible with this model's timing. I abandoned it for that model and ran the remaining cases manually, leaning on `promptfoo`'s response cache so a mid-suite crash wouldn't cost the cases already completed. That produced the sixth crash — and, on a later pass, the first fully clean completion of the suite.

One result from that run is still open: the same Costa Coffee receipt, same model, same config, produced an 18.86-minute non-terminating loop on one run and two clean 1–2 minute completions on two later runs. I don't have an explanation and I'm not pretending to — it's logged, worth a targeted repeat if it ever becomes decision-relevant, not worth blocking the suite on.

What I do have a clean answer for is what `qwen3-vl:2b` got right once a case completed: four of six receipts correct on vendor, date, and total, with Costa and Home Depot the two failures. The Costa failure was the same pattern I'd already hit twice on the PC's vision suite — the pre-tax subtotal instead of the VAT-inclusive total due. Third confirmed instance, third receipt, different model. That's not a coincidence, it's a pattern to design around rather than re-prompt away.

With that, I closed the Pi vision suite: `qwen3-vl:2b` at 4 of 6 (66.67% weighted, every receipt all-or-nothing, no partials), and `minicpm-v4.6` at 5.5 of 6 weighted (92%) — the latter an existing partial-run result from the day before, accepted as final rather than re-run, my call once I'd seen what re-running was costing in crash risk. As I put it at the time: "Pi vision suite (both models) can be marked closed. I'm good with what we have."

The practical upshot for anything I build on this board: active cooling is necessary, but treating it as sufficient was the mistake that cost the week. Any real product running sustained inference on a Pi 5 needs an application-level watchdog and auto-restart designed in from the start — tuned per-workload, not borrowed from this one, and with the per-model power draw measured first, since the postscript above says the difference between "fine indefinitely" and "dead in 29 seconds" was which model was loaded. The kill-window mismatch that sidelined the watchdog for `qwen3-vl:2b` is the reminder: "the watchdog works" and "the watchdog works for this model's timing" are two different claims, and only one matters in production.

There's no Pi project waiting on any of this, for what it's worth — I wanted to know what the board could do, and now I do.

## Tools & AI assist

The whole project ran inside a Claude Project ("Run Local LLM") using **Claude Cowork**. Three standing docs (Project Instructions, a Session Log, a Benchmark Log) got maintained as we went, so nothing had to get reconstructed from memory later — this post is largely a distillation of that log.

Cowork wrote every promptfoo config, the voice-assistant pipeline, the Pi thermal watchdog script, and the one-second crash logger in the postscript. I ran the actual hardware, watched the thermals, and made the calls on what to try next and when to stop — including a couple of times I overruled where the investigation was headed, like the Pi crash section above.

Gemini ran the original GPU env-var session, before this project existed; its explanation of why that fix worked is the one corrected in place in the GPU section above, after Cowork caught the contradiction in review.

Cowork also got things wrong, more than once. The GPU env vars earlier in this post are one example: its first pass at "optimizing" them cost me a 3x speed regression before we caught it. The Pi thermal watchdog's first version silently didn't work at all. Both are covered in place, where they happened, rather than saved up for a highlight reel here.

## Lessons learned & what's next

On the PC, the fast path is clear: get the GPU env vars right, stay under ~13B params at Q4_K_M unless you've specifically tested a bigger model's split-mode performance, and tune `num_ctx` down before you conclude a model is "slow" when it's actually just spilling out of VRAM. `qwen3.5:9b` was the most consistently reliable model across every eval suite I ran it through, comfortably inside the 12GB budget — as long as `think: false` is on for anything latency-sensitive and the conversation doesn't get long.

On the Pi, both halves of the picture are in now — real speed measurements across the sub-4B tier, and real quality scores across four separate workloads. The two don't point the same direction: the fastest model on the shortlist is also the weakest one, and `llama3.2:3b`/`qwen2.5:3b` are the actual recommendation despite running at less than half the speed.

The lesson threading through both machines is the one from the eval-harness section — none of this shows up until you run the test and check the raw output by hand:

- The PC's shortlisted best agentic-coding model doesn't reliably call tools at all.
- The judge grading my own benchmark suite got a right answer wrong.
- The purpose-built OCR model lost to a generalist because it can't stop repeating itself.
- The fastest model on the Pi is the one I'd trust least.
- The fastest TTFT I measured anywhere in this project came from the model that also got two of five answers wrong.
- The model whose spec sheet promises 256K tokens of context becomes unusably slow — 40x worse TTFT, 5x worse throughput — at an eighth of that number, with VRAM sitting nearly flat the entire time, so it can't even be blamed on running out of memory.

If you want to run any of this yourself rather than take my numbers on faith, the repo has everything: the promptfoo suites for both machines, the receipt images and encoder script behind the vision tests, the voice assistant script, and a `FINDINGS.md` with the full data behind every table above — the README covers PC and Pi setup separately since the env vars and model lists differ. The one-second thermal/power logger and the actual crash data behind the postscript above live in `benchmarks/pi-crash-capture/`. [github.com/dwooods/local-llm-benchmark](https://github.com/dwooods/local-llm-benchmark)

**So — more than a curiosity?** Not really. Not as a replacement for the closed models I started this post living inside of, and not on the hardware most people have. A 12GB card is a perfectly respectable GPU by any non-AI standard, and it caps you at roughly 13B parameters; a 13B model is a long way from ChatGPT or Claude on anything open-ended (that's two years of daily use talking, not a suite I ran), and the price of "free" is a tuning tax — env vars, `num_ctx`, `think: false`, a driver update that can silently undo all of it — plus a model that, asked a simple factual question, invented a Raspberry Pi product tier that doesn't exist.

Where local does earn its place is the lightweight, narrow stuff: the receipt-extraction pipeline from this post, pointed at a folder of scanned invoices instead of six test photos, running on a Pi with no API bill and no data leaving the house — or a voice assistant that only has to answer short questions, or a small fixed set of actions on a Pi. Work where "good enough, and no data leaves the building" beats "best possible answer."

I didn't put the closed models through the same suites, and that's the obvious next test: the one comparison this post talks about and doesn't measure. And I haven't found a job for an open model yet: I'm still paying for Claude, because it's the best fit for what I do right now, and that stays true until something I can run locally can compete with it.
