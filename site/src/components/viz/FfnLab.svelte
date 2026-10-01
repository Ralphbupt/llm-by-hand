<script lang="ts">
  /**
   * The feed-forward network: Linear (2 → 4) → ReLU → Linear (4 → 2), applied to each word on its own.
   * Drag a word: its 4 hidden units light up when their number is above 0.
   */
  import { matmul, relu } from '@lib/num'
  import MatrixGrid from './MatrixGrid.svelte'
  import VectorCanvas from './VectorCanvas.svelte'
  import LabFrame from './LabFrame.svelte'

  const words = ['cat', 'dog', 'car']
  const X0 = [[2, 0], [1, 1], [0, 2]]
  let X = $state(X0.map((r) => [...r]))
  const W1 = [[1, -1, 0, 1], [0, 1, -1, 1]]
  const b1 = [0, 0, 1, -2]
  const W2 = [[1, 0], [0, 1], [-1, 1], [0.5, 0.5]]
  let word = $state<number | null>(null)

  const pre = $derived(matmul(X, W1).map((r) => r.map((v, j) => v + b1[j])))
  const H = $derived(relu(pre))
  const out = $derived(matmul(H, W2))
  const hi = $derived(word === null ? [] : [word])
  const f = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(2))
  const changed = $derived(X.some((r, i) => r.some((v, j) => v !== X0[i][j])))
</script>

<LabFrame
  title="The feed-forward network works on one word at a time"
  hint="Move a word and watch which hidden units become nonzero. Point at or tap a row to follow one word."
  onreset={() => { X = X0.map((r) => [...r]); word = null }}
  resetDisabled={!changed}
>
  <div class="grid">
    <div class="col canvas">
      <VectorCanvas value={X} labels={words} hi={hi} domain={[-3, 4]} onchange={(v) => (X = v)} />
      <div class="chain">(3, 2) @ (2, 4) → (3, 4) → ReLU → (3, 4) @ (4, 2) → (3, 2)</div>
    </div>
    <div class="col">
      <MatrixGrid value={X} label="X (3, 2)" rowLabels={words} hiRows={hi} onhover={(c) => (word = c?.i ?? null)} />
      <div class="units" onpointerleave={() => (word = null)} role="group" aria-label="hidden units after ReLU">
        <div class="label">hidden units after ReLU (3, 4)</div>
        {#each H as row, i}
          <div class="urow" class:hi={word === i} onpointerenter={() => (word = i)} onfocus={() => (word = i)} onclick={() => (word = i)}
            onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); word = i } }}
            role="button" tabindex="0" aria-label={`${words[i]}: ${row.filter((v) => v > 0).length} of 4 units on`}>
            <span class="w">{words[i]}</span>
            {#each row as v, j}
              <span class="u" class:on={v > 0} title={`unit ${j}: ${f(pre[i][j])} before ReLU`}>{f(v)}</span>
            {/each}
            <span class="n">{row.filter((v) => v > 0).length} on</span>
          </div>
        {/each}
      </div>
      <MatrixGrid value={out} label="output (3, 2)" rowLabels={words} hiRows={hi} />
    </div>
  </div>

  {#snippet readout()}
    {#if word !== null}
      {words[word]}: before ReLU [{pre[word].map(f).join(', ')}], after [{H[word].map(f).join(', ')}]. Only this row’s numbers were used.
    {:else}
      <span class="idle">Point at or tap a word. A unit is on when its number before ReLU is above 0; ReLU turns everything else into 0.</span>
    {/if}
  {/snippet}

  {#snippet legend()}
    <span class="key"><i class="on"></i>unit on (above 0 before ReLU)</span>
    <span class="key"><i></i>unit off (ReLU made it 0)</span>
  {/snippet}
</LabFrame>

<style>
  .grid { display: grid; grid-template-columns: minmax(0, 280px) minmax(0, 1fr); gap: 1.5rem; align-items: start; }
  .col { display: flex; flex-direction: column; gap: 0.8rem; min-width: 0; }
  .chain { font-family: var(--mono); font-size: 0.75rem; color: var(--dim); }
  .label { font-size: 0.78rem; color: var(--dim); font-family: var(--mono); margin-bottom: 0.2rem; }
  .urow { display: flex; align-items: center; gap: 0.3rem; padding: 0.15rem 0.2rem; border-radius: 6px; cursor: pointer; }
  .urow.hi { background: var(--highlight); }
  .urow.hi .w { color: var(--accent); font-weight: 600; }
  .urow:focus-visible { outline: 2px solid var(--accent); outline-offset: 0; }
  .w { width: 2.4rem; font-size: 0.8rem; color: var(--dim); font-family: var(--mono); }
  .u { width: 2.6rem; height: 1.8rem; display: grid; place-items: center; font-family: var(--mono); font-size: 0.8rem; border: 1px solid var(--field); border-radius: 50%; color: var(--dim);
    transition: background-color 0.15s, color 0.15s; }
  .u.on { background: var(--accent); color: var(--on-solid); border-color: var(--accent); font-weight: 600; }
  .n { font-size: 0.75rem; color: var(--dim); margin-left: 0.3rem; white-space: nowrap; }
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
  .key { display: inline-flex; align-items: center; gap: 0.4rem; }
  .key i { width: 0.9rem; height: 0.9rem; border-radius: 50%; border: 1px solid var(--field); }
  .key i.on { background: var(--accent); border-color: var(--accent); }
  @media (max-width: 700px) { .grid { grid-template-columns: minmax(0, 1fr); } .canvas { max-width: 320px; } }
  @media (prefers-reduced-motion: reduce) { .u { transition: none; } }
</style>
