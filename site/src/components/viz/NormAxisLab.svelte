<script lang="ts">
  /**
   * BatchNorm vs LayerNorm on the same 4×4 batch: which numbers get averaged together.
   * BatchNorm: one column (a feature, across the examples). LayerNorm: one row (an example, across its features).
   * A 3D view shows the same choice on a (B, L, d) batch of sentences.
   */
  import { normalize, X4 } from '@lib/residuals'
  import Tensors3D from '../viz3d/Tensors3D.svelte'
  import LabFrame from './LabFrame.svelte'

  let kind = $state<'batch' | 'layer'>('batch')
  let pick = $state(0) // the column (BatchNorm) or row (LayerNorm) being shown
  let view = $state('grid')

  const r = $derived(normalize(X4, kind === 'batch' ? 0 : 1))
  const inGroup = (i: number, j: number) => (kind === 'batch' ? j === pick : i === pick)
  const f = (v: number) => (Math.abs(v) < 0.005 ? '0' : String(Number(v.toFixed(2))))
  const groupVals = $derived(kind === 'batch' ? X4.map((row) => row[pick]) : X4[pick])

  function setKind(k: 'batch' | 'layer') {
    kind = k
    pick = k === 'batch' ? 0 : 2
  }

  // 3D: a batch of 4 sentences × 3 tokens × 5 features
  const tensors = $derived([
    {
      shape: [4, 3, 5],
      axes: ['B sentences', 'L tokens', 'd features'],
      title: kind === 'batch' ? 'BatchNorm: one feature, every sentence and token' : 'LayerNorm: one token, all its features',
      highlight: kind === 'batch'
        ? [{ from: [0, 0, 1] as [number, number, number], to: [3, 2, 1] as [number, number, number], tone: 'accent' as const }]
        : [{ from: [0, 1, 0] as [number, number, number], to: [0, 1, 4] as [number, number, number], tone: 'accent' as const }],
    },
  ])
</script>

<LabFrame
  title="Which numbers are averaged together?"
  hint="Pick BatchNorm or LayerNorm, then point at, tap or focus a cell to choose its column or row."
  views={[{ id: 'grid', label: 'The 4×4 example' }, { id: '3d', label: '3D: a batch of sentences' }]}
  bind:view
>
  {#if view === 'grid'}
    <div class="pair">
      <div class="block">
        <div class="cap">X: 4 examples (rows) × 4 features (columns)</div>
        <table>
          <thead><tr><th></th>{#each [0, 1, 2, 3] as j}<th class:hi={kind === 'batch' && j === pick}>f{j}</th>{/each}</tr></thead>
          <tbody>
            {#each X4 as row, i}
              <tr>
                <th class:hi={kind === 'layer' && i === pick}>ex {i}</th>
                {#each row as v, j}
                  <td class:in={inGroup(i, j)}>
                    <button onclick={() => (pick = kind === 'batch' ? j : i)} onpointerenter={() => (pick = kind === 'batch' ? j : i)}
                      onfocus={() => (pick = kind === 'batch' ? j : i)} aria-label="example {i}, feature {j}: {v}">{v}</button>
                  </td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <div class="arrow" aria-hidden="true">→</div>
      <div class="block">
        <div class="cap">normalized: (x − mean) ÷ std of its {kind === 'batch' ? 'column' : 'row'}</div>
        <table>
          <thead><tr><th></th>{#each [0, 1, 2, 3] as j}<th>f{j}</th>{/each}</tr></thead>
          <tbody>
            {#each r.out as row, i}
              <tr><th>ex {i}</th>{#each row as v, j}<td class:in={inGroup(i, j)}>{f(v)}</td>{/each}</tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {:else}
    <Tensors3D tensors={tensors} keepView height="300px" ariaLabel="A batch of 4 sentences, 3 tokens each, 5 features per token, with the averaged group highlighted" />
  {/if}

  {#snippet controls()}
    <div class="seg" role="group" aria-label="Normalization">
      <button aria-pressed={kind === 'batch'} class:on={kind === 'batch'} onclick={() => setKind('batch')}>BatchNorm: down a column</button>
      <button aria-pressed={kind === 'layer'} class:on={kind === 'layer'} onclick={() => setKind('layer')}>LayerNorm: across a row</button>
    </div>
  {/snippet}

  {#snippet readout()}
    {#if view === 'grid'}
      {kind === 'batch' ? `feature ${pick}` : `example ${pick}`}: [{groupVals.join(', ')}] → mean <b>{f(r.means[pick])}</b>, std <b>{f(r.stds[pick])}</b>
    {:else}
      {kind === 'batch'
        ? 'BatchNorm averages feature 1 over all 4 × 3 = 12 tokens: one sentence’s result depends on the other sentences.'
        : 'LayerNorm averages the 5 features of one token: batch size and sentence length don’t matter.'}
    {/if}
  {/snippet}

  {#snippet legend()}
    <span><i class="sw"></i>the numbers averaged together</span>
  {/snippet}
</LabFrame>

<style>
  .seg { display: inline-flex; flex-wrap: wrap; border: 1px solid var(--field); border-radius: 6px; overflow: hidden; }
  .seg button { font: inherit; font-size: 0.85rem; padding: 0.3rem 0.8rem; min-height: 2.1rem; border: 0; background: var(--bg); color: var(--fg); cursor: pointer; }
  .seg button + button { border-left: 1px solid var(--field); }
  .seg button.on { color: var(--accent); background: var(--highlight); }
  .seg button:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
  @media (max-width: 560px) {
    .seg { flex-direction: column; width: 100%; }
    .seg button { text-align: left; }
    .seg button + button { border-left: 0; border-top: 1px solid var(--field); }
  }
  .pair { display: flex; flex-wrap: wrap; gap: 0.6rem 1rem; align-items: center; }
  .block { min-width: 0; }
  .cap { font-size: 0.8rem; color: var(--dim); margin-bottom: 0.25rem; }
  .arrow { color: var(--dim); font-size: 1.2rem; }
  table { border-collapse: collapse; width: auto; font-family: var(--mono); font-size: 0.85rem; }
  th { color: var(--dim); font-weight: 400; font-size: 0.76rem; padding: 0.15rem 0.35rem; border: 0; text-align: center; }
  th.hi { color: var(--accent); font-weight: 600; }
  td { border: 1px solid var(--line); padding: 0; min-width: 2.8rem; height: 2.1rem; text-align: right; transition: background 0.15s; }
  td:not(:has(button)) { padding: 0 0.45rem; }
  td.in { background: var(--highlight); }
  td button { width: 100%; height: 100%; padding: 0 0.45rem; font: inherit; text-align: right; border: 0; background: transparent; color: inherit; cursor: pointer; }
  td button:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
  .sw { display: inline-block; width: 0.8rem; height: 0.8rem; border-radius: 2px; background: var(--highlight); border: 1px solid var(--accent); vertical-align: -0.1em; margin-right: 0.3rem; }
  @media (prefers-reduced-motion: reduce) { td { transition: none; } }
</style>
