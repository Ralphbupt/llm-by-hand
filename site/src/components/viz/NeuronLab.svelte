<script lang="ts">
  /**
   * One neuron on four points: p = sigmoid(k · (w1·x1 + w2·x2 + b)).
   * The background is p. The line is where p = 0.5, the decision boundary.
   * Drag on the board to slide the line through the pointer; the sliders turn it.
   */
  import { onMount } from 'svelte'
  import { has, subscribe } from '@lib/progress'
  import LabFrame from './LabFrame.svelte'
  import { readable } from '@lib/readable'

  // z / p columns stay "?" until the question asking for them is solved
  let { hide = {} }: { hide?: { z?: string; p?: string } } = $props()
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
  const locked = (k: 'z' | 'p') => !!hide[k] && !solved[hide[k]!]

  const XS = [[0, 0], [0, 1], [1, 0], [1, 1]]
  const SETS: Record<string, number[]> = { AND: [0, 0, 0, 1], OR: [0, 1, 1, 1], XOR: [0, 1, 1, 0] }
  const LO = -0.25, HI = 1.25, GRID = 24

  let set = $state<'AND' | 'OR' | 'XOR'>('AND')
  let w1 = $state(1)
  let w2 = $state(1)
  let b = $state(-1.5)
  let k = $state(1)

  const sig = (z: number) => 1 / (1 + Math.exp(-z))
  const ys = $derived(SETS[set])
  const rows = $derived(
    XS.map((x, n) => {
      const z = k * (w1 * x[0] + w2 * x[1] + b)
      const p = sig(z)
      return { x, y: ys[n], z, p, guess: p > 0.5 ? 1 : 0 }
    }),
  )
  const correct = $derived(rows.filter((r) => r.guess === r.y).length)
  const loss = $derived(
    rows.reduce((s, r) => s - (r.y * Math.log(r.p + 1e-12) + (1 - r.y) * Math.log(1 - r.p + 1e-12)), 0) / 4,
  )
  const grid = $derived.by(() => {
    const g: number[][] = []
    for (let r = 0; r < GRID; r++) {
      const yy = HI - ((r + 0.5) / GRID) * (HI - LO)
      const row: number[] = []
      for (let c = 0; c < GRID; c++) {
        const xx = LO + ((c + 0.5) / GRID) * (HI - LO)
        row.push(sig(k * (w1 * xx + w2 * yy + b)))
      }
      g.push(row)
    }
    return g
  })

  const sx = (x: number) => ((x - LO) / (HI - LO)) * 100
  const sy = (y: number) => 100 - sx(y)

  // the boundary w1·x + w2·y + b = 0, clipped to the board
  const line = $derived.by(() => {
    const pts: [number, number][] = []
    if (Math.abs(w2) > 1e-9) {
      for (const x of [LO, HI]) pts.push([x, -(w1 * x + b) / w2])
    } else if (Math.abs(w1) > 1e-9) {
      for (const y of [LO, HI]) pts.push([-(w2 * y + b) / w1, y])
    }
    return pts
  })

  let dragging = false
  function at(e: PointerEvent) {
    const el = e.currentTarget as SVGSVGElement
    const r = el.getBoundingClientRect()
    const x = LO + ((e.clientX - r.left) / r.width) * (HI - LO)
    const y = HI - ((e.clientY - r.top) / r.height) * (HI - LO)
    b = Math.round(-(w1 * x + w2 * y) * 10) / 10
  }
  function down(e: PointerEvent) {
    dragging = true
    ;(e.currentTarget as Element).setPointerCapture(e.pointerId)
    at(e)
  }
  const move = (e: PointerEvent) => dragging && at(e)
  const up = () => (dragging = false)
  // arrow keys slide the line: b changes by 0.1 (Shift: 0.5)
  function key(e: KeyboardEvent) {
    const d = e.key === 'ArrowUp' || e.key === 'ArrowRight' ? 1 : e.key === 'ArrowDown' || e.key === 'ArrowLeft' ? -1 : 0
    if (!d) return
    e.preventDefault()
    b = Math.round(Math.max(-6, Math.min(6, b + d * (e.shiftKey ? 0.5 : 0.1))) * 10) / 10
  }

  function preset(a: number, c: number, d: number) {
    w1 = a; w2 = c; b = d; k = 1
  }
  function resetAll() {
    set = 'AND'
    preset(1, 1, -1.5)
  }
  const f = (v: number) => String(Number(v.toFixed(4)))
</script>

<LabFrame
  title="One neuron, four points"
  hint="Drag on the board, or use the arrow keys, to slide the line. The sliders turn and sharpen it."
  onreset={resetAll}
>
  <div class="pic">
    <div class="boardwrap">
      <svg
        viewBox="0 0 100 100" class="board" use:readable role="slider" tabindex="0" aria-valuenow={b} aria-valuetext={`b ${b.toFixed(1)}`}
        aria-label="Decision board: drag or use the arrow keys to move the boundary"
        onpointerdown={down} onpointermove={move} onpointerup={up} onpointercancel={up} onkeydown={key}
      >
        {#each grid as row, r}
          {#each row as p, c}
            <rect x={(c / GRID) * 100} y={(r / GRID) * 100} width={100 / GRID + 0.3} height={100 / GRID + 0.3} style="--p: {p}" />
          {/each}
        {/each}
        {#if line.length === 2}
          <line x1={sx(line[0][0])} y1={sy(line[0][1])} x2={sx(line[1][0])} y2={sy(line[1][1])} class="edge" />
        {/if}
        {#each rows as r}
          <circle cx={sx(r.x[0])} cy={sy(r.x[1])} r="4.4" class="pt" class:one={r.y === 1} />
          {#if r.guess !== r.y}<circle cx={sx(r.x[0])} cy={sy(r.x[1])} r="6.4" class="miss" />{/if}
          <text x={sx(r.x[0])} y={sy(r.x[1]) + 1.6} class="lbl" class:one={r.y === 1}>{r.y}</text>
        {/each}
        <text x="98" y="97" class="axis end">x1 →</text>
        <text x="2" y="6" class="axis">x2 ↑</text>
      </svg>
    </div>

    <div class="side">
      <p class="formula">p = sigmoid(k · (w1·x1 + w2·x2 + b))</p>
      <div class="scroll">
        <table>
          <thead><tr><th>x1, x2</th><th>target</th><th>z = k·(…)</th><th>p</th><th>says</th></tr></thead>
          <tbody>
            {#each rows as r}
              <tr class:miss={r.guess !== r.y}>
                <td>{r.x[0]}, {r.x[1]}</td><td>{r.y}</td><td>{#if locked('z')}<span class="q">?</span>{:else}{f(r.z)}{/if}</td><td>{#if locked('p')}<span class="q">?</span>{:else}{f(r.p)}{/if}</td><td>{r.guess}{r.guess === r.y ? ' ✓' : ' ✗'}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  </div>

  {#snippet controls()}
    <div class="seg" role="group" aria-label="Data">
      <span class="seg-l">Data</span>
      {#each Object.keys(SETS) as name}
        <button class="lab-btn seg" class:on={set === name} aria-pressed={set === name} onclick={() => (set = name as typeof set)}>{name}</button>
      {/each}
    </div>
    <div class="knobs">
      <label>w1 <input type="range" min="-4" max="4" step="0.1" bind:value={w1} /> <b>{w1.toFixed(1)}</b></label>
      <label>w2 <input type="range" min="-4" max="4" step="0.1" bind:value={w2} /> <b>{w2.toFixed(1)}</b></label>
      <label>b <input type="range" min="-6" max="6" step="0.1" bind:value={b} /> <b>{b.toFixed(1)}</b></label>
      <label>steepness k <input type="range" min="0.5" max="10" step="0.5" bind:value={k} /> <b>{k.toFixed(1)}</b></label>
    </div>
    <button class="lab-btn" onclick={() => preset(1, 1, -1.5)}>AND neuron (1, 1, −1.5)</button>
    <button class="lab-btn" onclick={() => preset(1, 1, -0.5)}>OR neuron (1, 1, −0.5)</button>
  {/snippet}

  {#snippet readout()}
    <span class:good={correct === 4}>{correct} / 4 correct</span> · loss (cross-entropy) {loss.toFixed(4)}
  {/snippet}

  {#snippet legend()}
    <span class="key"><i class="k-bg"></i>background: how sure the neuron is of 1 (stronger = surer)</span>
    <span class="key"><i class="k-one"></i>target 1</span>
    <span class="key"><i class="k-zero"></i>target 0</span>
    <span class="key"><i class="k-miss"></i>a wrong answer</span>
    <span class="key"><i class="k-edge"></i>p = 0.5, the decision line</span>
  {/snippet}
</LabFrame>

<style>
  .pic { display: grid; grid-template-columns: minmax(0, 280px) minmax(0, 1fr); gap: 1.2rem; align-items: start; }
  @media (max-width: 620px) { .pic { grid-template-columns: minmax(0, 1fr); } }
  .boardwrap, .side { min-width: 0; }
  .board { width: 100%; aspect-ratio: 1; border: 1px solid var(--line); border-radius: 6px; touch-action: none; cursor: crosshair; display: block; }
  .board:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  /* one hue: neutral where p ≈ 0, accent where p ≈ 1 */
  .board rect { fill: color-mix(in srgb, var(--accent) calc(var(--p) * 62%), var(--bg)); }
  .edge { stroke: var(--fg); stroke-width: 0.8; stroke-dasharray: 2 1.2; }
  .pt { fill: var(--bg); stroke: var(--fg); stroke-width: 1; }
  .pt.one { fill: var(--fg); stroke: var(--fg); }
  .miss { fill: none; stroke: var(--warn); stroke-width: 1.4; }
  .lbl { font-size: 4px; text-anchor: middle; fill: var(--fg); pointer-events: none; font-family: var(--mono); font-weight: 700; }
  .lbl.one { fill: var(--bg); }
  .axis { font-size: 3.6px; fill: var(--fg); font-family: var(--mono); }
  .end { text-anchor: end; }
  .formula { font-family: var(--mono); font-size: 0.85rem; color: var(--dim); margin: 0 0 0.4rem; }
  .scroll { overflow-x: auto; }
  table { font-family: var(--mono); font-size: 0.82rem; width: auto; }
  th, td { border: 1px solid var(--line); padding: 0.2rem 0.5rem; text-align: right; white-space: nowrap; }
  th { color: var(--dim); font-weight: 400; }
  tr.miss td { color: var(--warn); }
  .q { color: var(--warn); font-weight: 700; }
  .seg { display: inline-flex; align-items: center; gap: 0.35rem; margin-right: 0.6rem; }
  .seg-l { font-size: 0.88rem; color: var(--dim); }
  .knobs { display: flex; flex-wrap: wrap; gap: 0.3rem 1.1rem; width: 100%; font-size: 0.88rem; color: var(--dim); }
  .knobs label { display: flex; align-items: center; gap: 0.4rem; }
  .knobs input { width: 7.5rem; accent-color: var(--accent); }
  .knobs b { color: var(--fg); font-family: var(--mono); font-weight: 600; min-width: 2.5em; }
  .good { color: var(--ok); font-weight: 600; }
  .key { display: inline-flex; align-items: center; gap: 0.4rem; }
  .key i { flex: none; display: inline-block; width: 0.85rem; height: 0.85rem; border-radius: 50%; }
  .k-bg { border-radius: 2px !important; background: linear-gradient(90deg, var(--bg), color-mix(in srgb, var(--accent) 62%, var(--bg))); border: 1px solid var(--line); width: 1.4rem !important; }
  .k-one { background: var(--fg); }
  .k-zero { border: 1.5px solid var(--fg); }
  .k-miss { border: 2px solid var(--warn); }
  .k-edge { border-radius: 0 !important; height: 0 !important; width: 1rem !important; border-top: 2px dashed var(--fg); }
  .seg.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
</style>
