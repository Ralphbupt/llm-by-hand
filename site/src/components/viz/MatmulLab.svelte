<script lang="ts">
  /** Matmul lab: point at, tap or focus a cell of the result to see which row and column it comes from, term by term. */
  import { onMount } from 'svelte'
  import { matmul, shape } from '@lib/num'
  import { has, subscribe } from '@lib/progress'
  import MatrixGrid from './MatrixGrid.svelte'
  import LabFrame from './LabFrame.svelte'

  // hide: one cell of C stays "?" until the learner answers that question
  let { hide }: { hide?: { id: string; i: number; j: number } } = $props()
  let solved = $state(false)
  onMount(() => {
    if (!hide) return
    const sync = () => (solved = has(hide.id))
    sync()
    return subscribe(sync)
  })
  const masked = $derived(hide && !solved ? [{ i: hide.i, j: hide.j }] : [])
  const isMasked = (i: number, j: number) => masked.some((c) => c.i === i && c.j === j)

  const A0 = [[1, 2, 3], [0, 1, 0]]
  const B0 = [[1, 0], [0, 1], [1, 1]]
  let A = $state(A0.map((r) => [...r]))
  let B = $state(B0.map((r) => [...r]))
  const changed = $derived(JSON.stringify(A) !== JSON.stringify(A0) || JSON.stringify(B) !== JSON.stringify(B0))
  function resetAll() {
    A = A0.map((r) => [...r])
    B = B0.map((r) => [...r])
    cell = null
  }
  let cell = $state<{ i: number; j: number } | null>(null)

  const C = $derived.by(() => {
    try { return matmul(A, B) } catch { return null }
  })
  const sa = $derived(shape(A))
  const sb = $derived(shape(B))
  const terms = $derived(
    cell && C ? A[cell.i].map((v, k) => [v, B[k][cell!.j]] as [number, number]) : [],
  )

  /** Change k (columns of A = rows of B) on both sides so the product still works */
  function setK(k: number) {
    A = A.map((r) => Array.from({ length: k }, (_, j) => r[j] ?? 0))
    B = Array.from({ length: k }, (_, i) => B[i] ?? new Array(sb[1]).fill(0))
  }
  function setRows(n: number) {
    A = Array.from({ length: n }, (_, i) => A[i] ?? new Array(sa[1]).fill(0))
  }
  function setCols(m: number) {
    B = B.map((r) => Array.from({ length: m }, (_, j) => r[j] ?? 0))
  }
</script>

<LabFrame
  title="Multiply two matrices, one cell at a time"
  hint="Point at or tap a cell of C to see how it is computed. Every number in A and B can be edited."
  onreset={resetAll}
  resetDisabled={!changed}
>
  <div class="row">
    <MatrixGrid
      value={A} label="A" editable decimals={0}
      hiRows={cell ? [cell.i] : []}
      onchange={(v) => (A = v)}
    />
    <div class="grp">
      <span class="op">@</span>
      <MatrixGrid
        value={B} label="B" editable decimals={0}
        hiCols={cell ? [cell.j] : []}
        onchange={(v) => (B = v)}
      />
    </div>
    <div class="grp">
      <span class="op">=</span>
      {#if C}
        <MatrixGrid
          value={C} label="C" decimals={0} {masked}
          hiRows={cell ? [cell.i] : []} hiCols={cell ? [cell.j] : []}
          onhover={(c) => (cell = c)}
        />
      {:else}
        <span class="bad">Shapes don’t match</span>
      {/if}
    </div>
  </div>
  <div class="shapes">
    ({sa[0]}, <b>{sa[1]}</b>) @ (<b>{sb[0]}</b>, {sb[1]})
    {#if C}→ ({sa[0]}, {sb[1]}){:else}→ the two inner numbers must be equal{/if}
  </div>

  {#snippet controls()}
    <span class="knob">rows of A <b>{sa[0]}</b>
      <button class="lab-btn" aria-label="fewer rows of A" onclick={() => setRows(Math.max(1, sa[0] - 1))}>−</button>
      <button class="lab-btn" aria-label="more rows of A" onclick={() => setRows(Math.min(4, sa[0] + 1))}>+</button></span>
    <span class="knob">inner size <b>{sa[1]}</b>
      <button class="lab-btn" aria-label="smaller inner size" onclick={() => setK(Math.max(1, sa[1] - 1))}>−</button>
      <button class="lab-btn" aria-label="larger inner size" onclick={() => setK(Math.min(4, sa[1] + 1))}>+</button></span>
    <span class="knob">columns of B <b>{sb[1]}</b>
      <button class="lab-btn" aria-label="fewer columns of B" onclick={() => setCols(Math.max(1, sb[1] - 1))}>−</button>
      <button class="lab-btn" aria-label="more columns of B" onclick={() => setCols(Math.min(4, sb[1] + 1))}>+</button></span>
  {/snippet}

  {#snippet readout()}
    {#if cell && C}
      C[{cell.i}][{cell.j}] = row {cell.i} of A · column {cell.j} of B =
      {#each terms as [a, b], k}{k ? ' + ' : ''}{a}×{b}{/each}
      = <b>{isMasked(cell.i, cell.j) ? '? (answer the question below)' : C[cell.i][cell.j]}</b>
    {:else}
      <span class="idle">Pick a cell of C.</span>
    {/if}
  {/snippet}
</LabFrame>

<style>
  .row { display: flex; align-items: center; gap: 0.7rem; flex-wrap: wrap; }
  .grp { display: flex; align-items: center; gap: 0.7rem; }
  .op { color: var(--dim); font-family: var(--mono); align-self: center; padding-top: 1rem; }
  .bad { color: var(--warn); font-size: 0.85rem; }
  .shapes { margin-top: 0.7rem; font-family: var(--mono); font-size: 0.85rem; color: var(--dim); }
  .shapes b { color: var(--accent); }
  .knob { display: inline-flex; align-items: center; gap: 0.3rem; font-size: 0.82rem; color: var(--dim); margin-right: 0.6rem; }
  .knob b { color: var(--fg); font-family: var(--mono); min-width: 0.8rem; text-align: center; }
  .knob :global(.lab-btn) { min-width: 2.1rem; padding: 0.2rem 0.5rem; font-family: var(--mono); }
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
</style>
