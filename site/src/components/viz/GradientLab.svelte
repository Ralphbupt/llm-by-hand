<script lang="ts">
  /**
   * Gradient descent lab: three points, a line y = w·x + b, and the loss surface.
   * Move w and b by hand, or press "Take one step" and watch the gradient push them downhill.
   * Everything is computed live from the same formulas as demo.py.
   */
  import { onMount } from 'svelte'
  import { has, subscribe } from '@lib/progress'
  import Surface3D from '../viz3d/Surface3D.svelte'
  import LabFrame from './LabFrame.svelte'
  import { readable } from '@lib/readable'
  import { landMask } from './landMask'

  // Values that answer a question on the page stay hidden ("?") until that question is solved.
  //   loss: the error² column and the loss.  grad: the gradient columns and means.
  //   step: the step buttons stay locked, so the learner works out one step by hand first.
  let { hide = {} }: { hide?: { loss?: string; grad?: string; step?: string } } = $props()
  const mid = $props.id()
  let solved = $state<Record<string, boolean>>({})
  onMount(() => {
    const sync = () => {
      const next: Record<string, boolean> = {}
      for (const id of Object.values(hide)) if (id) next[id] = has(id)
      solved = next
    }
    sync()
    return subscribe(sync)
  })
  const locked = (k: 'loss' | 'grad' | 'step') => !!hide[k] && !solved[hide[k]!]

  const XS = [1, 2, 3]
  const YS = [2, 4, 6]
  const W0 = 0.5, B0 = 0, LR0 = 0.05

  // plot ranges
  const PX = [0, 4], PY = [-2, 10]
  const LW = [-1, 4], LB = [-3, 3]

  let w = $state(W0)
  let b = $state(B0)
  let lr = $state(LR0)
  let view = $state<string>('3d')
  const lossAt = (ww: number, bb: number) => stats(ww, bb).loss
  const snap = (v: number) => Math.round(v * 20) / 20
  let path = $state<{ w: number; b: number }[]>([{ w: W0, b: B0 }])
  let log = $state<{ k: number; w: number; b: number; loss: number; gw: number; gb: number; nw: number; nb: number }[]>([])

  function stats(w: number, b: number) {
    const rows = XS.map((x, i) => {
      const pred = w * x + b
      const err = pred - YS[i]
      return { x, y: YS[i], pred, err, gw: 2 * err * x, gb: 2 * err }
    })
    const mean = (f: (r: (typeof rows)[0]) => number) => rows.reduce((s, r) => s + f(r), 0) / rows.length
    return { rows, loss: mean((r) => r.err ** 2), gw: mean((r) => r.gw), gb: mean((r) => r.gb) }
  }

  const s = $derived(stats(w, b))
  const diverged = $derived(!Number.isFinite(s.loss) || s.loss > 1e6)

  function step(n = 1) {
    for (let i = 0; i < n; i++) {
      const cur = stats(w, b)
      if (!Number.isFinite(cur.loss) || cur.loss > 1e6) break
      const nw = w - lr * cur.gw
      const nb = b - lr * cur.gb
      log.push({ k: log.length + 1, w, b, loss: cur.loss, gw: cur.gw, gb: cur.gb, nw, nb })
      w = nw
      b = nb
      path.push({ w, b })
    }
  }

  function setByHand(nw: number, nb: number) {
    w = nw
    b = nb
    path = [{ w, b }]
    log = []
  }

  function reset() {
    lr = LR0
    setByHand(W0, B0)
  }

  // --- loss map: a smooth gray image, made once in the browser (same ramp as the 3D view: ln(1 + loss)) ---
  let maxLog = 0
  for (const ww of [LW[0], LW[1]]) for (const bb of [LB[0], LB[1]]) maxLog = Math.max(maxLog, Math.log1p(stats(ww, bb).loss))
  let land = $state('')
  onMount(() => {
    land = landMask((fx, fy) => Math.log1p(stats(LW[0] + fx * (LW[1] - LW[0]), LB[1] - fy * (LB[1] - LB[0])).loss) / maxLog)
  })

  const sx = (x: number) => ((x - PX[0]) / (PX[1] - PX[0])) * 100
  const sy = (y: number) => 100 - ((y - PY[0]) / (PY[1] - PY[0])) * 100
  const lx = (ww: number) => ((ww - LW[0]) / (LW[1] - LW[0])) * 100
  const ly = (bb: number) => ((LB[1] - bb) / (LB[1] - LB[0])) * 100

  // drag on the loss surface to set (w, b)
  let dragging = false
  function fromEvent(e: PointerEvent) {
    const el = e.currentTarget as SVGSVGElement
    const r = el.getBoundingClientRect()
    // the plot is the square 0..100 inside a viewBox of -9..100 × 0..108 (room for the ticks)
    const fx = Math.min(1, Math.max(0, (((e.clientX - r.left) / r.width) * 109 - 9) / 100))
    const fy = Math.min(1, Math.max(0, (((e.clientY - r.top) / r.height) * 108) / 100))
    const round = (v: number) => Math.round(v * 20) / 20
    setByHand(round(LW[0] + fx * (LW[1] - LW[0])), round(LB[1] - fy * (LB[1] - LB[0])))
  }
  function down(e: PointerEvent) {
    dragging = true
    ;(e.currentTarget as Element).setPointerCapture(e.pointerId)
    fromEvent(e)
  }
  const move = (e: PointerEvent) => dragging && fromEvent(e)
  const up = () => (dragging = false)
  // arrow keys move (w, b) on the map by 0.05; Shift moves by 0.25
  function key(e: KeyboardEvent) {
    const d = e.shiftKey ? 0.25 : 0.05
    const mv: Record<string, [number, number]> = { ArrowLeft: [-d, 0], ArrowRight: [d, 0], ArrowUp: [0, d], ArrowDown: [0, -d] }
    const m = mv[e.key]
    if (!m) return
    e.preventDefault()
    setByHand(snap(Math.min(LW[1], Math.max(LW[0], w + m[0]))), snap(Math.min(LB[1], Math.max(LB[0], b + m[1]))))
  }

  const f = (v: number, d = 4) => {
    if (!Number.isFinite(v)) return '∞'
    if (Math.abs(v) >= 1e5) return v.toExponential(2)
    return String(Number(v.toFixed(d)))
  }
  const last = $derived(log.at(-1))
</script>

<LabFrame
  title="Gradient descent on three points"
  hint="Move w and b by hand, or take steps. The line, the errors and the loss surface move together."
  views={[{ id: 'map', label: 'Map' }, { id: '3d', label: '3D' }]}
  bind:view
  onreset={reset}
>
  <div class="panes">
    <figure>
      <svg viewBox="0 0 100 100" class="plot" use:readable aria-label="Three data points and the line y = w·x + b">
        {#each [0, 2, 4, 6, 8] as gy}
          <line x1="8" x2="100" y1={sy(gy)} y2={sy(gy)} class="grid" />
          <text x="6" y={sy(gy) + 1.2} class="tick end">{gy}</text>
        {/each}
        {#each [1, 2, 3] as gx}
          <text x={sx(gx)} y="97" class="tick mid">{gx}</text>
        {/each}
        <text x="99" y="91" class="axis end">x →</text>
        <text x="9" y="5" class="axis">y</text>
        {#if !diverged}
          {#each s.rows as r}
            <line x1={sx(r.x)} x2={sx(r.x)} y1={sy(r.y)} y2={sy(r.pred)} class="resid" />
          {/each}
          <line x1={sx(PX[0])} x2={sx(PX[1])} y1={sy(w * PX[0] + b)} y2={sy(w * PX[1] + b)} class="fit" />
        {/if}
        {#each XS as x, i}
          <circle cx={sx(x)} cy={sy(YS[i])} r="2.4" class="pt" />
        {/each}
      </svg>
      <figcaption>The data, the line y = w·x + b, and each error as a dashed line.</figcaption>
    </figure>

    <figure>
      {#if view === '3d'}
        <Surface3D
          f={lossAt} xRange={[LW[0], LW[1]]} yRange={[LB[0], LB[1]]} zTransform={Math.log1p}
          path={path.map((p) => ({ x: p.w, y: p.b }))} point={diverged ? null : { x: w, y: b }} best={{ x: 2, y: 0 }}
          axes={{ x: 'w', y: 'b', z: 'loss' }} onpick={(x, y) => setByHand(snap(x), snap(y))} hover={!locked('loss')}
          step={diverged || locked('step') ? null : { x: w - lr * s.gw, y: b - lr * s.gb }}
          ariaLabel="Loss surface in 3D: height is ln(1 + loss) for each w and b"
        />
        <figcaption>Height is ln(1 + loss) for every (w, b): low is good, and the big losses are made much smaller so the bottom stays visible.</figcaption>
      {:else}
        <svg
          viewBox="-9 0 109 108" class="land" use:readable
          role="slider" aria-label="Loss map: drag, or use the arrow keys, to choose w and b" aria-valuenow={w} aria-valuetext={`w ${f(w, 2)}, b ${f(b, 2)}`} tabindex="0"
          onpointerdown={down} onpointermove={move} onpointerup={up} onpointercancel={up} onkeydown={key}
        >
          <defs><mask id={mid}><image href={land} x="0" y="0" width="100" height="100" preserveAspectRatio="none" /></mask></defs>
          <rect x="0" y="0" width="100" height="100" class="low" />
          {#if land}<rect x="0" y="0" width="100" height="100" class="high" mask="url(#{mid})" />{/if}
          <rect x="0" y="0" width="100" height="100" class="frame" />
          <circle cx={lx(2)} cy={ly(0)} r="2" class="best" />
          <polyline points={path.map((p) => `${lx(p.w)},${ly(p.b)}`).join(' ')} class="path" />
          {#if !diverged}<circle cx={lx(w)} cy={ly(b)} r="2.6" class="me" />{/if}
          {#each [0, 1, 2, 3] as tw}<text x={lx(tw)} y="104" class="tick mid">{tw}</text>{/each}
          {#each [-2, 0, 2] as tb}<text x="-1.5" y={ly(tb) + 1.2} class="tick end">{tb}</text>{/each}
          <text x="-1.5" y="4" class="tick end name">b</text>
          <text x="99" y="104" class="tick end name">w</text>
        </svg>
        <figcaption>Loss for every (w, b): the fainter the gray, the lower the loss. Drag or use the arrow keys to move.</figcaption>
      {/if}
    </figure>
  </div>

  {#if !diverged}
    <div class="scroll">
      <table>
        <thead><tr><th>x</th><th>y</th><th>w·x + b</th><th>error</th><th>error²</th><th>2·error·x</th><th>2·error</th></tr></thead>
        <tbody>
          {#each s.rows as r}
            <tr><td>{r.x}</td><td>{r.y}</td><td>{f(r.pred)}</td><td>{f(r.err)}</td>
              <td>{#if locked('loss')}<span class="q">?</span>{:else}{f(r.err ** 2)}{/if}</td>
              <td>{#if locked('grad')}<span class="q">?</span>{:else}{f(r.gw)}{/if}</td>
              <td>{#if locked('grad')}<span class="q">?</span>{:else}{f(r.gb)}{/if}</td></tr>
          {/each}
          <tr class="mean"><td colspan="4">mean</td>
            <td>loss = <b>{#if locked('loss')}<span class="q">?</span>{:else}{f(s.loss)}{/if}</b></td>
            <td>grad_w = <b>{#if locked('grad')}<span class="q">?</span>{:else}{f(s.gw)}{/if}</b></td>
            <td>grad_b = <b>{#if locked('grad')}<span class="q">?</span>{:else}{f(s.gb)}{/if}</b></td></tr>
        </tbody>
      </table>
    </div>
  {/if}

  {#snippet controls()}
    <div class="knobs">
      <label>w <input type="range" min="-1" max="4" step="0.05" value={w} oninput={(e) => setByHand(+e.currentTarget.value, b)} /> <b>{f(w, 3)}</b></label>
      <label>b <input type="range" min="-3" max="3" step="0.05" value={b} oninput={(e) => setByHand(w, +e.currentTarget.value)} /> <b>{f(b, 3)}</b></label>
      <label>learning rate <input type="range" min="0.01" max="0.25" step="0.01" bind:value={lr} /> <b>{lr.toFixed(2)}</b></label>
    </div>
    <button class="lab-btn primary" onclick={() => step(1)} disabled={diverged || locked('step')}>Take one step</button>
    <button class="lab-btn" onclick={() => step(10)} disabled={diverged || locked('step')}>10 steps</button>
    <button class="lab-btn" onclick={() => step(100)} disabled={diverged || locked('step')}>100 steps</button>
  {/snippet}

  {#snippet readout()}
    {#if diverged}
      <span class="warn">The loss is growing very fast: each step jumps past the lowest point and lands higher on the other side. Lower the learning rate and reset.</span>
    {:else if locked('step')}
      <span class="idle">The step buttons unlock once you compute one step by hand below.</span>
    {:else if last}
      Step {last.k}: w ← {f(last.w)} − {lr.toFixed(2)} × ({f(last.gw)}) = <b>{f(last.nw)}</b>,
      b ← {f(last.b)} − {lr.toFixed(2)} × ({f(last.gb)}) = <b>{f(last.nb)}</b>.
      Loss {f(last.loss)} → {f(s.loss)}.
    {:else}
      <span class="idle">Press “Take one step”. Each step moves w and b against their gradients.</span>
    {/if}
  {/snippet}

  {#snippet legend()}
    <span class="key"><i class="k-me"></i>you: (w, b) now</span>
    <span class="key"><i class="k-best"></i>the lowest loss, w = 2, b = 0</span>
    <span class="key"><i class="k-path"></i>the path of steps</span>
    <span class="key"><i class="k-err"></i>an error (prediction − y)</span>
  {/snippet}
</LabFrame>

<style>
  .panes { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
  @media (max-width: 560px) { .panes { grid-template-columns: minmax(0, 1fr); } }
  figure { margin: 0; min-width: 0; }
  figcaption { font-size: 0.8rem; color: var(--dim); margin-top: 0.3rem; line-height: 1.45; }
  svg { width: 100%; aspect-ratio: 1; border: 1px solid var(--line); border-radius: 6px; background: var(--bg); display: block; overflow: hidden; }
  .land { touch-action: none; cursor: crosshair; }
  .land:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .grid { stroke: var(--line); stroke-width: 0.3; }
  .tick { font-size: 3.4px; fill: var(--dim); font-family: var(--mono); }
  .axis { font-size: 3.6px; fill: var(--fg); font-family: var(--mono); }
  .mid { text-anchor: middle; }
  .end { text-anchor: end; }
  .resid { stroke: var(--warn); stroke-width: 0.7; stroke-dasharray: 1.2 1; }
  .fit { stroke: var(--accent); stroke-width: 0.9; }
  .pt { fill: var(--fg); }
  /* the neutral loss ramp of the 3D view (faint = low, a stronger gray = high): color stays for your point and the minimum */
  .land { aspect-ratio: 109 / 108; border: none; background: none; }
  .land .low { fill: color-mix(in srgb, var(--fg) 4%, var(--bg)); }
  .land .high { fill: color-mix(in srgb, var(--fg) 34%, var(--bg)); }
  .land .frame { fill: none; stroke: var(--line); stroke-width: 0.4; }
  .tick.name { fill: var(--fg); font-style: italic; }
  .path { fill: none; stroke: var(--fg); stroke-width: 0.6; }
  .me { fill: var(--accent); stroke: var(--bg); stroke-width: 0.7; }
  .best { fill: none; stroke: var(--ok); stroke-width: 0.8; }
  .knobs { display: flex; flex-wrap: wrap; gap: 0.4rem 1.2rem; font-size: 0.88rem; color: var(--dim); width: 100%; }
  .knobs label { display: flex; align-items: center; gap: 0.4rem; }
  .knobs input { width: 7rem; accent-color: var(--accent); }
  .knobs b { color: var(--fg); font-family: var(--mono); font-weight: 600; min-width: 3.2em; }
  .scroll { overflow-x: auto; margin-top: 0.8rem; }
  table { font-family: var(--mono); font-size: 0.82rem; width: auto; }
  th, td { border: 1px solid var(--line); padding: 0.2rem 0.5rem; text-align: right; white-space: nowrap; }
  th { color: var(--dim); font-weight: 400; }
  tr.mean td { color: var(--dim); }
  tr.mean b { color: var(--fg); }
  @media (max-width: 480px) { table { font-size: 0.74rem; } th, td { padding: 0.2rem 0.3rem; } tr.mean td { white-space: normal; } }
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
  .q { color: var(--warn); font-weight: 700; }
  .warn { font-family: system-ui, -apple-system, sans-serif; color: var(--warn); }
  .key { display: inline-flex; align-items: center; gap: 0.4rem; }
  .key i { flex: none; display: inline-block; }
  .k-me { width: 0.7rem; height: 0.7rem; border-radius: 50%; background: var(--accent); }
  .k-best { width: 0.7rem; height: 0.7rem; border-radius: 50%; border: 2px solid var(--ok); }
  .k-path { width: 1rem; height: 0; border-top: 2px solid var(--fg); }
  .k-err { width: 1rem; height: 0; border-top: 2px dashed var(--warn); }
</style>
