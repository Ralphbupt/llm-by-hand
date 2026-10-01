<script lang="ts">
  /**
   * Prototype B's hero: a tiny, untrained Transformer layer you can watch.
   * A three-word sentence flows token → embedding → attention → feed-forward → next-word scores.
   * Everything is computed live from a fixed random seed; hovering a block explains its shape and shows one real computation.
   */
  import { onMount } from 'svelte'

  const VOCAB = ['the', 'a', 'my', 'cat', 'dog', 'car', 'sat', 'ran', 'is', 'on', 'fast', 'red']
  const SENTENCES = [['the', 'cat', 'sat'], ['a', 'dog', 'ran'], ['my', 'car', 'is']]
  const D = 6, F = 8

  // seeded random numbers, so every visitor sees the same model
  function rng(seed: number) {
    let s = seed >>> 0
    return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 2 ** 32) * 2 - 1
  }
  const r = rng(7)
  const E = VOCAB.map(() => Array.from({ length: D }, () => +(r() * 1.2).toFixed(2)))
  const W1 = Array.from({ length: D }, () => Array.from({ length: F }, () => r() * 0.8))
  const W2 = Array.from({ length: F }, () => Array.from({ length: D }, () => r() * 0.8))

  const dot = (a: number[], b: number[]) => a.reduce((s, v, i) => s + v * b[i], 0)
  const softmax = (v: number[]) => { const m = Math.max(...v); const e = v.map((x) => Math.exp(x - m)); const z = e.reduce((a, b) => a + b, 0); return e.map((x) => x / z) }

  let si = $state(0)
  let hover = $state<string | null>('att')
  let pulse = $state(0) // bumps to replay the flow

  const toks = $derived(SENTENCES[si])
  const X = $derived(toks.map((t) => E[VOCAB.indexOf(t)]))
  const scores = $derived(X.map((q, i) => X.map((k, j) => (j > i ? -Infinity : dot(q, k) / Math.sqrt(D)))))
  const A = $derived(scores.map(softmax))
  const ctx = $derived(A.map((w) => Array.from({ length: D }, (_, d) => w.reduce((s, a, j) => s + a * X[j][d], 0))))
  const H = $derived(ctx.map((c, i) => c.map((v, d) => v + X[i][d]))) // residual
  const hid = $derived(H.map((h) => Array.from({ length: F }, (_, f) => Math.max(0, dot(h, W1.map((row) => row[f]))))))
  const out = $derived(H.map((h, i) => h.map((v, d) => v + hid[i].reduce((s, a, f) => s + a * W2[f][d], 0))))
  const logits = $derived(VOCAB.map((_, v) => dot(out[out.length - 1], E[v])))
  const probs = $derived(softmax(logits))
  const top = $derived(probs.map((p, i) => ({ w: VOCAB[i], p })).sort((a, b) => b.p - a.p).slice(0, 5))

  const f2 = (v: number) => (Math.abs(v) < 0.005 ? '0.00' : v.toFixed(2))
  const cell = (v: number) => Math.max(-1, Math.min(1, v / 1.2))

  const blocks = [
    { id: 'tok', name: 'Tokens', lv: 'level 12' },
    { id: 'emb', name: 'Embedding', lv: 'level 13' },
    { id: 'att', name: 'Attention', lv: 'levels 14–15' },
    { id: 'ffn', name: 'Feed-forward', lv: 'level 16' },
    { id: 'out', name: 'Next word', lv: 'level 17' },
  ]
  const explain = $derived.by(() => {
    const t = toks
    switch (hover) {
      case 'tok': return { shape: `(${t.length},) token ids`, text: `Each word becomes an id in a ${VOCAB.length}-word vocabulary.`, calc: t.map((w) => `${w} → ${VOCAB.indexOf(w)}`).join('   ') }
      case 'emb': return { shape: `(${t.length}, ${D})`, text: `Each id picks one row of a (${VOCAB.length}, ${D}) table of learned numbers.`, calc: `${t[1]} = [${X[1].map(f2).join(', ')}]` }
      case 'att': return { shape: `(${t.length}, ${t.length}) weights`, text: 'Each word scores every earlier word (dot product ÷ √6), softmax turns a row into weights that add up to 1.',
        calc: `${t[2]}·${t[1]} / √6 = ${f2(scores[2][1])}   →   weights of “${t[2]}”: ${A[2].map(f2).join(', ')}` }
      case 'ffn': return { shape: `(${t.length}, ${F}) → (${t.length}, ${D})`, text: 'A small two-layer network runs on every word separately; ReLU switches units off.',
        calc: `“${t[2]}” hidden units on: ${hid[2].filter((v) => v > 0).length} of ${F}` }
      case 'out': return { shape: `(${VOCAB.length},) scores`, text: 'The last word’s vector is compared with every word’s embedding; softmax gives the next-word chances.',
        calc: `p(“${top[0].w}”) = ${f2(top[0].p)}` }
      default: return null
    }
  })

  let reduced = $state(false)
  onMount(() => { reduced = matchMedia('(prefers-reduced-motion: reduce)').matches || document.documentElement.dataset.motion === 'reduce' })
  function pick(i: number) { si = i; pulse++ }
</script>

<div class="machine" class:still={reduced}>
  <div class="bar">
    <span class="lbl">Run a sentence:</span>
    {#each SENTENCES as s, i}
      <button class:on={si === i} onclick={() => pick(i)}>{s.join(' ')}</button>
    {/each}
    <span class="honest">An untrained tiny model, computed live. In level 21 you train one.</span>
  </div>

  {#key pulse}
    <div class="flow" role="group" aria-label="One Transformer layer, block by block">
      {#each blocks as b, bi}
        <button class="blk {b.id}" style:--i={bi} class:hl={hover === b.id}
          onmouseenter={() => (hover = b.id)} onfocus={() => (hover = b.id)} onclick={() => (hover = b.id)}>
          <span class="bname">{b.name}<small>{b.lv}</small></span>
          {#if b.id === 'tok'}
            <span class="toks">{#each toks as t}<i>{t}</i>{/each}</span>
          {:else if b.id === 'emb'}
            <span class="grid" style:--cols={D}>{#each X as row}{#each row as v}<i style:--v={cell(v)}></i>{/each}{/each}</span>
          {:else if b.id === 'att'}
            <span class="grid att" style:--cols={toks.length}>{#each A as row}{#each row as v}<i style:--a={v}></i>{/each}{/each}</span>
          {:else if b.id === 'ffn'}
            <span class="grid" style:--cols={F}>{#each hid as row}{#each row as v}<i class="relu" style:--a={Math.min(1, v / 1.5)}></i>{/each}{/each}</span>
          {:else}
            <span class="probs">{#each top as t}<span><em>{t.w}</em><i style:width="{t.p * 100}%"></i><b>{f2(t.p)}</b></span>{/each}</span>
          {/if}
        </button>
        {#if bi < blocks.length - 1}<span class="wire" style:--i={bi} aria-hidden="true"></span>{/if}
      {/each}
    </div>
  {/key}

  <div class="explain" aria-live="polite">
    {#if explain}
      <span class="shape">{explain.shape}</span>
      <p>{explain.text}</p>
      <code>{explain.calc}</code>
    {:else}
      <p class="dim">Point at a block to see its shape and how one of its numbers is computed.</p>
    {/if}
  </div>
</div>

<style>
  .machine { --c-tok: var(--m-ink); }
  .bar { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1rem; }
  .lbl { font-weight: 600; margin-right: 0.2rem; }
  .bar button { font: inherit; font-family: var(--m-mono); font-size: 0.85rem; padding: 0.25rem 0.7rem; border-radius: 999px; border: 1px solid var(--m-line);
    background: var(--m-panel); color: var(--m-text); cursor: pointer; }
  .bar button.on { border-color: var(--m-text); background: var(--m-text); color: var(--m-bg); }
  .honest { color: var(--m-dim); font-size: 0.82rem; margin-left: auto; }
  .flow { display: grid; grid-template-columns: 0.8fr auto 1.1fr auto 1fr auto 1.2fr auto 1.3fr; align-items: stretch; gap: 0; }
  .blk { font: inherit; text-align: left; border: 1.5px solid var(--m-line); border-radius: 10px; background: var(--m-panel); color: var(--m-text);
    padding: 0.7rem 0.75rem; display: flex; flex-direction: column; gap: 0.6rem; cursor: pointer; min-width: 0;
    border-top: 4px solid var(--col); }
  .blk.tok { --col: var(--m-dim); } .blk.emb { --col: var(--m-violet); } .blk.att { --col: var(--m-blue); } .blk.ffn { --col: var(--m-amber); } .blk.out { --col: var(--m-green); }
  .blk.hl { border-color: var(--col); box-shadow: 0 0 0 3px color-mix(in srgb, var(--col) 25%, transparent); }
  .bname { font-weight: 700; font-size: 0.95rem; display: flex; justify-content: space-between; gap: 0.4rem; align-items: baseline; }
  .bname small { font-weight: 500; color: var(--m-dim); font-size: 0.72rem; font-family: var(--m-mono); }
  .toks { display: flex; flex-direction: column; gap: 0.35rem; }
  .toks i { font-style: normal; font-family: var(--m-mono); padding: 0.2rem 0.4rem; border: 1px solid var(--m-line); border-radius: 5px; text-align: center; }
  .grid { display: grid; grid-template-columns: repeat(var(--cols), 1fr); gap: 3px; }
  .grid i { aspect-ratio: 1; border-radius: 3px;
    background: color-mix(in srgb, var(--m-violet) calc(max(var(--v, 0), 0) * 100%), color-mix(in srgb, var(--m-amber) calc(max(calc(var(--v, 0) * -1), 0) * 100%), var(--m-cell))); }
  .grid.att i { background: color-mix(in srgb, var(--m-blue) calc(var(--a) * 100%), var(--m-cell)); }
  .grid i.relu { background: color-mix(in srgb, var(--m-amber) calc(var(--a) * 100%), var(--m-cell)); }
  .probs { display: grid; gap: 0.3rem; font-family: var(--m-mono); font-size: 0.78rem; }
  .probs > span { display: grid; grid-template-columns: 2.4rem 1fr 2.4rem; align-items: center; gap: 0.35rem; }
  .probs em { font-style: normal; }
  .probs i { height: 0.55rem; border-radius: 2px; background: var(--m-green); min-width: 2px; }
  .probs b { font-weight: 500; text-align: right; color: var(--m-dim); }
  .wire { align-self: center; width: 1.4rem; height: 2px; background: var(--m-line); position: relative; overflow: hidden; }
  .wire::after { content: ''; position: absolute; inset: 0; background: var(--m-text); transform: translateX(-100%); }
  /* the one orchestrated moment: the sentence flows left to right */
  @media (prefers-reduced-motion: no-preference) {
    .machine:not(.still) .blk { animation: lit 0.5s ease-out both; animation-delay: calc(var(--i) * 0.28s); }
    .machine:not(.still) .wire::after { animation: run 0.3s ease-in both; animation-delay: calc(var(--i) * 0.28s + 0.2s); }
    @keyframes lit { from { opacity: 0.35; transform: translateY(4px); } to { opacity: 1; transform: none; } }
    @keyframes run { from { transform: translateX(-100%); } 50% { transform: none; } to { transform: translateX(100%); } }
  }
  .explain { margin-top: 1rem; min-height: 5.2rem; border: 1px dashed var(--m-line); border-radius: 10px; padding: 0.7rem 0.9rem; }
  .explain p { margin: 0.2rem 0; }
  .explain code { font-family: var(--m-mono); font-size: 0.85rem; color: var(--m-text); background: none; padding: 0; overflow-wrap: anywhere; }
  .shape { font-family: var(--m-mono); font-size: 0.8rem; color: var(--m-dim); }
  .dim { color: var(--m-dim); }
  @media (max-width: 860px) {
    .flow { grid-template-columns: minmax(0, 1fr); gap: 0; }
    .wire { width: 2px; height: 1rem; justify-self: center; }
    .grid { max-width: 16rem; }
    .honest { margin-left: 0; width: 100%; }
  }
</style>
