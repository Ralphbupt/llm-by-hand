<script lang="ts">
  /**
   * Level 21: what one training example looks like.
   * Type two numbers; see the tokens, the ids, the input x and the target y shifted by one,
   * which targets count in the loss, and the causal mask. Same rules as content/2-theory/write-a-gpt/demo.py.
   */
  import Tensors3D from '../viz3d/Tensors3D.svelte'
  import LabFrame from './LabFrame.svelte'

  const ITOS = ['<pad>', '<bos>', '<eos>', ...'0123456789'.split(''), '+', '=']
  const MAXLEN = 11

  let a = $state(23)
  let b = $state(58)
  let answerOnly = $state(true)
  let row = $state<number | null>(null)
  let view = $state('table')

  const clamp = (v: number) => Math.max(0, Math.min(99, Math.round(Number(v) || 0)))
  const ids = $derived.by(() => {
    const s = [1, ...`${clamp(a)}+${clamp(b)}=${clamp(a) + clamp(b)}`.split('').map((c) => ITOS.indexOf(c)), 2]
    return [...s, ...Array(MAXLEN - s.length).fill(0)]
  })
  const x = $derived(ids.slice(0, -1))
  const y = $derived(ids.slice(1))
  const eq = $derived(x.indexOf(ITOS.indexOf('=')))
  const counted = (t: number) => y[t] !== 0 && (!answerOnly || t >= eq)
  const L = $derived(x.length)

  // a batch of 4 examples shaped like this one, in 3D: the logits (B, L, V) with the rows the loss reads,
  // and the causal mask repeated for every example (B, L, L)
  const B3 = 4, V = ITOS.length
  type R3 = { from: [number, number, number]; to: [number, number, number]; tone: 'ok' | 'dim' }
  const shapes3d = $derived.by(() => {
    const lossRows: R3[] = x.map((_, t) => t).filter((t) => counted(t)).map((t) => ({ from: [0, t, 0], to: [B3 - 1, t, V - 1], tone: 'ok' }))
    const seen: R3[] = x.map((_, i) => ({ from: [0, i, 0], to: [B3 - 1, i, i], tone: 'dim' }))
    return [
      { shape: [B3, L, V], title: `logits (${B3}, ${L}, ${V})`, axes: ['example', 'position t', 'token'], highlight: lossRows },
      '  ',
      { shape: [B3, L, L], title: `causal mask (${B3}, ${L}, ${L})`, axes: ['example', 'position t', 'may look at'], highlight: seen },
    ]
  })
  const nCounted = $derived(y.filter((_, t) => counted(t)).length)
  function maskKey(e: KeyboardEvent) {
    const r = row ?? -1
    if (e.key === 'ArrowDown' || e.key === 'ArrowRight') { row = Math.min(L - 1, r + 1); e.preventDefault() }
    if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') { row = Math.max(0, r - 1); e.preventDefault() }
  }
</script>

<LabFrame
  title="One training example: the input x, and the target y shifted by one"
  hint="Type two numbers. Point at or tap a position to see which tokens it may look at."
  views={[{ id: 'table', label: 'One example' }, { id: '3d', label: 'A batch in 3D' }]} bind:view
  onreset={() => { a = 23; b = 58; answerOnly = true; row = null }} resetDisabled={a === 23 && b === 58 && answerOnly && row === null}
>
  {#if view === 'table'}
    <div class="pic">
      <table>
        <tbody>
          <tr><th scope="row"><span class="long">position</span> t</th>{#each x as _, t}<td class="t" class:hi={row === t}>{t}</td>{/each}</tr>
          <tr><th scope="row">x<span class="long">&nbsp;(input)</span></th>{#each x as id, t}
            <td class="cell" class:hi={row === t} onpointerenter={() => (row = t)} onclick={() => (row = t)}><span class="tok">{ITOS[id]}</span><span class="id">{id}</span></td>{/each}</tr>
          <tr><th scope="row">y<span class="long">&nbsp;(target)</span></th>{#each y as id, t}
            <td class="cell" class:off={!counted(t)} class:ans={counted(t)} class:hi={row === t}><span class="tok">{ITOS[id]}</span><span class="id">{counted(t) ? id : '—'}</span></td>{/each}</tr>
        </tbody>
      </table>

      <div class="mask">
        <div class="mlbl">causal mask: row = position t, column = what it may look at</div>
        <div class="grid" style="grid-template-columns: repeat({L}, 1.3rem)" role="slider" tabindex="0"
          aria-label="Causal mask: pick a position with the arrow keys" aria-valuemin={0} aria-valuemax={L - 1} aria-valuenow={row ?? 0}
          aria-valuetext={row === null ? 'no position picked' : `position ${row} may look at positions 0 to ${row}`} onkeydown={maskKey}>
          {#each x as _, i}
            {#each x as _, j}
              <span class="sq" class:see={j <= i} class:hi={row === i} onpointerenter={() => (row = i)} onclick={() => (row = i)} aria-hidden="true"></span>
            {/each}
          {/each}
        </div>
      </div>
    </div>
  {:else}
    <Tensors3D tensors={shapes3d} height="300px" keepView ariaLabel="A batch of four examples: the logits block with the rows the loss reads, and the causal mask for every example" />
    <p class="note">Left: the model scores all {V} tokens at every position of every example; the loss reads only the highlighted rows
      ({answerOnly ? 'the answer' : 'every position'}). Right: the same lower triangle (gray = may look) is used for every example in the batch.</p>
  {/if}

  {#snippet controls()}
    <label class="num">a <input type="number" min="0" max="99" bind:value={a} /></label>
    <label class="num">b <input type="number" min="0" max="99" bind:value={b} /></label>
    <span class="seg" role="group" aria-label="Which targets the loss counts">
      <span class="seglbl">loss on</span>
      <button type="button" class="lab-btn" aria-pressed={answerOnly} onclick={() => (answerOnly = true)}>answer digits only</button>
      <button type="button" class="lab-btn" aria-pressed={!answerOnly} onclick={() => (answerOnly = false)}>every position</button>
    </span>
  {/snippet}

  {#snippet readout()}
    {#if row !== null}
      position {row} (<b>{ITOS[x[row]]}</b>) sees: {x.slice(0, row + 1).map((i) => ITOS[i]).join(' ')} → target <b>{ITOS[y[row]]}</b>{counted(row) ? ', counted' : ', skipped by the loss'}
    {:else}
      y is x moved one step left. The loss counts <b>{nCounted}</b> of {y.length} targets.
    {/if}
  {/snippet}

  {#snippet legend()}
    <span class="lg"><i class="sw ans"></i>target counted in the loss</span>
    <span class="lg"><s class="mono">5</s>&nbsp;target skipped</span>
    <span class="lg"><i class="sw see"></i>may look at</span>
    <span class="lg"><i class="sw sel"></i>the position you picked</span>
  {/snippet}
</LabFrame>

<style>
  .pic { display: grid; gap: 1rem; width: max-content; min-width: 100%; }
  .mono { font-family: var(--mono); }
  table { border-collapse: collapse; width: auto; font-size: 0.85rem; }
  th { text-align: left; font-weight: 500; color: var(--dim); white-space: nowrap; padding: 0.25rem 0.6rem 0.25rem 0; border: 0; font-size: 0.8rem; }
  td { border: 1px solid var(--line); padding: 0.2rem 0.3rem; text-align: center; min-width: 2.5rem; background: var(--bg); }
  td.t { font-family: var(--mono); color: var(--dim); border: 0; background: transparent; font-size: 0.75rem; }
  td.t.hi { color: var(--accent); font-weight: 700; }
  td.cell { cursor: pointer; }
  td.cell.hi { box-shadow: inset 0 0 0 2px var(--accent); }
  .tok { display: block; font-family: var(--mono); font-weight: 600; white-space: nowrap; }
  .id { display: block; font-family: var(--mono); font-size: 0.75rem; color: var(--dim); }
  td.off .tok { text-decoration: line-through; color: var(--dim); font-weight: 400; }
  td.ans { background: color-mix(in srgb, var(--ok) 18%, var(--bg)); border-color: color-mix(in srgb, var(--ok) 55%, var(--line)); }
  .note { font-size: 0.82rem; color: var(--dim); margin: 0.5rem 0 0; }
  .mlbl { font-size: 0.8rem; color: var(--dim); margin-bottom: 0.35rem; width: 0; min-width: 100%; }
  .grid { display: grid; gap: 2px; width: max-content; border-radius: 3px; }
  .sq { width: 1.3rem; height: 1.3rem; border: 1px solid var(--line); border-radius: 2px; background: var(--bg); cursor: pointer; }
  .sq.see { background: color-mix(in srgb, var(--fg) 35%, var(--bg)); }
  .sq.hi { border-color: var(--accent); }
  .sq.see.hi { background: var(--accent); }
  .num { display: inline-flex; align-items: center; gap: 0.4rem; font-family: var(--mono); font-size: 0.9rem; }
  .num input { font: inherit; width: 4rem; min-height: 2.1rem; padding: 0.2rem 0.45rem; border: 1px solid var(--field); border-radius: 6px; background: var(--bg); color: var(--fg); }
  .seg { display: inline-flex; align-items: center; gap: 0.35rem; flex-wrap: wrap; }
  .seglbl { font-size: 0.85rem; color: var(--dim); }
  .lg { display: inline-flex; align-items: center; gap: 0.35rem; }
  .sw { width: 0.9rem; height: 0.8rem; border-radius: 2px; display: inline-block; border: 1px solid var(--line); }
  .sw.ans { background: color-mix(in srgb, var(--ok) 18%, var(--bg)); border-color: color-mix(in srgb, var(--ok) 55%, var(--line)); }
  .sw.see { background: color-mix(in srgb, var(--fg) 35%, var(--bg)); }
  .sw.sel { background: var(--accent); border-color: var(--accent); }
  @media (max-width: 560px) {
    /* phones: short row labels and narrow columns, so all positions fit without a swipe */
    .long { display: none; }
    th { padding-right: 0.4rem; }
    td { min-width: 1.5rem; padding: 0.2rem 0.1rem; }
    .tok { font-size: 0.74rem; }
    .num input { font-size: 16px; min-height: 2.5rem; }
  }
</style>
