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

```bash
hugo new content posts/my-post-title.md
```

New posts are created with `draft: true` — flip it to `false` (or drop the line) when ready to publish. Anything pushed to `main` with `draft: false` deploys automatically via the `Deploy Hugo site to GitHub Pages` workflow.

## Comments

Not enabled yet. LoveIt has built-in giscus support (GitHub Discussions-based) — see the setup steps and config in `hugo.toml` under `params.page.comment.giscus`.

## Search

Client-side search (Fuse.js) is already enabled via `params.search` — no external service needed.
