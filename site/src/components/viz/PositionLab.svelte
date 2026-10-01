<script lang="ts">
  /**
   * Positional encoding, as two labs (one idea each).
   * Lab 1: attention alone is order-blind — swap cat and car and cat's output is the same.
   *        Adding PE (a different vector for each position) fixes that.
   * Lab 2: the sin/cos stripes for 16 positions (or the sin columns as four small wave plots, one per pair).
   */
  import { addMat } from '@lib/num'
  import { positionalEncoding, selfAttention } from '@lib/parts'
  import MatrixGrid from './MatrixGrid.svelte'
  import LabFrame from './LabFrame.svelte'
  import { onMount } from 'svelte'
  import { has, subscribe } from '@lib/progress'

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

  const cat = [2, 0], dog = [1, 1], car = [0, 2]
  let usePE = $state(false)
  const PE2 = positionalEncoding(3, 2)
  const withPE = (X: number[][]) => (usePE ? addMat(X, PE2) : X)
  const A = $derived(withPE([cat, dog, car]))
  const B = $derived(withPE([car, dog, cat]))
  const catFirst = $derived(selfAttention(A).out[0])
  const catLast = $derived(selfAttention(B).out[2])
  const same = $derived(catFirst.every((v, i) => Math.abs(v - catLast[i]) < 1e-9))

  // stripes
  const N = 16, D = 8
  const PE = positionalEncoding(N, D)
  const ROW0 = 3
  let row = $state<number | null>(ROW0)
  let view = $state('stripes')
  // the even (sin) columns, one small plot per pair i: sin(p / 10000^(2i/D)). Only whole positions are real
  // rows of the table (dots); the thin line between them is the same formula, to show the wave's speed.
  const sinWave = (p: number, i: number) => Math.sin(p / 10000 ** ((2 * i) / D))
  const PAIRS = [0, 1, 2, 3]
  const WX = (p: number) => 6 + (p / (N - 1)) * 92
  const WY = (v: number) => 10 - v * 8
  const wavePath = (i: number) =>
    Array.from({ length: 121 }, (_, k) => { const p = (k / 120) * (N - 1); return `${k ? 'L' : 'M'}${WX(p).toFixed(2)},${WY(sinWave(p, i)).toFixed(2)}` }).join('')
  function pickWave(e: PointerEvent) {
    const r = (e.currentTarget as SVGSVGElement).getBoundingClientRect()
    const x = ((e.clientX - r.left) / r.width) * 100
    row = Math.min(N - 1, Math.max(0, Math.round(((x - 6) / 92) * (N - 1))))
  }
  function keyWave(e: KeyboardEvent) {
    const d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0
    if (!d) return
    e.preventDefault()
    row = Math.min(N - 1, Math.max(0, (row ?? -1) + d * (e.shiftKey ? 2 : 1)))
  }
  const cw = 100 / D, ch = 100 / N
  // signed values: the site's diverging pair (--pos / --neg), fading to the background at 0
  const color = (v: number) =>
    v >= 0 ? `color-mix(in srgb, var(--pos) ${Math.round(v * 85)}%, var(--bg))` : `color-mix(in srgb, var(--neg) ${Math.round(-v * 85)}%, var(--bg))`
  const f = (v: number) => v.toFixed(2)
  // pe01: PE[0][1] (and anything it can be read from) stays "?" until that question is solved
  const m10 = $derived(locked('pe01') ? [{ i: 0, j: 1 }] : [])
  const mAB = $derived(usePE ? m10 : [])
  const peText = (p: number) => PE[p].map((v, i) => (p === 0 && i === 1 && m10.length ? '?' : f(v))).join(', ')

  // point at, tap, or use the arrow keys to pick a row of the stripes
  function pickRow(e: PointerEvent) {
    const r = (e.currentTarget as SVGSVGElement).getBoundingClientRect()
    row = Math.min(N - 1, Math.max(0, Math.floor(((e.clientY - r.top) / r.height) * N)))
  }
  function keyRow(e: KeyboardEvent) {
    const d = e.key === 'ArrowDown' ? 1 : e.key === 'ArrowUp' ? -1 : 0
    if (!d) return
    e.preventDefault()
    row = Math.min(N - 1, Math.max(0, (row ?? -1) + d * (e.shiftKey ? 2 : 1)))
  }
</script>

<LabFrame
  title="Attention alone can’t see word order"
  hint="Compare cat’s output in the two orders. Then add positional encoding."
  onreset={() => (usePE = false)}
  resetDisabled={!usePE}
>
  <div class="pair">
    <div>
      <MatrixGrid value={A} label={usePE ? 'cat, dog, car + PE' : 'cat, dog, car'} rowLabels={['pos 0', 'pos 1', 'pos 2']} masked={mAB} />
      <div class="res">cat’s output: <code>[{catFirst.map(f).join(', ')}]</code></div>
    </div>
    <div>
      <MatrixGrid value={B} label={usePE ? 'car, dog, cat + PE' : 'car, dog, cat'} rowLabels={['pos 0', 'pos 1', 'pos 2']} masked={mAB} />
      <div class="res">cat’s output: <code>[{catLast.map(f).join(', ')}]</code></div>
    </div>
    {#if usePE}
      <MatrixGrid value={PE2} label="PE for positions 0–2: [sin(pos), cos(pos)]" rowLabels={['pos 0', 'pos 1', 'pos 2']} masked={m10} />
    {/if}
  </div>

  {#snippet controls()}
    <label class="sw"><input type="checkbox" bind:checked={usePE} /> add positional encoding (d = 2)</label>
  {/snippet}

  {#snippet readout()}
    <span class="verdict" class:diff={!same}>{same ? 'Same output. Attention does not know where cat is.' : 'Different output. Now the order matters.'}</span>
  {/snippet}
</LabFrame>

<LabFrame
  title="Positional encoding for 16 positions × 8 numbers"
  hint={view === 'stripes' ? 'Point at or tap a row (or focus the picture and use ↑ ↓) to read that position’s vector.' : 'Point at or tap a position (or focus a plot and use ← →) to read its vector.'}
  views={[{ id: 'stripes', label: 'Stripes' }, { id: 'waves', label: 'Waves' }]}
  bind:view
>
  {#if view === 'waves'}
    <p class="cap">The sin columns (0, 2, 4, 6), one plot each. A dot is one row of the table; the line between dots is the same sin, to show how fast it turns. Column 0 turns fast; column 6 has barely moved by position 15.</p>
    <div class="waves">
      {#each PAIRS as i}
        <div class="wave">
          <span class="wl">column {2 * i}<br /><small>pair {i}</small></span>
          <svg viewBox="0 0 100 20" preserveAspectRatio="none" role="slider" tabindex="0"
            aria-label={`Column ${2 * i}: sin value at each position`} aria-valuemin="0" aria-valuemax={N - 1} aria-valuenow={row ?? 0}
            aria-valuetext={row !== null ? `position ${row}: ${f(PE[row][2 * i])}` : 'none'}
            onpointermove={pickWave} onpointerdown={pickWave} onkeydown={keyWave}>
            <line x1="6" x2="98" y1={WY(0)} y2={WY(0)} class="zero" />
            <path d={wavePath(i)} class="curve" />
            {#if row !== null}<line x1={WX(row)} x2={WX(row)} y1="1" y2="19" class="cursor" />{/if}
            {#each PE as r, p}
              <!-- a zero-length line with round caps: a round dot even though the plot is stretched -->
              <line x1={WX(p)} x2={WX(p)} y1={WY(r[2 * i])} y2={WY(r[2 * i])} class="dot" class:pos={r[2 * i] >= 0} class:neg={r[2 * i] < 0} class:on={p === row} />
            {/each}
          </svg>
        </div>
      {/each}
      <div class="wave axis" aria-hidden="true"><span></span><div><span>pos 0</span><span>pos 15</span></div></div>
    </div>
  {:else}
    <div class="stripes">
      <span></span>
      <div class="cols" aria-hidden="true"><span>column 0 (fast)</span><span>column 7 (slow)</span></div>
      <div class="rows" aria-hidden="true"><span>pos 0</span><span>pos 15</span></div>
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" role="slider" tabindex="0"
        aria-label="Positional encoding stripes: pick a position" aria-valuemin="0" aria-valuemax={N - 1} aria-valuenow={row ?? 0}
        aria-valuetext={row !== null ? `position ${row}` : 'none'}
        onpointermove={pickRow} onpointerdown={pickRow} onkeydown={keyRow}>
        {#each PE as r, p}
          {#each r as v, i}
            {#if p === 0 && i === 1 && m10.length}
              <rect x={i * cw} y={p * ch} width={cw} height={ch} class="hid" />
            {:else}
              <rect x={i * cw} y={p * ch} width={cw} height={ch} fill={color(v)} />
            {/if}
          {/each}
        {/each}
        {#if row !== null}<rect x="0" y={row * ch} width="100" height={ch} class="ring" />{/if}
      </svg>
    </div>
  {/if}

  {#snippet readout()}
    {#if row !== null}
      position {row}: [{peText(row)}]
    {:else}
      Each row is one position’s vector. Left columns change fast from row to row, right columns slowly.
    {/if}
  {/snippet}

  {#snippet legend()}
    {#if view === 'stripes'}
      <span class="key"><i class="ramp"></i>−1 … 0 … +1</span>
      <span>Left columns change fast from row to row, right columns slowly.</span>
    {/if}
  {/snippet}
</LabFrame>

<style>
  .pair { display: flex; flex-wrap: wrap; gap: 1rem 1.6rem; align-items: flex-start; }
  .res { font-size: 0.82rem; margin-top: 0.35rem; color: var(--dim); }
  .res code { color: var(--fg); }
  .sw { font-size: 0.88rem; display: inline-flex; gap: 0.45rem; align-items: center; min-height: 2.5rem; cursor: pointer; }
  .sw input { width: 1.1rem; height: 1.1rem; accent-color: var(--accent); }
  .verdict { font-family: system-ui, -apple-system, sans-serif; font-weight: 600; }
  .verdict.diff { color: var(--ok); }
  .cap { margin: 0; font-size: 0.8rem; color: var(--dim); }
  .stripes { display: grid; grid-template-columns: 3rem minmax(0, 1fr); gap: 0.2rem 0.4rem; max-width: 20rem; }
  .cols { display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--dim); }
  .rows { display: flex; flex-direction: column; justify-content: space-between; font-size: 0.75rem; color: var(--dim); font-family: var(--mono); text-align: right; }
  .stripes svg { width: 100%; aspect-ratio: 1 / 1.4; display: block; border: 1px solid var(--line); touch-action: pan-y; cursor: crosshair; }
  .stripes svg:focus-visible, .wave svg:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .ring { fill: none; stroke: var(--accent); stroke-width: 2; vector-effect: non-scaling-stroke; }
  .hid { fill: var(--card); stroke: var(--warn); stroke-width: 1.5; vector-effect: non-scaling-stroke; }
  .key { display: inline-flex; align-items: center; gap: 0.4rem; font-family: var(--mono); }
  .key i.ramp { width: 4.5rem; height: 0.7rem; border-radius: 2px; border: 1px solid var(--line);
    background: linear-gradient(to right, color-mix(in srgb, var(--neg) 85%, var(--bg)), var(--bg), color-mix(in srgb, var(--pos) 85%, var(--bg))); }
  .waves { display: grid; gap: 0.35rem; max-width: 34rem; margin-top: 0.5rem; }
  .wave { display: grid; grid-template-columns: 4.2rem minmax(0, 1fr); gap: 0.4rem; align-items: center; }
  .wl { font-family: var(--mono); font-size: 0.75rem; color: var(--dim); line-height: 1.2; text-align: right; }
  .wave svg { width: 100%; height: 3.4rem; display: block; border: 1px solid var(--line); border-radius: 3px; touch-action: pan-y; cursor: crosshair; overflow: visible; }
  .wave.axis div { display: flex; justify-content: space-between; font-family: var(--mono); font-size: 0.72rem; color: var(--dim); padding: 0 1% 0 5%; }
  .wave .zero { stroke: var(--line); stroke-width: 1; vector-effect: non-scaling-stroke; }
  .wave .curve { fill: none; stroke: var(--dim); stroke-width: 1; opacity: 0.6; vector-effect: non-scaling-stroke; }
  .wave .cursor { stroke: var(--accent); stroke-width: 1.5; vector-effect: non-scaling-stroke; }
  .wave .dot { stroke-width: 7px; stroke-linecap: round; vector-effect: non-scaling-stroke; }
  .wave .dot.pos { stroke: var(--pos); }
  .wave .dot.neg { stroke: var(--neg); }
  .wave .dot.on { stroke: var(--accent); stroke-width: 11px; }
</style>
