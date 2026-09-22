# dwooods.github.io

Personal site/blog built with [Hugo](https://gohugo.io/) and the [LoveIt](https://github.com/dillonzq/LoveIt) theme, deployed to GitHub Pages via GitHub Actions.

Live at: https://dwooods.github.io/

## Local development

Requires Hugo **extended**, v0.128.0+.

```bash
git clone --recurse-submodules https://github.com/dwooods/dwooods.github.io.git
cd dwooods.github.io
hugo server --buildDrafts
```

If you already cloned without `--recurse-submodules`:

```bash
git submodule update --init --recursive
```

## Adding a post

Posts live in `content/posts/<slug>.md`. Either scaffold one with Hugo:

```bash
hugo new content posts/my-post-title.md
```

or just create the file directly with this site's front matter (which is how every post here has been written so far):

```yaml
---
title: "Post title"
date: 2026-09-21
draft: true
tags: ["ai", "raspberry-pi"]
description: "One or two sentences for the meta description — keep it under ~160 characters."
summary: "The hook LoveIt shows on the homepage and list pages in place of the auto-excerpt. Make it sell the story."
featuredImage: "/images/hero.png"
featuredImagePreview: "/images/hero.png"
---
```

Images go in `static/images/` and are referenced as `/images/<filename>`.

New posts start as `draft: true`. Preview locally with `hugo server --buildDrafts` (the `-D` flag is required or drafts are hidden) and check the post at `http://localhost:1313/posts/<slug>/` before flipping `draft` to `false`. Anything pushed to `main` with `draft: false` deploys automatically via the `Deploy Hugo site to GitHub Pages` workflow.

## Comments

Not enabled yet. LoveIt has built-in giscus support (GitHub Discussions-based) — see the setup steps and config in `hugo.toml` under `params.page.comment.giscus`.

## Search

Client-side search (Fuse.js) is already enabled via `params.search` — no external service needed.
