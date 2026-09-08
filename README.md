# dwooods.github.io

Personal site/blog built with [Hugo](https://gohugo.io/) and the [PaperMod](https://github.com/adityatelange/hugo-PaperMod) theme, deployed to GitHub Pages via GitHub Actions.

Live at: https://dwooods.github.io/

## Local development

Requires Hugo **extended**, v0.146.0+.

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

Not enabled yet. See the TODO in `layouts/_partials/comments.html` for how to wire up giscus when ready.
