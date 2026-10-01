<script lang="ts">
  /**
   * MLP lab: a fully connected network learns two interleaved spirals, live in the browser.
   * Pick the depth, the width and the activation; the background is the network's answer at every point.
   * Training is full-batch Adam on cross-entropy (level 6 explains where the gradients come from).
   */
  import { onMount, untrack } from 'svelte'
  import { has, subscribe } from '@lib/progress'
  import { accuracy, forward, makeNet, paramCount, spiral, trainStep, type Net } from '@lib/foundations'
  import Surface3D from '../viz3d/Surface3D.svelte'
  import { onThemeChange, reducedMotion } from '@lib/settings'
  import LabFrame from './LabFrame.svelte'
  import { readable } from '@lib/readable'

  // the parameter count stays "?" until every listed question is solved
  let { hide = {} }: { hide?: { params?: string[] } } = $props()
  let solved = $state(true)
  onMount(() => {
    const ids = hide.params ?? []
    if (!ids.length) return
    const sync = () => (solved = ids.every((id) => has(id)))
    sync()
    return subscribe(sync)
  })

  const { X, y } = spiral(100, 0.08, 1)
  const N = X.length
  const START = { depth: 1, width: 8, act: 'tanh' as 'tanh' | 'relu' }
  let depth = $state(START.depth)
  let width = $state(START.width)
  let act = $state<'tanh' | 'relu'>(START.act)
  let showLines = $state(false)
  let view = $state<string>('map')
  // the 3D surface is rebuilt when this changes: after a reset and every few dozen training steps
  let surfaceKey = $state(1)
  let lastRebuild = 0
  let running = $state(false)
  let ui = $state({ steps: 0, loss: 0, acc: 0 })
  let losses = $state<number[]>([])
  let lines: { w1: number; w2: number; b: number }[] = []

  const sizes = $derived([2, ...Array(depth).fill(width), 1])
  const nParams = $derived(paramCount(sizes))
  const shapeChain = $derived.by(() => {
    const parts = [`X (${N}, 2)`]
    for (let l = 0; l < sizes.length - 1; l++) parts.push(`@ W${l + 1} (${sizes[l]}, ${sizes[l + 1]}) → (${N}, ${sizes[l + 1]})`)
    return parts
  })

  let net: Net
  let canvas: HTMLCanvasElement
  let raf = 0
  const LO = -1.25, HI = 1.25, G = 44

  function init() {
    stop()
    net = makeNet([2, ...Array(depth).fill(width), 1], act)
    losses = []
    ui = { steps: 0, loss: 0, acc: accuracy(net, X, y) }
    draw()
    lastRebuild = 0
    surfaceKey++
  }

  function colors() {
    const cs = getComputedStyle(canvas)
    return { one: cs.getPropertyValue('--cat-1').trim() || '#4f5bd5', zero: cs.getPropertyValue('--cat-3').trim() || '#c0386b', bg: cs.getPropertyValue('--bg').trim() || '#fff', fg: cs.getPropertyValue('--fg').trim() || '#000' }
  }

  function draw() {
    if (!canvas || !net) return
    const ctx = canvas.getContext('2d')!
    const S = canvas.width
    const c = colors()
    ctx.fillStyle = c.bg
    ctx.fillRect(0, 0, S, S)
    const cell = S / G
    for (let r = 0; r < G; r++) {
      for (let k = 0; k < G; k++) {
        const px = LO + ((k + 0.5) / G) * (HI - LO)
        const py = HI - ((r + 0.5) / G) * (HI - LO)
        const p = forward(net, [px, py]).p
        ctx.globalAlpha = Math.abs(p - 0.5) * 0.7
        ctx.fillStyle = p > 0.5 ? c.one : c.zero
        const x0 = Math.round(k * cell), x1 = Math.round((k + 1) * cell)
        const y0 = Math.round(r * cell), y1 = Math.round((r + 1) * cell)
        ctx.fillRect(x0, y0, x1 - x0, y1 - y0) // integer edges: no overlap, so no darker seams
      }
    }
    ctx.globalAlpha = 1
    const toS = (v: number) => ((v - LO) / (HI - LO)) * S
    // first-layer lines: where each hidden unit's input is 0
    lines = net.W[0][0].map((_, h) => ({ w1: net.W[0][0][h], w2: net.W[0][1][h], b: net.b[0][h] }))
    if (showLines) {
      ctx.strokeStyle = c.fg
      ctx.globalAlpha = 0.35
      ctx.lineWidth = 1
      for (const ln of lines) {
        ctx.beginPath()
        if (Math.abs(ln.w2) > Math.abs(ln.w1)) {
          for (const xx of [LO, HI]) {
            const yy = -(ln.w1 * xx + ln.b) / ln.w2
            xx === LO ? ctx.moveTo(toS(xx), S - toS(yy)) : ctx.lineTo(toS(xx), S - toS(yy))
          }
        } else {
          for (const yy of [LO, HI]) {
            const xx = -(ln.w2 * yy + ln.b) / ln.w1
            yy === LO ? ctx.moveTo(toS(xx), S - toS(yy)) : ctx.lineTo(toS(xx), S - toS(yy))
          }
        }
        ctx.stroke()
      }
      ctx.globalAlpha = 1
    }
    for (let n = 0; n < N; n++) {
      ctx.beginPath()
      ctx.arc(toS(X[n][0]), S - toS(X[n][1]), S / 110, 0, 2 * Math.PI)
      ctx.fillStyle = y[n] ? c.one : c.zero
      ctx.fill()
      ctx.strokeStyle = c.bg
      ctx.lineWidth = 1
      ctx.stroke()
    }
  }

  function run(k: number) {
    let loss = 0
    for (let i = 0; i < k; i++) {
      loss = trainStep(net, X, y, 0.02)
      if ((ui.steps + i) % 10 === 0) losses.push(loss)
    }
    ui = { steps: ui.steps + k, loss, acc: accuracy(net, X, y) }
    draw()
    if (view === '3d' && ui.steps - lastRebuild >= 48) {
      lastRebuild = ui.steps
      surfaceKey++
    }
  }

  function loop() {
    run(8)
    if (running && ui.steps < 4000) raf = requestAnimationFrame(loop)
    else running = false
  }
  function toggle() {
    if (running) return stop()
    if (reducedMotion()) return burst() // no animation: jump ahead in one go
    running = true
    raf = requestAnimationFrame(loop)
  }
  function stop() {
    running = false
    cancelAnimationFrame(raf)
  }
  function burst() {
    stop()
    run(200)
  }

  function setArch(d: number, w: number, a: 'tanh' | 'relu') {
    depth = d
    width = w
    act = a
    init()
  }
  const changed = $derived(depth !== START.depth || width !== START.width || act !== START.act || ui.steps > 0)
  const resetAll = () => setArch(START.depth, START.width, START.act)

  onMount(() => {
    init()
    // redraw when the page switches light/dark (system or the settings menu)
    const off = onThemeChange(() => draw())
    return () => {
      stop()
      off()
    }
  })
  $effect(() => {
    showLines
    draw()
  })

  // the network's answer p(x1, x2) for the 3D view; reads the current net every time it is rebuilt
  const netP = (a: number, b: number) => (net ? forward(net, [a, b]).p : 0.5)
  const dots = X.map((p, n) => ({ x: p[0], y: p[1], tone: (y[n] ? 'cat-1' : 'cat-3') as 'cat-1' | 'cat-3' }))
  // switching to 3D shows the network as it is now
  $effect(() => {
    if (view === '3d') untrack(() => surfaceKey++)
  })

  const curve = $derived(
    losses.slice(-200).map((l, i, a) => `${8 + (i / Math.max(1, a.length - 1)) * 91},${38 - Math.min(35, l * 44)}`).join(' '),
  )
</script>

<LabFrame
  title="A network learns two spirals"
  hint="Pick the size of the network, then press Train. The background shows the network’s answer at every point."
  views={[{ id: 'map', label: 'Map' }, { id: '3d', label: '3D' }]}
  bind:view
  onreset={resetAll}
  resetDisabled={!changed}
>
  <div class="top">
    <figure class="pic">
      <div class="canvaswrap" class:gone={view !== 'map'}>
        <canvas bind:this={canvas} width="440" height="440" aria-label="Spiral data and the network's decision"></canvas>
        <span class="ax ax-x">x₁ →</span>
        <span class="ax ax-y">x₂ ↑</span>
        <!-- ticks on both axes, as on the gradient-descent map: −1, 0 and 1 for x₁ along the bottom, x₂ up the left -->
        {#each [-1, 0, 1] as v}
          <span class="ax tk tk-x" style:left="{((v - LO) / (HI - LO)) * 100}%">{v < 0 ? '−1' : v}</span>
          <span class="ax tk tk-y" style:top="{((HI - v) / (HI - LO)) * 100}%">{v < 0 ? '−1' : v}</span>
        {/each}
      </div>
      {#if view === '3d'}
        <Surface3D
          f={netP} xRange={[LO, HI]} yRange={[LO, HI]} zRange={[0, 1]} res={36} height={1}
          dots={dots} rebuildKey={surfaceKey} ramp="prob"
          note={losses.length === 0 ? { text: 'Untrained: every point is about 0.5. Press Train.', x: 0, y: 0 } : null} axes={{ x: 'x₁', y: 'x₂', z: 'p(arm 1)' }}
          ariaLabel="The network's output probability as a surface over the input plane, with the training points on it"
        />
      {/if}
      <figcaption>
        {#if view === '3d'}Height is the network’s answer p(arm 1) at every point: a point of arm 1 should sit high, a point of arm 2 low.
        {:else}Color is the network’s answer at every point; the stronger the color, the surer the network.{/if}
      </figcaption>
    </figure>

    <div class="side">
      <svg class="curve" viewBox="0 0 100 44" use:readable aria-label="Loss curve">
        <line x1="8" y1="38" x2="99" y2="38" class="axl" />
        <line x1="8" y1="3" x2="8" y2="38" class="axl" />
        <text x="10" y="7" class="tick">loss</text>
        <text x="7" y="38" class="tick end">0</text>
        <text x="99" y="43" class="tick end">steps →</text>
        {#if losses.length > 1}<polyline points={curve} />{:else}<text x="53" y="23" class="empty">Train to draw the loss</text>{/if}
      </svg>
      <div class="shapes">
        {#each shapeChain as s, i}<span>{s}{i < shapeChain.length - 1 ? ',' : ''}</span>{/each}
      </div>
    </div>
  </div>

  {#snippet controls()}
    <div class="arch">
      <div class="row">
        <span class="k">hidden layers</span>
        {#each [1, 2, 3] as d}
          <button class="lab-btn sm" class:on={depth === d} aria-pressed={depth === d} onclick={() => setArch(d, width, act)}>{d}</button>
        {/each}
      </div>
      <div class="row">
        <span class="k">units per layer</span>
        {#each [2, 4, 8, 16, 32] as w}
          <button class="lab-btn sm" class:on={width === w} aria-pressed={width === w} onclick={() => setArch(depth, w, act)}>{w}</button>
        {/each}
      </div>
      <div class="row">
        <span class="k">activation</span>
        {#each ['tanh', 'relu'] as a}
          <button class="lab-btn sm" class:on={act === a} aria-pressed={act === a} onclick={() => setArch(depth, width, a as 'tanh' | 'relu')}>{a === 'relu' ? 'ReLU' : 'tanh'}</button>
        {/each}
      </div>
    </div>
    <button class="lab-btn primary" onclick={toggle}>{running ? 'Pause' : 'Train'}</button>
    <button class="lab-btn" onclick={burst}>+200 steps</button>
    <button class="lab-btn" onclick={init}>New random weights</button>
    <label class="chk"><input type="checkbox" bind:checked={showLines} /> show each first-layer unit’s line</label>
  {/snippet}

  {#snippet readout()}
    step {ui.steps} · loss {ui.steps ? ui.loss.toFixed(3) : '–'} · {(ui.acc * 100).toFixed(0)}% of {N} correct · parameters {solved ? nParams : '?'}
  {/snippet}

  {#snippet legend()}
    <span class="key"><i class="k1"></i>arm 1</span>
    <span class="key"><i class="k3"></i>arm 2</span>
    <span class="key">background: the network’s answer, stronger = surer</span>
  {/snippet}
</LabFrame>

<style>
  .top { display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr); gap: 1rem; align-items: start; }
  @media (max-width: 640px) { .top { grid-template-columns: minmax(0, 1fr); } }
  .pic { margin: 0; min-width: 0; }
  .pic figcaption { font-size: 0.82rem; color: var(--dim); margin-top: 0.3rem; line-height: 1.45; }
  .canvaswrap { position: relative; }
  .canvaswrap.gone { display: none; }
  canvas { width: 100%; height: auto; aspect-ratio: 1; max-width: 100%; border: 1px solid var(--line); border-radius: 4px; background: var(--bg); display: block; }
  .ax { position: absolute; font-family: var(--mono); font-size: 0.75rem; color: var(--fg); background: color-mix(in srgb, var(--bg) 70%, transparent); padding: 0 0.2rem; border-radius: 3px; pointer-events: none; }
  .ax-x { right: 0.3rem; bottom: 0.3rem; }
  .ax-y { left: 0.3rem; top: 0.3rem; }
  .tk { color: var(--dim); }
  .tk-x { bottom: 0.3rem; transform: translateX(-50%); }
  .tk-y { left: 0.3rem; transform: translateY(-50%); }
  .ax-x { bottom: 1.6rem; }
  .side { display: flex; flex-direction: column; gap: 0.6rem; min-width: 0; }
  .curve { width: 100%; height: auto; aspect-ratio: 100 / 44; border: 1px solid var(--line); border-radius: 4px; background: var(--bg); display: block; }
  .curve polyline { fill: none; stroke: var(--accent); stroke-width: 1.2; vector-effect: non-scaling-stroke; }
  .axl { stroke: var(--line); stroke-width: 0.4; }
  .tick { font-size: 3.2px; fill: var(--dim); font-family: var(--mono); }
  .end { text-anchor: end; }
  .empty { font-size: 3.6px; fill: var(--dim); text-anchor: middle; font-family: system-ui, sans-serif; }
  .shapes { font-family: var(--mono); font-size: 0.82rem; color: var(--dim); display: flex; flex-wrap: wrap; gap: 0.2rem 0.5rem; }
  .arch { display: grid; gap: 0.35rem; width: 100%; }
  .row { display: flex; flex-wrap: wrap; gap: 0.3rem; align-items: center; }
  .k { color: var(--dim); font-size: 0.85rem; min-width: 8rem; }
  .sm { min-width: 2.4rem; padding: 0.25rem 0.55rem; font-family: var(--mono); }
  .sm.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  .chk { font-size: 0.88rem; color: var(--dim); display: flex; gap: 0.4rem; align-items: center; min-height: 2.1rem; }
  .chk input { accent-color: var(--accent); width: 1.05rem; height: 1.05rem; }
  .key { display: inline-flex; align-items: center; gap: 0.4rem; }
  .key i { width: 0.8rem; height: 0.8rem; border-radius: 50%; display: inline-block; }
  .k1 { background: var(--cat-1); }
  .k3 { background: var(--cat-3); }
</style>
