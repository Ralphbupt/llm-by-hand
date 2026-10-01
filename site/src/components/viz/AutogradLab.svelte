<script lang="ts">
  /**
   * Autograd lab: L = (a·b + c)·d as a graph that flows left → right.
   * One "Next step" button walks the forward pass (e, f, L), then the backward pass:
   * set L.grad = 1, then visit L, f, e in reverse order. Each visit sends gradient back along
   * the node's input edges, times the local factor written on the edge, exactly like
   * Value._backward() in the code on the page.
   * Gradients that a question asks for stay "?" until it is solved.
   */
  import { onMount } from 'svelte'
  import { has, subscribe } from '@lib/progress'
  import { readable } from '@lib/readable'
  import LabFrame from './LabFrame.svelte'

  let { hide = {} }: { hide?: Record<string, string> } = $props()
  let solved = $state<Record<string, boolean>>({})
  onMount(() => {
    const sync = () => {
      const next: Record<string, boolean> = {}
      for (const id of Object.values(hide)) next[id] = has(id)
      solved = next
    }
    sync()
    return subscribe(sync)
  })
  const masked = (n: string) => !!hide[n] && !solved[hide[n]]

  type N = 'a' | 'b' | 'c' | 'd' | 'e' | 'f' | 'L'
  type Leaf = 'a' | 'b' | 'c' | 'd'
  const START = { a: 2, b: 3, c: 1, d: -2 }
  let leaf = $state({ ...START })
  let fwd = $state(0) // 0..3: how many of e, f, L are computed
  let bwd = $state(0) // 0..4: 1 = L.grad set, 2 = L visited, 3 = f visited, 4 = e visited
  let log = $state<string[]>([])

  const val = $derived.by(() => {
    const e = leaf.a * leaf.b, f = e + leaf.c, L = f * leaf.d
    return { ...leaf, e, f, L } as Record<N, number>
  })
  const known = (n: N) => (n === 'e' ? fwd >= 1 : n === 'f' ? fwd >= 2 : n === 'L' ? fwd >= 3 : true)

  const grad = $derived.by(() => {
    const g: Partial<Record<N, number>> = {}
    const v = val
    if (bwd >= 1) g.L = 1
    if (bwd >= 2) { g.f = v.d; g.d = v.f }
    if (bwd >= 3) { g.e = g.f!; g.c = g.f! }
    if (bwd >= 4) { g.a = v.b * g.e!; g.b = v.a * g.e! }
    return g
  })

  const fmt = (x: number) => (Number.isInteger(x) ? String(x) : x.toFixed(2)).replace('-', '−')
  const G = (n: N) => (masked(n) ? '?' : fmt(grad[n]!))

  // ---- the steps -------------------------------------------------------------
  const FWD_LABEL = ['Compute e = a·b', 'Compute f = e + c', 'Compute L = f·d']
  const BWD_LABEL = ['Start backward: L.grad = 1', 'Send gradient from L to f and d', 'Send gradient from f to e and c', 'Send gradient from e to a and b']
  const done = $derived(bwd >= 4)
  const nextLabel = $derived(fwd < 3 ? FWD_LABEL[fwd] : bwd < 4 ? BWD_LABEL[bwd] : 'All gradients are computed')

  function next() {
    const v = val
    if (fwd < 3) {
      fwd += 1
      log = [...log, [
        `e = a · b = ${fmt(v.a)} × ${fmt(v.b)} = ${fmt(v.e)}`,
        `f = e + c = ${fmt(v.e)} + ${fmt(v.c)} = ${fmt(v.f)}`,
        `L = f · d = ${fmt(v.f)} × ${fmt(v.d)} = ${fmt(v.L)}`,
      ][fwd - 1]]
      return
    }
    if (bwd >= 4) return
    bwd += 1
    const ge = fmt(v.d)
    log = [...log, [
      'L.grad = 1   (L moves exactly as fast as L)',
      `L = f·d sends:  f.grad += d × 1 = ${fmt(v.d)}    d.grad += f × 1 = ${masked('d') ? '?' : fmt(v.f)}`,
      `f = e + c sends:  e.grad += 1 × ${ge} = ${ge}    c.grad += 1 × ${ge} = ${ge}`,
      `e = a·b sends:  a.grad += b × ${ge} = ${masked('a') ? '?' : fmt(v.b * v.d)}    b.grad += a × ${ge} = ${fmt(v.a * v.d)}`,
    ][bwd - 1]]
  }
  function runAll() { while (!done) next() }
  function clear() { fwd = 0; bwd = 0; log = [] }
  function reset() { leaf = { ...START }; clear() }
  function setLeaf(k: Leaf, raw: string) {
    const n = Number(raw)
    if (Number.isNaN(n)) return
    leaf = { ...leaf, [k]: n }
    clear()
  }
  const changed = $derived(Object.entries(START).some(([k, v]) => leaf[k as Leaf] !== v))

  // ---- layout ---------------------------------------------------------------------
  // Wide: the graph flows left → right (viewBox 648 × 206).
  // Narrow (phones): the same graph flows top → bottom (viewBox 350 × 380), so it fits without a sideways swipe.
  let labW = $state(700)
  const narrow = $derived(labW < 520)
  const OP = { w: 104, h: 58 }
  const LF = { w: 70, h: 44 }
  const H: Record<N, [number, number]> = {
    a: [44, 86], b: [44, 170], e: [204, 128],
    c: [278, 50], f: [392, 128],
    d: [480, 50], L: [588, 128],
  }
  const V: Record<N, [number, number]> = {
    a: [95, 30], b: [245, 30], e: [170, 126],
    c: [298, 236], f: [170, 236],
    d: [298, 346], L: [170, 346],
  }
  const C = $derived(narrow ? V : H)
  const viewBox = $derived(narrow ? '0 0 350 380' : '0 0 648 206')
  const isLeaf = (n: N) => 'abcd'.includes(n)
  const box = (n: N) => (isLeaf(n) ? LF : OP)
  // input edges: [from, to, offset where it enters `to`]
  const EDGES: { from: N; to: N; dy: number }[] = [
    { from: 'a', to: 'e', dy: -12 }, { from: 'b', to: 'e', dy: 12 },
    { from: 'c', to: 'f', dy: -12 }, { from: 'e', to: 'f', dy: 10 },
    { from: 'd', to: 'L', dy: -12 }, { from: 'f', to: 'L', dy: 10 },
  ]
  function pathH(from: N, to: N, dy: number) {
    const x2 = H[to][0] - box(to).w / 2 - 1, y2 = H[to][1] + dy
    const above = from === 'c' || from === 'd' // leaves parked above their op
    if (above) {
      // a leaf sitting above-left of its op: leave from the bottom, turn right into the op's left side
      const x1 = H[from][0], y1 = H[from][1] + box(from).h / 2
      return { d: `M${x1},${y1} C${x1},${y2} ${x1},${y2} ${x2},${y2}`, mx: x1 - 7, my: (y1 + y2) / 2 + 4, anchor: 'end' }
    }
    const x1 = H[from][0] + box(from).w / 2, y1 = H[from][1]
    const k = Math.max(18, (x2 - x1) / 2)
    // label above a → e, below the others, so no two labels meet
    const up = from === 'a'
    return { d: `M${x1},${y1} C${x1 + k},${y1} ${x2 - k},${y2} ${x2},${y2}`, mx: (x1 + x2) / 2, my: (y1 + y2) / 2 + (up ? -8 : 17), anchor: 'middle' }
  }
  function pathV(from: N, to: N) {
    if (from === 'c' || from === 'd') {
      // side leaf on the right of its op: a short arrow into the op's right edge
      const x1 = V[from][0] - LF.w / 2, x2 = V[to][0] + OP.w / 2 + 1, y = V[to][1]
      return { d: `M${x1},${y} L${x2},${y}`, mx: (x1 + x2) / 2, my: y - 7, anchor: 'middle' }
    }
    // from above: bottom of the source into the top of the target
    const off = from === 'a' ? -20 : from === 'b' ? 20 : 0
    const x1 = V[from][0], y1 = V[from][1] + box(from).h / 2
    const x2 = V[to][0] + off, y2 = V[to][1] - OP.h / 2 - 1
    const k = (y2 - y1) / 2
    const left = from === 'a' || from === 'e' || from === 'f'
    return { d: `M${x1},${y1} C${x1},${y1 + k} ${x2},${y2 - k} ${x2},${y2}`, mx: (x1 + x2) / 2 + (left ? -8 : 8), my: (y1 + y2) / 2 + 4, anchor: left ? 'end' : 'start' }
  }
  const path = (from: N, to: N, dy: number) => (narrow ? pathV(from, to) : pathH(from, to, dy))
  // which op's backward visit sends along this edge, and its local factor
  const VISIT: Record<N, number> = { L: 2, f: 3, e: 4, a: 0, b: 0, c: 0, d: 0 }
  function factor(from: N, to: N): string {
    const v = val
    if (to === 'f') return '× 1'
    const other: Record<string, N> = { a: 'b', b: 'a', f: 'd', d: 'f' }
    const o = other[from]
    // the factor on L → d is f, and f × 1 is exactly the answer to the d question
    if (masked(from)) return `× ${o}`
    return `× ${o} = ${fmt(v[o])}`
  }
  const edgeState = (to: N) => (bwd >= VISIT[to] && VISIT[to] > 0 ? (bwd === VISIT[to] ? 'now' : 'past') : '')
  const activeOp = $derived<N | null>(fwd < 3 ? null : bwd === 2 ? 'L' : bwd === 3 ? 'f' : bwd === 4 ? 'e' : null)
  const fwdNode = $derived<N | null>(bwd === 0 && fwd > 0 ? (['e', 'f', 'L'] as N[])[fwd - 1] : null)
  const OPTEXT: Record<string, string> = { e: 'e = a·b', f: 'f = e + c', L: 'L = f·d' }
</script>

<LabFrame
  title="Autograd, one node at a time: L = (a·b + c)·d"
  hint="Press the main button to compute forward, one node at a time, then send gradients back. Change an input to try other numbers."
  onreset={reset}
  resetDisabled={!changed}
>
  <div class="phase" aria-label="progress">
    <span class="ph" class:on={fwd < 3}>Forward</span>
    {#each [0, 1, 2] as i}<i class="dot" class:fill={fwd > i} class:cur={fwd === i}></i>{/each}
    <span class="arrow">▸</span>
    <span class="ph" class:on={fwd >= 3 && !done}>Backward</span>
    {#each [0, 1, 2, 3] as i}<i class="dot back" class:fill={bwd > i} class:cur={fwd >= 3 && bwd === i}></i>{/each}
  </div>

  <div class="scroll" bind:clientWidth={labW}>
    <svg use:readable {viewBox} class="graph" class:narrow role="img" aria-label="Computation graph of L = (a·b + c)·d, flowing {narrow ? 'top to bottom' : 'left to right'}">
      <defs>
        <marker id="ag-fwd" viewBox="0 0 10 10" refX="10" refY="5" markerUnits="userSpaceOnUse" markerWidth="9" markerHeight="9" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" class="ah" />
        </marker>
        <marker id="ag-bwd" viewBox="0 0 10 10" refX="10" refY="5" markerUnits="userSpaceOnUse" markerWidth="9" markerHeight="9" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" class="ah-b" />
        </marker>
      </defs>

      {#each EDGES as e}
        {@const p = path(e.from, e.to, e.dy)}
        {@const st = edgeState(e.to)}
        <path d={p.d} class="edge" class:lit={fwdNode === e.to} marker-end="url(#ag-fwd)" />
        {#if st}
          <!-- gradient flows back along the same edge: draw it again, reversed in direction -->
          <path d={p.d} class="bedge" class:now={st === 'now'} marker-start="url(#ag-bwd)" />
          <text x={p.mx} y={p.my} class="fac" class:now={st === 'now'} text-anchor={p.anchor}>{factor(e.from, e.to)}</text>
        {/if}
      {/each}

      {#each Object.keys(C) as k}
        {@const n = k as N}
        {@const b = box(n)}
        <g transform={`translate(${C[n][0] - b.w / 2}, ${C[n][1] - b.h / 2})`}>
          <rect width={b.w} height={b.h} rx="8" class="node" class:leaf={isLeaf(n)} class:hot={activeOp === n || fwdNode === n} />
          {#if isLeaf(n)}
            <text x={b.w / 2} y="18" class="lbl" text-anchor="middle">{n} = {fmt(val[n])}</text>
            {#if grad[n] !== undefined}<text x={b.w / 2} y="35" class="grd" text-anchor="middle">grad = {G(n)}</text>{/if}
          {:else}
            <text x={b.w / 2} y="18" class="lbl" text-anchor="middle">{OPTEXT[n]}</text>
            <text x={b.w / 2} y="34" class="val" class:unknown={!known(n)} text-anchor="middle">{known(n) ? `= ${fmt(val[n])}` : '= ?'}</text>
            {#if grad[n] !== undefined}<text x={b.w / 2} y="50" class="grd" text-anchor="middle">grad = {G(n)}</text>{/if}
          {/if}
        </g>
      {/each}
    </svg>
  </div>
  {#if log.length}<ol class="log" aria-label="What each step computed">{#each log as l}<li>{l}</li>{/each}</ol>{/if}

  {#snippet controls()}
    <button class="lab-btn primary" onclick={next} disabled={done}>{done ? 'Done' : nextLabel}</button>
    <button class="lab-btn" onclick={runAll} disabled={done}>Run all</button>
    <button class="lab-btn" onclick={clear} disabled={fwd === 0}>Clear</button>
    <span class="leaves">
      <span class="lh">Inputs</span>
      {#each ['a', 'b', 'c', 'd'] as k}
        {@const kk = k as Leaf}
        <label>{k} = <input type="number" step="1" value={leaf[kk]} onchange={(e) => setLeaf(kk, (e.currentTarget as HTMLInputElement).value)} /></label>
      {/each}
    </span>
  {/snippet}
  {#snippet readout()}
    {#if done}All gradients are computed. Press Clear to watch it again, or change an input.
    {:else if fwd === 0}Nothing computed yet. Press “Compute e = a·b” to compute the first node.
    {:else}{log.at(-1) ?? 'The forward pass is running.'}{/if}
  {/snippet}
  {#snippet legend()}
    <span><i class="sw f"></i>values flow forward</span>
    <span><i class="sw b"></i>gradients flow back, times the factor on each edge</span>
  {/snippet}
</LabFrame>

<style>
  .phase { display: flex; align-items: center; gap: 0.35rem; font-size: 0.78rem; color: var(--dim); margin-bottom: 0.5rem; flex-wrap: wrap; }
  .ph.on { color: var(--fg); font-weight: 700; }
  .arrow { margin: 0 0.2rem; }
  .dot { width: 9px; height: 9px; border-radius: 50%; border: 1.5px solid var(--accent); display: inline-block; }
  .dot.back { border-color: var(--grad); }
  .dot.fill { background: var(--accent); }
  .dot.back.fill { background: var(--grad); }
  .dot.cur { box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 30%, transparent); }
  .dot.back.cur { box-shadow: 0 0 0 3px color-mix(in srgb, var(--grad) 30%, transparent); }

  .scroll { overflow-x: auto; }
  .graph { width: 100%; display: block; }
  .graph.narrow { max-width: 380px; margin: 0 auto; }
  .edge { fill: none; stroke: var(--dim); stroke-width: 1.6; opacity: 0.7; }
  .edge.lit { stroke: var(--accent); opacity: 1; stroke-width: 2.2; }
  .ah { fill: var(--dim); }
  .ah-b { fill: var(--grad); }
  .bedge { fill: none; stroke: var(--grad); stroke-width: 2; opacity: 0.45; stroke-dasharray: 5 4; }
  .bedge.now { opacity: 1; stroke-width: 2.6; }
  .fac { font-family: var(--mono); font-size: 11px; fill: var(--grad); opacity: 0.7; paint-order: stroke; stroke: var(--card); stroke-width: 4px; }
  .fac.now { opacity: 1; font-weight: 700; }
  .node { fill: var(--bg); stroke: var(--dim); stroke-width: 1.2; transition: stroke 0.2s, stroke-width 0.2s; }
  .node.leaf { stroke-dasharray: 4 3; }
  .node.hot { stroke: var(--accent); stroke-width: 2.4; }
  .lbl { font-family: var(--mono); font-size: 13px; fill: var(--fg); font-weight: 700; }
  .val { font-family: var(--mono); font-size: 12.5px; fill: var(--fg); }
  .val.unknown { fill: var(--dim); opacity: 0.6; }
  .grd { font-family: var(--mono); font-size: 12px; fill: var(--grad); font-weight: 700; }
  .sw { display: inline-block; width: 1.1rem; height: 0; border-top: 2px solid var(--dim); margin-right: 0.3rem; vertical-align: middle; }
  .sw.b { border-top: 2px dashed var(--grad); }

  .leaves { display: inline-flex; flex-wrap: wrap; align-items: center; gap: 0.4rem 0.8rem; font-family: var(--mono); font-size: 0.85rem; }
  .lh { font-family: system-ui, sans-serif; color: var(--dim); font-size: 0.8rem; }
  .leaves input { width: 3.4rem; min-height: 2.1rem; font: inherit; padding: 0.1rem 0.3rem; border: 1px solid var(--field); border-radius: 4px; background: var(--bg); color: inherit; }
  .log { margin: 0.7rem 0 0; padding-left: 1.3rem; font-family: var(--mono); font-size: 0.76rem; overflow-x: auto; }
  .log li { white-space: pre-wrap; }
  @media (prefers-reduced-motion: reduce) { .node { transition: none; } }
</style>
