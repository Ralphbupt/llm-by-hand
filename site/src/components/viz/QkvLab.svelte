<script lang="ts">
  /**
   * Q, K, V: the same word gets three versions, X @ W_Q, X @ W_K, X @ W_V.
   * Toggle the projections off (Q = K = V = X) to see the scores turn symmetric again.
   */
  import { attention, matmul, transpose } from '@lib/num'
  import Heatmap from './Heatmap.svelte'
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

  const words = ['cat', 'dog', 'car']
  const I = [[1, 0], [0, 1]]
  let X = $state([[2, 0], [1, 1], [0, 2]])
  let WQ = $state(I.map((r) => [...r]))
  let WK = $state([[0, 0], [1, 0]])
  let WV = $state(I.map((r) => [...r]))
  let project = $state(true)
  let cell = $state<{ i: number; j: number } | null>(null)

  const Q = $derived(project ? matmul(X, WQ) : X)
  const K = $derived(project ? matmul(X, WK) : X)
  const V = $derived(project ? matmul(X, WV) : X)
  const r = $derived(attention(Q, K, V, 2))
  const raw = $derived(matmul(Q, transpose(K)))
  const symmetric = $derived(raw.every((row, i) => row.every((v, j) => Math.abs(v - raw[j][i]) < 1e-9)))
  const hiRows = $derived(cell ? [cell.i] : [])
  const hiCols = $derived(cell ? [cell.j] : [])

  const copy = (m: number[][]) => m.map((row) => [...row])
  // name, W_Q, W_K, W_V, and one line on what it does (shown under the buttons while it is on)
  const presets: [string, number[][], number[][], number[][], string][] = [
    ['All identity', I, I, I, 'All identity: Q, K and V are each word’s own vector, so a score is the plain dot product of two words.'],
    ['Swap the keys', I, [[0, 1], [1, 0]], I, 'Swap the keys: each key becomes [y, x], so a word now matches words that are strong where it is weak.'],
    ['One-way keys', I, [[0, 0], [1, 0]], I, 'One-way keys: each key is [y, 0], so cat can look at car, but car does not look at cat.'],
    ['V keeps only x', I, [[0, 0], [1, 0]], [[1, 0], [0, 0]], 'V keeps only x: each value is [x, 0], so the output only ever carries the first number.'],
  ]
  const active = $derived(project ? presets.find(([, q, k, v]) => same(WQ, q) && same(WK, k) && same(WV, v)) : undefined)
  const f = (v: number) => v.toFixed(2)
  // carCat: the score of car looking at cat stays "?" until that question is solved
  const mRaw = $derived(locked('carCat') ? [{ i: 2, j: 0 }] : [])
  const rawText = (i: number, j: number) => (mRaw.some((c) => c.i === i && c.j === j) ? '?' : f(raw[i][j]))
  const same = (a: number[][], b: number[][]) => a.every((row, i) => row.every((v, j) => v === b[i][j]))
  const changed = $derived(!project || !same(X, [[2, 0], [1, 1], [0, 2]]) || !same(WQ, I) || !same(WK, [[0, 0], [1, 0]]) || !same(WV, I))
  function resetAll() {
    X = [[2, 0], [1, 1], [0, 2]]
    WQ = copy(I); WK = [[0, 0], [1, 0]]; WV = copy(I)
    project = true
  }
</script>

<LabFrame
  title="Three roles for every word: a question (Q), a label (K) and content (V)"
  hint="Edit any number, or try a preset. Point at or tap a score to read how it was made."
  onreset={resetAll}
  resetDisabled={!changed}
>
  <div class="steps">
    <p class="step"><b>1</b> the words and the three projection matrices</p>
    <div class="row">
      <MatrixGrid value={X} label="X" editable decimals={1} rowLabels={words} onchange={(v) => (X = v)} />
      <div class="ws" class:off={!project}>
        <MatrixGrid value={WQ} label="W_Q" editable decimals={1} onchange={(v) => (WQ = v)} />
        <MatrixGrid value={WK} label="W_K" editable decimals={1} onchange={(v) => (WK = v)} />
        <MatrixGrid value={WV} label="W_V" editable decimals={1} onchange={(v) => (WV = v)} />
      </div>
    </div>

    <p class="step"><b>2</b> every word gets a query, a key and a value</p>
    <div class="row">
      <MatrixGrid value={Q} label={project ? 'Q = X W_Q' : 'Q = X'} rowLabels={words} hiRows={hiRows} />
      <MatrixGrid value={K} label={project ? 'K = X W_K' : 'K = X'} rowLabels={words} hiRows={hiCols} />
      <MatrixGrid value={V} label={project ? 'V = X W_V' : 'V = X'} rowLabels={words} />
    </div>

    <p class="step"><b>3</b> score each query against each key, softmax, mix the values</p>
    <div class="row">
      <div>
        <MatrixGrid value={raw} label="scores = Q Kᵀ" rowLabels={words} colLabels={words} {hiRows} {hiCols} masked={mRaw} onhover={(c) => (cell = c)} />
        <div class="badge" class:yes={symmetric} title={symmetric ? 'score(a, b) = score(b, a)' : 'a can look at b more than b looks at a'}>{symmetric ? 'symmetric' : 'not symmetric'}</div>
      </div>
      <Heatmap value={r.weights} label="weights = softmax(scores / √2)" rowLabels={words} colLabels={words} {hiRows} {hiCols} onhover={(c) => (cell = c)} />
      <MatrixGrid value={r.out} label="output = weights V" rowLabels={words} {hiRows} />
    </div>
  </div>

  {#snippet controls()}
    <label class="sw"><input type="checkbox" bind:checked={project} /> use projections W_Q, W_K, W_V</label>
    <span class="presets" role="group" aria-label="Presets">
      {#each presets as [name, q, k, v]}
        <button type="button" class="lab-btn" aria-pressed={active?.[0] === name} onclick={() => { WQ = copy(q); WK = copy(k); WV = copy(v); project = true }}>{name}</button>
      {/each}
    </span>
    <p class="pnote">{active ? active[4] : 'Your own numbers: no preset.'}</p>
  {/snippet}

  {#snippet readout()}
    {#if cell}
      {words[cell.i]}’s query [{Q[cell.i].map(f).join(', ')}] · {words[cell.j]}’s key [{K[cell.j].map(f).join(', ')}] = <b>{rawText(cell.i, cell.j)}</b>;
      reversed: <b>{rawText(cell.j, cell.i)}</b>
    {:else}
      <span class="idle">Pick a score. The question comes from the row word’s Q, the label from the column word’s K.</span>
    {/if}
  {/snippet}
</LabFrame>

<style>
  .steps { display: flex; flex-direction: column; gap: 0.8rem; }
  .row { display: flex; flex-wrap: wrap; gap: 1rem 1.4rem; align-items: flex-start; min-width: 0; }
  .ws { display: flex; flex-wrap: wrap; gap: 1rem; transition: opacity 0.2s; }
  .ws.off { opacity: 0.35; }
  .presets { display: inline-flex; flex-wrap: wrap; gap: 0.35rem; }
  .pnote { flex-basis: 100%; margin: 0; font-size: 0.85rem; color: var(--dim); }
  .sw { font-size: 0.88rem; display: inline-flex; gap: 0.45rem; align-items: center; min-height: 2.2rem; cursor: pointer; }
  .sw input { width: 1.1rem; height: 1.1rem; accent-color: var(--accent); }
  .step { font-size: 0.85rem; color: var(--dim); margin: 0; padding-top: 0.6rem; border-top: 1px solid var(--line); }
  .step:first-child { border-top: 0; padding-top: 0; }
  .step b { display: inline-grid; place-items: center; width: 1.35rem; height: 1.35rem; margin-right: 0.35rem; border-radius: 50%; background: var(--bg); border: 1px solid var(--field); color: var(--fg); font-size: 0.75rem; }
  /* a status line, not a control: plain text, no pill (a pill in accent reads as a pressed button) */
  .badge { margin-top: 0.4rem; font-size: 0.76rem; font-family: var(--mono); color: var(--fg); max-width: 15rem; }
  .badge.yes { color: var(--dim); }
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
  @media (prefers-reduced-motion: reduce) { .ws { transition: none; } }
</style>
