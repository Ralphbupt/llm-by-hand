<script lang="ts">
  /**
   * Reverse sampling, one step at a time, with the trained network.
   * Start from 300 random points, then repeat: guess the noise, take one reverse step.
   * The numbers on the right follow one point through each step.
   */
  import { onMount } from 'svelte'
  import {
    rng, makeShape, loadCondNet, predictNoiseCond, reverseStep, prepCanvas, drawAxes, drawPoints, themeColors,
    type CondNet, type Pt, type ShapeName,
  } from '@lib/diffusion'
  import { onThemeChange, reducedMotion } from '@lib/settings'
  import Points3D from '../viz3d/Points3D.svelte'
  import LabFrame from './LabFrame.svelte'

  const SPAN = 3.2, N = 300
  const CHOICES: { label: string; cls: number; shape: ShapeName | null }[] = [
    { label: 'Spiral', cls: 0, shape: 'spiral' },
    { label: 'Ring', cls: 1, shape: 'ring' },
    { label: 'Moons', cls: 2, shape: 'moons' },
    { label: 'Any shape', cls: 3, shape: null },
  ]

  let m = $state.raw<CondNet | null>(null)
  let error = $state<string | null>(null)
  let choice = $state(0)
  let seed = $state(1)
  let t = $state(50)              // the points below are x_t
  let pts = $state<Pt[]>([])
  let last = $state<{ t: number; x: Pt; eps: Pt; mean: Pt; z: Pt | null; next: Pt } | null>(null)
  let playing = $state(false)
  let r = rng(1)
  let timer = 0
  let cv: HTMLCanvasElement

  // --- 3D: time as the third axis, t = T (pure noise) at the top, t = 0 (the shape) at the bottom ---
  let view = $state<'2d' | '3d'>('2d')
  const TRACK = 20                                   // follow the first 20 points step by step
  let hist = $state.raw<{ t: number; pts: Pt[] }[]>([])
  const tz = (k: number) => -SPAN + (2 * SPAN * k) / (m ? m.s.T : 50)
  // reference shapes (the faint target drawn under the cloud), made once per shape
  const refs: Record<string, Pt[]> = {}
  const ref = (s: ShapeName) => (refs[s] ??= makeShape(s, 600, rng(9)))
  const trails3d = $derived(
    Array.from({ length: Math.min(TRACK, pts.length) }, (_, i) => ({
      pts: hist.map((h) => [h.pts[i][0], h.pts[i][1], tz(h.t)] as [number, number, number]),
      tone: (i === 0 ? 'accent' : 'dim') as 'accent' | 'dim',
    })),
  )
  const cloud3d = $derived([
    ...(CHOICES[choice].shape ? ref(CHOICES[choice].shape!) : []).filter((_, i) => i % 4 === 0)
      .map((p) => ({ p: [p[0], p[1], tz(0)] as [number, number, number], tone: 'ok' as const, size: 0.018 })),
    ...pts.filter((_, i) => i % 2 === 0).map((p) => ({ p: [p[0], p[1], tz(t)] as [number, number, number], color: cloudColor, size: 0.025 })),
    ...(pts[0] ? [{ p: [pts[0][0], pts[0][1], tz(t)] as [number, number, number], tone: 'accent' as const, size: 0.05 }] : []),
  ])
  const remember = () => (hist = [...hist, { t, pts: pts.slice(0, TRACK) }])
  let cloudColor = $state('#999')


  const T0 = $derived(m ? m.s.T : 50)
  function resetAll() { choice = 0; seed = 1; view = '2d'; restart() }

  function restart() {
    stopPlay()
    r = rng(seed)
    pts = Array.from({ length: N }, () => [r.normal(), r.normal()] as Pt)
    t = m ? m.s.T : 50
    last = null
    hist = []
    remember()
    draw()
  }

  function step() {
    if (!m || t < 1) return
    const c = CHOICES[choice].cls
    const eps = predictNoiseCond(m.layers, pts, t, m.s.T, c)
    const zs: (Pt | null)[] = pts.map(() => (t > 1 ? [r.normal(), r.normal()] : null))
    const next = pts.map((p, i) => reverseStep(p, eps[i], t, m!.s, zs[i]))
    const b = m.s.betas[t - 1], a = m.s.alphas[t - 1], ab = m.s.alphaBar[t - 1]
    const k = b / Math.sqrt(1 - ab)
    const mean: Pt = [(pts[0][0] - k * eps[0][0]) / Math.sqrt(a), (pts[0][1] - k * eps[0][1]) / Math.sqrt(a)]
    last = { t, x: pts[0], eps: eps[0], mean, z: zs[0], next: next[0] }
    pts = next
    t -= 1
    remember()
    draw()
  }

  function play() {
    if (playing) return stopPlay()
    if (t < 1) restart()
    if (reducedMotion()) return toEnd()          // no animation: jump straight to the result
    playing = true
    const tick = () => { step(); if (t >= 1 && playing) timer = window.setTimeout(tick, 70); else playing = false }
    tick()
  }
  function stopPlay() { playing = false; clearTimeout(timer) }
  function toEnd() { stopPlay(); while (t >= 1) step() }

  function draw() {
    if (!cv) return
    const c = themeColors(cv)
    const { ctx, px } = prepCanvas(cv, SPAN)
    drawAxes(ctx, px, SPAN, c.line)
    const sh = CHOICES[choice].shape
    // the target shape is where the points should land: --ok, drawn under the cloud
    if (sh) drawPoints(ctx, px, ref(sh), c.ok, 1.6, 0.45)
    else for (const s of ['spiral', 'ring', 'moons'] as ShapeName[]) drawPoints(ctx, px, ref(s), c.ok, 1.4, 0.25)
    drawPoints(ctx, px, pts, c.fg, 2, 0.55)
    if (pts[0]) drawPoints(ctx, px, [pts[0]], c.accent, 5.5, 1)
  }

  const f = (v: number) => v.toFixed(3)
  const fp = (p: Pt) => `[${f(p[0])},\u00a0${f(p[1])}]` // a no-break space: a point never splits across two lines

  onMount(() => {
    loadCondNet().then((net) => { m = net; restart() }).catch((e) => (error = String(e.message ?? e)))
    const ro = new ResizeObserver(draw)
    ro.observe(cv)
    const readTok = () => { cloudColor = getComputedStyle(cv).getPropertyValue('--dim').trim() || cloudColor }
    readTok()
    const offTheme = onThemeChange(() => { readTok(); draw() })
    return () => { stopPlay(); ro.disconnect(); offTheme() }
  })
</script>

<LabFrame
  title="Reverse sampling: from noise back to a shape"
  hint="Pick a shape, then press Step. Each step the network guesses the noise and removes a little of it."
  views={[{ id: '2d', label: 'Cloud at step t' }, { id: '3d', label: '3D: time going down' }]}
  bind:view
  onreset={resetAll}
  resetDisabled={choice === 0 && seed === 1 && t === T0 && view === '2d'}
>
  <div class="grid">
    <div class="pic">
      <div class="boardwrap" class:gone={view === '3d'}>
        <canvas bind:this={cv} class="board" aria-label="Points being sampled, over the target shape"></canvas>
        {#if !m && !error}<p class="loading">Loading the trained network…</p>{/if}
      </div>
      {#if view === '3d'}
        <Points3D points={cloud3d} trails={trails3d} range={SPAN} axes={['x', 'y', 't']} height="min(30rem, 92vw)"
          ariaLabel="Reverse sampling through time: noise at the top, the shape at the bottom, each line one point's path" />
        <p class="vcap">Noise starts at the top (t = {T0}); each step moves the slice of points down one level.
          Gray lines are 20 points' paths so far; the highlighted line is the point in the numbers. The target shape at the bottom is where they should land.</p>
      {/if}
    </div>
    <div class="side">
      {#if error}<p class="err">Could not load the trained network: {error}</p>{/if}
      <div class="big">t = <b>{t}</b> <span class="of">of {T0}</span></div>
      {#if last}
        <div class="calc">
          <div class="cap">the point we follow, step t = {last.t} → {last.t - 1}</div>
          <div class="row"><span>x_t</span><b>{fp(last.x)}</b></div>
          <div class="row"><span>noise guess</span><b>{fp(last.eps)}</b></div>
          <div class="row"><span>mean</span><b>{fp(last.mean)}</b></div>
          <div class="row"><span>fresh z</span><b>{last.z ? fp(last.z) : 'none (last step)'}</b></div>
          <div class="row"><span>x_(t−1)</span><b class="you">{fp(last.next)}</b></div>
        </div>
      {:else}
        <p class="dim">Every point starts as random noise. Press Step.</p>
      {/if}
    </div>
  </div>

  {#snippet controls()}
    <div class="seg" role="group" aria-label="What to draw">
      {#each CHOICES as ch, i}
        <button type="button" class="lab-btn" class:on={choice === i} aria-pressed={choice === i} onclick={() => { choice = i; restart() }}>{ch.label}</button>
      {/each}
    </div>
    <div class="seg">
      <button type="button" class="lab-btn primary" onclick={step} disabled={!m || t < 1}>Step</button>
      <button type="button" class="lab-btn" onclick={play} disabled={!m}>{playing ? '❚❚ Pause' : '▶ Play'}</button>
      <button type="button" class="lab-btn" onclick={toEnd} disabled={!m || t < 1}>To the end</button>
      <button type="button" class="lab-btn" onclick={() => { seed += 1; restart() }} disabled={!m}>New noise</button>
    </div>
  {/snippet}

  {#snippet readout()}
    {#if !m}loading…{:else if t === T0}t = {T0}: pure noise. {t >= 1 ? 'Press Step to take one step back.' : ''}{:else if t === 0}t = 0: done. The points should now sit on the {CHOICES[choice].shape ?? 'shapes'}.{:else}t = {t}: {T0 - t} of {T0} steps taken.{/if}
  {/snippet}

  {#snippet legend()}
    <span><i class="sw target"></i>the target shape</span>
    <span><i class="sw cloud"></i>the points at step t</span>
    <span><i class="sw you"></i>the point we follow</span>
  {/snippet}
</LabFrame>

<style>
  .grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 15rem); gap: 0.9rem; align-items: start; }
  @media (max-width: 640px) { .grid { grid-template-columns: minmax(0, 1fr); } }
  .pic { min-width: 0; }
  .gone { display: none !important; }
  .vcap { margin: 0.35rem 0 0; font-size: 0.8rem; color: var(--dim); }
  .boardwrap { position: relative; }
  .board { width: 100%; aspect-ratio: 1; display: block; background: var(--bg); border: 1px solid var(--line); border-radius: 6px; }
  .loading { position: absolute; inset: 0; display: grid; place-items: center; margin: 0; color: var(--dim); font-size: 0.9rem; }
  .big { font-family: var(--mono); font-size: 1.3rem; margin-bottom: 0.5rem; }
  .big .of { font-size: 0.85rem; color: var(--dim); }
  .seg { display: inline-flex; flex-wrap: wrap; gap: 0.4rem; }
  .seg .lab-btn.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  .seg + .seg { padding-left: 0.6rem; border-left: 1px solid var(--line); }
  @media (max-width: 640px) { .seg + .seg { padding-left: 0; border-left: 0; } }
  .lab-btn:disabled { opacity: 0.45; cursor: default; border-color: var(--line); color: var(--dim); background: transparent; }
  .calc { font-family: var(--mono); font-size: 0.8rem; display: grid; gap: 0.25rem; }
  .cap { color: var(--dim); }
  .row { display: flex; justify-content: space-between; gap: 0.5rem; }
  .row span { color: var(--dim); }
  .you { color: var(--accent); }
  .dim { color: var(--dim); font-size: 0.88rem; }
  .err { color: var(--warn); font-size: 0.85rem; }
  .sw { display: inline-block; width: 0.7rem; height: 0.7rem; border-radius: 50%; margin-right: 0.35rem; vertical-align: -0.05rem; }
  .sw.target { background: var(--ok); opacity: 0.7; }
  .sw.cloud { background: var(--fg); opacity: 0.5; }
  .sw.you { background: var(--accent); }
</style>
