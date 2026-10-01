<script lang="ts">
  /**
   * Dot product lab: three draggable 2D arrows.
   * The table shows every pairwise dot product, each length, and cos(angle) = a·b / (|a||b|).
   */
  import { readable } from '@lib/readable'
  import LabFrame from './LabFrame.svelte'
  const NAMES = ['cat', 'dog', 'car']
  // all arrows share one neutral color; the pair you point at turns blue (color means "what you are looking at", not identity)
  const START = [[2, 1], [1.5, 1.5], [-1, 2]]
  let V = $state(START.map((v) => [...v]))
  let svg: SVGSVGElement
  let dragging = $state<number | null>(null)
  let pair = $state<[number, number] | null>(null)

  const D = 3
  const sx = (x: number) => ((x + D) / (2 * D)) * 100
  const sy = (y: number) => 100 - ((y + D) / (2 * D)) * 100
  const snap = (v: number) => Math.max(-D, Math.min(D, Math.round(v * 2) / 2))
  function move(e: PointerEvent) {
    if (dragging === null) return
    const r = svg.getBoundingClientRect()
    const next = V.map((v) => [...v])
    next[dragging] = [snap(-D + ((e.clientX - r.left) / r.width) * 2 * D), snap(D - ((e.clientY - r.top) / r.height) * 2 * D)]
    V = next
  }
  // keyboard: arrow keys move a focused arrow tip by 0.5
  function key(e: KeyboardEvent, i: number) {
    const d = { ArrowLeft: [-0.5, 0], ArrowRight: [0.5, 0], ArrowUp: [0, 0.5], ArrowDown: [0, -0.5] }[e.key]
    if (!d) return
    e.preventDefault()
    const next = V.map((v) => [...v])
    next[i] = [snap(V[i][0] + d[0]), snap(V[i][1] + d[1])]
    V = next
  }
  const changed = $derived(V.some((v, i) => v[0] !== START[i][0] || v[1] !== START[i][1]))
  const togglePair = (i: number, j: number) => (pair = pair && pair[0] === i && pair[1] === j ? null : [i, j])
  const dot = (a: number[], b: number[]) => a[0] * b[0] + a[1] * b[1]
  const len = (a: number[]) => Math.hypot(a[0], a[1])
  const pairs: [number, number][] = [[0, 1], [0, 2], [1, 2]]
  const rows = $derived(pairs.map(([i, j]) => {
    const d = dot(V[i], V[j])
    const l = len(V[i]) * len(V[j])
    return { i, j, d, cos: l === 0 ? null : d / l }
  }))
  const g = (v: number) => (Math.abs(v) < 1e-9 ? 0 : v)
  const on = (i: number) => pair !== null && pair.includes(i)
  // angle arc between the highlighted pair, drawn at radius 12 (viewBox units) around the origin
  const arc = $derived.by(() => {
    if (!pair) return null
    const [a, b] = pair.map((k) => Math.atan2(V[k][1], V[k][0]))
    if (len(V[pair[0]]) === 0 || len(V[pair[1]]) === 0) return null
    let d = b - a
    while (d > Math.PI) d -= 2 * Math.PI
    while (d < -Math.PI) d += 2 * Math.PI
    const R = 12, cx0 = sx(0), cy0 = sy(0)
    const p0 = [cx0 + R * Math.cos(a), cy0 - R * Math.sin(a)], p1 = [cx0 + R * Math.cos(a + d), cy0 - R * Math.sin(a + d)]
    const mid = a + d / 2
    return { path: `M ${p0[0]} ${p0[1]} A ${R} ${R} 0 0 ${d > 0 ? 0 : 1} ${p1[0]} ${p1[1]}`, lx: cx0 + (R + 5) * Math.cos(mid), ly: cy0 - (R + 5) * Math.sin(mid), deg: Math.abs((d * 180) / Math.PI) }
  })
</script>

<LabFrame
  title="Dot product: direction and length"
  hint="Drag an arrow tip (or focus it and use the arrow keys); tips move in steps of 0.5. Pick a pair to see its angle."
  onreset={() => { V = START.map((v) => [...v]); pair = null }}
  resetDisabled={!changed}
>
  <div class="cols">
    <svg bind:this={svg} viewBox="0 0 100 100" use:readable role="group" aria-label="Three arrows from the origin: cat, dog and car"
      onpointermove={move} onpointerup={() => (dragging = null)} onpointercancel={() => (dragging = null)}>
      {#each [-2, -1, 0, 1, 2] as t}
        <line x1={sx(t)} y1="0" x2={sx(t)} y2="100" class="grid" class:axis={t === 0} />
        <line x1="0" y1={sy(t)} x2="100" y2={sy(t)} class="grid" class:axis={t === 0} />
      {/each}
      <defs>
        <marker id="dot-head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" class="head" />
        </marker>
        <marker id="dot-head-on" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" class="head on" />
        </marker>
      </defs>
      <text x="98" y={sy(0) - 2} class="ax-l" text-anchor="end">x →</text>
      <text x={sx(0) + 2} y="5" class="ax-l">↑ y</text>
      {#if arc}<path d={arc.path} class="arc" /><text x={arc.lx} y={arc.ly + 1.5} class="arc-t" text-anchor="middle">{arc.deg.toFixed(0)}°</text>{/if}
      {#each V as v, i}
        {@const dim = pair !== null && !pair.includes(i)}
        <line x1={sx(0)} y1={sy(0)} x2={sx(v[0])} y2={sy(v[1])} class="vec" class:on={on(i)} class:dim marker-end={on(i) ? "url(#dot-head-on)" : "url(#dot-head)"} />
        <g class="tip" role="button" tabindex="0" aria-label={`${NAMES[i]} arrow tip at [${g(v[0])}, ${g(v[1])}]`}
          onpointerdown={(e) => { dragging = i; svg.setPointerCapture(e.pointerId) }} onkeydown={(e) => key(e, i)}>
          <circle cx={sx(v[0])} cy={sy(v[1])} r="7" class="hit" />
          <circle cx={sx(v[0])} cy={sy(v[1])} r="3.2" class="dot" class:on={on(i)} class:dim />
        </g>
        <text x={sx(v[0]) + 4} y={sy(v[1]) - 3} class="tag" class:dim>{NAMES[i]}</text>
      {/each}
    </svg>
    <div class="panel">
      <table>
        <thead><tr><th>word</th><th>vector</th><th>length</th></tr></thead>
        <tbody>
          {#each V as v, i}
            <tr class:hl={on(i)}><td>{NAMES[i]}</td><td>[{g(v[0])}, {g(v[1])}]</td><td>{len(v).toFixed(2)}</td></tr>
          {/each}
        </tbody>
      </table>
      <table>
        <thead><tr><th>pair</th><th>dot product</th><th>cos(angle)</th></tr></thead>
        <tbody>
          {#each rows as r}
            {@const isOn = pair !== null && pair[0] === r.i && pair[1] === r.j}
            <tr class:hl={isOn} onpointerenter={() => (pair = [r.i, r.j])} onpointerleave={() => (pair = null)}>
              <td><button type="button" class="pairbtn" aria-pressed={isOn} onclick={() => togglePair(r.i, r.j)}>{NAMES[r.i]}·{NAMES[r.j]}</button></td>
              <td class:neg={r.d < 0} class:pos={r.d > 0}>
                {g(V[r.i][0])}×{g(V[r.j][0])} + {g(V[r.i][1])}×{g(V[r.j][1])} = <b>{g(r.d)}</b>
              </td>
              <td>{r.cos === null ? '—' : g(r.cos).toFixed(3)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </div>

  {#snippet readout()}
    {#if pair && arc}
      {NAMES[pair[0]]}·{NAMES[pair[1]]}: angle {arc.deg.toFixed(0)}°, dot product {g(dot(V[pair[0]], V[pair[1]]))}
    {:else}
      <span class="idle">Pick a pair in the table to see its angle.</span>
    {/if}
  {/snippet}

  {#snippet legend()}
    <span><b class="pos">positive</b> dot product: roughly the same direction</span>
    <span><b>0</b>: at a right angle</span>
    <span><b class="neg">negative</b>: roughly opposite</span>
  {/snippet}
</LabFrame>

<style>
  .cols { display: flex; flex-wrap: wrap; gap: 1rem; }
  svg { width: 100%; max-width: 290px; aspect-ratio: 1; display: block; border: 1px solid var(--line); border-radius: 6px; background: var(--bg); touch-action: none; }
  .grid { stroke: var(--line); stroke-width: 0.3; }
  .grid.axis { stroke: var(--field); stroke-width: 0.5; }
  .vec { stroke: var(--fg); stroke-width: 1.2; stroke-linecap: round; opacity: 0.75; transition: opacity 0.15s; }
  .vec.on { stroke: var(--accent); opacity: 1; stroke-width: 1.5; }
  .head { fill: var(--fg); }
  .head.on { fill: var(--accent); }
  .hit { fill: transparent; cursor: grab; }
  .dot { fill: var(--fg); pointer-events: none; transition: cx 0.12s, cy 0.12s; }
  .dot.on { fill: var(--accent); }
  .tip:focus { outline: none; }
  .tip:focus-visible .dot { stroke: var(--accent); stroke-width: 1.2; }
  .arc { fill: none; stroke: var(--accent); stroke-width: 0.6; stroke-dasharray: 1.2 0.8; }
  .arc-t { font-size: 4px; fill: var(--accent); font-family: var(--mono); }
  .ax-l { font-size: 4px; fill: var(--dim); font-family: var(--mono); }
  .tag { font-size: 4.5px; fill: var(--fg); font-family: var(--mono); pointer-events: none; }
  .dim { opacity: 0.25; }
  @media (prefers-reduced-motion: reduce) { .vec, .dot { transition: none; } }
  .panel { flex: 1 1 260px; min-width: 0; overflow-x: auto; }
  table { font-family: var(--mono); font-size: 0.85rem; margin-bottom: 0.6rem; width: auto; }
  th, td { padding: 0.15rem 0.5rem; }
  tr.hl td { background: var(--highlight); }
  .pairbtn { font: inherit; padding: 0.2rem 0.4rem; min-height: 2rem; border: 1px solid var(--field); border-radius: 5px; background: var(--bg); color: var(--fg); cursor: pointer; }
  .pairbtn[aria-pressed='true'] { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  .pairbtn:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
  .neg b, b.neg { color: var(--neg); }
  .pos b, b.pos { color: var(--pos); }
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
</style>
