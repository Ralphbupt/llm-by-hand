<script lang="ts">
  /**
   * Masks. A mask says, for every (query row, key column), "may not look".
   * Causal: no looking at later words. Padding: no looking at PAD tokens.
   * The two are combined with OR, then the blocked scores become -∞ before softmax.
   * Scores are all equal here, so the weights show the mask and nothing else.
   */
  import { maskedSoftmaxRows } from '@lib/num'
  import Heatmap from './Heatmap.svelte'
  import LabFrame from './LabFrame.svelte'

  const words = ['the', 'cat', 'sat', 'on', 'mat']
  const L = words.length
  const START_PAD = [false, false, false, true, true]
  let causal = $state(true)
  let pad = $state([...START_PAD])
  let cell = $state<{ i: number; j: number } | null>(null)

  const tokens = $derived(words.map((w, j) => (pad[j] ? 'PAD' : w)))
  const causalM = $derived(Array.from({ length: L }, (_, i) => Array.from({ length: L }, (_, j) => causal && j > i)))
  const padRow = $derived(pad.map((p) => p))
  const combined = $derived(causalM.map((row) => row.map((c, j) => c || padRow[j])))
  const weights = $derived(maskedSoftmaxRows(Array.from({ length: L }, () => new Array(L).fill(0)), combined))
  const open = $derived(combined.flat().filter((b) => !b).length)
  const changed = $derived(!causal || pad.some((p, j) => p !== START_PAD[j]))
  const isHi = (i: number, j: number) => !!cell && cell.i === i && cell.j === j

  function toggle(j: number) {
    if (j === 0) return // the first token always stays a real word, so every row can look somewhere
    pad = pad.map((p, k) => (k === j ? !p : p))
  }
</script>

<LabFrame
  title="Masks decide which words each word may attend to"
  hint="Tap a word to turn it into padding. Point at or tap a weight to see why it is blocked."
  onreset={() => { causal = true; pad = [...START_PAD]; cell = null }}
  resetDisabled={!changed}
>
  <div class="stack">
  <div class="eq">
    <div class="term">
      <div class="label">padding mask (1, {L}): one row</div>
      <table class="m"><tbody><tr>{#each padRow as b}<td class:b>{b ? 1 : 0}</td>{/each}</tr></tbody></table>
      <div class="arrow">↓ copied down every row (broadcast)</div>
      <table class="m"><tbody>
        {#each Array(L) as _, i}<tr>{#each padRow as b, j}<td class:b class:hi={isHi(i, j)}>{b ? 1 : 0}</td>{/each}</tr>{/each}
      </tbody></table>
    </div>
    <div class="op">OR</div>
    <div class="term">
      <div class="label">causal mask ({L}, {L})</div>
      <table class="m"><tbody>
        {#each causalM as row, i}<tr>{#each row as b, j}<td class:b class:hi={isHi(i, j)}>{b ? 1 : 0}</td>{/each}</tr>{/each}
      </tbody></table>
    </div>
    <div class="op">=</div>
    <div class="term">
      <div class="label">combined ({L}, {L})</div>
      <table class="m" onpointerleave={() => (cell = null)}><thead><tr><th></th>{#each tokens as t}<th>{t}</th>{/each}</tr></thead><tbody>
        {#each combined as row, i}<tr><th>{tokens[i]}</th>{#each row as b, j}<td class="pick" class:b class:hi={isHi(i, j)} onpointerenter={() => (cell = { i, j })} onclick={() => (cell = { i, j })}>{b ? 1 : 0}</td>{/each}</tr>{/each}
      </tbody></table>
    </div>
  </div>

  <div class="weights">
    <Heatmap value={weights} label="weights (equal scores, blocked cells set to −∞ before softmax)" rowLabels={tokens} colLabels={tokens}
      hiRows={cell ? [cell.i] : []} hiCols={cell ? [cell.j] : []} onhover={(c) => (cell = c)} />
  </div>
  <p class="cap">In a batch the padding mask has shape (B, 1, {L}); the 1 is the query axis it gets copied along.</p>
  </div>

  {#snippet controls()}
    <span class="toks" role="group" aria-label="Tokens: tap one to turn it into padding">
      {#each tokens as t, j}
        <button type="button" class="lab-btn tok" class:pad={pad[j]} aria-pressed={pad[j]} onclick={() => toggle(j)} disabled={j === 0}
          title={j === 0 ? 'the first token stays a word' : 'tap to toggle PAD'}>{t}</button>
      {/each}
    </span>
    <label class="sw"><input type="checkbox" bind:checked={causal} /> causal (no looking ahead)</label>
  {/snippet}

  {#snippet readout()}
    {#if cell}
      <b>{tokens[cell.i]}</b> (row {cell.i}) → <b>{tokens[cell.j]}</b> (column {cell.j}):
      {combined[cell.i][cell.j] ? 'blocked' : 'allowed'}{causalM[cell.i][cell.j] ? ', it is in the future' : ''}{padRow[cell.j] ? ', it is padding' : ''}.
    {:else}
      {open} of {L * L} cells are open.
    {/if}
  {/snippet}

  {#snippet legend()}
    <span class="key"><i class="b"></i>1 = blocked: this score becomes −∞, its weight 0</span>
    <span class="key"><i></i>0 = allowed</span>
  {/snippet}
</LabFrame>

<style>
  .stack { display: flex; flex-direction: column; gap: 1rem; }
  .eq { display: flex; flex-wrap: wrap; gap: 0.8rem 1rem; align-items: center; }
  .term { min-width: 0; }
  .label { font-size: 0.78rem; color: var(--dim); font-family: var(--mono); margin-bottom: 0.25rem; }
  .op { font-family: var(--mono); font-weight: 700; color: var(--dim); }
  .arrow { font-size: 0.75rem; color: var(--dim); margin: 0.3rem 0; }
  table.m { border-collapse: collapse; font-family: var(--mono); font-size: 0.8rem; width: auto; font-variant-numeric: tabular-nums; }
  table.m td { border: 1px solid var(--line); width: 1.8rem; height: 1.6rem; padding: 0; text-align: center; transition: background 0.15s; }
  /* blocked = hatched neutral: "not allowed", not an error */
  table.m td.b, .key i.b {
    background: repeating-linear-gradient(135deg, color-mix(in srgb, var(--dim) 34%, transparent) 0 3px, color-mix(in srgb, var(--dim) 12%, transparent) 3px 6px);
    color: var(--fg); font-weight: 700;
  }
  table.m td:not(.b) { color: var(--dim); }
  table.m td.hi { outline: 2px solid var(--fg); outline-offset: -2px; }
  table.m td.pick { cursor: pointer; }
  table.m th { font-weight: 400; font-size: 0.75rem; color: var(--dim); border: none; padding: 0 0.3rem; }
  .weights { overflow-x: auto; }
  .cap { margin: -0.5rem 0 0; font-size: 0.8rem; color: var(--dim); }
  .toks { display: inline-flex; flex-wrap: wrap; gap: 0.3rem; }
  .tok { font-family: var(--mono); min-width: 3.2rem; }
  .tok.pad { border-style: dashed; color: var(--dim);
    background: repeating-linear-gradient(135deg, color-mix(in srgb, var(--dim) 20%, transparent) 0 3px, transparent 3px 6px); }
  .tok:disabled { opacity: 1; cursor: default; border-color: var(--line); }
  .sw { font-size: 0.88rem; display: inline-flex; gap: 0.45rem; align-items: center; min-height: 2.5rem; cursor: pointer; }
  .sw input { width: 1.1rem; height: 1.1rem; accent-color: var(--accent); }
  .key { display: inline-flex; align-items: center; gap: 0.4rem; }
  .key i { width: 0.9rem; height: 0.9rem; border: 1px solid var(--line); flex: none; }
  @media (prefers-reduced-motion: reduce) { table.m td { transition: none; } }
  @media (max-width: 560px) { .op { width: 100%; text-align: center; } }
</style>
