<script lang="ts">
  /**
   * Where does the decoder look? Attention weights recorded from the trained models of level N5:
   *   numbers → words (demo.py --export): rows are the words it wrote, columns the digits it read;
   *   reversal (export.py): the anti-diagonal pattern of reading a string backwards.
   */
  import { onMount } from 'svelte'
  import Heatmap from './Heatmap.svelte'
  import LabFrame from './LabFrame.svelte'

  type Ex = { n: number; src: string[]; pad: number; out: string[]; right: boolean; weights: number[][] }
  let nums = $state<Ex[]>([])
  let rev = $state<{ src: number[]; pred: number[]; weights: number[][] } | null>(null)
  let error = $state('')
  let tab = $state('words')
  let pick = $state(0)
  let cell = $state<{ i: number; j: number } | null>(null)

  onMount(() => {
    Promise.all([
      fetch('/data/seq2seq-attention/alignments.json').then((r) => r.json()),
      fetch('/data/seq2seq-attention/bottleneck.json').then((r) => r.json()),
    ]).then(([a, b]) => { nums = a.examples; rev = b.example }).catch((e) => (error = String(e)))
  })

  const ex = $derived(nums[pick])
  // padding columns get weight 0 (they are masked), so leave them out of the picture
  const words = $derived(ex ? { value: ex.weights.map((row) => row.slice(ex.pad)), rows: [...ex.out, '<eos>'], cols: ex.src } : null)
  const tok = (t: number) => (t === 12 ? '<eos>' : t < 10 ? String(t) : '·')
  const reverse = $derived(rev ? { value: rev.weights, rows: rev.pred.map(tok), cols: rev.src.map(String) } : null)
  const view = $derived(tab === 'words' ? words : reverse)
  const strongest = (row: number[]) => row.reduce((b, v, j) => (v > row[b] ? j : b), 0)
  // a new tab or example starts with nothing picked
  $effect(() => { void tab; void pick; cell = null })
  const fmtN = (n: number) => n.toLocaleString('en-US')
</script>

<LabFrame
  title="Where the decoder looks"
  hint="Point at or tap a cell. Rows: what the decoder wrote. Columns: what it read. Darker = more weight."
  views={[{ id: 'words', label: 'Numbers → words' }, { id: 'reverse', label: 'Reversing digits' }]}
  bind:view={tab}
  onreset={() => { tab = 'words'; pick = 0; cell = null }}
  resetDisabled={tab === 'words' && pick === 0 && cell === null}
>
  {#if error}
    <p class="bad">Could not load the recorded weights: {error}</p>
  {:else if view}
    {#if tab === 'words' && ex}
      <div class="cap"><b>{fmtN(ex.n)}</b> → {ex.out.join(' ')} <span class:ok={ex.right} class:bad={!ex.right}>{ex.right ? '✓ correct' : '✗ wrong'}</span></div>
    {:else}
      <div class="cap">a digit string, read backwards</div>
    {/if}
    <Heatmap value={view.value} rowLabels={view.rows} colLabels={view.cols} hiRows={cell ? [cell.i] : []} hiCols={cell ? [cell.j] : []} onhover={(c) => (cell = c)} />
  {:else}
    <div class="loading">Loading the recorded weights…</div>
  {/if}

  {#snippet controls()}
    {#if tab === 'words' && nums.length}
      <span class="lbl">number</span>
      <button type="button" class="lab-btn step" aria-label="previous number" disabled={pick === 0} onclick={() => (pick = pick - 1)}>‹</button>
      <select bind:value={pick} aria-label="pick a number">
        {#each nums as e, k}<option value={k}>{fmtN(e.n)}</option>{/each}
      </select>
      <button type="button" class="lab-btn step" aria-label="next number" disabled={pick === nums.length - 1} onclick={() => (pick = pick + 1)}>›</button>
    {/if}
  {/snippet}

  {#snippet readout()}
    {#if view && cell}
      Writing “{view.rows[cell.i]}”, the decoder gives {tab === 'words' ? 'digit' : 'input'} {cell.j} (“{view.cols[cell.j]}”) weight <b>{view.value[cell.i][cell.j].toFixed(2)}</b>.
    {:else if tab === 'words' && ex}
      Rows: the words it wrote. Columns: the digits it read. Point at or tap a cell.
    {:else if view}
      Each output digit looks almost only at one input digit: the last one first, then backwards. Point at or tap a cell.
    {:else}
      <span class="idle">Waiting for the recorded weights…</span>
    {/if}
  {/snippet}

  {#snippet legend()}
    <span><i class="ramp"></i>attention weight, 0 → 1</span>
    {#if tab === 'words' && !cell && words}
      <span class="tip">Strongest look for each word: {words.rows.map((w, i) => `${w} → ${words.cols[strongest(words.value[i])]}`).join(', ')}</span>
    {/if}
  {/snippet}
</LabFrame>

<style>
  .loading { min-height: 16rem; display: grid; place-items: center; color: var(--dim); font-size: 0.85rem; border: 1px dashed var(--line); border-radius: 6px; }
  .cap { font-size: 0.85rem; color: var(--dim); margin-bottom: 0.35rem; font-family: var(--mono); }
  .cap b { color: var(--fg); }
  .cap .ok { color: var(--ok); font-family: system-ui, -apple-system, sans-serif; margin-left: 0.4rem; }
  .cap .bad { margin-left: 0.4rem; font-family: system-ui, -apple-system, sans-serif; }
  .lbl { font-size: 0.85rem; color: var(--dim); }
  .step { min-width: 2.5rem; font-family: var(--mono); padding: 0.3rem 0.6rem; }
  select { font: inherit; font-family: var(--mono); font-size: 0.88rem; min-height: 2.1rem; padding: 0.2rem 0.5rem; border: 1px solid var(--field); border-radius: 6px; background: var(--bg); color: var(--fg); }
  @media (max-width: 760px) { select { min-height: 2.5rem; } }
  .ramp { display: inline-block; width: 3rem; height: 0.7rem; border: 1px solid var(--line); border-radius: 2px; vertical-align: -0.1em; margin-right: 0.35rem;
    background: linear-gradient(to right, transparent, color-mix(in srgb, var(--accent) 75%, transparent)); }
  .tip { flex-basis: 100%; font-family: var(--mono); }
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
  .bad { color: var(--warn); }
  p.bad { margin: 0; }
</style>
