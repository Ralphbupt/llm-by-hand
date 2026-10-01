<script lang="ts">
  /**
   * Forward process lab: drag t and watch the spiral dissolve into noise.
   * Every point keeps its own fixed noise eps, so x_t = sqrt(ab)·x0 + sqrt(1−ab)·eps moves smoothly.
   * "Toy" mode uses the 3-step schedule from the page, with the one point you compute by hand.
   */
  import { onMount } from 'svelte'
  import {
    rng, makeShape, schedule, linearBetas, addNoise, prepCanvas, drawAxes, drawPoints, themeColors, type Pt,
  } from '@lib/diffusion'
  import { has, subscribe } from '@lib/progress'
  import { onThemeChange } from '@lib/settings'
  import Points3D from '../viz3d/Points3D.svelte'
  import LabFrame from './LabFrame.svelte'
  import { canvasFont } from '@lib/diffusion'

  const SPAN = 3.2
  const site = schedule(linearBetas(50))
  const toy = schedule([0.1, 0.2, 0.5])
  const r = rng(7)
  const x0s: Pt[] = makeShape('spiral', 500, r)
  const eps: Pt[] = x0s.map(() => [r.normal(), r.normal()])
  // the hand-computed point from the page
  const HAND_X0: Pt = [1, 2]
  const HAND_EPS: Pt = [0.5, -1]

  let mode = $state<'site' | 'toy'>('site')
  // In toy mode the page asks for alpha_bar and x_3 below this lab, so those stay hidden until answered.
  let solvedAb = $state(false)
  let solvedX = $state(false)
  const hideAb = $derived(mode === 'toy' && !solvedAb)
  const hideX = $derived(mode === 'toy' && !solvedX)
  let t = $state(0)
  let cv: HTMLCanvasElement
  let chart: HTMLCanvasElement

  const s = $derived(mode === 'site' ? site : toy)
  const ab = $derived(t === 0 ? 1 : s.alphaBar[t - 1])
  const p0 = $derived<Pt>(mode === 'toy' ? HAND_X0 : x0s[0])
  const e0 = $derived<Pt>(mode === 'toy' ? HAND_EPS : eps[0])
  const pt = $derived(addNoise(p0, e0, ab))
  $effect(() => { void solvedX; void solvedAb; draw() })

  const f = (v: number, d = 3) => v.toFixed(d)
  const fp = (p: Pt, d = 3) => `[${f(p[0], d)}, ${f(p[1], d)}]`

  function setMode(m: 'site' | 'toy') { mode = m; t = 0; if (m === 'toy') view = '2d' }
  function reset() { mode = 'site'; t = 0; view = '2d' }
  // colors for the 3D view come from the page's tokens (re-read on theme change)
  let cloudColor = $state('#888')

  // --- 3D: time as the third axis. A few points' whole journeys from t = 0 (bottom) to t = T (top). ---
  let view = $state<'2d' | '3d'>('2d')
  const changed = $derived(mode !== 'site' || t !== 0 || view !== '2d')
  const TRACKED = Array.from({ length: 36 }, (_, k) => Math.floor((k * x0s.length) / 36))
  const tz = (k: number) => -SPAN + (2 * SPAN * k) / site.T // t = 0 at the bottom, t = T at the top
  const at = (i: number, k: number) => addNoise(x0s[i], eps[i], k === 0 ? 1 : site.alphaBar[k - 1])
  const trails3d = TRACKED.map((i) => ({
    pts: Array.from({ length: site.T + 1 }, (_, k) => { const p = at(i, k); return [p[0], p[1], tz(k)] as [number, number, number] }),
    tone: (i === 0 ? 'accent' : 'dim') as 'accent' | 'dim',
  }))
  const cloud3d = $derived([
    // the starting spiral, faint, on the floor of the time axis
    ...x0s.filter((_, i) => i % 3 === 0).map((p) => ({ p: [p[0], p[1], tz(0)] as [number, number, number], tone: 'dim' as const, size: 0.018 })),
    // the whole cloud at the current t, as a slice through time
    ...x0s.filter((_, i) => i % 2 === 0).map((p, k) => {
      const q = at(k * 2, t)
      return { p: [q[0], q[1], tz(t)] as [number, number, number], color: cloudColor, size: 0.025 }
    }),
    { p: [at(0, t)[0], at(0, t)[1], tz(t)] as [number, number, number], tone: 'accent' as const, size: 0.05, label: 'one point' },
  ])

  function draw() {
    if (!cv) return
    const c = themeColors(cv)
    const { ctx, px } = prepCanvas(cv, SPAN)
    drawAxes(ctx, px, SPAN, c.line)
    // the cloud is plain data (neutral); the one point we follow is the learner's thing (accent)
    if (mode === 'site') drawPoints(ctx, px, x0s.map((p, i) => addNoise(p, eps[i], ab)), c.fg, 2, 0.4)
    else drawPoints(ctx, px, x0s, c.dim, 1.5, 0.15)
    // the tracked point: where it started, and where it is now
    const [ax, ay] = px(p0), [bx, by] = px(pt)
    if (!(hideX && t > 0)) {
      ctx.strokeStyle = c.accent; ctx.lineWidth = 1.5; ctx.setLineDash([4, 3]); ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(bx, by); ctx.stroke(); ctx.setLineDash([]); ctx.lineWidth = 1
    }
    // where the followed point started: an open ring
    { const [sx, sy] = px(p0); ctx.strokeStyle = c.fg; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(sx, sy, 5, 0, 7); ctx.stroke(); ctx.lineWidth = 1 }
    if (!(hideX && t > 0)) drawPoints(ctx, px, [pt], c.accent, 5.5, 1)

    // alpha-bar over t
    const { ctx: g, css, cssH } = prepCanvas(chart, 1)
    const W = css, H = cssH
    const X = (k: number) => 8 + ((W - 16) * k) / s.T
    const Y = (v: number) => H - 14 - (H - 28) * v
    g.strokeStyle = c.line; g.beginPath(); g.moveTo(X(0), Y(0)); g.lineTo(X(s.T), Y(0)); g.moveTo(X(0), Y(0)); g.lineTo(X(0), Y(1)); g.stroke()
    g.strokeStyle = c.fg; g.globalAlpha = 0.75; g.lineWidth = 2; g.beginPath()
    for (let k = 0; k <= s.T; k++) { const v = k === 0 ? 1 : s.alphaBar[k - 1]; k ? g.lineTo(X(k), Y(v)) : g.moveTo(X(k), Y(v)) }
    g.stroke(); g.lineWidth = 1; g.globalAlpha = 1
    if (!(hideAb && t > 0)) { g.fillStyle = c.accent; g.beginPath(); g.arc(X(t), Y(ab), 4.5, 0, 7); g.fill() }
    const fs = canvasFont(0.72)
    g.fillStyle = c.dim; g.font = `${fs}px ui-monospace, monospace`
    g.textAlign = 'right'; g.fillText('ᾱ (signal left)', X(s.T), Y(1) + fs); g.fillText(`t = ${s.T}`, X(s.T), H - 2)
    g.textAlign = 'left'; g.fillText('0', X(0), H - 2)
  }

  $effect(() => { void t; void mode; draw() })
  onMount(() => {
    const sync = () => { solvedAb = has('alpha-bar-3'); solvedX = has('x3-first') }
    sync()
    const off = subscribe(sync)
    const ro = new ResizeObserver(draw)
    ro.observe(cv)
    const readTok = () => { cloudColor = getComputedStyle(cv).getPropertyValue('--dim').trim() || cloudColor }
    readTok()
    const offTheme = onThemeChange(() => { readTok(); draw() })
    const htmlObs = new MutationObserver(draw) // text-size setting changes the chart labels
    htmlObs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-scale'] })
    return () => { off(); ro.disconnect(); offTheme(); htmlObs.disconnect() }
  })
</script>

<LabFrame
  title="The forward process: a spiral turning into noise"
  hint="Drag t. Every point is mixed with its own fixed noise, so it moves smoothly."
  views={mode === 'site' ? [{ id: '2d', label: 'Cloud at step t' }, { id: '3d', label: '3D: time going up' }] : undefined}
  bind:view
  onreset={reset}
  resetDisabled={!changed}
>
  <div class="grid">
    <div class="pic">
      <canvas bind:this={cv} class="board" class:gone={view === '3d'} aria-label="Point cloud at step t"></canvas>
      {#if view === '3d'}
        <Points3D points={cloud3d} trails={trails3d} range={SPAN} axes={['x', 'y', 't']} height="min(30rem, 92vw)"
          ariaLabel="The point cloud through time: t goes up, each line is one point's path from the spiral into noise" />
        <p class="cap">Time goes up. The faint spiral at the bottom is t = 0; the slice of colored points is the cloud at t = {t}.
          Each gray line is one point's whole path; the highlighted line is the point we follow. Drag t to move the slice.</p>
      {/if}
    </div>
    <div class="side">
      <label class="slider">
        <span>t = <b>{t}</b> of {s.T}</span>
        <input type="range" min="0" max={s.T} step="1" bind:value={t} aria-label="Noise step t" />
      </label>
      <canvas bind:this={chart} class="chart" aria-label="alpha-bar, the signal left, against t"></canvas>
      <div class="calc">
        <div class="row"><span>ᾱ (ab)</span><b class:q={hideAb && t > 0}>{hideAb && t > 0 ? '?' : f(ab, 4)}</b></div>
        <div class="row"><span>x0</span><b>{fp(p0)}</b></div>
        <div class="row"><span>eps</span><b>{fp(e0)}</b></div>
        <div class="eq">
          x_t = {hideAb && t > 0 ? '?' : f(Math.sqrt(ab))} × x0 + {hideAb && t > 0 ? '?' : f(Math.sqrt(1 - ab))} × eps
        </div>
        <div class="row"><span>x_t</span><b class="you" class:q={hideX && t > 0}>{hideX && t > 0 ? '[?, ?]' : fp(pt)}</b></div>
      </div>
    </div>
  </div>

  {#snippet controls()}
    <div class="seg" role="group" aria-label="Schedule">
      <button type="button" class="lab-btn" class:on={mode === 'site'} aria-pressed={mode === 'site'} onclick={() => setMode('site')}>Spiral · 50 steps</button>
      <button type="button" class="lab-btn" class:on={mode === 'toy'} aria-pressed={mode === 'toy'} onclick={() => setMode('toy')}>Hand example · 3 steps</button>
    </div>
  {/snippet}

  {#snippet readout()}
    {#if t === 0}t = 0: nothing added yet, every point is still on the spiral.
    {:else if hideAb}t = {t}: the numbers the page asks for appear once you have answered them.
    {:else}t = {t}: signal × {f(Math.sqrt(ab), 2)} + noise × {f(Math.sqrt(1 - ab), 2)} ({f(100 * ab, 0)}% of the variance is still signal){/if}
  {/snippet}

  {#snippet legend()}
    {#if mode === 'site'}<span><i class="sw cloud"></i>the cloud at step t</span>{/if}
    <span><i class="sw start"></i>where the point started</span>
    <span><i class="sw you"></i>the point we follow, and its path</span>
  {/snippet}
</LabFrame>

<style>
  .grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 15rem); gap: 0.9rem; align-items: start; }
  @media (max-width: 640px) { .grid { grid-template-columns: minmax(0, 1fr); } }
  .pic { min-width: 0; }
  .gone { display: none !important; }
  .cap { margin: 0.35rem 0 0; font-size: 0.8rem; color: var(--dim); }
  .board { width: 100%; aspect-ratio: 1; max-width: 100%; display: block; background: var(--bg); border: 1px solid var(--line); border-radius: 6px; }
  .chart { width: 100%; aspect-ratio: 1.6; display: block; background: var(--bg); border: 1px solid var(--line); border-radius: 6px; margin: 0.5rem 0; }
  .slider { display: grid; gap: 0.2rem; font-size: 0.9rem; }
  .slider input { width: 100%; min-height: 2rem; accent-color: var(--accent); }
  .calc { font-family: var(--mono); font-size: 0.82rem; display: grid; gap: 0.25rem; }
  .row { display: flex; justify-content: space-between; gap: 0.5rem; }
  .row span { color: var(--dim); }
  .eq { color: var(--dim); border-top: 1px dashed var(--line); padding-top: 0.25rem; overflow-wrap: anywhere; }
  .you { color: var(--accent); }
  .q { color: var(--warn); }
  .seg { display: inline-flex; flex-wrap: wrap; gap: 0.4rem; }
  .seg .lab-btn.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  .sw { display: inline-block; width: 0.7rem; height: 0.7rem; border-radius: 50%; margin-right: 0.35rem; vertical-align: -0.05rem; }
  .sw.cloud { background: var(--fg); opacity: 0.45; }
  .sw.start { background: transparent; border: 2px solid var(--fg); width: 0.6rem; height: 0.6rem; }
  .sw.you { background: var(--accent); }
</style>
