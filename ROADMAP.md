# Roadmap

Running log of improvement ideas that are deliberately not being done right now.
Not a commitment or a sprint board — just so ideas from a review don't get lost.

## Phase 2: Visual hierarchy / "builder's lab notebook" feel

Logged 2026-09-18, from a review of the homepage after the Tailscale/Plex post shipped.

**The gap:** the writing and projects have personality (weird, hands-on, self-deprecating);
the homepage structure is a conventional, tidy blog layout. Not broken, just a mismatch in
tone between the words and the page around them.

**Confirmed NOT a gap (checked the theme code, no action needed):**
- Featured images already render as real thumbnails in the homepage post list
  (`themes/LoveIt/layouts/summary.html`, `featured-image-preview` block). What looked like
  missing images was normal lazy-loading, not a missing feature.

**Cheap wins — content or CSS only, no layout/template risk:**
- [ ] "Currently building: ___" one-line status under the bio (pure content edit)
- [ ] Custom accent color / font tweak via LoveIt's `custom.css` override
- [ ] Tag styling as small pill/badge treatment instead of plain comma-separated text links
- [ ] Reading time / word count shown on the homepage list (not currently in `summary.html`)

**Real effort — needs actual template + CSS work, size before starting:**
- [ ] True "project cards" for the homepage list: grid layout, hero image treatment, hover
      states, small metadata row (stack/tools used, read time). Requires overriding
      `layouts/summary.html` and/or `_partials/home/profile.html`, not a config flag.
- [ ] Stronger visual separation between the intro/bio block and the projects list below it

**Explicitly out of scope:** anything gimmicky (animated AI graphics, hacker-aesthetic
theming). Subtle > loud.

**Suggested order:** do the cheap wins first — they may close most of the personality gap
on their own, and will make it obvious whether the card-grid rebuild is still worth doing.
