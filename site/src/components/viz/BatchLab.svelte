<script lang="ts">
  /**
   * Mini-batch lab: fit a line to four points, but each step only looks at a batch.
   * Batch size 4 walks smoothly downhill; batch size 1 zig-zags. Computed live (lib/training.ts).
   * Views: the loss surface (3D or flat map), the data with the batch this step used, and the loss after each step.
   */
  import { ALL, LINE_X, LINE_Y, lineGrad, rng, shuffled } from '@lib/training'
  import Surface3D from '../viz3d/Surface3D.svelte'
  import LabFrame from './LabFrame.svelte'
  import { readable } from '@lib/readable'
  import { onMount } from 'svelte'
  import { landMask } from './landMask'

  const W0 = 0.5, B0 = 0, LR0 = 0.02, BS0 = 1
  const LW: [number, number] = [-1, 4], LB: [number, number] = [-3, 3]
  const BEST = { w: 1.6, b: 1 }
  const BEST_LOSS = lineGrad(BEST.w, BEST.b, ALL).loss // 0.8: no line goes through all four points

  let bs = $state(BS0)
  let lr = $state(LR0)
  let w = $state(W0)
  let b = $state(B0)
  let view = $state('map')
  let path = $state<{ w: number; b: number }[]>([{ w: W0, b: B0 }])
  let losses = $state<number[]>([lineGrad(W0, B0, ALL).loss])
  let last = $state<{ idx: number[]; gw: number; gb: number; fw: number; fb: number } | null>(null)
  let r = rng(11)
  let queue: number[] = []

  function nextBatch(): number[] {
    const out: number[] = []
    while (out.length < bs) {
      if (!queue.length) queue = shuffled(4, r) // a new epoch: reshuffle
      out.push(queue.shift()!)
    }
    return out.sort((a, c) => a - c)
  }

  function step(n = 1) {
    for (let k = 0; k < n; k++) {
      const idx = nextBatch()
      const g = lineGrad(w, b, idx)
      const full = lineGrad(w, b, ALL)
      last = { idx, gw: g.gw, gb: g.gb, fw: full.gw, fb: full.gb }
      w -= lr * g.gw
      b -= lr * g.gb
      path.push({ w, b })
      losses.push(lineGrad(w, b, ALL).loss)
    }
  }

  function restart() {
    w = W0
    b = B0
    path = [{ w, b }]
    losses = [lineGrad(w, b, ALL).loss]
    last = null
    r = rng(11)
    queue = []
  }
  function reset() {
    bs = BS0
    lr = LR0
    restart()
  }
  const changed = $derived(bs !== BS0 || lr !== LR0 || path.length > 1)
  function setBs(v: number) {
    bs = v
    restart()
  }

  // ---- flat map of the loss surface: a smooth gray image, made once in the browser
  let maxLog = 0
  for (const ww of LW) for (const bb of LB) maxLog = Math.max(maxLog, Math.log1p(lineGrad(ww, bb, ALL).loss))
  const mid = $props.id()
  let land = $state('')
  onMount(() => {
    land = landMask((fx, fy) => Math.log1p(lineGrad(LW[0] + fx * (LW[1] - LW[0]), LB[1] - fy * (LB[1] - LB[0]), ALL).loss) / maxLog)
  })
  const lx = (ww: number) => ((ww - LW[0]) / (LW[1] - LW[0])) * 100
  const ly = (bb: number) => ((LB[1] - bb) / (LB[1] - LB[0])) * 100
  const lossAt = (ww: number, bb: number) => lineGrad(ww, bb, ALL).loss
  const path3d = $derived(path.map((p) => ({ x: Math.max(LW[0], Math.min(LW[1], p.w)), y: Math.max(LB[0], Math.min(LB[1], p.b)) })))

  // ---- data plot: x 0..5, y 0..9
  const dx = (x: number) => 6 + (x / 5) * 90
  const dy = (y: number) => 56 - (y / 9) * 52
  const used = $derived(new Set(last?.idx ?? []))

  // ---- loss after each step (log scale), with the best possible loss as a reference line
  const maxL = $derived(Math.max(...losses, 1e-9))
  const sy = (l: number) => 36 - (Math.log1p(l) / Math.log1p(maxL)) * 32
  const spark = $derived(losses.map((l, i) => `${8 + (i / Math.max(1, losses.length - 1)) * 90},${sy(l)}`).join(' '))
  const f = (v: number) => String(Number(v.toFixed(3)))
</script>

<LabFrame
  title="Mini-batches: each step sees only part of the data"
  hint="Pick a batch size and take steps. Batch size 4 walks straight downhill; batch size 1 zig-zags."
  views={[{ id: 'map', label: 'Map' }, { id: '3d', label: '3D' }]}
  bind:view
  onreset={reset}
  resetDisabled={!changed}
>
  <div class="panes">
    <figure>
      {#if view === '3d'}
        <Surface3D
          f={lossAt} xRange={LW} yRange={LB} zTransform={Math.log1p}
          path={path3d} point={{ x: Math.max(LW[0], Math.min(LW[1], w)), y: Math.max(LB[0], Math.min(LB[1], b)) }} best={{ x: BEST.w, y: BEST.b }}
          axes={{ x: 'w', y: 'b', z: 'loss' }}
          ariaLabel="Loss over all 4 points as a 3D surface, with the path of steps"
        />
      {:else}
        <svg viewBox="-9 0 109 108" class="land" use:readable aria-label="Loss surface over w and b with the path taken">
          <defs><mask id={mid}><image href={land} x="0" y="0" width="100" height="100" preserveAspectRatio="none" /></mask></defs>
          <rect x="0" y="0" width="100" height="100" class="low" />
          {#if land}<rect x="0" y="0" width="100" height="100" class="high" mask="url(#{mid})" />{/if}
          <rect x="0" y="0" width="100" height="100" class="frame" />
          <circle cx={lx(BEST.w)} cy={ly(BEST.b)} r="1.8" class="best" />
          <polyline points={path.map((p) => `${lx(p.w)},${ly(p.b)}`).join(' ')} class="path" />
          <circle cx={lx(w)} cy={ly(b)} r="2.2" class="me" />
          {#each [0, 1, 2, 3] as tw}<text x={lx(tw)} y="104" class="tick mid">{tw}</text>{/each}
          {#each [-2, 0, 2] as tb}<text x="-1.5" y={ly(tb) + 1.2} class="tick end">{tb}</text>{/each}
          <text x="99" y="104" class="tick end name">w</text>
          <text x="-1.5" y="4" class="tick end name">b</text>
        </svg>
      {/if}
      <figcaption>Loss over all 4 points for every (w, b): the fainter the gray, the lower the loss.</figcaption>
    </figure>

    <div class="col">
      <figure>
        <svg viewBox="-4 0 104 62" class="data" use:readable aria-label="The four points, the current line, and the points this step used">
          {#each [0, 3, 6, 9] as gy}
            <line x1="6" x2="96" y1={dy(gy)} y2={dy(gy)} class="grid" />
            <text x="3" y={dy(gy) + 1.2} class="tick end">{gy}</text>
          {/each}
          <line x1={dx(0)} x2={dx(5)} y1={dy(BEST.b)} y2={dy(BEST.w * 5 + BEST.b)} class="bestline" />
          <line x1={dx(0)} x2={dx(5)} y1={dy(b)} y2={dy(w * 5 + b)} class="fit" />
          {#each LINE_X as x, i}
            <circle cx={dx(x)} cy={dy(LINE_Y[i])} r={used.has(i) ? 2.6 : 1.8} class="pt" class:used={used.has(i)} />
            <text x={dx(x)} y="61" class="tick mid">x={x}</text>
          {/each}
        </svg>
        <figcaption>The 4 data points and your line.</figcaption>
      </figure>
      <figure>
        <svg viewBox="0 0 100 42" class="spark" use:readable aria-label="Loss on all four points after each step">
          <line x1="8" x2="98" y1={sy(BEST_LOSS)} y2={sy(BEST_LOSS)} class="floor" />
          <text x="98" y={sy(BEST_LOSS) - 1.2} class="tick end ok">best possible {f(BEST_LOSS)}</text>
          {#if losses.length > 1}
            <polyline points={spark} class="line" />
          {:else}
            <text x="53" y="22" class="tick mid">take a step to draw the loss</text>
          {/if}
          <text x="1" y="5" class="tick">loss</text>
          <text x="98" y="41" class="tick end">step →</text>
        </svg>
        <figcaption>Loss on all 4 points after each step ({losses.length - 1} so far). Now: <b>{f(losses.at(-1)!)}</b></figcaption>
      </figure>
    </div>
  </div>

  {#snippet controls()}
    <button class="lab-btn primary" onclick={() => step(1)}>Take one step</button>
    <button class="lab-btn" onclick={() => step(10)}>10 steps</button>
    <button class="lab-btn" onclick={() => step(100)}>100 steps</button>
    <span class="knob" role="group" aria-label="batch size">batch size
      {#each [1, 2, 4] as v}
        <button class="lab-btn seg" class:on={bs === v} aria-pressed={bs === v} onclick={() => setBs(v)}>{v === 4 ? '4 (full)' : v}</button>
      {/each}
    </span>
    <label class="knob">learning rate <input type="range" min="0.005" max="0.04" step="0.005" bind:value={lr} /> <b>{lr.toFixed(3)}</b></label>
  {/snippet}

  {#snippet readout()}
    {#if last}
      This step used point{last.idx.length > 1 ? 's' : ''}
      {last.idx.map((i) => `(${LINE_X[i]}, ${LINE_Y[i]})`).join(' ')}.
      Batch gradient: dL/dw = <b>{f(last.gw)}</b>, dL/db = <b>{f(last.gb)}</b>.
      The full-data gradient at the same spot was dL/dw = {f(last.fw)}, dL/db = {f(last.fb)}.
    {:else}
      <span class="idle">Start: w = 0.5, b = 0. Pick a batch size and take a few steps. Each epoch reshuffles the 4 points.</span>
    {/if}
  {/snippet}

  {#snippet legend()}
    <span><i class="sw acc"></i>your steps and your line</span>
    <span><i class="sw used"></i>point{bs > 1 ? 's' : ''} the last step used</span>
    <span><i class="sw okd"></i>the best line, w = 1.6, b = 1</span>
  {/snippet}
</LabFrame>

<style>
  .knob { display: inline-flex; align-items: center; gap: 0.35rem; font-size: 0.85rem; color: var(--dim); flex-wrap: wrap; }
  .knob b { color: var(--fg); font-family: var(--mono); font-variant-numeric: tabular-nums; }
  .knob input[type='range'] { width: 8rem; accent-color: var(--accent); }
  .seg { min-width: 2.4rem; }
  .seg.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  .panes { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr); gap: 1rem; }
  @media (max-width: 600px) { .panes { grid-template-columns: minmax(0, 1fr); } }
  .col { display: flex; flex-direction: column; gap: 0.8rem; min-width: 0; }
  figure { margin: 0; min-width: 0; }
  figcaption { font-size: 0.8rem; color: var(--dim); margin-top: 0.3rem; }
  figcaption b { font-family: var(--mono); color: var(--fg); }
  svg { width: 100%; display: block; overflow: visible; }
  .land { aspect-ratio: 109 / 108; }
  /* the neutral loss ramp of the 3D view (faint = low, a stronger gray = high): color stays for your point and the minimum */
  .land .low { fill: color-mix(in srgb, var(--fg) 4%, var(--bg)); }
  .land .high { fill: color-mix(in srgb, var(--fg) 34%, var(--bg)); }
  .land rect.frame { fill: none; stroke: var(--line); stroke-width: 0.4; }
  .best { fill: none; stroke: var(--ok); stroke-width: 0.8; }
  .path { fill: none; stroke: var(--accent); stroke-width: 0.6; stroke-linejoin: round; }
  .me { fill: var(--accent); stroke: var(--bg); stroke-width: 0.5; transition: cx 0.18s, cy 0.18s; }
  .tick { font-size: 3.4px; fill: var(--dim); font-family: var(--mono); }
  .tick.ok { fill: var(--ok); }
  .tick.name { fill: var(--fg); font-style: italic; }
  .mid { text-anchor: middle; }
  .end { text-anchor: end; }
  .data, .spark { border: 1px solid var(--line); border-radius: 4px; background: var(--bg); overflow: hidden; }
  .grid { stroke: var(--line); stroke-width: 0.25; }
  .fit { stroke: var(--accent); stroke-width: 0.7; }
  .bestline { stroke: var(--ok); stroke-width: 0.5; stroke-dasharray: 1.5 1.2; }
  .pt { fill: var(--bg); stroke: var(--fg); stroke-width: 0.5; transition: r 0.15s; }
  .pt.used { fill: var(--accent); stroke: var(--accent); }
  .spark .line { fill: none; stroke: var(--accent); stroke-width: 0.6; stroke-linejoin: round; }
  .floor { stroke: var(--ok); stroke-width: 0.35; stroke-dasharray: 1.5 1.2; }
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
  .sw { display: inline-block; width: 1.1rem; height: 0; border-top: 2px solid; vertical-align: 0.25rem; margin-right: 0.35rem; }
  .sw.acc { border-color: var(--accent); }
  .sw.okd { border-top-style: dashed; border-color: var(--ok); }
  .sw.used { width: 0.65rem; height: 0.65rem; border: 0; border-radius: 50%; background: var(--accent); vertical-align: -0.05rem; }
  @media (prefers-reduced-motion: reduce) { .me, .pt { transition: none; } }
</style>
