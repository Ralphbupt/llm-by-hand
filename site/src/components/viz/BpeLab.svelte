<script lang="ts">
  /**
   * BPE lab (level 12): count neighboring pairs, merge the most frequent one, repeat.
   * Watch the vocabulary grow and the number of tokens shrink, and encode new words with the merges so far.
   * Same algorithm and tie-breaking as content/2-theory/tokenization/demo.py.
   */
  import { bpeEncode, bpeTrain, generatedWords, type Word } from '@lib/lm'
  import { readable } from '@lib/readable'
  import LabFrame from './LabFrame.svelte'

  const PRESETS: Record<string, { name: string; words: Word[]; max: number }> = {
    hand: { name: 'cat, cats, hat, hats', words: [{ w: 'cat', n: 4 }, { w: 'cats', n: 2 }, { w: 'hat', n: 3 }, { w: 'hats', n: 1 }], max: 6 },
    gen: { name: 'generated words (40)', words: generatedWords(), max: 40 },
  }
  let preset = $state<'hand' | 'gen'>('hand')
  let k = $state(0)
  let probe = $state('chats')

  const P = $derived(PRESETS[preset])
  const run = $derived(bpeTrain(P.words, P.max))
  const maxK = $derived(run.merges.length)
  const st = $derived(run.history[k])
  const merges = $derived(run.merges.slice(0, k))
  const top = $derived(st.pairs.slice(0, 8))
  const best = $derived(st.pairs[0])
  const lastMerge = $derived(k > 0 ? run.merges[k - 1].join('') : null)
  /** which tokens of a word belong to an occurrence of the top pair (left to right, no overlaps) — these merge next */
  function nextMerge(seg: string[]): boolean[] {
    const on = seg.map(() => false)
    if (!best) return on
    for (let i = 0; i + 1 < seg.length; i++)
      if (seg[i] === best.a && seg[i + 1] === best.b) { on[i] = on[i + 1] = true; i++ }
    return on
  }
  const wordVocab = $derived(new Set(P.words.map((x) => x.w)))
  const probeWords = $derived(probe.trim().split(/\s+/).filter(Boolean))

  function choose(p: 'hand' | 'gen') { preset = p; k = 0 }
  function reset() { preset = 'hand'; k = 0; probe = 'chats' }

  // chart: vocab size (x) against total tokens (y), one dot per merge count
  const CW = 300, CH = 130
  const pts = $derived(run.history.map((h) => [h.vocab.length, h.totalTokens]))
  const xr = $derived([Math.min(...pts.map((p) => p[0])), Math.max(...pts.map((p) => p[0]))])
  const yr = $derived([0, Math.max(...pts.map((p) => p[1]))])
  const cx = (v: number) => 30 + ((v - xr[0]) / Math.max(1, xr[1] - xr[0])) * (CW - 40)
  const cy = (v: number) => CH - 18 - (v / yr[1]) * (CH - 30)
</script>

<LabFrame
  title="BPE, one merge at a time"
  hint="Merge the most frequent neighboring pair, again and again. Watch the vocabulary grow and the token count shrink."
  onreset={reset}
  resetDisabled={preset === 'hand' && k === 0 && probe === 'chats'}
>
  <div class="row" role="group" aria-label="Words to learn from">
    <span class="dim">Words:</span>
    {#each Object.entries(PRESETS) as [key, p]}
      <button type="button" class="seg" class:on={preset === key} aria-pressed={preset === key} onclick={() => choose(key as 'hand' | 'gen')}>{p.name}</button>
    {/each}
  </div>

  <div class="cols">
    <div class="col">
      <p class="sec">Each word, cut into its current tokens</p>
      <div class="words">
        {#each P.words as wd, i}
          {@const hot = nextMerge(st.segs[i])}
          <div class="wd"><span class="n">×{wd.n}</span>{#each st.segs[i] as t, j}<span class="tok" class:hot={hot[j]} class:fresh={t === lastMerge}>{t}</span>{/each}</div>
        {/each}
      </div>
    </div>
    <div class="col">
      <p class="sec">Neighboring pairs, counted over all words</p>
      {#if top.length}
        <table class="pairs">
          <tbody>
            {#each top as p, i}
              <tr class:best={i === 0}><td><span class="tok">{p.a}</span> + <span class="tok">{p.b}</span></td><td class="num">{p.count}</td></tr>
            {/each}
          </tbody>
        </table>
        {#if st.pairs.length > top.length}<p class="dim">…and {st.pairs.length - top.length} more</p>{/if}
      {:else}
        <p class="dim">No pairs left: every word is one token.</p>
      {/if}
      <p class="sec">Merges learned, in order</p>
      {#if merges.length === 0}<p class="none">None yet. Press “Merge the top pair”.</p>{/if}
      <ol class="merges">{#each merges as [a, b]}<li><span class="tok">{a}</span> + <span class="tok">{b}</span> → <span class="tok new">{a + b}</span></li>{/each}</ol>
    </div>
  </div>

  {#if preset === 'gen'}
    <p class="sec">Vocabulary size against total tokens, one dot per merge (the ringed dot is now)</p>
    <svg viewBox="0 0 {CW} {CH}" class="chart" use:readable role="img" aria-label="Vocabulary size against total tokens">
      <line x1="30" y1={CH - 18} x2={CW - 10} y2={CH - 18} class="ax" />
      <line x1="30" y1="8" x2="30" y2={CH - 18} class="ax" />
      <text x={CW - 10} y={CH - 4} class="tx" text-anchor="end">vocabulary →</text>
      <text x="34" y="14" class="tx">tokens</text>
      <text x="26" y={cy(yr[1]) + 3} class="tx" text-anchor="end">{yr[1]}</text>
      {#each pts as p, i}<circle cx={cx(p[0])} cy={cy(p[1])} r={i === k ? 4 : 2} class:cur={i === k} />{/each}
    </svg>
  {/if}

  <p class="sec">Encode new text with the {k} merge{k === 1 ? '' : 's'} so far</p>
  <label class="probe-l"><span class="sr-only">Text to encode</span><input class="probe" bind:value={probe} spellcheck="false" maxlength="40" autocomplete="off" /></label>
  <div class="enc-wrap">
    <table class="enc">
      <tbody>
        <tr><th>characters</th><td>{#each probeWords as w}{#each [...w] as c}<span class="tok">{c}</span>{/each}<span class="gap"></span>{/each}</td></tr>
        <tr><th>whole words</th><td>{#each probeWords as w}<span class="tok" class:unk={!wordVocab.has(w)}>{wordVocab.has(w) ? w : '<unk>'}</span>{/each}</td></tr>
        <tr><th>BPE</th><td>{#each probeWords as w}{#each bpeEncode(w, merges) as t}<span class="tok">{t}</span>{/each}<span class="gap"></span>{/each}</td></tr>
      </tbody>
    </table>
  </div>

  {#snippet controls()}
    <button type="button" class="lab-btn primary" onclick={() => (k = Math.min(maxK, k + 1))} disabled={k === maxK}>Merge the top pair</button>
    <button type="button" class="lab-btn" onclick={() => (k = Math.max(0, k - 1))} disabled={k === 0}>Undo a merge</button>
    {#if preset === 'gen'}<button type="button" class="lab-btn" onclick={() => (k = maxK)} disabled={k === maxK}>All {maxK} merges</button>{/if}
  {/snippet}

  {#snippet readout()}
    merges <b>{k}</b> · vocabulary <b>{st.vocab.length}</b> · tokens in all words (× their counts) <b>{st.totalTokens}</b>
    {#if best}· next: {best.a} + {best.b} ({best.count}×){/if}
  {/snippet}

  {#snippet legend()}
    <span><span class="tok hot">a</span> merges next</span>
    <span><span class="tok fresh">at</span> just merged</span>
    <span><span class="tok unk">&lt;unk&gt;</span> not in the word list</span>
  {/snippet}
</LabFrame>

<style>
  .row { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; }
  .seg { font: inherit; font-size: 0.85rem; padding: 0.3rem 0.75rem; min-height: 2.1rem; border: 1px solid var(--field); border-radius: 999px; background: var(--bg); color: var(--fg); cursor: pointer; }
  .seg.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  .seg:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .cols { display: flex; flex-wrap: wrap; gap: 1rem; }
  .col { flex: 1 1 240px; min-width: 0; }
  .sec { margin: 0.8rem 0 0.35rem; font-size: 0.82rem; color: var(--dim); }
  .words { display: grid; gap: 0.25rem; max-height: 16rem; overflow-y: auto; }
  .wd { display: flex; flex-wrap: wrap; gap: 0.15rem; align-items: center; }
  .wd .n { font-family: var(--mono); font-size: 0.75rem; color: var(--dim); min-width: 2rem; }
  .tok { display: inline-block; padding: 0 0.3rem; border: 1px solid var(--line); border-radius: 3px; background: var(--bg); font-family: var(--mono);
    font-size: 0.88rem; margin: 0 0.08rem; transition: background-color 0.2s, border-color 0.2s, color 0.2s; }
  .tok.hot { border-color: var(--accent); background: var(--highlight); }
  .tok.fresh, .tok.new { border-color: var(--cat-2); color: var(--cat-2); }
  .tok.unk { border-color: var(--warn); color: var(--warn); }
  .gap { display: inline-block; width: 0.6rem; }
  table { font-family: var(--mono); font-size: 0.85rem; width: auto; border-collapse: collapse; }
  td, th { border: none; padding: 0.15rem 0.4rem; }
  td.num { text-align: right; }
  tr.best td { background: var(--highlight); font-weight: 700; }
  .merges { margin: 0; padding-left: 1.4rem; font-size: 0.85rem; }
  .chart { width: 100%; max-width: 26rem; height: auto; border: 1px solid var(--line); border-radius: 6px; background: var(--bg); }
  .chart circle { fill: var(--dim); }
  .chart circle.cur { fill: var(--accent); stroke: var(--accent); stroke-width: 2; fill-opacity: 0.3; }
  .ax { stroke: var(--field); }
  .tx { font-size: 9px; fill: var(--dim); font-family: var(--mono); }
  .probe { font: inherit; font-family: var(--mono); font-size: 1rem; padding: 0.35rem 0.55rem; border: 1px solid var(--field); border-radius: 5px; background: var(--bg); color: var(--fg); width: 100%; max-width: 18rem; }
  .probe:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
  .enc-wrap { overflow-x: auto; }
  .enc { margin-top: 0.4rem; }
  .enc th { color: var(--dim); font-weight: 400; text-align: left; font-size: 0.8rem; white-space: nowrap; vertical-align: top; }
  .enc td { overflow-wrap: anywhere; }
  .dim { color: var(--dim); font-size: 0.82rem; margin: 0.2rem 0; }
  .none { margin: 0.3rem 0 0; font-size: 0.85rem; color: var(--dim); }
</style>
