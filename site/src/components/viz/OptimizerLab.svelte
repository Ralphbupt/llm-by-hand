<script lang="ts">
  /**
   * Optimizer race on a narrow valley f(w1, w2) = 0.5·(w1² + 25·w2²), start (-4, 1).
   * SGD, momentum and Adam step side by side; the last update of each is written out with numbers.
   * Two views of the same race: a 3D surface (height = ln(1 + loss)) and a flat contour map.
   */
  import { onDestroy } from 'svelte'
  import { adamStep, momentumStep, optStart, ravine, ravineGrad, sgdStep, type OptState } from '@lib/training'
  import Surface3D from '../viz3d/Surface3D.svelte'
  import { reducedMotion } from '@lib/settings'
  import LabFrame from './LabFrame.svelte'
  import { readable } from '@lib/readable'

  const START: [number, number] = [-4, 1]
  const LR0 = 0.03, BETA0 = 0.9, ALR0 = 0.3
  const RX: [number, number] = [-5, 5], RY: [number, number] = [-1.6, 1.6]

  let lr = $state(LR0)
  let beta = $state(BETA0)
  let alr = $state(ALR0)
  let view = $state('map')
  type Run = { s: OptState; path: [number, number][]; dead: boolean }
  const fresh = (): Run => ({ s: optStart(START), path: [[...START]], dead: false })
  let runs = $state<{ sgd: Run; mom: Run; adam: Run }>({ sgd: fresh(), mom: fresh(), adam: fresh() })
  let lastG = $state<[number, number] | null>(null)

  function advance(run: Run, f: (s: OptState) => OptState) {
    if (run.dead) return
    run.s = f(run.s)
    run.path.push([...run.s.w])
    if (!Number.isFinite(ravine(...run.s.w)) || ravine(...run.s.w) > 1e4) run.dead = true
  }
  function step(n = 1) {
    for (let k = 0; k < n; k++) {
      lastG = ravineGrad(...runs.adam.s.w)
      advance(runs.sgd, (s) => sgdStep(s, lr))
      advance(runs.mom, (s) => momentumStep(s, lr, beta))
      advance(runs.adam, (s) => adamStep(s, alr))
    }
  }

  // "Play": one step every 120 ms for 60 steps, then stop (nothing loops forever)
  let timer: ReturnType<typeof setInterval> | null = null
  let playing = $state(false)
  function stop() {
    if (timer) clearInterval(timer)
    timer = null
    playing = false
  }
  function play() {
    if (playing) return stop()
    if (reducedMotion()) return step(60) // no animation: take the 60 steps at once
    playing = true
    let left = 60
    timer = setInterval(() => {
      step(1)
      if (--left <= 0) stop()
    }, 120)
  }
  onDestroy(stop)

  function restart() {
    stop()
    runs = { sgd: fresh(), mom: fresh(), adam: fresh() }
    lastG = null
  }
  function reset() {
    lr = LR0
    beta = BETA0
    alr = ALR0
    restart()
  }

  // ---- 2D map
  const px = (x: number) => ((x - RX[0]) / (RX[1] - RX[0])) * 100
  const py = (y: number) => ((RY[1] - y) / (RY[1] - RY[0])) * 60
  const clampPath = (p: [number, number][]) =>
    p.map(([a, b]) => `${px(Math.max(RX[0] - 1, Math.min(RX[1] + 1, a)))},${py(Math.max(RY[0] - 1, Math.min(RY[1] + 1, b)))}`).join(' ')
  const levels = [0.05, 0.3, 1, 3, 8, 20]
  const head = (r: Run) => r.path[r.path.length - 1]

  // ---- 3D: same paths, clamped to the drawn surface
  const clampXY = ([a, b]: [number, number]) => ({ x: Math.max(RX[0], Math.min(RX[1], a)), y: Math.max(RY[0], Math.min(RY[1], b)) })
  const paths3d = $derived([
    { points: runs.sgd.path.map(clampXY), color: 'cat-5' as const, label: 'SGD' },
    { points: runs.mom.path.map(clampXY), color: 'cat-3' as const, label: 'momentum' },
    { points: runs.adam.path.map(clampXY), color: 'cat-1' as const, label: 'Adam' },
  ])

  const f = (v: number, d = 4) => (Number.isFinite(v) ? String(Number(v.toFixed(d))) : '∞')
  const t = $derived(Math.max(runs.sgd.s.t, runs.mom.s.t, runs.adam.s.t))
  const changed = $derived(lr !== LR0 || beta !== BETA0 || alr !== ALR0 || t > 0)
  const rows = $derived([['SGD', runs.sgd, 'sgd'], ['momentum', runs.mom, 'mom'], ['Adam', runs.adam, 'adam']] as [string, Run, 'sgd' | 'mom' | 'adam'][])
  const dist = (r: Run) => Math.hypot(r.s.w[0], r.s.w[1])
  const leader = $derived.by(() => {
    if (t === 0) return null
    const alive = rows.filter(([, r]) => !r.dead)
    if (!alive.length) return null
    return alive.reduce((a, b) => (dist(b[1]) < dist(a[1]) ? b : a))[0]
  })
</script>

<LabFrame
  title="Three optimizers, one valley"
  hint="All three start at (−4, 1). Take steps or press Play and see which one reaches the minimum first."
  views={[{ id: 'map', label: 'Map' }, { id: '3d', label: '3D' }]}
  bind:view
  onreset={reset}
  resetDisabled={!changed}
>
  {#if view === '3d'}
    <Surface3D
      f={ravine} xRange={RX} yRange={RY} zTransform={Math.log1p} res={60}
      paths={paths3d} best={{ x: 0, y: 0 }} bestLabel="minimum" start={{ x: START[0], y: START[1] }} height={0.75} view={{ azimuth: 6, elevation: 44 }}
      aspect={(RY[1] - RY[0]) / (RX[1] - RX[0])}
      axes={{ x: 'w1', y: 'w2', z: 'loss' }}
      ariaLabel="The valley loss as a 3D surface, with the three optimizers' paths on it"
    />
    <p class="cap">Height is ln(1 + loss), so the very high parts don’t hide the bottom of the valley. {#if t === 0}Press Play to start the race.{/if}</p>
  {:else}
    <svg viewBox="-7 -3 109 70" use:readable aria-label="Ravine loss as a contour map with three optimizer paths">
      <rect x="0" y="0" width="100" height="60" class="plot" />
      <defs><clipPath id="opt-plot"><rect x="0" y="0" width="100" height="60" /></clipPath></defs>
      <g clip-path="url(#opt-plot)">
      {#each levels as L}
        <!-- ellipse 0.5(w1² + 25 w2²) = L → semi-axes √(2L) and √(2L/25) -->
        <ellipse cx={px(0)} cy={py(0)} rx={(Math.sqrt(2 * L) / (RX[1] - RX[0])) * 100} ry={(Math.sqrt((2 * L) / 25) / (RY[1] - RY[0])) * 60} class="lvl" />
      {/each}
      </g>
      <line x1="0" x2="100" y1={py(0)} y2={py(0)} class="axis" />
      <line x1={px(0)} x2={px(0)} y1="0" y2="60" class="axis" />
      <g clip-path="url(#opt-plot)">
        <polyline points={clampPath(runs.sgd.path)} class="p sgd" />
        <polyline points={clampPath(runs.mom.path)} class="p mom" />
        <polyline points={clampPath(runs.adam.path)} class="p adam" />
      </g>
      <text x={px(0) - 2} y={py(0) + 4.6} class="tick ok halo end">minimum (0, 0)</text>
      <circle cx={px(0)} cy={py(0)} r="1.3" class="best" />
      <circle cx={px(START[0])} cy={py(START[1])} r="1.6" class="start" />
      {#each rows as [, run, k]}
        {#if !run.dead}<circle cx={px(head(run)[0])} cy={py(head(run)[1])} r="1.2" class="hd {k}" />{/if}
      {/each}
      <text x={px(START[0]) + 2.5} y={py(START[1]) - 1.8} class="tick lbl">start (−4, 1)</text>
      {#each [-4, -2, 0, 2, 4] as tx}
        <line x1={px(tx)} x2={px(tx)} y1="60" y2="61.5" class="tk" />
        <text x={px(tx)} y="64.2" class="tick mid">{String(tx).replace('-', '−')}</text>
      {/each}
      {#each [-1, 0, 1] as ty}
        <line x1="-1.5" x2="0" y1={py(ty)} y2={py(ty)} class="tk" />
        <text x="-2.3" y={py(ty) + 1} class="tick end">{String(ty).replace('-', '−')}</text>
      {/each}
      <text x="100" y="66.5" class="tick end name">w1</text>
      <text x="-2.3" y="-0.5" class="tick end name">w2</text>
    </svg>
    <p class="cap">Each ring is one loss level. The rings are squeezed: the valley is 25 times steeper across (w2) than along (w1).</p>
  {/if}

  <div class="tbl">
    <table>
      <thead><tr><th></th><th>w1</th><th>w2</th><th>loss</th><th>to (0, 0)</th></tr></thead>
      <tbody>
        {#each rows as [name, run, k]}
          <tr class:lead={leader === name} class="main">
            <td class="nm"><i class="sw {k}"></i>{name}</td>
            {#if run.dead}
              <td colspan="4" class="bad">grew very large: each step jumps past the lowest point and lands farther away</td>
            {:else}
              <td>{f(run.s.w[0])}</td><td>{f(run.s.w[1])}</td><td>{f(ravine(...run.s.w))}</td><td>{f(dist(run), 3)}</td>
            {/if}
          </tr>
          {#if !run.dead}
            <tr class="eqrow"><td colspan="5">
              {#if t === 0}last update: —
              {:else if k === 'sgd'}w ← w − {lr.toFixed(2)}·g
              {:else if k === 'mom'}u ← {beta.toFixed(2)}·u + g = ({f(run.s.m[0], 3)}, {f(run.s.m[1], 3)}); w ← w − {lr.toFixed(2)}·u
              {:else}step = {alr.toFixed(2)}·m̂/√v̂ per weight; m = ({f(run.s.m[0], 3)}, {f(run.s.m[1], 3)}), v = ({f(run.s.v[0], 3)}, {f(run.s.v[1], 3)})
              {/if}
            </td></tr>
          {/if}
        {/each}
      </tbody>
    </table>
  </div>

  {#snippet controls()}
    <button class="lab-btn primary" onclick={() => step(1)}>One step</button>
    <button class="lab-btn" onclick={() => step(10)}>10 steps</button>
    <button class="lab-btn" onclick={play}>{playing ? 'Pause' : 'Play 60 steps'}</button>
    <span class="count">steps: {t}</span>
    <div class="knobs">
      <label>SGD and momentum lr <input type="range" min="0.01" max="0.1" step="0.01" bind:value={lr} oninput={restart} /> <b>{lr.toFixed(2)}</b></label>
      <label>momentum β <input type="range" min="0" max="0.99" step="0.01" bind:value={beta} oninput={restart} /> <b>{beta.toFixed(2)}</b></label>
      <label>Adam lr <input type="range" min="0.05" max="1" step="0.05" bind:value={alr} oninput={restart} /> <b>{alr.toFixed(2)}</b></label>
    </div>
  {/snippet}

  {#snippet readout()}
    {#if leader}After {t} step{t === 1 ? '' : 's'}, <b>{leader}</b> is closest to the bottom.{/if}
    The gradient is g = (w1, 25·w2): 25 times steeper across the valley than along it.
    {#if lastG}Adam’s gradient on the last step was ({f(lastG[0], 3)}, {f(lastG[1], 3)}).{/if}
  {/snippet}

  {#snippet legend()}
    <span><i class="sw sgd"></i>SGD</span>
    <span><i class="sw mom"></i>momentum</span>
    <span><i class="sw adam"></i>Adam</span>
    <span><i class="sw ok round"></i>minimum</span>
    <span><i class="sw ring round"></i>start</span>
  {/snippet}
</LabFrame>

<style>
  svg { width: 100%; display: block; overflow: visible; }
  .plot { fill: var(--bg); stroke: var(--line); stroke-width: 0.3; }
  .lvl { fill: none; stroke: var(--dim); stroke-width: 0.25; opacity: 0.55; }
  .axis { stroke: var(--line); stroke-width: 0.2; }
  .tk { stroke: var(--dim); stroke-width: 0.25; }
  .best { fill: var(--ok); }
  .start { fill: none; stroke: var(--fg); stroke-width: 0.45; }
  .p { fill: none; stroke-width: 0.6; stroke-linejoin: round; }
  .hd { stroke: var(--bg); stroke-width: 0.3; transition: cx 0.15s, cy 0.15s; }
  .p.sgd { stroke: var(--cat-5); } .hd.sgd, .sw.sgd { fill: var(--cat-5); background: var(--cat-5); }
  .p.mom { stroke: var(--cat-3); } .hd.mom, .sw.mom { fill: var(--cat-3); background: var(--cat-3); }
  .p.adam { stroke: var(--cat-1); } .hd.adam, .sw.adam { fill: var(--cat-1); background: var(--cat-1); }
  .sw { display: inline-block; width: 0.7rem; height: 0.7rem; border-radius: 2px; margin-right: 0.35rem; vertical-align: -0.05rem; }
  .sw.ok { background: var(--ok); }
  .sw.round { border-radius: 50%; }
  .sw.ring { background: transparent; border: 1.5px solid var(--fg); }
  .tick { font-size: 2px; fill: var(--dim); font-family: var(--mono); }
  .tick.ok { fill: var(--ok); }
  /* below-left of the minimum (the race ends on the point, not on its name), with a halo over the paths */
  .halo { paint-order: stroke; stroke: var(--bg); stroke-width: 0.9; stroke-linejoin: round; }
  .tick.lbl, .tick.name { fill: var(--fg); }
  .tick.name { font-style: italic; }
  .mid { text-anchor: middle; }
  .end { text-anchor: end; }
  .cap { margin: 0.35rem 0 0; font-size: 0.8rem; color: var(--dim); }
  .knobs { display: flex; flex-wrap: wrap; gap: 0.3rem 1.1rem; flex-basis: 100%; font-size: 0.85rem; color: var(--dim); }
  .knobs label { display: flex; align-items: center; gap: 0.4rem; min-height: 2.5rem; }
  .knobs input { width: 7rem; accent-color: var(--accent); }
  .knobs b { color: var(--fg); font-family: var(--mono); font-variant-numeric: tabular-nums; }
  .count { color: var(--dim); font-size: 0.8rem; font-family: var(--mono); }
  .tbl { overflow-x: auto; margin-top: 0.8rem; }
  table { font-size: 0.8rem; font-family: var(--mono); font-variant-numeric: tabular-nums; border-collapse: collapse; width: 100%; }
  th { white-space: nowrap; text-align: right; color: var(--dim); font-weight: 500; padding: 0 0 0.25rem 0.6rem; border-bottom: 1px solid var(--line); }
  td { text-align: right; white-space: nowrap; padding: 0.3rem 0 0 0.6rem; }
  td.nm { text-align: left; padding-left: 0; }
  tr.lead td.nm { font-weight: 700; }
  tr.eqrow td { font-size: 0.74rem; color: var(--dim); text-align: left; white-space: normal; padding: 0.05rem 0 0.35rem 1.05rem; border-bottom: 1px solid var(--line); overflow-wrap: anywhere; }
  .bad { color: var(--warn); text-align: left; white-space: normal; }
  @media (max-width: 480px) { table { font-size: 0.74rem; } th, td { padding-left: 0.35rem; } .sw { margin-right: 0.25rem; } }
  @media (prefers-reduced-motion: reduce) { .hd { transition: none; } }
</style>
