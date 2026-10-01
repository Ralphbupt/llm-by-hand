<script lang="ts">
  import NoWrapText from './NoWrapText.svelte'
  import { onMount } from 'svelte'
  import { debugOn, hasReal, pass, recordMiss, subscribe } from '@lib/progress'
  import { pickHint } from '@lib/grade'
  import { optionOrder } from '@lib/shuffle'
  import type { PredictEx } from '@lib/quiz'

  // practice: start fresh even if already answered (the mistake book's "redo", the warm-up)
  let { id, ex, practice = false }: { id: string; ex: PredictEx; practice?: boolean } = $props()

  let picked = $state<number | null>(null)
  let revealed = $state(false)

  let showAnswer = $state(false)
  onMount(() => {
    if (!practice && hasReal(id)) revealed = true
    const sync = () => {
      showAnswer = debugOn('answers')
      if (!practice && !revealed && hasReal(id)) revealed = true
    }
    sync()
    return subscribe(sync)
  })

  // With `answer`, this is a graded multiple-choice question; without it, an ungraded "commit to a guess first".
  const graded = ex.answer !== undefined
  // graded options are shown in a fixed shuffled order (seeded by the id), so the right one is not always in the same
  // place; `i` stays the option's index in exercises.yaml, so `answer` and hint `equals` keep pointing at the same option
  const order = graded ? optionOrder(id, ex.options.length) : ex.options.map((_, i) => i)
  let wrong = $state<number[]>([])
  let hint = $state<string | undefined>(undefined)

  function choose(i: number) {
    if (revealed) return
    picked = i
    if (graded && i !== ex.answer) {
      wrong = [...wrong, i]
      recordMiss(id)
      hint = pickHint(ex.hints, { value: i }, wrong.length) ?? 'Not this one. Try another option.'
      return
    }
    revealed = true
    hint = undefined
    pass(id) // ungraded: choosing counts; graded: only the right option gets here
  }
</script>

<div class="predict" class:revealed>
  <div class="prompt"><span class="tag">{graded ? 'Choose' : 'Predict first'}</span><NoWrapText text={ex.prompt} /></div>
  <div class="opts">
    {#each order as i (i)}
      {@const opt = ex.options[i]}
      <button class:picked={picked === i && !wrong.includes(i)} class:wrong={wrong.includes(i)} onclick={() => choose(i)} disabled={(revealed && picked !== i) || wrong.includes(i)}>
        <NoWrapText text={opt} />
      </button>
    {/each}
  </div>
  {#if hint && !revealed}
    <p class="hint"><NoWrapText text={hint} /></p>
  {/if}
  {#if revealed}
    <p class="reveal">{graded && wrong.length === 0 ? '✓ ' : ''}<NoWrapText text={ex.reveal} /></p>
  {:else if showAnswer}
    <p class="dbg"><b>debug · reveal:</b> {ex.reveal}</p>
  {/if}
</div>

<style>
  .hint { margin: 0.6rem 0 0; color: var(--fg); font-size: 0.9rem; }
  button.wrong { border-color: var(--warn) !important; color: var(--warn); text-decoration: line-through; opacity: 0.7; }
  .dbg { margin: 0.6rem 0 0; padding: 0.35rem 0.6rem; border: 1px dashed var(--warn); border-radius: 4px; font-size: 0.85rem; font-family: var(--mono); color: var(--warn); white-space: pre-wrap; }
  .dbg b { font-family: inherit; }

  .predict {
    border: 1px solid var(--line);
    border-left: 3px solid var(--accent);
    border-radius: 6px;
    padding: 0.9rem 1rem;
    margin: 1.2rem 0;
    background: var(--card);
  }
  .prompt { margin-bottom: 0.6rem; }
  .tag {
    font-size: 0.72rem;
    padding: 0.1rem 0.4rem;
    border-radius: 3px;
    border: 1px solid var(--accent);
    color: var(--accent);
    font-weight: 600;
    margin-right: 0.4rem;
  }
  .opts { display: flex; flex-wrap: wrap; gap: 0.5rem; }
  button {
    font: inherit;
    text-align: left;
    padding: 0.35rem 0.8rem;
    border: 1px solid var(--line);
    border-radius: 4px;
    background: var(--bg);
    color: inherit;
    cursor: pointer;
  }
  button.picked { border-color: var(--accent); color: var(--accent); }
  @media (max-width: 760px) { button { min-height: 40px; } }
  button:disabled { opacity: 0.45; cursor: default; }
  .reveal { margin: 0.7rem 0 0; font-size: 0.92rem; }
</style>
