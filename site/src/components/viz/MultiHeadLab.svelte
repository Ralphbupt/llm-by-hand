<script lang="ts">
  /**
   * Multi-head attention: d_model = 4, 2 heads, d_k = 2.
   * Head h owns columns 2h, 2h+1 of Q, K, V. Each head runs ordinary attention on its own columns.
   * The head outputs sit side by side in concat; rows 2h, 2h+1 of W_O read head h.
   */
  import { attention, matmul } from '@lib/num'
  import Heatmap from './Heatmap.svelte'
  import MatrixGrid from './MatrixGrid.svelte'
  import LabFrame from './LabFrame.svelte'
  import Tensors3D from '../viz3d/Tensors3D.svelte'

  const words = ['cat', 'dog', 'car']
  const X0 = [[2, 0, 1, 0], [1, 1, 0, 1], [0, 2, 1, 1]]
  const WO0 = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
  let X = $state(X0.map((r) => [...r]))
  let swap2 = $state(true)
  let head = $state(0)
  let WO = $state(WO0.map((r) => [...r]))

  // W_Q = W_V = identity; W_K is identity for head 0 and (optionally) swaps head 1's two key numbers
  const WK = $derived([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, swap2 ? 0 : 1, swap2 ? 1 : 0], [0, 0, swap2 ? 1 : 0, swap2 ? 0 : 1]])
  const K = $derived(matmul(X, WK))
  const cols = (m: number[][], h: number) => m.map((r) => r.slice(2 * h, 2 * h + 2))
  const heads = $derived([0, 1].map((h) => attention(cols(X, h), cols(K, h), cols(X, h), 2)))
  const concat = $derived(heads[0].out.map((r, i) => [...r, ...heads[1].out[i]]))
  const out = $derived(matmul(concat, WO))
  const mine = $derived([2 * head, 2 * head + 1])
  let view = $state('numbers')

  const same = (a: number[][], b: number[][]) => a.every((row, i) => row.every((v, j) => v === b[i][j]))
  const changed = $derived(!swap2 || head !== 0 || !same(X, X0) || !same(WO, WO0))
  function reset() { X = X0.map((r) => [...r]); WO = WO0.map((r) => [...r]); swap2 = true; head = 0 }

  // the same computation as shapes: X splits into heads (depth = head), each head attends, concat joins them back
  const shapes3d = $derived([
    { shape: [3, 4], title: 'X (3, 4)', axes: ['L', 'd_model'], highlight: [{ from: [0, 0, mine[0]] as [number, number, number], to: [0, 2, mine[1]] as [number, number, number] }] },
    '→',
    { shape: [2, 3, 2], title: 'per head (2, 3, 2)', axes: ['head', 'L', 'd_k'], highlight: [{ from: [head, 0, 0] as [number, number, number], to: [head, 2, 1] as [number, number, number] }] },
    '→',
    { shape: [2, 3, 3], title: 'weights (2, 3, 3)', axes: ['head', 'L', 'L'], highlight: [{ from: [head, 0, 0] as [number, number, number], to: [head, 2, 2] as [number, number, number] }] },
    '→',
    { shape: [3, 4], title: 'concat (3, 4)', axes: ['L', '2·d_k'], highlight: [{ from: [0, 0, mine[0]] as [number, number, number], to: [0, 2, mine[1]] as [number, number, number] }] },
    '@',
    { shape: [4, 4], title: 'W_O (4, 4)', highlight: [{ from: [0, mine[0], 0] as [number, number, number], to: [0, mine[1], 3] as [number, number, number] }] },
  ])
</script>

<LabFrame
  title="Two heads, each on separate columns, mixed back together by W_O"
  hint="Pick a head to see which numbers it owns. X and W_O can be edited."
  views={[{ id: 'numbers', label: 'Numbers' }, { id: '3d', label: '3D shapes' }]}
  bind:view
  onreset={reset}
  resetDisabled={!changed}
>
  {#if view === '3d'}
    <Tensors3D tensors={shapes3d} height="min(300px, 80vw)" ariaLabel="Multi-head attention as shapes: X splits into two heads, each head attends, concat joins them, W_O mixes them" />
    <ol class="flow">
      <li>split d_model into heads</li><li>each head attends separately</li><li>concat the heads</li><li>W_O mixes them</li>
    </ol>
  {:else}
    <div class="steps">
      <p class="step"><b>1</b> the words; W_Q and W_V are the identity, so Q = V = X</p>
      <div class="row">
        <MatrixGrid value={X} label="X (3 words × d_model 4) = Q = V" editable decimals={1} rowLabels={words} colLabels={['0', '1', '2', '3']} hiCols={mine} onchange={(v) => (X = v)} />
        <MatrixGrid value={K} label="K = X W_K" rowLabels={words} colLabels={['0', '1', '2', '3']} hiCols={mine} />
      </div>

      <p class="step"><b>2</b> each head attends using only its own two columns</p>
      <div class="row">
        {#each heads as r, h}
          <div class="h" class:faded={h !== head}>
            <Heatmap value={r.weights} label={`head ${h} weights (columns ${2 * h}, ${2 * h + 1})`} rowLabels={words} colLabels={words} />
          </div>
        {/each}
      </div>

      <p class="step"><b>3</b> the head outputs sit side by side; W_O mixes them into one output</p>
      <div class="row">
        <MatrixGrid value={concat} label="concat(head 0, head 1) (3 × 4)" rowLabels={words} colLabels={['h0', 'h0', 'h1', 'h1']} hiCols={mine} />
        <MatrixGrid value={WO} label="W_O (4 × 4)" editable decimals={1} rowLabels={['h0', 'h0', 'h1', 'h1']} hiRows={mine} onchange={(v) => (WO = v)} />
        <MatrixGrid value={out} label="output = concat W_O" rowLabels={words} />
      </div>
    </div>
  {/if}

  {#snippet controls()}
    <span class="seg" role="group" aria-label="Pick a head">
      {#each [0, 1] as h}
        <button type="button" class="lab-btn" class:on={head === h} aria-pressed={head === h} onclick={() => (head = h)}>head {h}</button>
      {/each}
    </span>
    <label class="sw"><input type="checkbox" bind:checked={swap2} /> head 1 swaps its keys</label>
  {/snippet}

  {#snippet readout()}
    {#if view === '3d'}
      Head {head} is slice {head} of the (head, L, d_k) block and makes its own L×L weights.
    {:else}
      Head {head} reads columns {mine[0]}–{mine[1]} of Q, K and V, writes columns {mine[0]}–{mine[1]} of concat, and only rows {mine[0]}–{mine[1]} of W_O read it.
    {/if}
  {/snippet}

  {#snippet legend()}
    <span class="key"><i></i>the numbers head {head} owns</span>
    <span>W_O is where the heads get mixed: 2 heads in, 1 output out.</span>
  {/snippet}
</LabFrame>

<style>
  .steps { display: flex; flex-direction: column; gap: 0.8rem; }
  .step { font-size: 0.85rem; color: var(--dim); margin: 0; padding-top: 0.6rem; border-top: 1px solid var(--line); }
  .step:first-child { border-top: 0; padding-top: 0; }
  .step b { display: inline-grid; place-items: center; width: 1.35rem; height: 1.35rem; margin-right: 0.35rem; border-radius: 50%; background: var(--bg); border: 1px solid var(--field); color: var(--fg); font-size: 0.75rem; }
  .row { display: flex; flex-wrap: wrap; gap: 1rem 1.4rem; align-items: flex-start; min-width: 0; }
  .h { transition: opacity 0.2s; }
  .h.faded { opacity: 0.35; }
  .flow { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.3rem 0.4rem; font-size: 0.82rem; color: var(--fg); }
  .flow li + li::before { content: '→ '; color: var(--dim); }
  .seg { display: inline-flex; gap: 0.3rem; }
  .seg .lab-btn.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  .sw { font-size: 0.88rem; display: inline-flex; gap: 0.45rem; align-items: center; min-height: 2.5rem; cursor: pointer; }
  .sw input { width: 1.1rem; height: 1.1rem; accent-color: var(--accent); }
  .key { display: inline-flex; align-items: center; gap: 0.4rem; }
  .key i { width: 0.9rem; height: 0.9rem; border-radius: 2px; background: var(--highlight); border: 1px solid var(--accent); flex: none; }
  @media (prefers-reduced-motion: reduce) { .h { transition: none; } }
</style>
