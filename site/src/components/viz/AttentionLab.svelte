<script lang="ts">
  /**
   * Attention as a weighted average, drawn: pick a word, see how strongly it looks at every word
   * (lines from its tip, thicker = more weight), and see its output built tip to tail from the
   * weighted word vectors. The tables on the right are the same numbers. Everything is computed
   * live with lib/num.ts (checked against numpy).
   */
  import { onMount } from 'svelte'
  import { Tween } from 'svelte/motion'
  import { reducedMotion } from '@lib/settings'
  import { cubicOut } from 'svelte/easing'
  import { attention } from '@lib/num'
  import { has, subscribe } from '@lib/progress'
  import Heatmap from './Heatmap.svelte'
  import MatrixGrid from './MatrixGrid.svelte'
  import LabFrame from './LabFrame.svelte'
  import { readable } from '@lib/readable'

  // A value that a question on the page asks for stays "?" until that question is solved.
  let { hide = {} }: { hide?: Record<string, string | undefined> } = $props()
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
  const locked = (k: string) => !!hide[k] && !solved[hide[k]!]

  const START = [[2, 0], [1, 1], [0, 2]]
  let X = $state(START.map((r) => [...r]))
  let scaled = $state(true)
  let q = $state(0) // the word whose output we draw
  let cell = $state<{ i: number; j: number } | null>(null)

  const words = ['cat', 'dog', 'car']
  // words are categories: the site's categorical palette (--cat-1 …), not ad-hoc hues
  const col = (j: number) => `var(--cat-${(j % 5) + 1})`
  const dk = 2
  const r = $derived(attention(X, X, X, scaled ? dk : 1))

  const presets: [string, number[][]][] = [
    ['Car becomes [5, 5]', [[2, 0], [1, 1], [5, 5]]],
    ['All three the same', [[1, 1], [1, 1], [1, 1]]],
    ['Cat and dog opposite', [[2, 0], [-1, 0], [0, 2]]],
  ]
  const f = (v: number) => (Math.abs(v) < 0.005 ? '0' : v.toFixed(2))

  // masks — score: cat↔dog score cells · outX: cat's output x · unscaledSelf: cat's self-weight with the scaling off
  const mScores = $derived(locked('score') ? [{ i: 0, j: 1 }, { i: 1, j: 0 }] : [])
  const mOut = $derived(locked('outX') ? [{ i: 0, j: 0 }] : [])
  const mWeights = $derived(!scaled && locked('unscaledSelf') ? [{ i: 0, j: 0 }] : [])
  const hidden = (list: { i: number; j: number }[], i: number, j: number) => list.some((c) => c.i === i && c.j === j)
  // drawing cat's output (or its self-weight line) would give an answer away, so the picture waits too
  const outHidden = $derived(q === 0 && mOut.length > 0)
  const weightHidden = (j: number) => hidden(mWeights, q, j)

  // focus follows hovering a table cell; otherwise the chosen word
  const focus = $derived(cell ? cell.i : q)
  $effect(() => {
    if (cell) q = cell.i
  })

  // animate the weights and the output point so the eye can follow what moved
  const dur = () => (reducedMotion() ? 0 : 220)
  const wT = new Tween([0.77, 0.19, 0.05], { duration: 220, easing: cubicOut })
  const oT = new Tween([1.72, 0.28], { duration: 220, easing: cubicOut })
  $effect(() => {
    const w = r.weights[focus]
    const o = r.out[focus]
    wT.set([...w], { duration: dur() })
    oT.set([...o], { duration: dur() })
  })

  // --- the plane ---
  // the plane zooms to fit the words (but holds still while you drag)
  const fitDomain = (m: number[][]) => {
    const all = m.flat()
    const lo = Math.min(-1, Math.floor(Math.min(...all)) - 1)
    const hi = Math.max(3, Math.ceil(Math.max(...all)) + 1)
    return [lo, hi] as [number, number]
  }
  let dom = $state<[number, number]>(fitDomain(START))
  $effect(() => {
    const d = fitDomain(X)
    if (dragging === null) dom = d
  })
  const D0 = $derived(dom[0]), D1 = $derived(dom[1])
  const ticks = $derived(Array.from({ length: D1 - D0 + 1 }, (_, k) => D0 + k).filter((t) => t !== 0 && t !== D0 && t !== D1))
  const sx = (x: number) => ((x - D0) / (D1 - D0)) * 100
  const sy = (y: number) => 100 - ((y - D0) / (D1 - D0)) * 100
  const snap = (v: number) => Math.min(D1, Math.max(D0, Math.round(v * 2) / 2))
  let svg: SVGSVGElement
  let dragging = $state<number | null>(null)
  function grab(i: number, e: PointerEvent) {
    dragging = i
    q = i
    svg.setPointerCapture(e.pointerId)
  }
  // keyboard: arrow keys move the focused word by one step (Shift: two steps)
  function nudge(i: number, e: KeyboardEvent) {
    const d = ({ ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, 1], ArrowDown: [0, -1] } as Record<string, number[]>)[e.key]
    if (!d) return
    e.preventDefault()
    const k = e.shiftKey ? 1 : 0.5
    const next = X.map((v) => [...v])
    next[i] = [snap(next[i][0] + d[0] * k), snap(next[i][1] + d[1] * k)]
    X = next
    q = i
  }
  function move(e: PointerEvent) {
    if (dragging === null) return
    const b = svg.getBoundingClientRect()
    const x = snap(D0 + ((e.clientX - b.left) / b.width) * (D1 - D0))
    const y = snap(D1 - ((e.clientY - b.top) / b.height) * (D1 - D0))
    const next = X.map((v) => [...v])
    next[dragging] = [x, y]
    X = next
  }
  function head(x0: number, y0: number, x1: number, y1: number, s = 2.6) {
    const dx = x1 - x0, dy = y1 - y0
    const L = Math.hypot(dx, dy)
    if (L < 1e-6) return ''
    const ux = dx / L, uy = dy / L
    const bx = x1 - ux * s, by = y1 - uy * s
    return `${x1},${y1} ${bx - uy * s * 0.55},${by + ux * s * 0.55} ${bx + uy * s * 0.55},${by - ux * s * 0.55}`
  }
  // the output as a chain: start at 0, add w0·x0, then w1·x1, then w2·x2
  const chain = $derived.by(() => {
    const pts: { from: number[]; to: number[]; j: number }[] = []
    let p = [0, 0]
    wT.current.forEach((w, j) => {
      const to = [p[0] + w * X[j][0], p[1] + w * X[j][1]]
      pts.push({ from: p, to, j })
      p = to
    })
    return pts
  })
</script>

<LabFrame
  title="Each word’s output is a weighted average of all the words"
  hint="Drag a word’s dot (or focus it and use the arrow keys). Point at or tap a weight to see who looks at whom."
  onreset={() => { X = START.map((row) => [...row]); scaled = true; q = 0; cell = null }}
>

  <div class="grid">
    <div class="col">
      <svg
        bind:this={svg} use:readable viewBox="0 0 100 100" role="application"
        aria-label="Word vectors. Drag a dot to move a word. The highlighted word's attention and output are drawn."
        onpointermove={move} onpointerup={() => (dragging = null)} onpointercancel={() => (dragging = null)}
      >
        {#each ticks as t}
          <line x1={sx(t)} y1="0" x2={sx(t)} y2="100" class="gl" />
          <line x1="0" y1={sy(t)} x2="100" y2={sy(t)} class="gl" />
          <text x={sx(t)} y={Math.min(97, sy(0) + 4)} class="tick">{t}</text>
        {/each}
        <line x1={sx(D0)} y1={sy(0)} x2={sx(D1)} y2={sy(0)} class="ax" />
        <line x1={sx(0)} y1={sy(D0)} x2={sx(0)} y2={sy(D1)} class="ax" />
        <text x="98" y={sy(0) - 1.5} class="axl end">x</text>
        <text x={sx(0) + 1.5} y="4" class="axl">y</text>

        <!-- attention lines: the focus word looks at every word; thicker = more weight -->
        {#each X as v, j}
          {#if weightHidden(j)}
            <!-- nothing: this weight is a question on the page -->
          {:else if j === focus}
            <!-- looking at itself: a ring around its own tip, wider = more weight -->
            <circle cx={sx(v[0])} cy={sy(v[1])} r={4 + 6 * wT.current[j]} class="self"
              style:stroke-width={0.4 + 2.4 * wT.current[j]} style:opacity={0.18 + 0.7 * wT.current[j]} />
          {:else}
            <line
              x1={sx(X[focus][0])} y1={sy(X[focus][1])} x2={sx(v[0])} y2={sy(v[1])}
              class="look" style:stroke-width={0.4 + 3.2 * wT.current[j]} style:opacity={0.18 + 0.7 * wT.current[j]}
            />
          {/if}
        {/each}

        <!-- input word vectors -->
        {#each X as v, j}
          {@const on = j === focus || (cell && cell.j === j)}
          <line x1={sx(0)} y1={sy(0)} x2={sx(v[0])} y2={sy(v[1])} stroke={col(j)} class="vec" class:faint={!on} />
          <polygon points={head(sx(0), sy(0), sx(v[0]), sy(v[1]))} fill={col(j)} class:faint={!on} />
          <!-- a ~44px invisible grab area around the visible dot (touch) -->
          <circle cx={sx(v[0])} cy={sy(v[1])} r="7" class="hit" onpointerdown={(e) => grab(j, e)} aria-hidden="true" />
          <circle
            cx={sx(v[0])} cy={sy(v[1])} r={dragging === j ? 4.4 : 3.4} fill={col(j)} class="dot"
            onpointerdown={(e) => grab(j, e)} onkeydown={(e) => nudge(j, e)} role="slider" tabindex="0"
            aria-label={`${words[j]}: drag, or use the arrow keys`} aria-valuetext={`[${v[0]}, ${v[1]}]`} aria-valuenow={v[0]}
          />
          <text x={sx(v[0]) + 4} y={sy(v[1]) - 3} class="tag" class:strong={j === focus}>{words[j]}</text>
        {/each}

        <!-- the focus word's output, built tip to tail -->
        {#if !outHidden}
          {#each chain as c}
            <line x1={sx(c.from[0])} y1={sy(c.from[1])} x2={sx(c.to[0])} y2={sy(c.to[1])} stroke={col(c.j)} class="seg" />
          {/each}
          <line x1={sx(0)} y1={sy(0)} x2={sx(oT.current[0])} y2={sy(oT.current[1])} class="out" />
          <polygon points={head(sx(0), sy(0), sx(oT.current[0]), sy(oT.current[1]), 3)} class="outhead" />
          <circle cx={sx(oT.current[0])} cy={sy(oT.current[1])} r="2.2" class="outdot" />
          <text x={sx(oT.current[0]) - 2} y={sy(oT.current[1]) - 3} class="tag out-tag end">{words[focus]}′</text>
        {/if}
      </svg>

      <div class="legend">
        <span><i class="sw look-sw"></i>how much {words[focus]} looks at each word</span>
        <span><i class="sw out-sw"></i>{words[focus]}′ = {words[focus]}’s output, the weighted mix (dashes: each word’s weight)</span>
      </div>

      <div class="ctl">
        <span class="lbl">Draw the output of</span>
        {#each words as w, j}
          <button class="lab-btn chip" aria-pressed={q === j} onclick={() => { q = j; cell = null }}><i class="dot" style:background={col(j)}></i>{w}</button>
        {/each}
      </div>
    </div>

    <div class="col tables">
      <MatrixGrid
        value={X} label="X (3 words × 2 numbers)" editable decimals={1}
        rowLabels={words} colLabels={['x', 'y']} hiRows={[focus]}
        onchange={(v) => (X = v)}
      />
      <div class="arrow">↓ <span>dot every word with every word{scaled ? ', divide by √2' : ''}</span></div>
      <MatrixGrid
        value={r.scores} label={scaled ? 'scores = X Xᵀ / √2' : 'scores = X Xᵀ'}
        rowLabels={words} colLabels={words} hiRows={[focus]} hiCols={cell ? [cell.j] : []} masked={mScores}
        onhover={(c) => (cell = c)}
      />
      <div class="arrow">↓ <span>softmax each row, so it adds up to 1</span></div>
      <Heatmap masked={mWeights}
        value={r.weights} label="weights"
        rowLabels={words} colLabels={words} hiRows={[focus]} hiCols={cell ? [cell.j] : []}
        onhover={(c) => (cell = c)}
      />
      <div class="arrow">↓ <span>mix the word vectors with those weights</span></div>
      <MatrixGrid value={r.out} label="output = weights @ X" rowLabels={words} colLabels={['x', 'y']} hiRows={[focus]} masked={mOut} />
    </div>
  </div>

  {#snippet controls()}
    <label class="sw-check"><input type="checkbox" bind:checked={scaled} /> divide the scores by √d_k (d_k = 2)</label>
    <span class="presets" role="group" aria-label="Try a preset">
      {#each presets as [name, v]}
        <button class="lab-btn" onclick={() => (X = v.map((row) => [...row]))}>{name}</button>
      {/each}
    </span>
  {/snippet}

  {#snippet readout()}
    {#if cell}
      <b>{words[cell.i]}</b> looks at <b>{words[cell.j]}</b>: score
      <code>{hidden(mScores, cell.i, cell.j) ? '?' : f(r.scores[cell.i][cell.j])}</code>, weight
      <code>{hidden(mWeights, cell.i, cell.j) ? '?' : f(r.weights[cell.i][cell.j])}</code>.
    {:else}
      <b>{words[q]}</b>’s output =
      {#each r.weights[q] as w, j}{j ? ' + ' : ''}<code>{hidden(mWeights, q, j) ? '?' : f(w)}</code>×{words[j]}{/each}
      = <code>{q === 0 && mOut.length ? '[?, ' + f(r.out[0][1]) + ']' : `[${f(r.out[q][0])}, ${f(r.out[q][1])}]`}</code>
    {/if}
    {#if outHidden}<span class="note">Cat’s output appears in the picture once you compute its x below.</span>{/if}
  {/snippet}
</LabFrame>

<style>
  .grid { display: grid; grid-template-columns: minmax(0, 340px) minmax(0, 1fr); gap: 1.4rem; align-items: start; }
  .col { display: flex; flex-direction: column; gap: 0.6rem; min-width: 0; }
  .tables { gap: 0.35rem; overflow-x: auto; }
  svg { width: 100%; aspect-ratio: 1; touch-action: pan-y; border: 1px solid var(--line); border-radius: 6px; background: var(--bg); }
  .gl { stroke: var(--line); stroke-width: 0.3; }
  .ax { stroke: var(--dim); stroke-width: 0.6; }
  .axl { font-size: 3.4px; fill: var(--dim); font-family: var(--mono); }
  .axl.end { text-anchor: end; }
  .tick { font-size: 3px; fill: var(--dim); font-family: var(--mono); text-anchor: middle; }
  .look { stroke: var(--accent); stroke-linecap: round; }
  .self { fill: none; stroke: var(--accent); }
  .vec { stroke-width: 1.5; stroke-linecap: round; transition: opacity 0.2s; }
  .faint { opacity: 0.35; }
  .hit { fill: transparent; cursor: grab; touch-action: none; }
  .dot { cursor: grab; stroke: var(--bg); stroke-width: 0.8; touch-action: none; }
  .dot:focus-visible { outline: none; stroke: var(--accent); stroke-width: 1.2; }
  .tag { font-size: 4px; fill: var(--dim); font-family: var(--mono); pointer-events: none; }
  .tag.strong { fill: var(--fg); font-weight: 700; }
  .seg { stroke-width: 1.1; stroke-dasharray: 1.4 1; stroke-linecap: round; }
  .out { stroke: var(--fg); stroke-width: 1.3; }
  .outhead, .outdot { fill: var(--fg); }
  .out-tag { fill: var(--fg); font-size: 4px; font-weight: 700; }
  .tag.end { text-anchor: end; }
  .legend { display: flex; flex-wrap: wrap; gap: 0.3rem 1rem; font-size: 0.76rem; color: var(--dim); }
  .legend span { display: inline-flex; align-items: center; gap: 0.35rem; }
  .sw { display: inline-block; width: 16px; height: 0; border-top: 3px solid var(--accent); opacity: 0.7; }
  .out-sw { border-top: 2px solid var(--fg); opacity: 1; }
  .ctl { display: flex; flex-wrap: wrap; align-items: center; gap: 0.35rem; }
  .lbl { font-size: 0.8rem; color: var(--dim); margin-right: 0.2rem; }
  /* the word's color sits in a dot; the button itself uses the shared "on" style */
  .chip { display: inline-flex; align-items: center; gap: 0.4rem; }
  .dot { width: 0.5rem; height: 0.5rem; border-radius: 50%; flex: none; }
  .arrow { font-size: 0.75rem; color: var(--dim); font-family: var(--mono); padding-left: 0.2rem; }
  .arrow span { font-family: inherit; }
  .sw-check { font-size: 0.85rem; display: flex; gap: 0.4rem; align-items: center; }
  .presets { display: flex; flex-wrap: wrap; gap: 0.35rem; }
  .presets :global(.lab-btn) { font-size: 0.8rem; padding: 0.25rem 0.6rem; }
  code { color: var(--fg); }
  .note { display: block; margin-top: 0.3rem; font-family: system-ui, sans-serif; font-size: 0.8rem; color: var(--dim); }
  @media (max-width: 720px) { .grid { grid-template-columns: minmax(0, 1fr); } svg { max-width: 360px; } }
</style>
