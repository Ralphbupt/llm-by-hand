<script lang="ts">
  /** Character tokenizer (level 12): type text → sorted vocabulary → ids → decoded back. */
  import LabFrame from './LabFrame.svelte'

  const START = 'hello'
  let text = $state(START)
  const chars = $derived([...new Set([...text])].sort())
  const stoi = $derived(Object.fromEntries(chars.map((c, i) => [c, i])) as Record<string, number>)
  const ids = $derived([...text].map((c) => stoi[c]))
  const show = (c: string) => (c === ' ' ? '␣' : c)
  let hover = $state<number | null>(null) // a vocabulary id under the pointer or focus: its uses light up
  const pick = (i: number) => (hover = hover === i ? null : i)
</script>

<LabFrame
  title="A character tokenizer"
  hint="Type any text. Point at, tap or tab to a character to see every place it is used."
  onreset={() => { text = START; hover = null }}
  resetDisabled={text === START}
>
  <label class="inp">Text <input bind:value={text} maxlength="60" spellcheck="false" autocomplete="off" /></label>
  {#if text.length === 0}
    <p class="empty">Type something to see its tokens.</p>
  {:else}
    <p class="sec">Vocabulary: {chars.length} distinct characters, sorted. The small number is the id.</p>
    <div class="chips">
      {#each chars as c, i}
        <button type="button" class="chip" class:on={hover === i} aria-pressed={hover === i}
          onpointerenter={() => (hover = i)} onpointerleave={() => (hover = null)} onclick={() => pick(i)}
          onfocus={() => (hover = i)} onblur={() => (hover = null)}><b>{show(c)}</b><small>{i}</small></button>
      {/each}
    </div>
    <p class="sec">Encoded: {ids.length} tokens, each character above its id.</p>
    <div class="seq">
      {#each [...text] as c, j}
        <span class="cell" class:on={hover === ids[j]} onpointerenter={() => (hover = ids[j])} onpointerleave={() => (hover = null)}
          ><b>{show(c)}</b><small>{ids[j]}</small></span>
      {/each}
    </div>
  {/if}

  {#snippet readout()}
    {#if text.length}
      ids [{ids.join(', ')}] → decoded “{ids.map((i) => chars[i]).join('')}”
    {:else}
      <span class="idle">No text, no tokens.</span>
    {/if}
  {/snippet}
</LabFrame>

<style>
  .inp { display: flex; gap: 0.6rem; align-items: center; font-size: 0.88rem; color: var(--dim); }
  .inp input { flex: 1; min-width: 0; font-family: var(--mono); font-size: 1rem; padding: 0.4rem 0.55rem; border: 1px solid var(--field);
    border-radius: 5px; background: var(--bg); color: var(--fg); }
  .inp input:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
  .sec { margin: 0.8rem 0 0.35rem; font-size: 0.82rem; color: var(--dim); }
  .empty { margin: 0.8rem 0 0; color: var(--dim); font-size: 0.88rem; }
  .chips { display: flex; flex-wrap: wrap; gap: 0.35rem; }
  .chip { font: inherit; display: inline-flex; flex-direction: column; align-items: center; justify-content: center; min-width: 2.5rem; min-height: 2.5rem;
    padding: 0.15rem 0.35rem; border: 1px solid var(--line); border-radius: 5px; background: var(--bg); color: var(--fg);
    font-family: var(--mono); font-size: 0.95rem; line-height: 1.15; cursor: pointer; }
  .chip small { font-size: 0.74rem; color: var(--dim); }
  .chip, .cell { transition: background-color 0.15s, border-color 0.15s; }
  .chip.on, .cell.on { border-color: var(--accent); background: var(--highlight); }
  .chip:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
  .seq { display: flex; flex-wrap: wrap; gap: 3px; }
  .cell { display: inline-flex; flex-direction: column; align-items: center; min-width: 1.7rem; padding: 0.12rem 0.2rem; border: 1px solid var(--line);
    border-radius: 4px; background: var(--bg); font-family: var(--mono); font-size: 0.9rem; line-height: 1.15; }
  .cell small { font-size: 0.74rem; color: var(--accent); }
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
</style>
