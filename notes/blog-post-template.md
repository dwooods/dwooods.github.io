# Blog post drafting template (master copy)

Master copy for drafting any new post on dwooods.github.io. Any Claude chat can read it from:
https://raw.githubusercontent.com/dwooods/dwooods.github.io/main/notes/blog-post-template.md

Version 1.1 · Last updated 2026-11-03 · Change log at the bottom.

## For David: how to use this

Open a chat in the project that holds the story, then paste this and fill in the two bracketed fields:

    Read https://raw.githubusercontent.com/dwooods/dwooods.github.io/main/notes/blog-post-template.md
    in full and follow it to draft a blog post.
    Project/repo for the story: [repo URL or "this project"]
    Anything different this time: [e.g. shorter, a specific angle, or "none"]

If the chat cannot fetch the URL, attach this file instead. Do not paste an older copy from memory; this file is the only master.

## For Claude: how to treat this file

This file is the whole brief. It is written to David's blog voice and rules, so follow it over your defaults. Do not push, publish, or flip any draft flag. Your output is a draft in chat plus a downloadable `.md` file.

Keeping it current: if David corrects your draft in a way that reveals a rule this file lacks or gets wrong (a voice miss, a convention, a rubric point), say so at the end of that turn, propose the exact edit, and update this file only with his yes. The master lives in the blog repo; edit it by pull request, and he merges. Add a line to the change log with the date and why. If the rubric or conventions also live in his blog project docs (`blog-post-ratings.md`, `claude/blog-project-instructions.md`, `claude/diagram-conventions.md`), tell him to mirror the change there.

---

## STEP 0: READ FIRST

1. Fetch and read the two reference posts and match them on voice, structure, pacing and paragraph shape. Do not copy their phrasing or reuse their anecdotes.
   - https://raw.githubusercontent.com/dwooods/dwooods.github.io/main/content/posts/wagging-the-dog-tailscale-plex-vacation.md (voice and length model, rated 9.0)
   - https://raw.githubusercontent.com/dwooods/dwooods.github.io/main/content/posts/fantasy-football-ai.md (second reference, rated 8.5)
   If you cannot fetch them, ask David to attach them. Do not draft from memory of the blog.
2. Read the project's repo, README and chat history for the real story.

## STEP 1: ASK BEFORE DRAFTING

Ask David up to five short questions about what actually happened: what he decided, what broke, what Claude got wrong, what he rejected, and which AI tools besides Claude he used. Never invent personal, family, or technical details. If a fact isn't in the material or his answers, leave a [TODO: ask David] marker instead of filling it in.

## STEP 2: FIND THE LOOP

Every post follows one loop: idea -> AI-assisted build -> real-world friction -> problem-solving -> lesson. State the loop for this post in three lines and wait for David's OK before drafting.

The throughline under it: AI handles implementation and information-gathering; David makes the decisions. Show that through small concrete moments (David decides, Claude implements; Claude proposes a workaround, David rejects it). Do not assert it in a closing summary.

## LENGTH (HARD RULE, overridable only by David)

Target 3,000-3,300 words, hard cap 3,500, about a 15-minute read. Count words on the final text (code blocks excluded, captions included) and report the number. If over 3,500, cut before showing it. Budget by section:

1. Hook and pitch: 250-300
2. Why I built this: 350-400
3. Architecture and tech stack, including "Tools & AI assist": 500-600
4. Key challenges (1-3 real problems): 1,200-1,400
5. Lessons and what's next: 400-500
6. Call to action and links: 80-120

Consolidate rather than add sections. Watch the ratio of David's experience to setup instructions: setup the README already covers gets a link, not a walkthrough.

## VOICE AND TONE

- Educational first. Conversational, a little self-deprecating, comfortable saying things broke, like explaining the project to a friend. An honest "here's what happened" beats polish.
- First person. No buzzwords, hype, humble-bragging, or business-case framing for a side project.
- Dry, specific humor spread across sections, not clustered in one.
- Don't oversell the AI. Call out where it was mundane or produced nothing, so the useful moments are believable.
- Normal paragraphs. A one-sentence paragraph only for a beat, contrast or punchline, never several in a row.
- Include at least one lesson abstract enough that a reader can swap in their own project.
- Prefer narrative prose to bullet lists in narrative sections; use lists only for specs, steps or comparisons a reader will scan.
- A non-engineer should be able to follow it: explain jargon in plain words at first use.
- Describe what a third party did rather than asserting their motive. Hedge claims about others ("as far as I can tell"). Don't state facts about products or companies that can't be proven; say what David did or saw. Link primary sources named in the post.
- Never invent family or personal details. Blank out local file paths in screenshots before they go in a post.

## AI TOOLING

Call it "Claude" or "AI". Do not name the product surface, editor, or model version. Name any non-Claude AI tool and say what it did. Say concretely what Claude did (scaffolded, debugged X, wrote the docs), including misses ("Claude confidently suggested X; it failed"). Include a "Tools & AI assist" subsection: short, credits who did what, names the misses, does not retell the story. Caption any AI-generated or AI-altered image as such.

## STRUCTURE

Follow the six sections above; skip one only if truly not needed. In section 4, use 10-20 line annotated snippets and explain why each fix worked, not just that it did. Call out where AI was part of finding the fix.

One payoff ending. Pick the true closing beat (usually personal, not technical, ideally a concrete image or real result), put everything else before it, and fold the repo invite into section 6. If the draft ends up with several closing lines, tell David and ask which one closes. Do not state the thesis "the interesting part wasn't the code, it was how I work with AI"; other posts own it. Show it, don't say it.

If something David built is later superseded, don't quietly edit: add a short dated postscript saying what changed, what is true now, and whether he would still have built it. Check real dates and report the less flattering truth if that is what is true.

## HUGO FORMAT

- File: `content/posts/<slug>.md`.
- Front matter: `title`, `date`, `draft: true` (never false unless David says so), `tags`, `description` (under about 160 characters), `summary` (a punchy 1-2 sentence hook that shows the loop; LoveIt uses it on the homepage and list pages), and `featuredImage` / `featuredImagePreview` pointing to `/images/hero-<slug>.jpeg` if there is a hero.
- Images live in `static/images/` and are referenced as `/images/<file>` with plain markdown image syntax, so they zoom site-wide. Raw HTML `<img>`, the hero and video do not zoom (use raw HTML on purpose for decorative thumbnails). Every image gets alt text. Put a screenshot or GIF at the top. Tell David which other moments deserve a screenshot, GIF or diagram, and what each should show.

### Diagrams (SVG only)

Never use a fenced mermaid block: LoveIt's mermaid script does not load on this site, so the diagram silently fails. Never paste SVG markup into the post body either; Hugo's markdown renderer here can strip raw inline HTML or SVG, so it renders blank. A diagram is a separate `.svg` file in `static/images/<slug>-<what>.svg`, referenced with `![one-sentence alt text](/images/<slug>-<what>.svg)` on its own line with a blank line above and below (no leading spaces).

Every SVG you produce must meet all of these, and you must check and report them:
- Native SVG `<text>` labels only. No `<foreignObject>`, no HTML labels, no external fonts or scripts. (HTML labels display in desktop Chrome but vanish in Safari and on some phones.) Report the count of `foreignObject` (must be 0) and of `<text` (must be above 0).
- A white background set on the root tag: `style="background-color:#fff"`. It is static and will not follow the site's light/dark switch, so use light, neutral colors that read on white.
- A `viewBox`, with no fixed pixel width or height, so it scales to the page.
- Text readable at about 800px wide and when zoomed to 1600px.
- If built from mermaid: render with `htmlLabels: false`, neutral theme.
- Test it by loading the file as an `<img>`, not by inlining it.
- Deliver it as a downloadable `.svg` file, not pasted into chat. SVGs do not need the JPEG resize script below.
- Give a one-sentence alt text.

### Raster images (screenshots, photos, heroes): watch the file size

Oversized images are the most common way a post gets slow. AI image generators routinely hand back 2,000-3,000px files of 2 MB or more; phone screenshots and photos can be as bad. Rules:
- Resize every raster image before it is committed: max 1600px wide, never upscale, JPEG quality 82, aspect ratio preserved. That typically lands around 150-300 KB.
- Treat any PNG, JPEG or photo over about 300 KB, or wider than 1600px, as needing the script. Ask David for the original's size if you don't know it.
- Give David the script proactively, in the same message where an image first comes up, without being asked. He runs it from the blog repo root in PowerShell with the original already in `static\images\`, then reports the printed "Original" and "New size" lines.
- Reference only the resized output (a new filename; do not overwrite the source) and tell him to keep the original multi-MB file out of the repo so it is never committed.
- Do not treat an image as done until David reports the resized dimensions and size. If the draft references an image he has not resized, say so in the open-questions list.
- The script does not handle GIFs or video. For those, tell David the file size and ask whether it should be trimmed.
- Text inside screenshots must stay readable at 1600px. If the resized output is narrower than the content column, cap it rather than upscaling.

```powershell
Add-Type -AssemblyName System.Drawing
$srcName = "ORIGINAL-FILE-NAME.png"   # what's currently in static\images
$outName = "hero-<slug>.jpeg"         # new name the post will reference (must differ from $srcName)
$src = (Resolve-Path "static\images\$srcName").Path
$out = Join-Path (Get-Location) "static\images\$outName"
$img = [System.Drawing.Image]::FromFile($src)
"Original: $($img.Width) x $($img.Height)"
$w = [Math]::Min(1600, $img.Width); $h = [int]($img.Height * $w / $img.Width)
$bmp = New-Object System.Drawing.Bitmap $w, $h
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.InterpolationMode = 'HighQualityBicubic'
$g.DrawImage($img, 0, 0, $w, $h)
$enc = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object MimeType -eq 'image/jpeg'
$p = New-Object System.Drawing.Imaging.EncoderParameters 1
$p.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, [long]82)
$bmp.Save($out, $enc, $p)
$g.Dispose(); $bmp.Dispose(); $img.Dispose()
"New size: $w x $h, " + [int]((Get-Item $out).Length / 1KB) + " KB"
```

### Other Hugo conventions

- LoveIt stretches featured images to the full content column. If the hero is narrower than that, cap it with a page-scoped style right after the front matter instead of upscaling: `<style>.featured-image img, .featured-image img.lazyloaded { max-width: <native-px>px; width: 100% !important; }</style>`.
- Sample data only. No real account data, balances, keys, or personal identifiers in text or images.
- Preview (optional, offer it after any major change): from the blog repo, `hugo server -D --disableFastRender` (Hugo Extended; `-D` shows drafts), then `http://localhost:1313/posts/<slug>/`. Hard-refresh after a pull; a stale server shows truncated text. Click each markdown image to confirm it zooms.
- Pushing: never push to `main` or flip `draft` to false without asking David and getting a clear yes, every time. Text edits to a draft post (`draft: true`) go to `main` once he says so; anything that touches a live page goes by pull request and is merged only when he says "merge it". Each new post's homepage summary should read as a parallel example of the loop; keep the homepage intro at pattern level.

## DELIVERABLES

1. The three-line loop (Step 2). Wait for David's OK.
2. The full draft as a downloadable `.md` file, with the word count.
3. A self-score using the rubric below.
4. A list of [TODO: ask David] markers and open questions.
5. An image list: for each image, what it shows, where it goes, its alt text, and (for rasters) whether it still needs the resize script; for each SVG, the `foreignObject` and `<text` counts. Include the resize script.

Do not offer to publish. David will review the draft, then take it to his blog project for rating and push.

## SELF-SCORE RUBRIC

Score the finished draft 1-10 on each of eight dimensions after a full read (not the opening and a word count). Give one sentence of evidence per score, quoting the post. Be conservative: scores on this blog have run 0.5-1 point generous when Claude scores its own writing.

| Dimension | 9-10 looks like | 6 or below looks like |
|---|---|---|
| Hook | First paragraph is a concrete problem or scene the reader can picture | Opens on background, a definition, or "I've been meaning to..." |
| Focus | One problem or question carries the whole post; every section serves it | Two stories compete, or sections drift into side topics |
| Voice | Sounds like David throughout: first person, dry, specific, humor spread across sections | Generic phrasing ("a genuinely different way to work"), or the jokes cluster in one section |
| Clarity | A non-engineer can follow it; jargon explained in plain words at first use | Unexplained terms, dense paragraphs, reader must already know the stack |
| Usefulness | Contains something a stranger can reuse: a fix, a gotcha, a command, a pattern | Interesting but nothing transferable |
| Honesty & evidence | Claims are measured or sourced; AI mistakes and David's own are named in place; limits stated; every non-real image captioned | Unverified claims, or AI shown only succeeding |
| Ending | Closes on a concrete image or a real result | Closes on an abstraction, a list, or a restated thesis |
| Economy | Every section earns its length; nothing said twice | Same point or story told more than once, or far longer than the content needs |

Overall = average of the eight, rounded to the nearest 0.5. An exact tie between two roundings (for example 8.25 or 7.75) rounds DOWN.

Benchmarks on this blog: the best posts score 9.0 (sum 72/80); typical is 8.0-8.5 (sum 66-67). A first draft scoring above 8.5 is probably over-scored.

With the table, also give:
- Why it is that score, what costs it, and the one path to the next half-point.
- The weakest sentence in the post, quoted.
- A blog-level pattern check. Mark each [hit / clear] with one line of evidence:
  1. The thesis "the interesting part wasn't AI writing code, it's how I work with AI" is stated outright.
  2. "Tools & AI assist" retells the story instead of crediting who did what and naming misses.
  3. Naming is inconsistent (only "Claude" or "AI"; no product surface, editor or model version; non-Claude AI tools named).
  4. The ending is an abstraction, a list, or several closing lines instead of one concrete image or result.
  5. The same point or story appears twice (previewed, then retold).
  6. Two products or two stories compete (ask which one is the product).
  7. Any diagram is a fenced mermaid block, pasted inline SVG, or an SVG with `foreignObject` labels; any image carrying small text uses raw HTML instead of markdown image syntax; or any raster image is over about 300 KB or wider than 1600px without the resize script having been run.

---

## Change log

| Date | Change | Why |
|---|---|---|
| 2026-11-03 | v1.0: first version, merged from the length-capped blog-post prompt, the blog project instructions (voice, structure, Hugo conventions, resize script), the diagram conventions, and the rating rubric in `blog-post-ratings.md`. Made self-contained and fetchable by URL. | David asked for a standing template so a new prompt is not generated for each post. |
| 2026-11-03 | v1.1: split image rules into "Diagrams (SVG only)" and "Raster images: watch the file size". SVG now has an explicit checklist (no `foreignObject`, white background, `viewBox`, separate `.svg` file, never pasted inline) and must be reported with counts. Added the oversized-image warning (over about 300 KB or wider than 1600px needs the PowerShell resize; do not treat an image as done until David reports sizes). Deliverable 5 and pattern check 7 extended to match. | A chat produced an SVG without these constraints, and David asked that the template warn against it and cover oversized images and the resize script. |
