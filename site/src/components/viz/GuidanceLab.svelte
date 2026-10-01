<script lang="ts">
  /**
   * Guidance strength lab. For each step the network makes two noise guesses, one without the
   * shape name and one with it, and we use eps_free + w · (eps_shape − eps_free).
   * Every change of w re-samples 300 points with the same starting noise, so only w differs.
   */
  import { onMount } from 'svelte'
  import { onThemeChange } from '@lib/settings'
  import { readable } from '@lib/readable'
  import LabFrame from './LabFrame.svelte'
  import {
    rng, makeShape, loadCondNet, predictNoiseCond, reverseStep, guide, shapeScore,
    prepCanvas, drawAxes, drawPoints, themeColors, type CondNet, type Pt, type ShapeName,
  } from '@lib/diffusion'

  const SPAN = 3.2, N = 300
  const SHAPE_LIST: ShapeName[] = ['spiral', 'ring', 'moons']

  let m = $state.raw<CondNet | null>(null)
  let error = $state<string | null>(null)
  let cls = $state(0)
  let w = $state(1)
  let busy = $state(false)
  let pts = $state<Pt[]>([])
  let score = $state<{ onShape: number; covered: number } | null>(null)
  let watch = $state<{ free: Pt; cond: Pt; g: Pt } | null>(null)
  let cv: HTMLCanvasElement
  let run = 0

  // --- the trade-off chart: a cheaper sweep over w (fewer points), computed once per shape in the background ---
  const SWEEP_W = [0, 0.5, 1, 2, 3, 5, 7, 10]
  const SWEEP_N = 120
  let sweep = $state<Record<number, { w: number; onShape: number; covered: number }[]>>({})
  let sweepRun = 0
  async function runSweep(c: number) {
    if (!m || sweep[c]) return
    const id = ++sweepRun
    const out: { w: number; onShape: number; covered: number }[] = []
    for (const ww of SWEEP_W) {
      const r = rng(2)
      let x: Pt[] = Array.from({ length: SWEEP_N }, () => [r.normal(), r.normal()] as Pt)
      for (let t = m.s.T; t >= 1; t--) {
        const free = predictNoiseCond(m.layers, x, t, m.s.T, m.NULL)
        const cond = predictNoiseCond(m.layers, x, t, m.s.T, c)
        x = x.map((p, i) => reverseStep(p, guide(free[i], cond[i], ww), t, m!.s, t > 1 ? [r.normal(), r.normal()] : null))
        if (t % 25 === 0) { await new Promise((res) => setTimeout(res, 0)); if (id !== sweepRun) return }
      }
      out.push({ w: ww, ...shapeScore(x, ref(SHAPE_LIST[c])) })
      sweep = { ...sweep, [c]: [...out] }
    }
  }
  // chart geometry (SVG units)
  const CW = 300, CH = 150, PL = 46, PR = 12, PT = 12, PB = 30
  const cx = (ww: number) => PL + ((CW - PL - PR) * ww) / 10
  const cy = (v: number) => PT + (CH - PT - PB) * (1 - v)
  const line = (pts: { w: number; v: number }[]) => pts.map((p, i) => `${i ? 'L' : 'M'}${cx(p.w).toFixed(1)},${cy(p.v).toFixed(1)}`).join(' ')

  const refs: Record<string, Pt[]> = {}
  const ref = (s: ShapeName) => (refs[s] ??= makeShape(s, 400, rng(9)))

  async function sample() {
    if (!m) return
    const id = ++run
    busy = true
    const r = rng(1)
    let x: Pt[] = Array.from({ length: N }, () => [r.normal(), r.normal()] as Pt)
    for (let t = m.s.T; t >= 1; t--) {
      const free = predictNoiseCond(m.layers, x, t, m.s.T, m.NULL)
      const cond = predictNoiseCond(m.layers, x, t, m.s.T, cls)
      const eps = free.map((f, i) => guide(f, cond[i], w))
      if (t === 25) watch = { free: free[0], cond: cond[0], g: eps[0] }
      x = x.map((p, i) => reverseStep(p, eps[i], t, m!.s, t > 1 ? [r.normal(), r.normal()] : null))
      if (t % 10 === 0) {
        pts = x; draw()
        await new Promise((res) => setTimeout(res, 0))            // keep the page responsive
        if (id !== run) return                                    // w changed again: drop this run
      }
    }
    pts = x
    score = shapeScore(x, ref(SHAPE_LIST[cls]))
    busy = false
    draw()
  }

  function draw() {
    if (!cv) return
    const c = themeColors(cv)
    const { ctx, px } = prepCanvas(cv, SPAN)
    drawAxes(ctx, px, SPAN, c.line)
    drawPoints(ctx, px, ref(SHAPE_LIST[cls]), c.ok, 1.6, 0.45)
    drawPoints(ctx, px, pts, c.accent, 2, busy ? 0.3 : 0.8)
  }

  const pct = (v: number) => `${Math.round(v * 100)}%`
  function pickShape(i: number) { cls = i; score = null; sample().then(() => runSweep(i)) }
  function resetAll() { cls = 0; w = 1; score = null; sample() }
  const f = (v: number) => v.toFixed(3)
  const fp = (p: Pt) => `[${f(p[0])},\u00a0${f(p[1])}]` // a no-break space: a point never splits across two lines

  onMount(() => {
    loadCondNet().then(async (net) => { m = net; await sample(); runSweep(cls) }).catch((e) => (error = String(e.message ?? e)))
    const ro = new ResizeObserver(draw)
    ro.observe(cv)
    const offTheme = onThemeChange(draw)
    return () => { run++; sweepRun++; ro.disconnect(); offTheme() }
  })
</script>

<LabFrame
  title="Guidance: how strongly w moves points toward the shape"
  hint="Drag w. The same starting noise is used every time, so only w changes."
  onreset={resetAll}
  resetDisabled={cls === 0 && w === 1}
>
  <div class="grid">
    <div class="boardwrap">
      <canvas bind:this={cv} class="board" aria-label="300 samples drawn with guidance w, over the target shape"></canvas>
      {#if !m && !error}<p class="loading">Loading the trained network…</p>{/if}
    </div>
    <div class="side">
      {#if error}<p class="err">Could not load the trained network: {error}</p>{/if}
      <label class="slider">
        <span>guidance w = <b>{w.toFixed(1)}</b></span>
        <input type="range" min="0" max="10" step="0.5" bind:value={w} onchange={() => sample()} aria-label="Guidance strength w" />
      </label>
      <div class="scale"><span>0: ignore the shape</span><span>1: plain</span><span>10: push hard</span></div>
      <div class="stats">
        <div class="stat"><span>on the shape</span><b class="s1">{score && !busy ? pct(score.onShape) : '…'}</b></div>
        <div class="stat"><span>shape covered</span><b class="s2">{score && !busy ? pct(score.covered) : '…'}</b></div>
      </div>
      <figure class="trade">
        <svg viewBox="0 0 {CW} {CH}" use:readable role="img" aria-label="On the shape and shape covered, for w from 0 to 10">
          {#each [0, 0.5, 1] as v}
            <line x1={PL} x2={CW - PR} y1={cy(v)} y2={cy(v)} class="gl" />
            <text x={PL - 5} y={cy(v) + 3.5} class="tick" text-anchor="end">{Math.round(v * 100)}%</text>
          {/each}
          {#each [0, 1, 5, 10] as tw}<text x={cx(tw)} y={CH - 12} class="tick" text-anchor="middle">{tw}</text>{/each}
          <text x={CW - PR} y={CH - 1} class="tick" text-anchor="end">w</text>
          <line x1={cx(w)} x2={cx(w)} y1={PT} y2={CH - PB} class="now" />
          {#if sweep[cls]?.length}
            <path d={line(sweep[cls].map((p) => ({ w: p.w, v: p.onShape })))} class="l1" />
            <path d={line(sweep[cls].map((p) => ({ w: p.w, v: p.covered })))} class="l2" />
            {#each sweep[cls] as p}<circle cx={cx(p.w)} cy={cy(p.onShape)} r="2.6" class="d1" /><circle cx={cx(p.w)} cy={cy(p.covered)} r="2.6" class="d2" />{/each}
          {:else if m}
            <text x={(CW + PL) / 2} y={CH / 2} class="tick" text-anchor="middle">computing the curve…</text>
          {/if}
        </svg>
      </figure>
    </div>
  </div>

  {#snippet controls()}
    <div class="seg" role="group" aria-label="Shape to ask for">
      {#each SHAPE_LIST as sh, i}
        <button type="button" class="lab-btn" class:on={cls === i} aria-pressed={cls === i} onclick={() => pickShape(i)}>{sh[0].toUpperCase() + sh.slice(1)}</button>
      {/each}
    </div>
  {/snippet}

  {#snippet readout()}
    {#if watch}point 0 at t = 25: eps_free {fp(watch.free)} + w·(eps_shape {fp(watch.cond)} − eps_free) = {fp(watch.g)}{:else}sampling…{/if}
  {/snippet}

  {#snippet legend()}
    <span><i class="sw target"></i>the true shape</span>
    <span><i class="sw you"></i>samples at this w</span>
    <span><i class="ln l1"></i>on the shape: samples within 0.15 of it</span>
    <span><i class="ln l2"></i>shape covered: parts of it with a sample within 0.15</span>
    <span>the curve is a quicker run with 120 points, so it differs a little from the boxes</span>
  {/snippet}
</LabFrame>

<style>
  .grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 16rem); gap: 0.9rem; align-items: start; }
  @media (max-width: 640px) { .grid { grid-template-columns: minmax(0, 1fr); } }
  .boardwrap { position: relative; min-width: 0; }
  .board { width: 100%; aspect-ratio: 1; display: block; background: var(--bg); border: 1px solid var(--line); border-radius: 6px; }
  .loading { position: absolute; inset: 0; display: grid; place-items: center; margin: 0; color: var(--dim); font-size: 0.9rem; }
  .slider { display: grid; gap: 0.2rem; font-size: 0.9rem; }
  .slider input { width: 100%; min-height: 2rem; accent-color: var(--accent); }
  .scale { display: flex; justify-content: space-between; gap: 0.4rem; color: var(--dim); font-size: 0.75rem; margin: 0 0 0.6rem; }
  .stats { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin-bottom: 0.6rem; }
  .stat { border: 1px solid var(--line); border-radius: 6px; padding: 0.35rem 0.5rem; background: var(--bg); }
  .stat span { display: block; color: var(--dim); font-size: 0.75rem; }
  .stat b { font-family: var(--mono); font-size: 1.15rem; }
  .s1 { color: var(--cat-1); } .s2 { color: var(--cat-3); }
  .trade { margin: 0; }
  .trade svg { width: 100%; height: auto; display: block; background: var(--bg); border: 1px solid var(--line); border-radius: 6px; }
  .gl { stroke: var(--line); stroke-width: 1; }
  .tick { fill: var(--dim); font-size: 9px; font-family: var(--mono); }
  .now { stroke: var(--accent); stroke-width: 1.5; stroke-dasharray: 3 3; }
  .l1 { fill: none; stroke: var(--cat-1); stroke-width: 2; } .d1 { fill: var(--cat-1); }
  .l2 { fill: none; stroke: var(--cat-3); stroke-width: 2; } .d2 { fill: var(--cat-3); }
  .seg { display: inline-flex; flex-wrap: wrap; gap: 0.4rem; }
  .seg .lab-btn.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  .err { color: var(--warn); font-size: 0.85rem; }
  .sw { display: inline-block; width: 0.7rem; height: 0.7rem; border-radius: 50%; margin-right: 0.35rem; vertical-align: -0.05rem; }
  .sw.target { background: var(--ok); opacity: 0.7; }
  .sw.you { background: var(--accent); }
  .ln { display: inline-block; width: 1.1rem; height: 0; margin-right: 0.35rem; vertical-align: 0.25rem; border-top: 2px solid; }
  .ln.l1 { border-color: var(--cat-1); } .ln.l2 { border-color: var(--cat-3); }
</style>
