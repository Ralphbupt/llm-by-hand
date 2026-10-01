<script lang="ts">
  /**
   * Cut a 28×28 digit into p×p patches. Each patch, read left to right and top to bottom,
   * becomes one token: a row of p·p numbers. Hover a patch or a token row to link them.
   * Below: the shape of everything inside a DiT for the chosen patch size.
   */
  import { onMount } from 'svelte'
  import { themeColors } from '@lib/diffusion'
  import { has, subscribe } from '@lib/progress'
  import { onThemeChange, reducedMotion } from '@lib/settings'
  import Tensors3D from '../viz3d/Tensors3D.svelte'
  import LabFrame from './LabFrame.svelte'

  const SIZES = [2, 4, 7, 14]
  const D = 96
  let data = $state<{ labels: number[]; digits: number[][] } | null>(null)
  let error = $state<string | null>(null)
  let pick = $state(0)
  let p = $state(7)
  let hover = $state<number | null>(null)
  // a patch chosen by click, tap or arrow keys stays chosen; hovering only previews another one
  let sel = $state<number | null>(null)
  const cur = $derived(hover ?? sel)
  let pic: HTMLCanvasElement, toks: HTMLCanvasElement
  // the page asks for these two below the lab: keep them hidden until answered
  let solvedShape = $state(false)
  let solvedScores = $state(false)

  const per = $derived(28 / p)
  const n = $derived(per * per)
  const img = $derived(data ? data.digits[pick] : null)

  function tokensOf(a: number[], p: number): number[][] {
    const out: number[][] = []
    for (let by = 0; by < 28 / p; by++)
      for (let bx = 0; bx < 28 / p; bx++) {
        const row: number[] = []
        for (let y = 0; y < p; y++) for (let x = 0; x < p; x++) row.push(a[(by * p + y) * 28 + bx * p + x])
        out.push(row)
      }
    return out
  }

  function size(cv: HTMLCanvasElement, w: number, h: number) {
    const dpr = window.devicePixelRatio || 1
    cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr)
    cv.style.height = `${h}px`
    const ctx = cv.getContext('2d')!
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    return ctx
  }

  function draw() {
    if (!img || !pic || !toks) return
    const c = themeColors(pic)
    // the picture
    const W = pic.clientWidth || 280, cell = W / 28
    const g = size(pic, W, W)
    g.fillStyle = c.bg; g.fillRect(0, 0, W, W)
    g.fillStyle = c.fg
    for (let i = 0; i < 784; i++) {
      if (!img[i]) continue
      g.globalAlpha = img[i] / 255
      g.fillRect((i % 28) * cell, Math.floor(i / 28) * cell, cell + 0.5, cell + 0.5)
    }
    g.globalAlpha = 1
    g.strokeStyle = c.dim; g.lineWidth = 1; g.globalAlpha = 0.6
    for (let k = 1; k < per; k++) {
      g.beginPath(); g.moveTo(k * p * cell, 0); g.lineTo(k * p * cell, W); g.moveTo(0, k * p * cell); g.lineTo(W, k * p * cell); g.stroke()
    }
    g.globalAlpha = 1
    if (cur !== null) {
      g.strokeStyle = c.accent; g.lineWidth = 3
      g.strokeRect((cur % per) * p * cell + 1.5, Math.floor(cur / per) * p * cell + 1.5, p * cell - 3, p * cell - 3)
    }
    // the tokens: n rows × p·p columns
    const TW = toks.clientWidth || 280
    const cw = TW / (p * p)
    const rh = Math.max(2, Math.min(18, 300 / n))
    const t = size(toks, TW, rh * n)
    t.fillStyle = c.bg; t.fillRect(0, 0, TW, rh * n)
    tokensOf(img, p).forEach((row, r) => {
      row.forEach((v, k) => {
        if (!v) return
        t.globalAlpha = v / 255; t.fillStyle = c.fg
        t.fillRect(k * cw, r * rh, cw + 0.5, rh + 0.5)
      })
    })
    t.globalAlpha = 1
    if (cur !== null) { t.strokeStyle = c.accent; t.lineWidth = 2; t.strokeRect(1, cur * rh + 1, TW - 2, Math.max(rh - 2, 2)) }
  }

  function patchAt(e: PointerEvent) {
    const r = pic.getBoundingClientRect()
    const bx = Math.floor(((e.clientX - r.left) / r.width) * per), by = Math.floor(((e.clientY - r.top) / r.height) * per)
    return bx >= 0 && by >= 0 && bx < per && by < per ? by * per + bx : null
  }
  function rowAt(e: PointerEvent) {
    const r = toks.getBoundingClientRect()
    const row = Math.floor(((e.clientY - r.top) / r.height) * n)
    return row >= 0 && row < n ? row : null
  }
  // mouse hover previews; a click or tap chooses (touch has no hover)
  const onPic = (e: PointerEvent) => { if (e.pointerType === 'mouse') hover = patchAt(e) }
  const onTok = (e: PointerEvent) => { if (e.pointerType === 'mouse') hover = rowAt(e) }
  const pickPic = (e: PointerEvent) => { sel = patchAt(e); hover = null }
  const pickTok = (e: PointerEvent) => { sel = rowAt(e); hover = null }
  function keys(e: KeyboardEvent) {
    const k = sel ?? 0, bx = k % per, by = Math.floor(k / per)
    const move: Record<string, [number, number]> = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }
    const d = move[e.key]
    if (!d) return
    e.preventDefault()
    const nx = Math.min(per - 1, Math.max(0, bx + d[0])), ny = Math.min(per - 1, Math.max(0, by + d[1]))
    sel = ny * per + nx
  }
  function setP(s: number) { p = s; hover = null; sel = null; cancelAnimationFrame(raf); cutT = 2 }
  function resetAll() { p = 7; pick = 0; hover = null; sel = null; view = 'flat'; cancelAnimationFrame(raf); cutT = 2 }

  $effect(() => { void pick; void p; void cur; void data; draw() })
  onMount(() => {
    const sync = () => { solvedShape = has('dit-shape'); solvedScores = has('scores-49') }
    sync()
    const off = subscribe(sync)
    fetch('/data/latents-and-dit/digits.json').then((r) => r.json()).then((d) => (data = d)).catch((e) => (error = String(e)))
    const ro = new ResizeObserver(draw)
    ro.observe(pic)
    const offTheme = onThemeChange(draw)
    return () => { off(); ro.disconnect(); offTheme(); cancelAnimationFrame(raf) }
  })

  // --- 3D: the picture → a stack of patches, one slab per token (each slab is then flattened into one row) ---
  let view = $state('flat')
  // pixel brightness 0..1, as the picture (28, 28) and as the stack of patches (n, p, p)
  const pix2d = $derived(img ? Array.from({ length: 28 }, (_, r) => Array.from({ length: 28 }, (_, c) => img[r * 28 + c] / 255)) : undefined)
  const stack = $derived(img ? tokensOf(img, p).map((row) => Array.from({ length: p }, (_, y) => row.slice(y * p, y * p + p).map((v) => v / 255))) : undefined)
  // with nothing hovered, show the patch with the most ink (a blank corner patch says nothing)
  const inkiest = $derived(img ? tokensOf(img, p).reduce((best, row, k, all) => (row.reduce((a, b) => a + b, 0) > all[best].reduce((a, b) => a + b, 0) ? k : best), 0) : 0)
  // the cut, played as an animation: 0 → 1 the patches fly into the stack, 1 → 2 each slab flattens into a row
  // (the rows step only when the token matrix is not too tall to see: 49 tokens or fewer)
  let cutT = $state(2)
  const withRows = $derived(n <= 49)
  const cutEnd = $derived(withRows ? 2 : 1)
  let raf = 0
  function playCut() {
    cancelAnimationFrame(raf)
    if (reducedMotion()) { cutT = cutEnd; return }
    const t0 = performance.now(), dur = 1700 * cutEnd
    const tick = (now: number) => {
      cutT = Math.min(cutEnd, ((now - t0) / dur) * cutEnd)
      if (cutT < cutEnd) raf = requestAnimationFrame(tick)
    }
    cutT = 0
    raf = requestAnimationFrame(tick)
  }
  // patch picking in 3D (no canvas to point at): step through the patches
  const shown3d = $derived(cur ?? inkiest)
  const stepPatch = (d: number) => { sel = (shown3d + d + n) % n; hover = null }
  const tensors3d = $derived.by(() => {
    const h = shown3d
    const by = Math.floor(h / per), bx = h % per
    const out: any[] = [
      { shape: [28, 28], axes: ['row', 'col'], title: 'picture (28, 28)', values: pix2d,
        highlight: [{ from: [0, by * p, bx * p], to: [0, by * p + p - 1, bx * p + p - 1], tone: 'accent' }] },
      '→',
      { shape: [n, p, p], axes: ['token', 'row', 'col'], title: `${n} patches (${n}, ${p}, ${p})`, values: stack,
        highlight: [{ from: [h, 0, 0], to: [h, p - 1, p - 1], tone: 'accent' }], hidden: cutT < 1 },
    ]
    if (withRows)
      out.push('→', { shape: [n, p * p], axes: ['token', 'number'], title: `tokens (${n}, ${p * p})`,
        values: stack?.map((slab) => slab.flat()),
        highlight: [{ from: [0, h, 0], to: [0, h, p * p - 1], tone: 'accent' }], hidden: cutT < 2 })
    return out
  })
  // where each moving cell comes from: a stack cell (k, y, x) is picture pixel (row, col) of patch k;
  // a token cell (0, k, m) is stack cell (k, m ÷ p, m mod p)
  const explode = $derived.by(() => {
    if (cutT <= 0 || cutT >= cutEnd) return null
    const P = p, PER = per
    if (cutT < 1) return { from: 0, to: 1, t: cutT, map: (k: number, y: number, x: number) => [0, Math.floor(k / PER) * P + y, (k % PER) * P + x] as [number, number, number] }
    return { from: 1, to: 2, t: cutT - 1, map: (_: number, k: number, m: number) => [k, Math.floor(m / P), m % P] as [number, number, number] }
  })

  const rows = $derived([
    ['picture', '(28, 28)', '784 numbers'],
    ['cut into patches', `(${n}, ${p * p})`, `${n} tokens of ${p * p} numbers`],
    ['@ W_in', `(${p * p}, ${D}) → ${solvedShape ? `(${n}, ${D})` : '(?, ?)'}`, 'each patch becomes a token vector'],
    ['+ position', solvedShape ? `(${n}, ${D})` : '(?, ?)', 'which patch is where'],
    ['+ step t and label', `(${D}) added to every token`, 'like D1–D2, but as a vector'],
    ['Transformer blocks', solvedShape ? `(${n}, ${D}) → (${n}, ${D})` : '(?, ?) → (?, ?)',
      `attention scores per head: ${solvedScores ? `${n} × ${n} = ${(n * n).toLocaleString()}` : '? (answer the question below)'}`],
    ['@ W_out', `(${D}, ${p * p}) → (${n}, ${p * p})`, 'a noise guess for every patch'],
    ['put patches back', '(28, 28)', 'the noise guess for the picture'],
  ])
</script>

<LabFrame
  title="Cut a picture into patches: each patch becomes one token"
  hint="Pick a patch size. Point at, tap or arrow-key through the patches to see which token each one becomes."
  views={[{ id: 'flat', label: 'Picture and tokens' }, { id: '3d', label: '3D: the stack of patches' }]}
  bind:view
  onreset={resetAll}
  resetDisabled={p === 7 && pick === 0 && sel === null && view === 'flat'}
>
  {#if error}<p class="err">Could not load the digits: {error}</p>{/if}
  <div class="grid" class:gone={view !== 'flat'}>
      <div>
        <div class="cap">picture, cut into {n} patches of {p} × {p} pixels</div>
        <canvas bind:this={pic} class="pic" tabindex="0" onpointermove={onPic} onpointerleave={() => (hover = null)} onpointerdown={pickPic} onkeydown={keys}
          aria-label="Digit with its patch grid. Arrow keys move between patches."></canvas>
      </div>
      <div>
        <div class="cap">tokens: shape <b>({n}, {p * p})</b>, one row per patch</div>
        <canvas bind:this={toks} class="toks" onpointermove={onTok} onpointerleave={() => (hover = null)} onpointerdown={pickTok} aria-label="Token rows"></canvas>
      </div>
  </div>
  {#if view === '3d'}
    <Tensors3D tensors={tensors3d} height="320px" {explode}
      ariaLabel="The picture, the same picture cut into a stack of patches, and the stack flattened into token rows, with the chosen patch highlighted" />
    <div class="cut">
      <button type="button" class="lab-btn primary" onclick={playCut}>▶ Play the cut</button>
      <label class="scrub"><span>cut</span>
        <input type="range" min="0" max={cutEnd} step="0.01" bind:value={cutT} aria-label="Move through the cut: picture, then stack, then rows" />
      </label>
      <span class="seg" role="group" aria-label="Choose a patch">
        <button type="button" class="lab-btn" onclick={() => stepPatch(-1)} aria-label="Previous patch">◀</button>
        <span class="mono">patch {shown3d}</span>
        <button type="button" class="lab-btn" onclick={() => stepPatch(1)} aria-label="Next patch">▶</button>
      </span>
    </div>
    <p class="cap">The picture is cut into {n} patches. Each patch moves to its place in a stack of {n} thin blocks, read left to right and top to bottom.
      {#if withRows}Then each thin block is flattened into one row of {p * p} numbers: the token matrix ({n}, {p * p}).{:else}Flattening each thin block into one row of {p * p} numbers gives the token matrix ({n}, {p * p}); with 196 rows it is too tall to draw here, so pick a bigger patch to watch that step.{/if}
      The highlighted patch is the same in every block.</p>
  {/if}

  <div class="flow">
    <div class="flow-h">Inside a DiT with patch size {p}</div>
    <table>
      <tbody>
        {#each rows as [what, sh, note]}
          <tr><td class="what">{what}</td><td class="mono" class:q={sh.includes('?')}>{sh}</td><td class="dim" class:q={note.includes('?')}>{note}</td></tr>
        {/each}
      </tbody>
    </table>
  </div>

  {#snippet controls()}
    <div class="seg" role="group" aria-label="Patch size in pixels per side">
      <span class="lbl">patch size</span>
      {#each SIZES as sz}
        <button type="button" class="lab-btn" class:on={p === sz} aria-pressed={p === sz} onclick={() => setP(sz)} title={`each patch is ${sz} × ${sz} pixels`}>{sz}</button>
      {/each}
    </div>
    {#if data}
      <div class="seg" role="group" aria-label="Digit">
        <span class="lbl">digit</span>
        {#each data.labels as l, i}
          <button type="button" class="lab-btn" class:on={pick === i} aria-pressed={pick === i} onclick={() => (pick = i)}>{l}</button>
        {/each}
      </div>
    {/if}
  {/snippet}

  {#snippet readout()}
    {#if cur === null}{n} patches → {n} tokens of {p * p} numbers each. Choose a patch to follow it.
    {:else}patch {cur} (row {Math.floor(cur / per)}, column {cur % per}) → token {cur}: one row of {p * p} numbers{/if}
  {/snippet}
</LabFrame>

<style>
  .grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 0.9rem; }
  .gone { display: none !important; }
  @media (max-width: 560px) { .grid { grid-template-columns: minmax(0, 1fr); } }
  .cap { font-size: 0.82rem; color: var(--dim); margin: 0 0 0.3rem; }
  .cut { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem 0.9rem; margin: 0.4rem 0; }
  .scrub { display: inline-flex; align-items: center; gap: 0.4rem; font-size: 0.82rem; color: var(--dim); }
  .scrub input { width: 9rem; min-height: 2rem; accent-color: var(--accent); }
  .cap b { font-family: var(--mono); color: var(--fg); }
  .pic { width: 100%; aspect-ratio: 1; display: block; border: 1px solid var(--line); border-radius: 6px; cursor: pointer; }
  .pic:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .toks { width: 100%; display: block; border: 1px solid var(--line); border-radius: 6px; cursor: pointer; }
  .seg { display: inline-flex; flex-wrap: wrap; align-items: center; gap: 0.4rem; }
  .seg + .seg { padding-left: 0.6rem; border-left: 1px solid var(--line); }
  .seg .lab-btn { font-family: var(--mono); min-width: 2.5rem; }
  .seg .lab-btn.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  .lbl { color: var(--dim); font-size: 0.82rem; }
  .flow { margin-top: 0.4rem; }
  .flow-h { font-size: 0.82rem; color: var(--dim); margin-bottom: 0.3rem; }
  table { font-size: 0.85rem; width: 100%; }
  td { border: 0; border-top: 1px solid var(--line); padding: 0.32rem 0.5rem; vertical-align: top; }
  .mono { font-family: var(--mono); white-space: nowrap; }
  .dim { color: var(--dim); }
  .q { color: var(--warn); }
  .err { color: var(--warn); }
  /* phones: each row becomes a small card (step name, then its shape, then the note) */
  @media (max-width: 560px) {
    table, tbody, tr, td { display: block; width: auto; }
    tr { border-top: 1px solid var(--line); padding: 0.35rem 0; }
    td { border: 0; padding: 0.05rem 0; }
    .what { font-weight: 600; }
    .mono { white-space: normal; overflow-wrap: anywhere; }
    .seg + .seg { padding-left: 0; border-left: 0; }
  }
</style>
