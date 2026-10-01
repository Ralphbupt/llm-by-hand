# Writing a level

Level 1 (`content/1-foundations/matrices/`) is the reference. Copy its shape.

## Files

```
content/<step>/<slug>/
  lesson.en.mdx     the page (English is the source language)
  exercises.yaml    every question on the page
  demo.py           one self-contained script that prints every intermediate number
  export.py         optional: trains or records something and writes site/public/data/<slug>/*.json
```

The folder name is the URL: `content/2-theory/attention` → `/learn/attention/`.
Slugs carry no numbers, so levels can be added or reordered without breaking links.
Refer to other levels by number in prose ("in level 12"); numbers come from `level:` below.

## Frontmatter

```yaml
title: Self-attention
short: Attention     # optional: a shorter title (≤ 22 characters) for the sidebar and the map
level: "14"           # main line: "1".."21". Side branches: a letter + number ("N1", "U1", "D1")
order: 14             # global sort key; branch levels sit after their part's main line (e.g. 10.1, 21.1)
part: theory          # foundations | theory | engineering
branch: diffusion     # only for side branches: classic | internals | diffusion | training
question: How does one word "look at" the other words?
run: browser          # browser | local | mixed (browser, last part local) | cloud
checkpoint: some-id   # the exercise that marks the level as cleared (usually the last one)
mustSolve: [boss-x]   # boss levels only: in-browser boss parts that must be solved too (see "In-browser boss parts")
boss: "..."           # only for boss levels: the challenge, one or two sentences (`code` and $math$ render)
testOut: [id1, id2, checkpoint-id]   # optional: the questions of "Already know this? Test out" (see below)
recap:                # optional: the recap card at the end of the level (see below)
  can: ["…", "…", "…"]           # "You can now": three short lines
  keys: ["$C_{ij} = \\sum_k A_{ik} B_{kj}$", "`(n, k) @ (k, m)` → `(n, m)`"]   # "Keep in mind": formulas, shapes
  mistakes: ["…", "…"]           # "Common mistakes": two lines
```

## Level features (around the lesson)

- **Test out**: a quiet “Already know this? Test out” link under the question opens a panel with a few of the level’s
  own questions (the real quiz components, same ids). Solving all of them on your own, after opening the panel, clears the
  level with ★★★ and opens every Gate on the page; a shown answer means the test-out can’t count. It is stored in
  stats as `testOuts[slug]`. Without `testOut:` the default is the checkpoint plus up to two other non-Predict
  questions, each the last question of its `##` section, spread over the level. List ids that are solvable without
  the lab above them (they state their own numbers). The link hides once the level is cleared and in reading mode.
  A question whose `prompt` leans on the page (“the same example”, “the same model”) gets a `promptShort` that
  states every number again. The test-out and the warm-up both show `promptShort` when there is one.
  A boss level's `testOut` must include its checkpoint (and so the boss itself); `check_exercises.py` checks this.
- **Recap**: `recap:` renders one card at the end of the level: You can now / Keep in mind / Common mistakes. Every
  line may use `$KaTeX$` and backtick code. Keep it compact: three, three to five, and two lines. Level 1 has an example.
  It stays folded until the level is cleared (or in reading mode), so nobody reads the formulas before working them out.
  Opened before that, it shows only You can now. Still, no recap line may hold the answer of the checkpoint or of a
  testOut question: no solution line, no shape, no number answer. Say the rule in words instead (“dQ collects the
  rows of dS”). `check_exercises.py` flags these; a line checked by hand goes in its `RECAP_OK` list.
- **End card**: when the level is cleared, one card shows the stars, a primary “Next: level N · title” button (the
  same target as the Next link, see The path) and Share. A main level that opens side trips ends with a
  “Side trips after this level” box listing them, one line per branch.
- **Warm-up**: at the top of every level after level 1, two questions from the levels it builds on: number, shape
  and graded Predict only. A main level draws from the main levels before it and the side trips that opened before it;
  a side-trip level draws only from its prerequisites (the main line up to the level it opens after, and the earlier
  levels of its own branch). It picks, in order: missed and not solved since, then solved the longest ago, then never
  tried from the previous two main levels. Answers count like the mistake book (misses, solve times). Nothing to write
  per level, but every eligible question must make sense on its own, away from its page and lab. Keep a question out
  with `warmup: false` in exercises.yaml; `run: local`, and prompts that ask to run something on your computer, are
  left out automatically. An `after` note that points at the page (“in the lab”, “above”) is dropped in the warm-up.
  The warm-up starts folded to one line on phones, in reading mode, and when the learner jumped here (nothing tried
  on the main level just before).
- **Reading mode** (Settings): every Gate opens and every masked lab value shows; nothing is recorded and no stars are
  given. Labs only need `has()` from `@lib/progress`, which already respects it.

## Every level has

- one example small enough to compute on paper (2–3 words, 2 dimensions, 3 points)
- an interactive lab where the picture and the numbers move together
- at least one `Predict` (commit to a guess before seeing the answer)
- at least three `Blank`s (number or shape) and one `CodeBlank`
- `Gate`s, so the next part opens only after the question above is answered
- one `TryIt`, at least one `Deeper`, at least one `Stuck`
- a `demo.py` that prints every number the page asks about

## Components

```mdx
import Blank from '@quiz/Blank.astro'          // number or shape
import CodeBlank from '@quiz/CodeBlank.astro'  // numpy in the browser, graded by hidden tests
import Predict from '@quiz/Predict.astro'
import Gate from '@quiz/Gate.astro'            // <Gate requires="id">…</Gate>
import Deeper from '@text/Deeper.astro'        // <Deeper title="…">…</Deeper>
import Stuck from '@text/Stuck.astro'          // <Stuck q="…">…</Stuck>
import TryIt from '@text/TryIt.astro'
```

Interactive labs live in `site/src/components/viz/`: a `FooLab.svelte` plus a two-line `FooLab.astro`
wrapper that renders it with `client:visible`. Small math that must match numpy goes in `site/src/lib/num.ts`.

## Exercises

Types: `number` (with `tol`), `shape`, `code`, `predict`. Hints are matched in order; the first match wins:

```yaml
hints:
  - when: { equals: 4 }               # they typed 4
    say: "4 is C[0][0]. ..."
  - when: { shape: [2, 3] }
  - when: { error: "not aligned" }    # regex on the Python error
  - when: { testFailed: 1 }           # test 2 failed (counting from 0)
  - when: { any: true }               # fallback
```

Every question states the numbers it is about. Never write "with the default values in the lab": the
learner may have changed the lab, so write the numbers into the prompt (e.g. "A = [[1, 2, 3], [0, 1, 0]] …").
Labs with editable values get a "Reset to the starting numbers" button.

The hints are the most valuable part. Write one for each mistake a learner actually makes.

Every hint of a `code` exercise must be reachable: some wrong answer has to show it (`scripts/check_exercises.py`
checks this with `scripts/hint_reach.py`). A `testFailed: 1` hint is dead when the mistake it explains already fails
test 0: put the test that catches that mistake first. When the automatic search finds no wrong answer for a hint,
add the typical wrong fill it was written for as `wrong:` (a string or a list); the page never sees it.
A regex for shape errors must also match NumPy 2's matmul message: add `|matmul|core dimension`.

Every `code` exercise has a `solution`: the text that replaces `____`. The browser preamble gives you
`np` and `softmax(x, axis=-1)`. Every `code` exercise also has an `after:` (1–3 sentences on why the answer works),
shown once it is solved or revealed.

**Local boss parts** (a line the learner pastes from a script on their computer) have no `solution`, so there is no
“Show answer”. Instead:
- `paste: boss.py` names the script in the level folder. It defines `example_paste(id)`, the text a passing learner would
  paste; `check_exercises.py` runs the tests with it. `mustFail: [...]` lists easy fakes that must fail.
- The script prints one line: `<LEVEL> PASS <score> <code>`, where the code is the first 8 hex digits of
  `sha256("llm-by-hand/<LEVEL>/<score>")` (level 21 adds a `check` field to its JSON report instead). The page's tests
  recompute it. The code only shows that the line was pasted unchanged: anyone can read the script, so the page says that
  this part relies on the learner's honesty.
- Level 21's `check.py` hashes with the salt `llm-by-hand/20/…`, from when it was level 20. Keep the "20" on purpose:
  changing it to 21 would make every code that learners already earned invalid.
- Scripts print symptoms (what they measured), never the cause of a bug. Causes go in the hint ladder.
- Learners download the scripts from `/files/<level>/`. List them in `DOWNLOADS` in `scripts/sync_files.py` and run it
  after every edit; `check_exercises.py` fails while a served copy is out of date. Pages link the download and say
  “download it into a folder of its own and run it there”.
- Code between `# >>> course-only` and `# <<< course-only` (such as `example_paste` and the example scores) is
  stripped from the served copy. `check_exercises.py` fails if a download contains `example_paste` or a valid PASS line.

**In-browser boss parts** use `reference:` instead of `solution:`. `check_exercises.py` tests a `reference` like a
solution, but `site/src/lib/quiz.ts` strips it before the page is built, so the answer never reaches the HTML and there
is no “Show answer”. A boss checkpoint never has a `solution`, and neither does any other boss part (an id that
starts `boss-`, or a prompt that starts “The boss”). List every in-browser boss part that is not the checkpoint in the
frontmatter `mustSolve: [...]` (and in `testOut`): the level counts as cleared only when the checkpoint and every
`mustSolve` part are solved, so “Skip for now” can’t carry a learner past them (checked). Other templates on the level must not contain the lines of
a boss `reference` (checked). When a boss answer is a set of numbers (level 21 `boss-forward`), the page stores only a
hash of a code the script prints, never the numbers.

## Checks

```bash
.venv/bin/python scripts/check_exercises.py   # solutions pass their tests; every id on the page exists
.venv/bin/python scripts/check_demos.py       # every demo.py runs
.venv/bin/python scripts/check_tokens.py      # color tokens stay apart (Delta E ≥ 15)
.venv/bin/python scripts/hint_reach.py        # number hints: each `equals` is the value its `wrong:` sum gives
.venv/bin/python scripts/check_english.py     # plain English: blacklisted words, glossary senses
node scripts/check_overflow.mjs                # no page scrolls sideways (390px; code at 1280px); needs the dev server and Chrome
node scripts/check_overflow.mjs /learn/attention/ /math/   # only these pages
cd site && npm run check                       # type-check every component (0 errors required)
cd site && npm run test && npm run build
```

## Writing

- Short, plain sentences. Name things the way a learner would.
- Lead with the question, then the lab, then the explanation. Explanations are short; the deeper version goes in `Deeper`.
- Numbers on the page must be the numbers `demo.py` prints.
- Don't mention other courses, books, or sites. Write everything ourselves.
- Training text is synthetic, generated by our own rules (template stories, arithmetic, number words).
  Never use or download other people's prose or pretrained models.
- Well-known public benchmark datasets such as MNIST are fine (download them in the demo; don't commit them).

## The path

Foundations (main): 1 matrices · 2 gradient-descent · 3 neurons-and-loss · 4 activations · 5 mlp · 6 backprop (boss) ·
  7 optimization · 8 generalization · 9 numpy-to-pytorch · 10 probability
- branch Under the hood: U1 tensors-in-memory (after level 1) · U2 numbers-in-a-computer (after level 3) ·
  U3 autograd (after level 6) · U4 data-pipeline (after level 9) · U5 debugging (boss, after level 9) ·
  U6 attention-backward (after level 17). Orders 6.1–6.6.
- branch Classic networks (opens after level 10): N1 convolutions · N2 residuals-and-norms · N3 rnn · N4 lstm (boss) · N5 seq2seq-attention (boss) · N6 autoencoders · N7 encoder-decoder (after level 17). Orders 10.1–10.7.

Theory (main): 11 language-models · 12 tokenization · 13 vectors · 14 attention · 15 masks-and-heads · 16 transformer-parts ·
  17 full-model · 18 generation · 19 modern-llm · 20 inference-cost · 21 write-a-gpt (boss)
- branch Diffusion: D1 noise-and-denoise · D2 sampling-and-guidance (after Foundations) · D3 latents-and-dit (boss, after level 16)

Where side trips sit (one rule for the sidebar, the map and Prev/Next):
- Each branch level opens after one main level, its real prerequisite. The table is `OPENS_AFTER` in
  `site/src/lib/nav.ts`; a new branch level must be added there (a test fails otherwise). `order` only sorts
  levels inside a branch.
- The sidebar lists each branch level under the main level it opens after (“Under the hood · after 9”). The map draws
  a side-trip box next to that level (“opens after level 9”), with the branch notes (`BRANCH_NOTE` in
  `lib/levels.ts`) above the map and in the phone list. A branch page says “Side trip · best after level N”.
- Prev/Next on a main level follow the main line only. That level ends with “Side trips after this level”, one line
  per branch. A level in `RECOMMENDED` (`nav.ts`) is listed first there, with a half-line note: N7 comes first after
  level 17 (“the original design, with an encoder and a decoder”). In the sidebar, a branch with one level there shows that level directly (no fold).
- Inside a branch, Prev/Next walk the branch. A branch level whose Prev would cross to a level that opens after a
  different main level (the first level of a branch, or U6 and N7, which open after level 17 while U5 and N6 open
  earlier) leads back to the main level the learner came from (“Back to level N”: the last main level they opened;
  the opening level if unknown). The last level’s Next
  continues the main line with the main level after that one (“Continue: level N+1”), and so does Next when the next
  branch level opens after a main level the learner hasn’t reached yet. So Prev and Next never point at the same page.

After Theory come three planned parts, in this order (not written yet; each needs only Theory):
- Engineering: shared ground (workload ledger · accelerators · kernels and FlashAttention · talking between GPUs) →
  training systems (parallelism · ZeRO and memory · mixed precision · checkpoints and failures) and
  inference systems (KV cache · batching and scheduling · quantization · speculative decoding · distributed inference · device/edge/cloud)
- Training large models (methods): pretraining (data, objective, scale) · training stability · fine-tuning and LoRA ·
  instruction tuning and preference alignment · evaluation
- Applications: prompts and in-context learning · structured output and tool calls · retrieval · RAG · the agent loop ·
  the harness · evaluating and securing an agent (boss). Labs replay recorded model traces by default; an optional mode
  lets the reader paste their own API key to call a real model.

## House style (copy and layout)

- **American English** (neighbor, color, normalize). Second person ("you"), present tense, short sentences.
- **No filler**: no "Note that", "Simply", "Let's", "Basically", exclamation marks, or asides set off by em dashes.
- **Quotes and apostrophes**: typographic everywhere a reader sees text, including frontmatter `question:` and every
  string in `exercises.yaml`: “like this”, it’s. (Code and code-like values stay straight.)
- **Headings**: sentence case. Main sections are numbered: `## 1. A weighted average`. Sub-headings `###` unnumbered.
- **Names**: Transformer, PyTorch, NumPy (in prose; `numpy` only in code), softmax, ReLU, GELU, LayerNorm, RMSNorm,
  LSTM, GRU, BPE, KV cache, GPT. Refer to levels as “level 12” (lowercase mid-sentence).
- **Math**: formulas in KaTeX (`$…$`, display `$$` on its own lines); code, shapes and variable names in backticks:
  `X @ W`, `(B, L, 64)`. Numbers: use the same rounding as `demo.py` prints.
- **Lists of three or more parallel steps** become a numbered or bulleted list, not a long sentence.
- **Every number question is hand-computable** in under a minute with pen and paper: small integers, simple
  fractions, one or two multiplications. No exp, log, sqrt, sigmoid or softmax values that need a calculator, unless
  the prompt gives the needed values (“use e¹ ≈ 2.72, e⁰ = 1”) or they are trivial (σ(0) = 0.5, ln 1 = 0, e⁰ = 1).
  Otherwise, ask something else: the sign, which is bigger, a shape, a count, an integer step, or a Predict with options.
  Tolerances are generous enough for hand rounding (e.g. two decimals → tol 0.01).
- **Exercise prompts** end with a question mark or a clear instruction, and state their own numbers.
  Hints say what went wrong and where to look, in one or two sentences.
- **Layout**: every lab works at 390 px wide with no page-level horizontal scroll (wide tables scroll inside their own box);
  no two Gates back to back without at least a sentence between them; one idea per paragraph.

## Visual style (labs)

- **Color has a meaning, the same on every page**: `--accent` (blue) = the learner's thing (their point, their
  weights, the current step); `--ok` (green) = the target, the correct answer, the minimum; `--warn` (orange) =
  errors, danger, divergence, masked “?”; `--dim` = context (grids, axes, inactive). Never color by decoration.
- **One lab = one idea**, laid out as: a short title line, the picture, the controls, then a one-line live readout
  (“cat looks at dog with weight 0.19”). Controls sit under the picture, grouped, with labels that say what they do.
- **Numbers**: monospace, tabular, aligned right in tables, the same rounding as `demo.py`. Every axis has a label
  and units; every color has a legend or an in-picture label.
- **Theme**: canvas or WebGL labs that read colors must redraw on `onThemeChange()` from `@lib/settings`
  (it covers the system switch and the reader's Light/Dark choice); check `reducedMotion()` before animating.
- **Motion**: animations that run without the learner (training loops, play buttons) check `reducedMotion()`.
- **Motion**: changes animate briefly (150–250 ms) so the eye can follow what moved; nothing loops forever;
  respect `prefers-reduced-motion`. Hover and tap do the same thing.
- **3D** (site/src/components/viz3d/): use it when the third dimension carries meaning — a surface over two inputs
  (loss surfaces, a network’s output over the input plane), points or vectors with three numbers, tensors with three
  axes (batch × length × features, heads, channels), or a 2D cloud changing over time (time as the third axis).
  Keep a 2D view next to it or behind a “3D / Map” switch when exact reading matters. See “3D” below for the API.
- **Phone**: at 390 px every label is at least 11 px, nothing overlaps, wide tables scroll inside their own box.

### 3D

Four components, one shared core (`lib/three/stage.ts` camera, input, context budget; `kit.ts` look;
`labels.ts` HTML labels; `geom.ts` pure helpers, unit-tested). Labs never import `three` themselves.

- `Surface3D` — z = f(x, y): `f, xRange, yRange`, `zTransform` (e.g. `Math.log1p`), `path` / `paths` (each with a
  `color` tone and a `label` written at its head, which is the legend), `point` (accent), `best` (ok), `start`, `step`
  (an arrow), `dots`, `zRange`, `rebuildKey`, `onpick`. Colors: `ramp="seq"` (sizes, losses: card → warn, never
  blue), `"div"` (signed values: `--neg` ← card → `--pos`, 0 in the middle), `"prob"` (`--cat-3` ← → `--cat-1`), or
  `tones={{low, high}}`; the default `auto` picks `div` when the heights have both signs. The height caption must be
  true: with `zTransform={Math.log1p}` it says “log(1 + loss)” automatically; `zCaption` overrides it. Captions
  under the view then say “height is log(1 + loss)”, not “height is the loss”.
- `Points3D` — `points` (`p: [x, y, z]`, `tone`, `label`, `size`), `arrows`, `trails` (a tone other than dim/fg is
  drawn thick: the one to follow), `range`, `axes`, `highlight`, `gridStep` (round data steps, so integers sit on
  grid lines), `floorAt` (default 0, or the bottom when the data starts there, e.g. t = 0), `dropLines` (on for arrows).
- `Tensors3D` — `tensors` (blocks and operator strings), each block with `shape`, `name`/`title`, `axes`,
  `highlight` / `ghost` ranges, `values` (0..1 shading). Short row-axis names stand upright (“L↓”).
- All three take `ariaLabel`, `view={{azimuth, elevation}}` (degrees; only when the default angle hides the point),
  and `fallback` — a snippet shown when the browser has no WebGL (default: a note saying what the view shows).
  Test fallbacks with `?no3d` in the URL (or localStorage `llmbh-no3d = 1`).

- `Net3D` — a whole network from one spec (`lib/three/net.ts`, type `Net3DSpec`; builders in `netSpecs.ts` and
  `netLessons.ts`, all numbers computed there and checked in `net.test.ts`). `layout`: `row`, `hourglass` (one cell
  size for every block, so size = count), `unrolled` / `encdec` (nodes give `at`), `stack` (with a residual rail).
  Nodes: `neurons` (discs; `along: 'x'` for a row of positions, `names` for one word per disc), `tensor` (cells:
  columns → right, rows ↓, channels go back; `draw` caps the drawn shape), `op` (“+”), `block`. Edges: `dense` with
  `weights[i][j]` (line color = sign, width = |w|, the largest 512 kept, 128 on touch), `conv` with `window` (a funnel
  from the window to one output cell), `recurrent` / `copy` (one line), `residual` (the rail), `attention` with weights
  (arcs toward the reader; a step's `focus` lights one row). `shared` / `group` give one cat color to a reused cell.
  `steps` (forward: `values`, accent; backward: `grads`, `--grad`: halos grow with |∂L/∂a|, lines switch to |∂L/∂w|)
  play with flowing dots once per step (none with reduced motion). `Net2D` draws the same spec as SVG (the Flat view,
  the no-WebGL fallback). Don't place them bare: use `<ArchLab which="…" />` (or `NetLab` for a new one), which adds
  the Flat / 3D switch, step buttons, the step text as the readout, a focusable layer list and the selected layer's
  panel (shape, parameters, numbers; `hide={{ params: [ids] }}` keeps counts as “?” until answered). One placement =
  one idea: a title saying it, and a caption saying what to look at. At most 10 draw calls per net; phones turn it so
  data flows down (long nets get a taller view there). NetLab starts in Flat (`initialView`); ArchLab picks 3D only
  where size and depth are the information (conv, autoencoder, full). The legend is built from the spec (signed
  weights, shared weights, forward, backward, attention only when drawn). The layer list sits after the readout,
  folded when it has more than 5 rows, so the step buttons stay right under the picture.

Rules the core enforces (don't fight them):
- **Camera**: one three-quarter view from the front right (azimuth/elevation: surfaces 34°/28°, points 34°/22°,
  tensors 20°/18°, so a block’s depth always shows), auto-fitted to the content and its labels. It refits only when the content’s size changes by
  more than 15% (never on highlight changes), keeps the reader’s angle, and eases 250 ms (instantly with reduced
  motion; damping is off then too). No panning; you can’t turn under a surface. “Reset view” goes back to the default.
- **Look**: colors only from tokens (`tone` = `accent | ok | warn | fg | dim | pos | neg | grad | cat-1…5`). One
  light setup, matte (no shine): a face pointing up shows the token color exactly, sides are darker. Tensor cells need
  no light: front face = the legend color, top lighter, sides darker, edges drawn ~1 px. Solid by default; plain cells
  turn see-through only when a highlight sits behind the front slice; broadcast copies are faint outlines. Floors are
  a flat card with a grid at round tick values; surfaces also show their contour lines there (like the 2D map).
  Lines that carry data are thick in screen pixels (paths 3 px, the followed trail 2.75 px, axes 1.25 px); grids are hairlines.
- **Labels** are HTML over the canvas (`stage.labels.set(set, key, text, at, { role, tone, anchor, vertical })`,
  between `begin(set)` / `end(set)`): roles `tick` (0.68rem, dim), `axis` (0.74rem, dim), `name` (0.8rem),
  `op` (1.1rem), `callout` (0.75rem, on a plate). They follow the text-size setting, have a halo in the page
  background, never rotate or mirror, stay inside the view, hide the lower-priority one of two that overlap, and fade
  when a surface hides their anchor (a tick hides). A label that is the only name of a mark (a path's name) passes
  `keep: true`: it steps up to 3 rows away instead of hiding. Surface and point axes have round-number ticks and a caption.
- **Input**: the wheel scrolls the page until the view is clicked (or Ctrl/⌘ is held); on touch one finger scrolls
  the page until the view is tapped (then “Done” gives it back), two fingers always turn and pinch-zoom. When focused:
  arrow keys turn (Shift: more), + / − zoom, 0 resets, Esc releases. The hint and Reset sit on one line under the view.
- **Cost**: render on demand only, nothing drawn offscreen, pixel ratio ≤ 2 (1.5 on touch devices). A page keeps at
  most 4 WebGL contexts (3 on touch): the least recently seen offscreen view gives its context back and makes a new
  one when it scrolls back; switching a view off frees its context at once. Tensor blocks are one instanced draw call
  each (a 28×28 picture is one call, not 1,568). Rebuilds free their geometries and materials (`clearGroup`).

## Hints, questions and glossary

- **Hint ladders**: a hint's `say` may be a list. The 1st wrong try shows the first entry, the 2nd the next, and so on:
  direction → half a step → a nudge. Never the full answer: that is what “Show answer” is for (it costs a star).
  `check_exercises.py` fails when one ladder (all its rungs together) holds 80% or more of a code solution's tokens.
  A number question's fallback ladder says which rule to use, then gives the first intermediate number, never the result.
- **`equals` hints on number questions** show only when the learner types exactly that value, so the value must be what
  the mistake in the hint really gives. Write the mistake as a sum in `wrong:` (for example `wrong: "8*1024*1024/512"`;
  ×, −, √, ln and 10⁴ work too). `python scripts/hint_reach.py` recomputes every `wrong:` and fails on a mismatch, or on an
  `equals` value that is also accepted as the right answer. `--unverified` lists the hints with no `wrong:` whose value
  does not appear in the hint text. `wrong:` is stripped before the page gets the hints.
  ```yaml
  - when: { any: true }
    say: ["Which row of A, which column of B?", "Row 0 of A is [1, 2, 3]; read column 1 of B top to bottom.", "Multiply pairwise: 1×0 + 2×1 + …"]
  ```
- **Two kinds of Predict**: a concept question with one right option gets `answer: <index>` (graded, wrong picks go to the
  mistake book, hints may match `{ equals: <index> }`). A real “guess before you see it” has no `answer` (ungraded).
- **Teach before you ask**: every fact a question needs appears in the page *above* it (not only in a hint, a closed Deeper,
  or a later section). Every numpy function a code blank needs (`np.triu`, `reshape`, `transpose`…) is shown once before.
- **Glossary**: if a glossary word means something else on a page (“shape” as a drawn shape, the encoder of an autoencoder),
  list it in frontmatter: `glossarySkip: [shape, encoder, decoder]`.
  A term that means one thing on one page and something else everywhere (“code” in autoencoders) gets `only: [slug]`
  in content/glossary.yaml instead. Every word written in **bold** as a new term needs a glossary card.
- **Local work**: any level with `run: local` or `run: mixed` links to the setup page `/setup/` near its top.

## Notation (the same on every page)

| Thing | Write it as |
|---|---|
| vectors | rows. A layer is `X @ W + b` with `W` of shape `(d_in, d_out)`; this includes RNN/LSTM cells: `x_t @ W_x + h_{t-1} @ W_h + b` |
| sizes | batch `B`, length `L`, vocabulary `V`, model width `d_model`, per-head width `d_k`, heads `h`, FFN width `d_ff` |
| indices | positions, rows, columns, tokens all count from 0 |
| spread | standard deviation, “std” (σ); say once that std = √variance |
| logarithm | natural log, written `ln` in prose and math (`np.log` in code); say once that `np.log` is ln |
| masks | `True` (or 1) = blocked; blocked scores become −∞ before softmax |
| loss words | “error” = prediction − target only in level 2; the gradient of the loss w.r.t. z is written `dz` (∂L/∂z) |
| optimizers | momentum’s velocity `u`; Adam’s moments `m`, `v` with `beta1`, `beta2` |
| diffusion | `α_t` = kept in this step, `ᾱ_t` (“alpha-bar”, code `ab`) = kept so far; signal × √ᾱ_t, noise × √(1−ᾱ_t) |
| patches | “patch size p” = each patch is p × p pixels |
| epoch | one pass over the whole training set (define it where first used) |
| subscripts | no bare `_` in prose, questions or lab readouts: a name with `_` is code (`d_k`, `W_Q`, `x_hat`), or use Unicode subscripts where they exist (pᵢ, hₜ₋₁, x₁). One notation per recap cell |
| prime | `′` (U+2032), not the apostrophe: d′, H′ |
| course units | **Part** = Foundations / Theory / …; **Level** = one page (“level 12”); **section** = a numbered `##` part of a level (“section 3”). Never “lesson”, “chapter”, “step” or “stage” for these. |


## Plain English (many readers learn English as a second language)

1. A metaphor always comes with the plain statement in the same sentence, or is replaced by it.
2. No phrasal verbs (verb + up/out/off/in/apart/through/down): take in → use, work out → compute, blow up → grow very large,
   fall apart → fail, run out → is not enough, rule out → give zero probability to, level off → stop falling, tell apart → distinguish.
3. Common words only in their common sense: not catch (= problem), volume, effectively, floor (= lower limit), toy (= small),
   share (= fraction), die (= dice), twist, room (= space for).
4. No preposition at the end of a sentence; no passive + relative-clause knots (“what this word offers to be found by” →
   “what other words compare against”).
5. At most one colon per sentence; split “A: B, C: D” into two sentences.
6. A pronoun (it, this, that) points only to a noun in the previous sentence; otherwise repeat the noun.
7. One word, one meaning, site-wide: `dz` is never “error”; “memory” as a term means the encoder output (in the hardware sense, write “computer memory” or “GPU memory” the first time on a page); “weight” or “parameter”,
   never “knob”.
8. No stacked noun strings: “the answer-only loss” → “the loss on the answer digits only”.
9. Foreign or cultural examples get a gloss: “die Katze schläft” (German for “the cat sleeps”).
`scripts/check_english.py` flags words from the blacklist in lessons and exercises; fix every flag or justify it.
It also lists the line that gets the glossary card for every term with a `senses:` field in content/glossary.yaml
(words with an everyday meaning too, like shape, seed or bias). When that line is new or changed, read it: if the card
gives the right meaning, record it with `--accept-senses`; if not, reword the line or add the term to `glossarySkip`.


## Color tokens (global.css; every lab uses these, never raw colors)

| Token | Means | Never use it for |
|---|---|---|
| `--accent` | the learner's thing: their answer, their point, the current step, the selected item | categories, decoration |
| `--ok` | correct, the target, the minimum, cleared | weights, ordinary series |
| `--warn` | an error, divergence, a masked “?”, boss levels on the map | negative numbers, a class, gradients, help or hints, a shadow, a two-star score, emphasis |
| `--pos` / `--neg` | the sign of a value (diverging data: weights, scores, differences) | anything without a sign |
| `--grad` | gradients and anything flowing backward | forward values |
| `--cat-1` … `--cat-5` | categories that are just different (words, classes, curves, heads, a shared-weight group). Ochre, olive, rose, slate, sand: hues the meaning tokens don't use | meaning “good/bad” |
| `--dim` / `--line` | context (axes, grids) / hairlines | text you must read (use `--fg` or `--dim`) |
| `--field` | borders of things you can type into or edit (≥ 3:1) | decoration |
| `--highlight` | hover / linked-cell background | text color |
| `--on-solid` | text on a solid `--accent`/`--ok`/`--warn` fill | — |
Captions never say “orange” or “red”: label the thing in the picture instead.
Surfaces of sizes and losses use the neutral `seq` ramp (card → gray); color on top of them is the learner's point,
the minimum, or an error. `scripts/check_tokens.py` keeps every pair of the tokens above (accent … cat-5) at
Delta E ≥ 15 in both themes and ≥ 3:1 against the background, and each of them at Delta E ≥ 15 from the neutral
ink (`--fg`, `--dim`, `--line`), so a series never looks like a grid line; run it after changing a color.

## Lab chrome: LabFrame

Every lab is wrapped in `site/src/components/viz/LabFrame.svelte`:

```svelte
<LabFrame title="One line: what this lab shows" hint="One line: what to do" views={[{id:'map',label:'Map'},{id:'3d',label:'3D'}]}
          bind:view onreset={reset} resetDisabled={!changed}>
  …the picture…
  {#snippet controls()}<button class="lab-btn primary">Train</button> <button class="lab-btn">Step</button>{/snippet}
  {#snippet readout()}cat looks at dog with weight 0.19{/snippet}
  {#snippet legend()}…{/snippet}
</LabFrame>
```
Order is fixed: title → picture → controls (primary, secondary, then “Reset to the starting numbers” at the end) →
one live readout line → (optional `after`: a list or panel) → legend. Buttons use the global classes `lab-btn`,
`lab-btn primary`, `lab-btn ghost`; a toggle sets `aria-pressed` and gets the shared “on” look (accent text and
outline on a `--highlight` wash; in a segmented control just the text and the wash). Solid accent is only for the
primary action, never for a selected choice or view. A 3D-only lab can
`bind:has3d` and draw a flat picture when there is no WebGL (Embed3DLab draws the plane through the two arrows).
A view switch puts the exact-reading view first (Map before 3D). Wide pictures scroll inside the frame (a swipe cue
appears by itself; scroll boxes inside a lab get the same right-edge fade). Reference migrations: MatmulLab, AttentionLab.

## Text size and input

- Lab text is sized in rem/em, never px (min 0.72rem), so the Settings text size reaches it.
- SVG charts drawn in viewBox units use the `readable` action (`import { readable } from '@lib/readable'`;
  `<svg use:readable …>`): labels never fall below ~11.5px on screen and follow the text-size setting.
- 3D labels are HTML in rem (see “3D”), at least 11px on screen, so the text size reaches them too.
- Everything you can hover also works with tap and keyboard focus (say “point at or tap”, not “hover”).
  Draggable points: a ~44px invisible grab area, `role="slider"`, arrow keys move one step (Shift: two).
- 3D views never steal page scroll: the shared stage zooms only after a click/tap inside the view (or Ctrl/⌘ +
  wheel); one finger scrolls the page until the view is active; two fingers always turn/zoom; arrow keys turn a
  focused view. Don't override this.
- Touch targets on phones are ≥ 40px tall. Never move keyboard focus on mount.
