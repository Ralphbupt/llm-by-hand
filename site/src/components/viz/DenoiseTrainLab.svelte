<script lang="ts">
  /**
   * Train a noise guesser in the browser. Real gradient descent (Adam), not a recording.
   * Network: [x, y, 12 time numbers] → 64 → 64 → [noise x, noise y], ReLU in between.
   * The board shows noisy points (gray) and the network's guess of where each one started (blue).
   */
  import { onMount } from 'svelte'
  import { onThemeChange, reducedMotion } from '@lib/settings'
  import LabFrame from './LabFrame.svelte'
  import {
    rng, makeShape, SITE_SCHEDULE as S, addNoise, timeFeatures, initLayers, adamFor, trainStep,
    predictNoise, guessClean, prepCanvas, drawAxes, drawPoints, themeColors, canvasFont, type Pt, type Layer, type Adam,
  } from '@lib/diffusion'

  const SPAN = 3.2, BATCH = 128, LR = 3e-3, MAX = 4000
  const data = makeShape('spiral', 2000, rng(1))
  const vr = rng(3)
  const show: Pt[] = makeShape('spiral', 250, vr)
  const showEps: Pt[] = show.map(() => [vr.normal(), vr.normal()])

  let net: Layer[], opt: Adam, r = rng(11)
  let running = $state(false)
  let steps = $state(0)
  let curve = $state<number[]>([])     // average loss of every 50 steps
  const FLOOR = 0.32        // where this data's loss levels off (demo.py: about 0.32)
  const FLOOR_AFTER = 300   // show the floor line once training has flattened
  let t = $state(10)
  let cv: HTMLCanvasElement, chart: HTMLCanvasElement
  let timer = 0, acc = 0, accN = 0

  function reset() {
    stop()
    r = rng(11)
    net = initLayers([14, 64, 64, 2], r)
    opt = adamFor(net)
    steps = 0; curve = []; acc = 0; accN = 0
    draw()
  }

  function oneStep() {
    const X = new Float32Array(BATCH * 14), Y = new Float32Array(BATCH * 2)
    for (let i = 0; i < BATCH; i++) {
      const x0 = data[Math.floor(r.uniform() * data.length)]
      const tt = 1 + Math.floor(r.uniform() * S.T)
      const e: Pt = [r.normal(), r.normal()]
      const xt = addNoise(x0, e, S.alphaBar[tt - 1])
      X[i * 14] = xt[0]; X[i * 14 + 1] = xt[1]; X.set(timeFeatures(tt, S.T), i * 14 + 2)
      Y[i * 2] = e[0]; Y[i * 2 + 1] = e[1]
    }
    acc += trainStep(net, opt, X, Y, BATCH, LR); accN++
    steps++
    if (accN === 50) { curve = [...curve, acc / accN]; acc = 0; accN = 0 }
  }

  // setTimeout rather than requestAnimationFrame, so training keeps going in a background tab
  function loop() {
    // with reduced motion, train in big chunks so the picture changes a few times instead of animating
    const chunk = reducedMotion() ? 500 : 20
    for (let i = 0; i < chunk && steps < MAX; i++) oneStep()
    draw()
    if (running && steps < MAX) timer = window.setTimeout(loop, 0)
    else running = false
  }
  function start() { if (running) return stop(); if (steps >= MAX) reset(); running = true; timer = window.setTimeout(loop, 0) }
  function stop() { running = false; clearTimeout(timer) }

  const lastLoss = $derived(curve.length ? curve[curve.length - 1] : null)

  function draw() {
    if (!cv || !net) return
    const c = themeColors(cv)
    const ab = S.alphaBar[t - 1]
    const noisy = show.map((p, i) => addNoise(p, showEps[i], ab))
    const eh = predictNoise(net, noisy, t, S.T)
    const guess = noisy.map((p, i) => guessClean(p, eh[i], ab))
    const { ctx, px } = prepCanvas(cv, SPAN)
    drawAxes(ctx, px, SPAN, c.line)
    drawPoints(ctx, px, noisy, c.dim, 1.8, 0.35)
    ctx.strokeStyle = c.accent; ctx.globalAlpha = 0.25; ctx.beginPath()
    for (let i = 0; i < 60; i++) { const [a, b] = px(noisy[i]), [x, y] = px(guess[i]); ctx.moveTo(a, b); ctx.lineTo(x, y) }
    ctx.stroke(); ctx.globalAlpha = 1
    drawPoints(ctx, px, guess, c.accent, 2, 0.8)

    const { ctx: g, css: W, cssH: H } = prepCanvas(chart, 1)
    const n = Math.max(curve.length, MAX / 50)
    const X = (k: number) => 30 + ((W - 38) * k) / n
    const Y = (v: number) => 8 + (H - 22) * (1 - Math.min(v, 1.2) / 1.2)
    g.strokeStyle = c.line; g.beginPath(); g.moveTo(X(0), Y(0)); g.lineTo(X(n), Y(0)); g.stroke()
    // reference line: what you get by always guessing zero noise (context, not an error)
    g.setLineDash([4, 3]); g.strokeStyle = c.dim; g.beginPath(); g.moveTo(X(0), Y(1)); g.lineTo(X(n), Y(1)); g.stroke(); g.setLineDash([])
    const fs = canvasFont(0.72)
    g.fillStyle = c.dim; g.font = `${fs}px ui-monospace, monospace`
    g.textAlign = 'right'; g.fillText('1.0', 26, Y(1) + fs * 0.35); g.fillText('0', 26, Y(0) + fs * 0.35)
    g.fillText('always guess 0', X(n), Y(1) - 4)
    // the floor: shown once the curve has flattened, so it doesn't answer the "where does it end?" guess in advance
    if (steps >= FLOOR_AFTER) {
      g.setLineDash([2, 3]); g.strokeStyle = c.ok; g.beginPath(); g.moveTo(X(0), Y(FLOOR)); g.lineTo(X(n), Y(FLOOR)); g.stroke(); g.setLineDash([])
      g.fillStyle = c.ok; g.fillText('lower limit ≈ 0.32', X(n), Y(FLOOR) + fs + 2)
    }
    g.strokeStyle = c.accent; g.lineWidth = 2; g.beginPath()
    curve.forEach((v, k) => (k ? g.lineTo(X(k + 1), Y(v)) : g.moveTo(X(k + 1), Y(v))))
    g.stroke(); g.lineWidth = 1; g.textAlign = 'left'
  }

  $effect(() => { void t; draw() })
  onMount(() => {
    reset()
    const ro = new ResizeObserver(draw)
    ro.observe(cv)
    const offTheme = onThemeChange(draw)
    const htmlObs = new MutationObserver(draw)
    htmlObs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-scale'] })
    return () => { stop(); ro.disconnect(); offTheme(); htmlObs.disconnect() }
  })
</script>

<LabFrame
  title="Train a noise-guessing network in your browser"
  hint="Press Train. Then drag t to see how well it guesses at each amount of noise."
  onreset={reset}
  resetDisabled={steps === 0}
>
  <div class="grid">
    <canvas bind:this={cv} class="board" aria-label="Noisy points and the network's guess of where each one started"></canvas>
    <div class="side">
      <canvas bind:this={chart} class="chart" aria-label="Loss curve"></canvas>
      {#if steps >= FLOOR_AFTER}<p class="flat">Flat is normal. From a noisy point alone, nobody can tell exactly which noise was added, so some error always stays.</p>{/if}
      <label class="slider">
        <span>look at step t = <b>{t}</b></span>
        <input type="range" min="1" max={S.T} step="1" bind:value={t} aria-label="Noise step t to look at" />
      </label>
    </div>
  </div>

  {#snippet controls()}
    <button type="button" class="lab-btn primary" onclick={start}>{running ? '❚❚ Pause' : steps ? '▶ Keep training' : '▶ Train'}</button>
  {/snippet}

  {#snippet readout()}
    step {steps} of {MAX} · loss (average of the last 50 steps) {lastLoss === null ? '—' : lastLoss.toFixed(3)}
  {/snippet}

  {#snippet legend()}
    <span><i class="sw noisy"></i>noisy points at step t</span>
    <span><i class="sw guess"></i>the network’s guess of where each started: (x_t − √(1 − ᾱ)·guess) / √ᾱ</span>
    <span><i class="ln ref"></i>always guessing 0</span>
    {#if steps >= FLOOR_AFTER}<span><i class="ln floor"></i>the lowest loss this data allows</span>{/if}
  {/snippet}
</LabFrame>

<style>
  .grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 15rem); gap: 0.9rem; align-items: start; }
  @media (max-width: 640px) { .grid { grid-template-columns: minmax(0, 1fr); } }
  .board { width: 100%; aspect-ratio: 1; display: block; background: var(--bg); border: 1px solid var(--line); border-radius: 6px; }
  .chart { width: 100%; aspect-ratio: 1.6; display: block; background: var(--bg); border: 1px solid var(--line); border-radius: 6px; margin: 0 0 0.5rem; }
  .slider { display: grid; gap: 0.2rem; font-size: 0.9rem; }
  .slider input { width: 100%; min-height: 2rem; accent-color: var(--accent); }
  .flat { margin: 0 0 0.5rem; font-size: 0.82rem; color: var(--ok); }
  .sw { display: inline-block; width: 0.7rem; height: 0.7rem; border-radius: 50%; margin-right: 0.35rem; vertical-align: -0.05rem; }
  .sw.noisy { background: var(--dim); opacity: 0.6; }
  .sw.guess { background: var(--accent); }
  .ln { display: inline-block; width: 1.2rem; height: 0; margin-right: 0.35rem; vertical-align: 0.25rem; border-top: 2px dashed; }
  .ln.ref { border-color: var(--dim); }
  .ln.floor { border-color: var(--ok); }
</style>
