# LLM by Hand

Learn how large language models work by computing every number yourself.

Each level is one question. You answer it with an example small enough to check on paper,
in an interactive page where the pictures and the numbers move together, and you have to get it right to move on.

## The path

37 levels: a main line of 21 and three side trips.

1. **Foundations**: how numbers learn (levels 1–10)
2. **Theory**: what the model computes (levels 11–21)
3. **Engineering**: making it fast and cheap (coming later)

Side trips open along the way:

- **Under the hood** (U1–U6): tensors in memory, numbers in a computer, your own autograd, feeding data, debugging,
  and the backward pass of attention. U1–U5 open during Foundations, U6 after level 17.
- **Classic networks** (N1–N7): convolutions, residuals, recurrent networks, LSTMs, the first attention,
  autoencoders, and the 2017 encoder–decoder Transformer. They open after level 10; N7 opens after level 17.
- **Diffusion** (D1–D3): generating from noise. D1 and D2 open after Foundations; D3 builds on levels 14–16.

## Run it locally

```bash
cd site
npm install
npm run dev          # http://localhost:4321
npm run test         # unit tests for the in-browser math
```

Every level also has a standalone `demo.py` that prints each intermediate number:

```bash
python content/1-foundations/matrices/demo.py
.venv/bin/python scripts/check_demos.py      # run all of them
```

The scripts in `scripts/` need numpy and PyTorch, so run them with the project's `.venv/bin/python`.
See AUTHORING.md for every check.

## Layout

```
content/<step>/<level>/
  lesson.en.mdx     the page
  exercises.yaml    questions, answers, and hints for common mistakes
  demo.py           one runnable script for the level
site/               the Astro site that renders content/
  src/config/site.ts  the public URL, name and analytics ID (one place)
  public/           static files, Cloudflare _headers
scripts/            checks
archive/            old design previews (not built)
```

The site also publishes `/llms.txt`, `/llms-full.txt` and every level as Markdown (`/learn/<slug>.md`), generated
from the lessons at build time without answers. `scripts/check_public_text.py` checks that.
To publish the site, see `site/DEPLOY.md`.

## License

Code: MIT (`LICENSE`). Lesson text, exercises, figures and videos: CC BY-SA 4.0 (`LICENSE-CONTENT`).
