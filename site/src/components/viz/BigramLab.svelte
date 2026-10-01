<script lang="ts">
  /**
   * Bigram lab (level 11): count which word follows which in the generated stories,
   * turn the counts into probabilities, and write new sentences one word at a time.
   * Same corpus and math as content/2-theory/language-models/demo.py.
   */
  import { onMount } from 'svelte'
  import { bigramCounts, rowProbs, streamPerplexity } from '@lib/lm'
  import LabFrame from './LabFrame.svelte'

  let vocab = $state<string[]>([])
  let train = $state<string[]>([])
  let held = $state<string[]>([])
  let show = $state('counts') // 'counts' | 'probs' (the LabFrame view switch)
  let row = $state(0)
  let written = $state<{ w: string; p: number }[][]>([])
  let failed = $state(false)

  onMount(async () => {
    try {
      const d = await (await fetch('/data/language-models/corpus.json')).json()
      vocab = d.vocab; train = d.train; held = d.heldout
    } catch { failed = true }
  })

  const tokens = $derived(train.join(' ').split(' ').filter(Boolean))
  const C = $derived(vocab.length ? bigramCounts(tokens, vocab) : [])
  const P = $derived(C.length ? rowProbs(C) : [])
  const all = $derived(new Set([...train, ...held]))
  const pplCount = $derived(P.length ? streamPerplexity(held.join(' ').split(' '), vocab, P) : 0)

  function sample(probs: number[]): number {
    let r = Math.random()
    for (let j = 0; j < probs.length; j++) { r -= probs[j]; if (r <= 0) return j }
    return probs.length - 1
  }
  function write() {
    const dot = vocab.indexOf('.')
    let prev = dot
    const out: { w: string; p: number }[] = []
    for (let k = 0; k < 15; k++) {
      const j = sample(P[prev])
      out.push({ w: vocab[j], p: P[prev][j] })
      prev = j
      if (j === dot) break
    }
    written = [out, ...written].slice(0, 6)
  }
  const sentence = (s: { w: string }[]) => s.map((x) => x.w).join(' ')
  const f = (v: number) => (show === 'counts' ? String(v) : v === 0 ? '0' : v.toFixed(2))
  const changed = $derived(show !== 'counts' || row !== 0 || written.length > 0)
  function reset() { show = 'counts'; row = 0; written = [] }
</script>

<LabFrame
  title="Count which word follows which"
  hint="Pick a word on the left to see what can come after it, then let the counts write a sentence."
  views={[{ id: 'counts', label: 'Counts' }, { id: 'probs', label: 'Probabilities' }]}
  bind:view={show}
  onreset={reset}
  resetDisabled={!changed}
>
  {#if failed}
    <p class="state">Could not load the stories. Reload the page to try again.</p>
  {:else if !vocab.length}
    <p class="state">Loading the stories…</p>
  {:else}
    <p class="sec">The stories: {train.length} sentences for counting ({tokens.length} words), {held.length} held out for testing. The first four:</p>
    <ul class="corpus">{#each train.slice(0, 4) as s}<li>{s}</li>{/each}</ul>

    <p class="sec">{show === 'counts' ? 'How often the next word follows this word' : 'Each row divided by its total: the chance of each next word'}</p>
    <div class="scroll">
      <table>
        <thead>
          <tr><th class="corner">this ↓ · next →</th>{#each vocab as w}<th>{w}</th>{/each}</tr>
        </thead>
        <tbody>
          {#each vocab as w, i}
            <tr class:on={i === row}>
              <th><button type="button" class="rowbtn" aria-pressed={i === row} onclick={() => (row = i)}>{w}</button></th>
              {#each vocab as _, j}
                <td style="--w: {P[i][j]}" class:zero={C[i][j] === 0}>{f(show === 'counts' ? C[i][j] : P[i][j])}</td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <p class="sec">After “<b>{vocab[row]}</b>” the next word is…</p>
    <div class="bars">
      {#each vocab.map((w, j) => [w, P[row][j]] as [string, number]).filter(([, q]) => q > 0).sort((a, b) => b[1] - a[1]) as [w, q] (w)}
        <div class="b"><span class="lab2">{w}</span><span class="track"><i style="width: {q * 100}%"></i></span><span class="v">{q.toFixed(3)}</span></div>
      {/each}
    </div>

    {#if written.length}
      <p class="sec">Sentences written by the counts (each word with the probability it was picked with)</p>
      {#each written as s, k}
        <div class="out" class:latest={k === 0}>
          <div class="words">{#each s as x}<span class="w">{x.w}<small>{x.p.toFixed(2)}</small></span>{/each}</div>
          <span class="tag" class:new={!all.has(sentence(s))}>{all.has(sentence(s)) ? 'in the stories' : 'never in the stories'}</span>
        </div>
      {/each}
    {/if}
  {/if}

  {#snippet controls()}
    <button type="button" class="lab-btn primary" onclick={write} disabled={!vocab.length}>Write a sentence</button>
    <span class="note">Starts after a “.” and picks each next word by its probability.</span>
  {/snippet}

  {#snippet readout()}
    {#if vocab.length}
      perplexity on the {held.length} held-out sentences: counting model <b>{pplCount.toFixed(3)}</b> · guessing uniformly among {vocab.length} words <b>{vocab.length.toFixed(3)}</b>
    {:else}
      <span class="idle">Perplexity appears when the stories have loaded.</span>
    {/if}
  {/snippet}
</LabFrame>

<style>
  .state { min-height: 12rem; display: grid; place-items: center; margin: 0; color: var(--dim); font-size: 0.9rem; }
  .sec { font-size: 0.82rem; color: var(--dim); margin: 0.6rem 0 0.35rem; }
  .corpus { margin: 0 0 0.4rem; padding-left: 1.2rem; font-family: var(--mono); font-size: 0.85rem; }
  .scroll { overflow-x: auto; max-width: 100%; }
  table { font-family: var(--mono); font-size: 0.8rem; width: auto; border-collapse: collapse; }
  th, td { border: 1px solid var(--line); padding: 0.18rem 0.38rem; text-align: right; min-width: 2.5rem; }
  thead th { color: var(--dim); font-weight: 400; text-align: center; border: none; }
  th.corner { font-size: 0.72rem; text-align: left; min-width: 5rem; }
  td { background: color-mix(in srgb, var(--accent) calc(var(--w) * 55%), transparent); transition: background 0.2s; }
  td.zero { color: var(--dim); opacity: 0.45; }
  tbody th { border: none; text-align: left; }
  .rowbtn { font: inherit; border: none; padding: 0.2rem 0.3rem; min-height: 1.9rem; background: none; color: var(--dim); font-family: var(--mono); font-size: 0.8rem; cursor: pointer; border-radius: 4px; }
  .rowbtn:hover { background: var(--highlight); color: var(--fg); }
  .rowbtn:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
  tr.on .rowbtn { color: var(--accent); font-weight: 700; }
  tr.on td { outline: 1px solid var(--accent); }
  .bars { display: grid; gap: 0.25rem; max-width: 26rem; }
  .b { display: grid; grid-template-columns: 3.2rem 1fr 3.4rem; gap: 0.4rem; align-items: center; font-family: var(--mono); font-size: 0.82rem; }
  .track { height: 0.75rem; background: var(--bg); border: 1px solid var(--line); border-radius: 3px; overflow: hidden; }
  .track i { display: block; height: 100%; background: var(--accent); transition: width 0.25s; }
  @media (prefers-reduced-motion: reduce) { .track i, td { transition: none; } }
  .v { text-align: right; }
  .out { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; margin: 0.3rem 0; opacity: 0.65; }
  .out.latest { opacity: 1; }
  .words { display: flex; flex-wrap: wrap; gap: 0.25rem; }
  .w { display: inline-flex; flex-direction: column; align-items: center; padding: 0.05rem 0.3rem; border: 1px solid var(--line); border-radius: 4px; background: var(--bg); font-family: var(--mono); font-size: 0.88rem; line-height: 1.2; }
  .w small { font-size: 0.72rem; color: var(--dim); }
  .tag { font-size: 0.76rem; color: var(--dim); border: 1px solid var(--line); border-radius: 999px; padding: 0 0.5rem; }
  .tag.new { color: var(--cat-2); border-color: var(--cat-2); }
  .note { font-size: 0.82rem; color: var(--dim); }
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
</style>
