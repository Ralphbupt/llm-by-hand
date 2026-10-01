<script lang="ts">
  /**
   * Neural bigram lab (level 11): P(next | prev) = softmax(onehot(prev) @ W), W is 10×10, starting at zero.
   * Full-batch gradient descent on the generated stories, the same steps as language-models/demo.py.
   * The chart shows held-out perplexity falling toward the counting model's.
   */
  import { onMount } from 'svelte'
  import { bigramCounts, neuralBigramStep, rowProbs, softmaxRow, streamPerplexity } from '@lib/lm'
  import { readable } from '@lib/readable'
  import LabFrame from './LabFrame.svelte'

  const LR0 = 5
  let vocab = $state<string[]>([])
  let train = $state<string[]>([])
  let held = $state<string[]>([])
  let W = $state<number[][]>([])
  let step = $state(0)
  let lr = $state(LR0)
  let loss = $state<number | null>(null)
  let curve = $state<number[]>([])
  let row = $state(0)
  let failed = $state(false)

  onMount(async () => {
    try {
      const d = await (await fetch('/data/language-models/corpus.json')).json()
      vocab = d.vocab; train = d.train; held = d.heldout
      reset()
    } catch { failed = true }
  })

  const trTok = $derived(train.join(' ').split(' ').filter(Boolean))
  const hoTok = $derived(held.join(' ').split(' ').filter(Boolean))
  const C = $derived(vocab.length ? bigramCounts(trTok, vocab) : [])
  const Pc = $derived(C.length ? rowProbs(C) : [])
  const pplCount = $derived(Pc.length ? streamPerplexity(hoTok, vocab, Pc) : 0)
  const Pw = $derived(W.map(softmaxRow))
  const pplNow = $derived(Pw.length ? streamPerplexity(hoTok, vocab, Pw) : 0)

  function reset() {
    W = vocab.map(() => vocab.map(() => 0))
    step = 0
    lr = LR0
    loss = null
    curve = [streamPerplexity(hoTok, vocab, W.map(softmaxRow))]
  }
  function train_(n: number) {
    const w = W.map((r) => [...r])
    let l = 0
    const add: number[] = []
    for (let k = 0; k < n; k++) {
      l = neuralBigramStep(w, C, lr)
      add.push(streamPerplexity(hoTok, vocab, w.map(softmaxRow)))
    }
    W = w
    step += n
    loss = l
    curve = [...curve, ...add].slice(-2000)
  }

  // chart: held-out perplexity against steps, log scale from 1.8 to 10 so the approach to the counting model is visible
  const H = 130, Wd = 320, L0 = 34, B0 = 18
  const LO = Math.log(1.8), HI = Math.log(10)
  const y = (v: number) => 6 + (1 - (Math.log(Math.max(1.8, Math.min(10, v))) - LO) / (HI - LO)) * (H - B0 - 6)
  const xs = (i: number) => L0 + (i / Math.max(1, curve.length - 1)) * (Wd - L0 - 6)
  const path = $derived(curve.map((v, i) => `${i ? 'L' : 'M'}${xs(i)},${y(v)}`).join(' '))
</script>

<LabFrame
  title="Learn the same table with gradient descent"
  hint="Train the 10×10 weight table W and watch its perplexity on the held-out sentences fall toward the counting model’s."
  onreset={reset}
  resetDisabled={step === 0 && lr === LR0}
>
  {#if failed}
    <p class="state">Could not load the stories. Reload the page to try again.</p>
  {:else if !vocab.length}
    <p class="state">Loading the stories…</p>
  {:else}
    <svg viewBox="0 0 {Wd} {H}" class="chart" use:readable role="img" aria-label="Perplexity on the held-out sentences over training steps">
      {#each [10, 5, 3, 2] as t}
        <line x1={L0} x2={Wd - 6} y1={y(t)} y2={y(t)} class="grid" />
        <text x={L0 - 4} y={y(t) + 3} class="tx" text-anchor="end">{t}</text>
      {/each}
      <line x1={L0} x2={Wd - 6} y1={y(pplCount)} y2={y(pplCount)} class="ref" />
      <text x={Wd - 8} y={y(pplCount) + 11} class="tx okt" text-anchor="end">counting model {pplCount.toFixed(3)}</text>
      <text x={L0 + 3} y={y(10) + 11} class="tx">10 = guessing uniformly</text>
      <path d={path} class="line" />
      {#if curve.length}<circle cx={xs(curve.length - 1)} cy={y(curve[curve.length - 1])} r="3.5" class="head" />{/if}
      <text x={L0} y={H - 4} class="tx">↑ perplexity (log scale)</text>
      <text x={Wd - 6} y={H - 4} class="tx" text-anchor="end">step → ({step} so far)</text>
    </svg>

    <p class="sec">Compare one row. After
      <label class="sel"><span class="sr-only">previous word</span><select bind:value={row}>{#each vocab as w, i}<option value={i}>{w}</option>{/each}</select></label>
      the next word is…</p>
    <div class="bars">
      <div class="b bh"><span></span><span>neural: softmax(W[row])</span><span>counting</span></div>
      {#each vocab as w, j}
        <div class="b">
          <span class="l2">{w}</span>
          <span class="pair">
            <span class="track"><i style="width: {Pw[row][j] * 100}%"></i></span><span class="v">{Pw[row][j].toFixed(3)}</span>
          </span>
          <span class="pair">
            <span class="track"><i class="c" style="width: {Pc[row][j] * 100}%"></i></span><span class="v">{Pc[row][j].toFixed(3)}</span>
          </span>
        </div>
      {/each}
    </div>
  {/if}

  {#snippet controls()}
    <button type="button" class="lab-btn primary" onclick={() => train_(100)} disabled={!vocab.length}>Train 100 steps</button>
    <button type="button" class="lab-btn" onclick={() => train_(10)} disabled={!vocab.length}>Train 10 steps</button>
    <label class="lr">learning rate <input type="range" min="0.5" max="20" step="0.5" bind:value={lr} /> <b>{lr}</b></label>
  {/snippet}

  {#snippet readout()}
    step <b>{step}</b> · train loss <b>{loss === null ? '–' : loss.toFixed(4)}</b> · perplexity <b class="acc">{pplNow.toFixed(3)}</b> (counting model {pplCount.toFixed(3)})
  {/snippet}

  {#snippet legend()}
    <span><i class="sw acc-sw"></i> the neural table (yours, being trained)</span>
    <span><i class="sw ok-sw"></i> the counting model (the target)</span>
  {/snippet}
</LabFrame>

<style>
  .state { min-height: 12rem; display: grid; place-items: center; margin: 0; color: var(--dim); font-size: 0.9rem; }
  .lr { display: inline-flex; align-items: center; gap: 0.4rem; font-size: 0.85rem; color: var(--dim); }
  .lr input { width: 7rem; accent-color: var(--accent); }
  .lr b { font-family: var(--mono); color: var(--fg); min-width: 2rem; }
  .acc { color: var(--accent); }
  .chart { width: 100%; max-width: 32rem; height: auto; display: block; border: 1px solid var(--line); border-radius: 6px; background: var(--bg); }
  .line { fill: none; stroke: var(--accent); stroke-width: 2; }
  .ref { stroke: var(--ok); stroke-dasharray: 4 3; }
  .grid { stroke: var(--line); }
  .tx { font-size: 9px; fill: var(--dim); font-family: var(--mono); }
  .tx.okt { fill: var(--ok); }
  .head { fill: var(--accent); }
  .sec { font-size: 0.85rem; color: var(--dim); margin: 0.9rem 0 0.35rem; }
  select { font: inherit; font-family: var(--mono); padding: 0.2rem 0.3rem; min-height: 2rem; background: var(--bg); color: var(--fg); border: 1px solid var(--field); border-radius: 4px; }
  .bars { display: grid; gap: 0.2rem; max-width: 34rem; }
  .b { display: grid; grid-template-columns: 2.8rem 1fr 1fr; gap: 0.5rem; align-items: center; font-family: var(--mono); font-size: 0.8rem; }
  .b.bh { color: var(--dim); font-size: 0.75rem; }
  .pair { display: grid; grid-template-columns: 1fr 3rem; gap: 0.3rem; align-items: center; min-width: 0; }
  .track { height: 0.65rem; background: var(--bg); border: 1px solid var(--line); border-radius: 3px; overflow: hidden; }
  .track i { display: block; height: 100%; background: var(--accent); }
  .track i.c { background: var(--ok); }
  .v { text-align: right; }
  .sw { display: inline-block; width: 0.8rem; height: 0.55rem; border-radius: 2px; margin-right: 0.3rem; vertical-align: 0.05em; }
  .acc-sw { background: var(--accent); }
  .ok-sw { background: var(--ok); }
</style>
