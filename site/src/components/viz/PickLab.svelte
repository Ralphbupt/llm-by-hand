<script lang="ts">
  /**
   * Pick lab (level 18): five candidate words after "the cat sat on the".
   * Temperature, then a filter (none / top-k / top-p), then the choice: greedy or a weighted die.
   */
  import { onMount } from 'svelte'
  import LabFrame from './LabFrame.svelte'
  import { has, subscribe } from '@lib/progress'
  import { softmax, order, cumulative, topKKeep, topPKeep, sampleIndex } from '@lib/generation'

  // values a question asks for stay "?" until that question is solved
  let { hide = {} }: { hide?: { prob?: string; renorm?: string; cum?: string } } = $props()
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
  const locked = (k: 'prob' | 'renorm' | 'cum') => !!hide[k] && !solved[hide[k]!]

  const WORDS = ['mat', 'sofa', 'rug', 'roof', 'moon']
  const SCORES = [2.0, 1.5, 1.0, 0.0, -1.0]

  let T = $state(1)
  let mode = $state<'none' | 'topk' | 'topp'>('none')
  let k = $state(2)
  let p = $state(0.9)
  let counts = $state([0, 0, 0, 0, 0])
  let last = $state<number | null>(null)

  const probs = $derived(softmax(SCORES, T))
  const keep = $derived(mode === 'topk' ? topKKeep(probs, k) : mode === 'topp' ? topPKeep(probs, p) : probs.map(() => true))
  const final = $derived.by(() => {
    const kept = probs.map((q, i) => (keep[i] ? q : 0))
    const s = kept.reduce((a, b) => a + b, 0)
    return kept.map((q) => q / s)
  })
  const cum = $derived(cumulative(probs))
  const rows = $derived(order(probs))
  const greedy = $derived(rows[0])
  const total = $derived(counts.reduce((a, b) => a + b, 0))
  // hide the column that would give away the open question in the current mode
  const hideFinal = $derived(locked('prob') || (mode === 'topk' && locked('renorm')) || (mode === 'topp' && locked('cum')))
  const hideCum = $derived(locked('prob') || (mode === 'topp' && locked('cum')))

  function clear() { counts = [0, 0, 0, 0, 0]; last = null }
  function sample(n: number) {
    const c = [...counts]
    let i = 0
    for (let t = 0; t < n; t++) { i = sampleIndex(final); c[i]++ }
    counts = c
    last = i
  }
  function reset() { T = 1; mode = 'none'; k = 2; p = 0.9; clear() }
  const changed = $derived(T !== 1 || mode !== 'none' || k !== 2 || p !== 0.9 || total > 0)
  const fmt = (v: number) => v.toFixed(4)
</script>

<LabFrame
  title="Pick the next word: temperature, then a filter, then a draw"
  hint="Change T and the filter, then sample. Rows are sorted by probability, largest first."
  onreset={reset}
  resetDisabled={!changed}
>
  <p class="ctx">the cat sat on the <b>{last === null ? '___' : WORDS[last]}</b></p>

  <!-- all five words in one row in sorted order: widths are probabilities, so the right edge is 1 -->
  <div class="strip-wrap">
    <div class="strip-label">running total, largest first{mode === 'topp' ? ` · top-p cuts at ${p.toFixed(2)}` : mode === 'topk' ? ` · top-k keeps the first ${k}` : ''}</div>
    {#if locked('prob')}
      <div class="strip blank">? (answer the question below first)</div>
    {:else}
      {@const showCut = mode !== 'none' && !(mode === 'topp' && locked('cum'))}
      <div class="strip" class:withcut={mode === 'topp' && showCut} role="img" aria-label="The five probabilities in one row, largest first">
        {#each rows as i, r}
          <span class="seg" class:out={showCut && !keep[i]} style:width="{probs[i] * 100}%" style:--o={1 - r * 0.15}>
            {#if probs[i] > 0.08}{WORDS[i]}{/if}
          </span>
        {/each}
        {#if mode === 'topp' && showCut}
          <i class="cut" style:left="{p * 100}%"><b>p = {p.toFixed(2)}</b></i>
        {/if}
      </div>
      <div class="ticks"><span>0</span><span>0.5</span><span>1</span></div>
    {/if}
  </div>

  <div class="table" role="table">
    <div class="tr th" role="row">
      <span>word</span><span>score</span><span>p</span><span>running total</span><span>kept?</span><span>after filter</span><span>sampled</span>
    </div>
    {#each rows as i}
      <div class="tr" class:out={!keep[i]} role="row">
        <span class="w">{WORDS[i]}{i === greedy ? ' ★' : ''}</span>
        <span class="num">{SCORES[i].toFixed(1)}</span>
        <span class="num">{locked('prob') ? '?' : fmt(probs[i])}</span>
        <span class="num">{hideCum ? '?' : fmt(cum[i])}</span>
        <span class="num">{mode === 'topp' && locked('cum') ? '?' : keep[i] ? 'yes' : 'no'}</span>
        <span class="bar"><i style="width:{hideFinal ? 0 : final[i] * 100}%"></i><em>{hideFinal ? '?' : fmt(final[i])}</em></span>
        <span class="num">{counts[i]}</span>
      </div>
    {/each}
  </div>
  <p class="dim">★ = greedy’s pick: always the top word. Rows are sorted by p, largest first.</p>


  {#snippet controls()}
    <div class="ctrl">
    <label>temperature T = <b>{T.toFixed(2)}</b>
      <input type="range" min="0.1" max="3" step="0.05" value={T} oninput={(e) => { T = +e.currentTarget.value; clear() }} />
    </label>
    <div class="modes" role="group" aria-label="Filter">
      <button type="button" aria-pressed={mode === 'none'} class:on={mode === 'none'} onclick={() => { mode = 'none'; clear() }}>no filter</button>
      <button type="button" aria-pressed={mode === 'topk'} class:on={mode === 'topk'} onclick={() => { mode = 'topk'; clear() }}>top-k</button>
      <button type="button" aria-pressed={mode === 'topp'} class:on={mode === 'topp'} onclick={() => { mode = 'topp'; clear() }}>top-p</button>
    </div>
    {#if mode === 'topk'}
      <label>k = <b>{k}</b><input type="range" min="1" max="5" step="1" value={k} oninput={(e) => { k = +e.currentTarget.value; clear() }} /></label>
    {:else if mode === 'topp'}
      <label>p = <b>{p.toFixed(2)}</b><input type="range" min="0.05" max="1" step="0.05" value={p} oninput={(e) => { p = +e.currentTarget.value; clear() }} /></label>
    {/if}
    </div>
    <div class="acts">
      <button type="button" class="lab-btn primary" onclick={() => sample(1)}>Sample 1</button>
      <button type="button" class="lab-btn" onclick={() => sample(1000)}>Sample 1000</button>
      <button type="button" class="lab-btn ghost" onclick={clear} disabled={total === 0}>Clear counts</button>
    </div>
  {/snippet}

  {#snippet readout()}
    {#if last === null}<span class="idle">Press Sample to draw a word.</span>{:else}{total} samples · last draw: <b>{WORDS[last]}</b> · greedy would always say <b>{WORDS[greedy]}</b>{/if}
    {#if hideFinal}<span class="idle"> · some numbers show “?” until you answer the question about them below</span>{/if}
  {/snippet}
</LabFrame>

<style>
  .ctx { margin: 0 0 0.4rem; font-size: 1.05rem; }
  .ctx b { color: var(--accent); font-family: var(--mono); }
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
  .ctrl { display: flex; flex-wrap: wrap; gap: 0.6rem 1.2rem; align-items: center; font-family: var(--mono); font-size: 0.85rem; width: 100%; }
  .ctrl label { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; }
  .ctrl input { min-width: 140px; accent-color: var(--accent); }
  .acts { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }
  .modes { display: inline-flex; border: 1px solid var(--field); border-radius: 999px; overflow: hidden; }
  .modes button { font: inherit; font-size: 0.82rem; padding: 0.25rem 0.8rem; min-height: 2.1rem; border: 0; background: var(--bg); color: var(--dim); cursor: pointer; }
  .modes button + button { border-left: 1px solid var(--field); }
  .modes button.on { color: var(--accent); background: var(--highlight); }
  .modes button:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
  .strip-wrap { margin-top: 0.6rem; }
  .strip-label { font-size: 0.8rem; color: var(--dim); font-family: var(--mono); margin-bottom: 0.25rem; }
  .strip { position: relative; display: flex; height: 32px; border-radius: 4px; background: var(--bg); border: 1px solid var(--line); margin-bottom: 0.25rem; }
  .strip.withcut { margin-bottom: 1.4rem; }
  .strip.blank { height: auto; display: block; padding: 0.4rem; font-size: 0.85rem; color: var(--warn); border-style: dashed; margin-bottom: 0.3rem; }
  .seg { display: grid; place-items: center; overflow: hidden; white-space: nowrap; font-family: var(--mono); font-size: 0.78rem; font-weight: 600;
    color: var(--fg); background: color-mix(in srgb, var(--cat-1) calc(25% + 40% * var(--o)), transparent);
    border-right: 1px solid var(--card); transition: width 0.2s ease-out, background 0.2s; }
  .seg.out { background: repeating-linear-gradient(135deg, var(--bg) 0 4px, var(--line) 4px 5px); color: var(--dim); }
  .cut { position: absolute; top: -5px; bottom: -5px; width: 0; border-left: 2.5px solid var(--accent); transition: left 0.2s ease-out; }
  .cut b { position: absolute; top: 100%; transform: translateX(-50%); font-size: 0.75rem; font-weight: 600; color: var(--accent); font-family: var(--mono); white-space: nowrap; }
  .ticks { display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--dim); font-family: var(--mono); }
  .table { margin-top: 0.8rem; font-size: 0.85rem; }
  .tr { display: grid; grid-template-columns: 4rem 3rem 4rem 4.6rem 3rem minmax(5.5rem, 1fr) 3rem; gap: 0.4rem; align-items: center; padding: 0.12rem 0; }
  .tr.out { opacity: 0.45; }
  .th { color: var(--dim); font-size: 0.78rem; }
  .th > span:nth-child(n+2):nth-child(-n+5), .th > span:last-child { text-align: right; }
  .w { font-family: var(--mono); font-weight: 600; }
  .num { font-family: var(--mono); text-align: right; }
  .bar { position: relative; height: 1.4rem; background: var(--bg); border: 1px solid var(--line); border-radius: 3px; overflow: hidden; }
  .bar i { position: absolute; inset: 0 auto 0 0; background: var(--cat-1); opacity: 0.45; transition: width 0.2s ease-out; }
  .bar em { position: relative; font-style: normal; font-family: var(--mono); font-size: 0.78rem; padding-left: 0.3rem; line-height: 1.4rem; }
  .dim { color: var(--dim); font-size: 0.82rem; margin: 0.4rem 0 0; }
  /* phone: drop the score and kept? columns (kept shows as the faded row) so the table fits */
  @media (max-width: 560px) {
    .tr { grid-template-columns: 3.6rem 3.8rem 4.2rem minmax(4.2rem, 1fr) 2.4rem; }
    .tr > :nth-child(2), .tr > :nth-child(5) { display: none; }
  }
  @media (prefers-reduced-motion: reduce) { .seg, .cut, .bar i { transition: none; } }
  /* phones: touch targets at least 40px tall; 16px fields so iOS does not zoom */
  @media (max-width: 760px) { .modes button { min-height: 2.5rem; } .ctrl input { min-height: 2.5rem; } }
</style>
