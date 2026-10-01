<script lang="ts">
  /**
   * Repeat lab (level 18): greedy decoding with a counting model trained on our own rule-made sentences.
   * The model looks at the last two words. A repetition penalty lowers the score of every word
   * by `penalty × (times it was already written)`.
   */
  import { onMount } from 'svelte'
  import LabFrame from './LabFrame.svelte'
  import { has, subscribe } from '@lib/progress'
  import { greedyWithPenalty, repeatLength, followsRules, type Trigram } from '@lib/generation'

  // the "score after penalty" column stays "?" until that question is solved
  let { hide }: { hide?: string } = $props()
  let solved = $state(false)
  let model = $state<Trigram | null>(null)
  let failed = $state(false)
  onMount(() => {
    fetch('/data/generation/trigram.json').then((r) => r.json()).then((m) => (model = m)).catch(() => (failed = true))
    if (!hide) return
    const sync = () => (solved = has(hide))
    sync()
    return subscribe(sync)
  })
  const masked = $derived(!!hide && !solved)

  const START = ['.', 'the']
  const N = 14
  let penalty = $state(0)
  let at = $state(7) // which step to inspect

  const run = $derived(model ? greedyWithPenalty(model, START, N, penalty) : null)
  const words = $derived(run ? run.words.slice(1) : [])
  const loop = $derived(repeatLength(words))
  const valid = $derived(followsRules(words))
  const step = $derived(run ? run.steps[at] : null)
  const top = $derived(step ? [...step.scores].sort((a, b) => b.score - a.score).slice(0, 4) : [])
  const fmt = (v: number) => (Number.isFinite(v) ? (Math.abs(v) < 5e-5 ? '0.0000' : v.toFixed(4)) : '−∞')
</script>

<LabFrame
  title="Why greedy writing loops, and how a penalty breaks the loop"
  hint="Raise the repetition penalty and watch the loop break. Tap a word to see the scores that chose it."
  onreset={() => { penalty = 0; at = 7 }}
  resetDisabled={penalty === 0 && at === 7}
>
  {#if failed}
    <p class="dim">Could not load the model data. Reload the page to try again.</p>
  {:else if !run}
    <div class="skeleton" aria-hidden="true"></div>
    <p class="dim">Loading the counting model…</p>
  {:else}
    <p class="text" aria-label="generated text">
      {#each words as w, i}
        {#if loop > 0 && i === loop}<span class="loopmark" title={`from here the same ${loop} words come again`}>↻</span>{/if}
        <button type="button" class="tok" class:inspect={i === at + 1} class:loop={loop > 0 && i >= loop} aria-pressed={i === at + 1} onclick={() => i > 0 && (at = i - 1)}>{w}</button>
      {/each}
    </p>
    <p class="status">
      {#if loop}<span class="pill warn">↻ repeats every {loop} words</span>{:else}<span class="pill ok">no loop in these 14 words</span>{/if}
      <span class="dim">{valid ? 'Every word fits the sentence rules.' : 'Some words break the sentence rules.'}</span>
    </p>

    {#if step}
      <div class="step">
        <div class="ctxline">Step {at + 1}: after “<b>{step.context[0]} {step.context[1]}</b>”, the 4 best scores</div>
        <div class="table" role="table">
          <div class="tr th" role="row"><span>word</span><span>log p</span><span><span class="long">times written</span><span class="short">times</span></span><span><span class="long">− penalty × times</span><span class="short">− penalty</span></span><span>score</span><span class="barcol"></span></div>
          {#each top as s}
            <div class="tr" class:pick={s.word === step.pick} role="row">
              <span class="w">{s.word}{s.word === step.pick ? ' ←' : ''}</span>
              <span class="num">{fmt(s.logp)}</span>
              <span class="num">{s.seen}</span>
              <span class="num">{penalty * s.seen === 0 ? '0' : '−' + (penalty * s.seen).toFixed(1)}</span>
              <span class="num">{masked && penalty > 0 && s.seen > 0 ? '?' : fmt(s.score)}</span>
              <span class="sbar barcol"><i style:width="{masked && penalty > 0 && s.seen > 0 ? 0 : Math.exp(s.score - top[0].score) * 100}%"></i></span>
            </div>
          {/each}
        </div>
      </div>
    {/if}
  {/if}

  {#snippet controls()}
    <label class="knob">repetition penalty <b>{penalty.toFixed(1)}</b>
      <input type="range" min="0" max="3" step="0.1" value={penalty} oninput={(e) => (penalty = +e.currentTarget.value)} />
    </label>
  {/snippet}

  {#snippet readout()}
    {#if run}
      {loop ? `Greedy repeats a ${loop}-word loop` : 'No loop'} at penalty {penalty.toFixed(1)} · model: last two words → next word, counted from {model?.n_words.toLocaleString()} rule-made words
      {#if masked && penalty > 0}<span class="idle"> · scores of penalized words show “?” until you answer the question below</span>{/if}
    {:else}…{/if}
  {/snippet}

  {#snippet legend()}
    <span class="lg"><i class="sw" style="background: var(--accent)"></i>the word being inspected</span>
    <span class="lg"><i class="sw" style="background: color-mix(in srgb, var(--warn) 30%, var(--bg)); border: 1px solid var(--warn)"></i>words inside the loop</span>
  {/snippet}
</LabFrame>

<style>
  .skeleton { height: 8rem; border-radius: 6px; background: var(--bg); border: 1px dashed var(--line); }
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
  .knob { display: flex; flex-wrap: wrap; gap: 0.3rem 0.8rem; align-items: center; font-family: var(--mono); font-size: 0.88rem; width: 100%; }
  .knob b { color: var(--accent); }
  .knob input { flex: 1; min-width: 160px; accent-color: var(--accent); }
  .text { display: flex; flex-wrap: wrap; gap: 0.3rem; margin: 0; }
  .tok { font: inherit; font-family: var(--mono); font-size: 0.92rem; padding: 0.15rem 0.45rem; min-height: 2rem; border: 1px solid var(--field); border-radius: 4px; background: var(--bg); color: inherit; cursor: pointer; }
  .tok:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .tok.loop { background: color-mix(in srgb, var(--warn) 14%, var(--bg)); border-color: color-mix(in srgb, var(--warn) 50%, var(--field)); }
  .tok.inspect { border-color: var(--accent); color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
  .loopmark { align-self: center; color: var(--warn); font-weight: 700; padding: 0 0.1rem; }
  .status { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; margin: 0.5rem 0 0; font-size: 0.85rem; }
  .pill { display: inline-block; padding: 0.05rem 0.55rem; border-radius: 999px; font-size: 0.8rem; font-family: var(--mono); border: 1px solid; }
  .pill.warn { color: var(--warn); border-color: var(--warn); }
  .pill.ok { color: var(--ok); border-color: var(--ok); }
  .sbar { height: 0.75rem; background: var(--bg); border-radius: 2px; overflow: hidden; }
  .sbar i { display: block; height: 100%; background: var(--cat-1); opacity: 0.6; transition: width 0.2s ease-out; }
  .tr.pick .sbar i { background: var(--accent); opacity: 1; }
  .step { margin-top: 0.8rem; }
  .ctxline { font-size: 0.88rem; }
  .table { margin-top: 0.4rem; font-size: 0.85rem; }
  .tr { display: grid; grid-template-columns: 4.5rem 5rem 6.5rem 9rem 5rem minmax(4rem, 1fr); align-items: center; gap: 0.4rem; padding: 0.15rem 0; }
  .tr.pick { color: var(--accent); font-weight: 600; }
  .th { color: var(--dim); font-size: 0.78rem; }
  .th > span:nth-child(n+2):nth-child(-n+5) { text-align: right; }
  .short { display: none; }
  .w { font-family: var(--mono); }
  .num { font-family: var(--mono); text-align: right; }
  .dim { color: var(--dim); font-size: 0.85rem; margin: 0; }
  .lg { display: inline-flex; align-items: center; gap: 0.35rem; }
  .sw { width: 0.85rem; height: 0.7rem; border-radius: 2px; display: inline-block; }
  /* phone: short headers, no bar column, so all five numbers fit */
  @media (max-width: 560px) {
    .tr { grid-template-columns: 3.6rem 4.4rem 2.8rem 4.4rem 4.4rem; gap: 0.3rem; }
    .barcol { display: none; }
    .long { display: none; }
    .short { display: inline; }
  }
  @media (prefers-reduced-motion: reduce) { .sbar i { transition: none; } }
  /* phones: touch targets at least 40px tall; 16px fields so iOS does not zoom */
  @media (max-width: 760px) { .tok { min-height: 2.5rem; min-width: 2.5rem; } .knob input { min-height: 2.5rem; } }
</style>
