# Blog Post Ratings — dwooods.github.io

Last updated: 2026-10-01 · Rated by Claude from a full read of each post · 6 posts

This file tracks quality ratings for every post on the blog, using one rubric, so new posts can be scored the same way and compared. When a post is revised, re-score it, update its row, and add a line to the change log at the bottom. Don't overwrite old scores without logging them.

---

## The rubric

Each post is scored 1–10 on eight dimensions. **Overall = the average of the eight, rounded to the nearest 0.5.** That keeps the overall checkable: if a dimension score changes, the overall follows from the math, not from a gut call.

| Dimension | What a 9–10 looks like | What a 6 or below looks like |
|---|---|---|
| **Hook** | The first paragraph is a concrete problem or scene the reader can picture. | It opens on background, a definition, or "I've been meaning to…". |
| **Focus** | One problem or question carries the whole post, and every section serves it. | Two stories compete, or sections drift into side topics. |
| **Voice** | Sounds like David throughout: first person, dry, dad-humor, specific. | Generic phrasing ("a genuinely different way to work"), or the jokes cluster in one section. |
| **Clarity** | A non-engineer can follow it; jargon is explained in plain words at first use. | Unexplained terms, dense paragraphs, or a reader has to already know the stack. |
| **Usefulness** | Contains something a stranger can reuse: a fix, a gotcha, a command, a pattern. | Interesting to read but nothing transferable. |
| **Honesty & evidence** | Claims are measured or sourced; AI mistakes and the author's own are named in place; limits are stated. | Unverified claims, or AI shown only succeeding. |
| **Ending** | Closes on a concrete image or a real result. | Closes on an abstraction, a list, or a restated thesis. |
| **Economy** | Every section earns its length; nothing is said twice. | The same point or story appears more than once, or the post is far longer than its content needs. |

---

## Scoreboard

| Rank | Post | Date | Words | Hook | Focus | Voice | Clarity | Useful | Honesty | Ending | Economy | **Overall** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | The Scan That Wouldn't Die (ClamAV on Synology) | 2026-09-24 | 4,986 | 9 | 9 | 9 | 9 | 9 | 10 | 10 | 7 | **9.0** |
| 2 | Wagging the Dog (Plex over Tailscale) | 2026-09-18 | 3,445 | 9 | 8 | 10 | 8 | 8 | 10 | 10 | 6 | **8.5** |
| 2 | Spec by Screenshot (Robinhood Dividend Dashboard) | 2026-10-01 | 3,640 | 8 | 7 | 9 | 8 | 9 | 10 | 8 | 8 | **8.5** |
| 4 | Local LLMs on a PC and a Pi | 2026-09-21 | 10,186 | 7 | 8 | 7 | 7 | 10 | 10 | 9 | 5 | **8.0** |
| 5 | Building a Raspberry Pi LED Controller with Claude | 2026-09-10 | 2,464 | 9 | 7 | 7 | 8 | 9 | 7 | 6 | 7 | **7.5** |
| 6 | Building a Fantasy Football Co-Manager with Claude | 2026-09-14 | 3,344 | 8 | 6 | 9 | 8 | 6 | 8 | 6 | 5 | **7.0** |

Word counts include front matter and markup, from `wc -w` on the source file.

---

## Post-by-post

### 1. The Scan That Wouldn't Die — 9.0
`clamav-synology-nas.md`

**Why it's a 9.** One constraint (the NAS sleeps 11PM–7AM, so the scan has a 16-hour window) carries the entire post. Every challenge is concrete and reusable by strangers: ClamAV's silent 100MB cap, `--exclude-dir` being a prefix match with no un-exclude, generating the exclude list with `find` instead of memory, and the failure-only email that stayed silent on clean runs. It names Claude's misses and David's own in place. The "fire inspector, not a smoke alarm" framing is the clearest statement of a tool's limits on the blog, and the closing paragraph (the NAS quietly scanning while nobody in the house cares) is the best ending.

**What keeps it from a 10.**
- Length: about 5,000 words.
- The "How often should you run this at all?" section wanders through sources, gut feel and irony before landing.

**Path to 10.** Cut the frequency section to two paragraphs (what the sources say, what I chose and why) and trim the Synology `@` folder audit to its two findings.

### 2. Wagging the Dog — 8.5
`wagging-the-dog-tailscale-plex-vacation.md`

**Why it's an 8.5.** The strongest hook-and-ending pair on the blog: no Netflix and a grudge against Plex at the start, handing a kid a phone 600 miles from home at the end, with "the word 'blank' pretending to be a security researcher" as the toll booth. The Terms of Service paragraph names the gray area plainly instead of pretending it isn't there, which is the most mature passage on the blog. The commercial-VPN-versus-subnet-router explanation and the TUN-mode fix are reusable.

**What costs it.**
- The grep/"blank" story is told twice, once in Tools & AI Assist and again in Key Technical Challenges.
- The project is unfinished: the smart TV, which was the whole point, is untested.

**Path to 9.** Tell the grep story once, in Challenges, and cut Tools & AI Assist down to credits and misses. Publish a follow-up, or update this post, once the TV test happens.

### 2. Spec by Screenshot — 8.5
`robinhood-dividend-dashboard.md`

**Why it's an 8.5.** It has the best product thinking on the blog: designing by screenshot, the reconstructed account-value chart disclosed with a footnote, the one-hour cache "rule to protect Robinhood from me," and the two-account surprise against Robinhood's own tracker. It makes the best use of visuals (numbered composites, side-by-side chart iterations, the tree-swing cartoon) and of callouts (sample-data notice, mismatch table, TL;DR). Its payoff is unique: a clickable sample-data concept and a set of concrete asks. Three independent reviews (Claude, Gemini, ChatGPT) landed at 7.5–8.5.

**What keeps it from a 9.**
- It does two jobs: a build story, and product asks to Robinhood.
- About 3,600 words for a mixed audience.
- "Why I Built This" ¶2 is still the densest paragraph (MCP, the Agentic account, read versus trade, and the retirement question in six sentences).

**Path to 9.** Move "What I'd Ask Robinhood For" and the concept link into a short companion post and end this one at the Dividend Tracker section and Lessons. That's a rewrite rather than an edit; not planned.

### 4. Local LLMs on a PC and a Pi — 8.0
`local-llms-pc-and-pi.md`

**Why it's an 8.** It's the most rigorous post on the blog, and it has the highest usefulness and honesty scores. Highlights include the judge model grading a correct answer wrong, `think: false` as the real time-to-first-token lever (6–30x), the 12GB VRAM cliff, and the Pi thermal postscript with one-second data proving the cooler holds about 7 W but not 12 W. The closing "What I assumed / What the test found" table is the best summary device on the blog.

**What costs it.**
- Economy: about 10,000 words and a dozen tables. It reads as a lab report, not a story.
- Long parenthetical hedges slow the reading.
- The opening takes five paragraphs to reach the hardware.

**Path to 9.** Cut 40%. Keep every finding, but move the per-suite detail and secondary tables to the repo's `FINDINGS.md` and link to it. Start with the assumed/found table as a preview.

### 5. Building a Raspberry Pi LED Controller — 7.5
`led-strip.md`

**Why it's a 7.5.** It has a great hook: the strip blinking random colors with power and no data, which looks broken and is normal. The Pi 5 gotcha (older `rpi_ws281x`/neopixel tutorials silently fail because GPIO moved to the RP1 chip; the fix is hardware SPI) is the most searchable, reusable fix on the blog. The build is fully reproducible: wiring diagram, photos, architecture diagram, code, repo, and a six-step setup. The 13-year-old shipping the Rocket Launch effect is the best human moment on the blog.

**What costs it.**
- The thesis ("the LED strip is just the vehicle… the interesting part is how I work with AI") is stated four times.
- A paragraph is spent on a "confidently wrong" moment that didn't happen.
- Generic phrasing in the AI sections.
- It ends on an abstraction.
- It says "Cowork" about a dozen times.

**Path to 8.** State the thesis once, cut the paragraph about nothing going wrong, end on a concrete image (the strip running, or his effect in the menu), and switch "Cowork" to "Claude."

### 6. Building a Fantasy Football Co-Manager — 7.0
`fantasy-football-ai.md`

**Why it's a 7.** It has the most of David in it: the family league, the 49ers, "Ctrl+C. Ctrl+V.", and "I still get blamed when the lineup sucks." "The API is not the product" is a strong, transferable lesson. The screenshot-beats-API and blocked-CORS-relay stories are concrete and honest.

**What costs it.**
- One-sentence-paragraph LinkedIn rhythm at blog length reads choppy.
- "It helps, I decide" is repeated three times, and "co-manager" five times at the end.
- The official FantasyPros MCP server is teased early and resolved late, undercutting the build twice.
- The cache gets its own section after already being introduced.
- It ends on an abstract list.
- There's no real result (record or standing).

**Path to 8.** Revision prompt prepared in `fantasy-football-revision-prompt.md`: merge paragraphs, say each point once, mention the official MCP server once, merge the cache section, end on a concrete Sunday scene, and add an actual season result.

---

## Blog-level patterns

These matter more than any single score. Check new posts against them.

1. **The same thesis in every post.** "The interesting part wasn't AI writing the code, it was how I work with AI" appears in LED, Fantasy, ClamAV and the dividend post. A reader of two posts will notice. Let one post own it; the others should show it, not say it.
2. **Tools & AI Assist sections retell the main story.** In Plex and LED especially, this section previews challenges that come later. ClamAV's version is the model: short, credits who did what, names the misses, no story.
3. **Naming is inconsistent.** Four posts say "Cowork" or "Claude Cowork"; the dividend post says "Claude." The current standard is "Claude."
4. **The best posts end on a concrete image.** ClamAV (the NAS scanning while nobody cares) and Plex (a kid finishing a movie 600 miles from home) score 10 on Ending. Fantasy and LED end on abstractions and score 6.
5. **Economy is the most common weak dimension.** Four of six posts score 7 or below on it, usually from telling one story twice, not from overall length.
6. **Honesty is the blog's strength.** Every post names AI mistakes or its own limits. Keep it.

---

## How to rate a new post

1. Read the whole post, not just the opening. (A rating from stats and the first paragraph was wrong by a full point on the LED post.)
2. Score each of the eight dimensions against the rubric table, with one sentence of evidence per score, quoting the post where possible.
3. Overall = average of the eight, rounded to the nearest 0.5.
4. Write: why it's that score, what costs it, and the path to the next half-point.
5. Check it against the six blog-level patterns.
6. Add a row to the scoreboard, re-rank, and add a change-log line.

---

## Change log

| Date | Post | Change | Old → New |
|---|---|---|---|
| 2026-10-01 | All six | First full-read ratings with the eight-dimension rubric | — |
| 2026-10-01 | LED strip | First estimate was from stats and opening only; corrected after a full read | 6.5 → 7.5 |
| 2026-10-01 | ClamAV | Corrected after a full read | 8.5 → 9.0 |
| 2026-10-01 | Plex / Tailscale | Corrected after a full read | 8.0 → 8.5 |
| 2026-10-01 | Local LLMs | Corrected after a full read | 7.0 → 8.0 |
| 2026-10-01 | Dividend Dashboard | Rated after the final review round (Gemini and ChatGPT fixes applied) | 8.5 |
