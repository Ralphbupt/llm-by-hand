<script lang="ts">
  import { onMount } from 'svelte'
  import { grade } from '@lib/grade'
  import { debugOn, hasReal, pass, recordMiss, subscribe, wasShown } from '@lib/progress'
  import RevealAnswer from './RevealAnswer.svelte'
  import NoWrapText from './NoWrapText.svelte'
  import type { NumberEx, ShapeEx } from '@lib/quiz'

  // practice: start fresh even if already solved (the mistake book's "redo"); solving never un-solves anything
  let { id, ex, practice = false }: { id: string; ex: NumberEx | ShapeEx; practice?: boolean } = $props()

  let value = $state('')
  let result = $state<{ ok: boolean; hint?: string } | null>(null)
  let done = $state(false)
  let misses = $state(0)
  let shown = $state(false)
  // hints so far: a ladder is easier to climb when the earlier rungs stay visible
  let hints = $state<string[]>([])

  let showAnswer = $state(false)
  const correctText = () => (ex.type === 'shape' ? `(${ex.answer.join(', ')})` : String(ex.answer))
  onMount(() => {
    if (!practice && hasReal(id)) { done = true; value = correctText() }
    if (!practice && wasShown(id)) shown = true
    const sync = () => {
      showAnswer = debugOn('answers')
      // the same question solved in another copy on this page (the test-out panel) shows as solved here too
      if (!practice && !done && hasReal(id)) { done = true; value = correctText(); shown = wasShown(id) }
    }
    sync()
    return subscribe(sync)
  })
  const answerText = $derived(ex.type === 'shape' ? `(${ex.answer.join(', ')})` : String(ex.answer) + (ex.type === 'number' && ex.tol ? ` (± ${ex.tol})` : ''))

  function check() {
    result = grade(ex, value, misses + 1)
    if (result.ok) {
      done = true
      pass(id)
    } else {
      misses++
      recordMiss(id)
      const h = result.hint ?? 'Not quite. Try again.'
      if (hints.at(-1) !== h) hints = [...hints, h]
    }
  }

  function reveal() {
    value = ex.type === 'shape' ? `(${ex.answer.join(', ')})` : String(ex.answer)
    result = null
    done = true
    shown = true
    pass(id, { shown: true })
  }
</script>

<div class="blank" class:done class:shown>
  <div class="prompt">
    <span class="tag">{ex.type === 'shape' ? 'Shape' : 'Number'}</span>
    <NoWrapText text={ex.prompt} />
  </div>
  <div class="row">
    <input
      bind:value
      aria-label={ex.prompt.replaceAll('`', '')}
      readonly={done}
      placeholder={ex.type === 'shape' ? 'e.g. (3, 4)' : 'a number'}
      onkeydown={(e) => e.key === 'Enter' && check()}
    />
    {#if ex.type === 'number' && ex.unit}<span class="unit">{ex.unit}</span>{/if}
    <button onclick={check} disabled={done}>{done ? (shown ? 'Answer shown' : '✓ Correct') : 'Check'}</button>
  </div>
  {#if hints.length && !done}
    <ol class="hints" aria-live="polite">
      {#each hints as h, i}<li class:latest={i === hints.length - 1}><span class="hn">Hint {i + 1}</span> <NoWrapText text={h} /></li>{/each}
    </ol>
  {/if}
  {#if !done && misses > 0}
    <RevealAnswer onreveal={reveal} />
  {/if}
  {#if showAnswer}
    <p class="dbg"><b>debug · answer:</b> {answerText}</p>
  {/if}
  {#if done && ex.after}
    <p class="after"><NoWrapText text={ex.after} /></p>
  {/if}
</div>

<style>
  .dbg { margin: 0.6rem 0 0; padding: 0.35rem 0.6rem; border: 1px dashed var(--warn); border-radius: 4px; font-size: 0.85rem; font-family: var(--mono); color: var(--warn); white-space: pre-wrap; }
  .dbg b { font-family: inherit; }

  .blank {
    border: 1px solid var(--line);
    border-left: 3px solid var(--accent);
    border-radius: 6px;
    padding: 0.9rem 1rem;
    margin: 1.2rem 0;
    background: var(--card);
  }
  .blank.done { border-left-color: var(--ok); }
  .blank.shown { border-left-color: var(--dim); }
  .prompt { margin-bottom: 0.6rem; }
  .tag {
    font-size: 0.72rem;
    padding: 0.1rem 0.4rem;
    border-radius: 3px;
    background: var(--accent);
    color: var(--on-solid);
    font-weight: 600;
    margin-right: 0.4rem;
  }
  .row { display: flex; gap: 0.5rem; align-items: center; }
  input {
    font: inherit;
    font-family: var(--mono);
    padding: 0.3rem 0.5rem;
    width: 9rem;
    border: 1px solid var(--field);
    border-radius: 4px;
    background: var(--bg);
    color: inherit;
  }
  input:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
  input[readonly] { border-color: var(--line); }
  .unit { color: var(--dim); font-size: 0.85rem; }
  button {
    font: inherit;
    padding: 0.3rem 0.9rem;
    border: 1px solid var(--line);
    border-radius: 4px;
    background: var(--bg);
    color: inherit;
    cursor: pointer;
  }
  button:disabled { cursor: default; color: var(--ok); border-color: var(--ok); }
  .shown button:disabled { color: var(--dim); border-color: var(--line); }
  .hints { list-style: none; margin: 0.6rem 0 0; padding: 0; display: grid; gap: 0.25rem; font-size: 0.9rem; color: var(--dim); }
  .hints li.latest { color: var(--fg); font-weight: 600; }
  .hn { font-size: 0.75rem; font-weight: 600; margin-right: 0.3rem; }
  @media (max-width: 760px) { input, button { min-height: 40px; } input { font-size: 16px; } }
  .after { margin: 0.6rem 0 0; color: var(--dim); font-size: 0.9rem; }
</style>
