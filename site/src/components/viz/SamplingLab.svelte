<script lang="ts">
  /**
   * Sampling lab: candidate next words with fixed scores.
   * Temperature divides the scores before softmax. Sampling draws real random words
   * and counts them, so you can compare the counts with the probabilities.
   */
  import { onMount } from 'svelte'
  import { has, subscribe } from '@lib/progress'
  import LabFrame from './LabFrame.svelte'

  // A value that a question on the page asks for stays "?" until that question is solved.
  let { hide = {} }: { hide?: Record<string, string | undefined> } = $props()
  let solved = $state<Record<string, boolean>>({})
  onMount(() => {
    const sync = () => {
      const next: Record<string, boolean> = {}
      for (const id of Object.values(hide)) if (id) next[id] = has(id)
      solved = next
    }
    sync()
    return subscribe(sync)
  })
  const locked = (k: string) => !!hide[k] && !solved[hide[k]!]

  const WORDS = ['mat', 'sofa', 'roof', 'moon']
  const SCORES = [2.0, 1.0, 0.5, -1.0]

  let T = $state(1)
  let counts = $state([0, 0, 0, 0])
  let last = $state<number | null>(null)

  const probs = $derived.by(() => {
    const z = SCORES.map((s) => s / T)
    const m = Math.max(...z)
    const e = z.map((v) => Math.exp(v - m))
    const sum = e.reduce((a, b) => a + b, 0)
    return e.map((v) => v / sum)
  })
  const total = $derived(counts.reduce((a, b) => a + b, 0))

  function draw(): number {
    let r = Math.random()
    for (let i = 0; i < probs.length; i++) {
      r -= probs[i]
      if (r < 0) return i
    }
    return probs.length - 1
  }
  function sample(n: number) {
    const c = [...counts]
    let k = 0
    for (let i = 0; i < n; i++) { k = draw(); c[k]++ }
    counts = c
    last = k
  }
  function clear() { counts = [0, 0, 0, 0]; last = null }
  function setT(v: number) { T = v; clear() }
</script>

<LabFrame
  title="Temperature changes the probabilities; sampling picks words with them"
  hint="Move the temperature, then sample words and compare the counts with the probabilities."
  onreset={() => setT(1)}
  resetDisabled={T === 1 && total === 0}
>
  <p class="ctx">The cat sat on the <b class:blank={last === null}>{last === null ? '___' : WORDS[last]}</b></p>

  <div class="table" role="table" aria-label="Scores, probabilities and sampled fractions">
    <div class="tr th" role="row"><span role="columnheader">word</span><span role="columnheader" class="r">score</span><span role="columnheader" class="r">score / T</span><span role="columnheader">probability</span><span role="columnheader" class="r">sampled</span></div>
    {#each WORDS as w, i}
      <div class="tr" class:hit={last === i} role="row">
        <span class="w" role="cell">{w}</span>
        <span class="num" role="cell">{SCORES[i].toFixed(1)}</span>
        <span class="num" role="cell">{(SCORES[i] / T).toFixed(2)}</span>
        <span class="bar" role="cell">
          <i class="p" style="width:{locked('prob') ? 0 : probs[i] * 100}%"></i>
          {#if total}<b class="s" style="left:{(counts[i] / total) * 100}%"></b>{/if}
          <em class:ask={locked('prob')}>{locked('prob') ? '?' : probs[i].toFixed(3)}</em>
        </span>
        <span class="num sh" role="cell">{total ? (counts[i] / total).toFixed(2) : '—'}<small>{total ? ` ${counts[i]}` : ''}</small></span>
      </div>
    {/each}
  </div>
  {#if locked('prob')}<p class="note">The probabilities appear once you answer the question below.</p>{/if}

  {#snippet controls()}
    <button class="lab-btn primary" onclick={() => sample(1)}>Sample 1 word</button>
    <button class="lab-btn" onclick={() => sample(100)}>Sample 100</button>
    <button class="lab-btn" onclick={() => sample(1000)}>Sample 1000</button>
    <button class="lab-btn" onclick={clear} disabled={total === 0}>Clear counts</button>
    <div class="temp">
      <label class="knob">
        <span>temperature T = <b>{T.toFixed(2)}</b></span>
        <input type="range" min="0.1" max="3" step="0.05" value={T}
          oninput={(e) => setT(+(e.currentTarget as HTMLInputElement).value)} />
      </label>
      <span class="presets" role="group" aria-label="Temperature presets">
        {#each [0.1, 0.5, 1, 2, 3] as v}
          <button class="lab-btn seg" class:on={T === v} aria-pressed={T === v} onclick={() => setT(v)}>T = {v}</button>
        {/each}
      </span>
    </div>
  {/snippet}

  {#snippet readout()}
    {#if total}{total} sample{total === 1 ? '' : 's'} at T = {T.toFixed(2)}. Last word drawn: <b>{WORDS[last ?? 0]}</b>.
    {:else}<span class="idle">No samples yet. Changing T clears the counts.</span>{/if}
  {/snippet}

  {#snippet legend()}
    <span><i class="key p"></i>probability</span>
    <span><i class="key s"></i>fraction of the samples so far</span>
    <span><i class="key hit"></i>the word drawn last</span>
  {/snippet}
</LabFrame>

<style>
  .ctx { margin: 0 0 0.8rem; font-size: 1.05rem; }
  .ctx b { color: var(--accent); font-family: var(--mono); }
  .ctx b.blank { color: var(--dim); }
  .temp { display: flex; flex-wrap: wrap; gap: 0.4rem 1rem; align-items: center; flex-basis: 100%; }
  .knob { display: flex; flex-wrap: wrap; gap: 0.3rem 0.8rem; align-items: center; font-family: var(--mono); font-size: 0.85rem; min-height: 2.5rem; flex: 1 1 16rem; }
  .knob b { font-variant-numeric: tabular-nums; }
  .knob input { flex: 1; min-width: 10rem; accent-color: var(--accent); }
  .presets { display: flex; flex-wrap: wrap; gap: 0.3rem; }
  .seg { font-size: 0.8rem; padding: 0.3rem 0.6rem; font-family: var(--mono); }
  .seg.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  .table { font-size: 0.85rem; }
  .tr { display: grid; grid-template-columns: 3.2rem 2.8rem 4.2rem minmax(0, 1fr) 4.6rem; gap: 0.5rem; align-items: center; padding: 0.2rem 0.25rem; border-radius: 4px; transition: background 0.25s; }
  .tr.hit { background: var(--highlight); }
  .tr.hit .w { color: var(--accent); }
  @media (max-width: 480px) { .tr { grid-template-columns: 2.9rem 2.4rem 3.3rem minmax(0, 1fr) 2.9rem; gap: 0.3rem; } .tr small { display: none; } }
  .r { text-align: right; }
  .sh small { color: var(--dim); font-size: 0.74rem; margin-left: 0.2rem; }
  .th { color: var(--dim); font-size: 0.76rem; }
  .w { font-family: var(--mono); font-weight: 600; }
  .num { font-family: var(--mono); text-align: right; font-variant-numeric: tabular-nums; }
  .bar { position: relative; height: 1.5rem; background: var(--bg); border: 1px solid var(--line); border-radius: 3px; overflow: hidden; }
  .bar i.p { position: absolute; inset: 0 auto 0 0; background: var(--cat-1); opacity: 0.45; transition: width 0.25s; }
  .bar b.s { position: absolute; top: 0; bottom: 0; width: 3px; margin-left: -1.5px; background: var(--fg); transition: left 0.25s; }
  .bar em { position: relative; font-style: normal; font-family: var(--mono); font-size: 0.78rem; padding-left: 0.3rem; line-height: 1.5rem; white-space: nowrap; font-variant-numeric: tabular-nums; }
  .bar em.ask { color: var(--warn); font-weight: 700; }
  .key { display: inline-block; vertical-align: -0.1rem; margin-right: 0.35rem; }
  .key.p { width: 0.9rem; height: 0.65rem; background: var(--cat-1); opacity: 0.55; border-radius: 2px; }
  .key.s { width: 3px; height: 0.8rem; background: var(--fg); }
  .key.hit { width: 0.9rem; height: 0.65rem; background: var(--highlight); border: 1px solid var(--accent); border-radius: 2px; }
  .sh { color: var(--dim); }
  @media (prefers-reduced-motion: reduce) { .bar i.p, .bar b.s, .tr { transition: none; } }
  .note { color: var(--dim); font-size: 0.8rem; margin: 0.5rem 0 0; }
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
</style>
