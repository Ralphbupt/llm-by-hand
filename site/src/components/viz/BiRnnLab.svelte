<script lang="ts">
  /**
   * A bidirectional RNN (level N4): one RNN reads left to right, another right to left, and each position's
   * output is the two states side by side. Pick a word to see what each direction has read by the time it gets there.
   */
  import LabFrame from './LabFrame.svelte'

  const words = ['he', 'sat', 'by', 'the', 'bank', 'of', 'the', 'river']
  const START = 4
  let at = $state(START)
  const fwdRead = $derived(words.slice(0, at + 1))
  const bwdRead = $derived(words.slice(at).reverse())

  let btns: HTMLButtonElement[] = []
  // arrow keys move along the sentence (focus follows, like a row of tabs)
  function key(e: KeyboardEvent) {
    const d = ({ ArrowLeft: -1, ArrowRight: 1, Home: -99, End: 99 } as Record<string, number>)[e.key]
    if (!d) return
    e.preventDefault()
    at = Math.max(0, Math.min(words.length - 1, at + d))
    btns[at]?.focus()
  }
</script>

<LabFrame
  title="Reading both ways: what each direction has seen"
  hint="Tap a word. The forward RNN has read everything up to it; the backward RNN everything after it."
  onreset={() => (at = START)}
  resetDisabled={at === START}
>
  <div class="board" style="--n: {words.length}">
    <span class="corner"></span>
    <div class="words" role="group" aria-label="Pick a word">
      {#each words as w, i}
        <button bind:this={btns[i]} class:on={i === at} aria-pressed={i === at} tabindex={i === at ? 0 : -1}
          onclick={() => (at = i)} onkeydown={key}>{w}</button>
      {/each}
    </div>

    <span class="tag fwd">→ forward RNN</span>
    <div class="lane fwd" aria-hidden="true">
      {#each words as _, i}
        <span class="cell" class:lit={i <= at} class:l={i <= at && i > 0} class:r={i < at} class:here={i === at}><i></i></span>
      {/each}
    </div>

    <span class="tag bwd">← backward RNN</span>
    <div class="lane bwd" aria-hidden="true">
      {#each words as _, i}
        <span class="cell" class:lit={i >= at} class:l={i > at} class:r={i >= at && i < words.length - 1} class:here={i === at}><i></i></span>
      {/each}
    </div>

    <span class="tag out">output</span>
    <div class="lane outs" aria-hidden="true">
      {#each words as _, i}
        <span class="cell">{#if i === at}<span class="pair" title="both states side by side"><b class="f"></b><b class="b"></b></span>{/if}</span>
      {/each}
    </div>
  </div>

  {#snippet readout()}
    At “{words[at]}”, the forward state has read <b>{fwdRead.join(' ')}</b>; the backward state has read <b>{bwdRead.join(' ')}</b>.
    The output for “{words[at]}” is both states side by side.
  {/snippet}

  {#snippet legend()}
    <span><i class="sw fwd"></i>forward RNN, left to right</span>
    <span><i class="sw bwd"></i>backward RNN, right to left</span>
    <span><i class="dot"></i>a word that direction has already read</span>
  {/snippet}
</LabFrame>

<style>
  .board { display: grid; grid-template-columns: 7.5rem minmax(0, 1fr); align-items: center; gap: 0.45rem 0.6rem; max-width: 42rem; }
  .words, .lane { display: grid; grid-template-columns: repeat(var(--n), minmax(0, 1fr)); gap: 0.25rem; align-items: center; }
  .words button { font: inherit; font-size: 0.85rem; min-height: 2.2rem; padding: 0.2rem 0; border: 1px solid var(--field); border-radius: 6px;
    background: var(--bg); color: var(--fg); cursor: pointer; min-width: 0; }
  .words button:hover { border-color: var(--fg); }
  .words button.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  .tag { font-size: 0.8rem; font-family: var(--mono); white-space: nowrap; }
  .tag.fwd { color: var(--cat-1); }
  .tag.bwd { color: var(--cat-2); }
  .tag.out { color: var(--dim); }
  .lane { height: 1.6rem; }
  .lane.outs { height: auto; min-height: 1.4rem; }
  .cell { position: relative; height: 100%; display: grid; place-items: center; }
  /* the line that joins the words a direction has read */
  .lane.fwd { --c: var(--cat-1); }
  .lane.bwd { --c: var(--cat-2); }
  .cell.l::before, .cell.r::after { content: ''; position: absolute; top: 50%; height: 2px; margin-top: -1px; background: var(--c); }
  .cell.l::before { left: -0.125rem; right: 50%; }
  .cell.r::after { left: 50%; right: -0.125rem; }
  .cell i { position: relative; z-index: 1; width: 0.55rem; height: 0.55rem; border-radius: 50%; border: 1.5px solid var(--line); background: var(--card); }
  .lane .cell.lit i { background: var(--c); border-color: var(--c); }
  .lane .cell.here i { width: 0.95rem; height: 0.95rem; box-shadow: 0 0 0 3px var(--card), 0 0 0 4.5px var(--accent); }
  .pair { display: inline-flex; border-radius: 3px; overflow: hidden; box-shadow: 0 0 0 1.5px var(--accent); }
  .pair b { display: block; width: 0.85rem; height: 0.85rem; }
  .pair .f { background: var(--cat-1); }
  .pair .b { background: var(--cat-2); }
  .corner { display: block; }

  .sw { display: inline-block; width: 1rem; height: 2px; vertical-align: middle; margin-right: 0.35rem; }
  .sw.fwd { background: var(--cat-1); }
  .sw.bwd { background: var(--cat-2); }
  .dot { display: inline-block; width: 0.55rem; height: 0.55rem; border-radius: 50%; background: var(--dim); vertical-align: -0.02em; margin-right: 0.35rem; }

  @media (max-width: 560px) {
    .board { grid-template-columns: minmax(0, 1fr); gap: 0.2rem; }
    .corner { display: none; }
    .tag { margin-top: 0.35rem; }
    .words button { min-height: 2.5rem; font-size: 0.8rem; }
  }
</style>
