<script lang="ts">
  /**
   * Entropy lab: four candidate words, drag how much the model believes in each.
   * Shows p, the surprise −ln p of each word, the entropy (the p-weighted average surprise)
   * and the perplexity e^entropy.
   */
  import LabFrame from './LabFrame.svelte'

  const WORDS = ['mat', 'sofa', 'roof', 'moon']
  const START = [1, 1, 1, 1]
  let w = $state([...START])

  const p = $derived.by(() => {
    const s = w.reduce((a, b) => a + b, 0)
    return s > 0 ? w.map((v) => v / s) : w.map(() => 1 / w.length)
  })
  const surprise = $derived(p.map((q) => (q > 0 ? -Math.log(q) : Infinity)))
  const H = $derived(p.reduce((a, q, i) => a + (q > 0 ? q * surprise[i] : 0), 0))
  const ppl = $derived(Math.exp(H))

  const presets: [string, number[]][] = [
    ['even', [1, 1, 1, 1]],
    ['sure', [1, 0, 0, 0]],
    ['choosing between two', [1, 1, 0, 0]],
    ['skewed', [7, 1, 1, 1]],
  ]
  function set(i: number, v: number) {
    const next = [...w]
    next[i] = v
    w = next
  }
  const fmt = (x: number) => (Number.isFinite(x) ? x.toFixed(3) : '∞')
</script>

<LabFrame
  title="Entropy and perplexity: how unsure is the model?"
  hint="Drag how much the model believes in each word, or press a preset."
  onreset={() => (w = [...START])}
  resetDisabled={w.every((v, i) => v === START[i])}
>
  <div class="rows">
    <div class="row head"><span>word</span><span>belief (drag)</span><span>p</span><span class="r">−ln p</span></div>
    {#each WORDS as word, i}
      <div class="row">
        <span class="w">{word}</span>
        <input type="range" min="0" max="10" step="0.5" value={w[i]} aria-label={`belief in ${word}`}
          oninput={(e) => set(i, +(e.currentTarget as HTMLInputElement).value)} />
        <span class="bar"><i style="width:{p[i] * 100}%"></i><em>{p[i].toFixed(3)}</em></span>
        <span class="num">{fmt(surprise[i])}</span>
      </div>
    {/each}
  </div>

  <div class="dice" aria-label={`Perplexity ${ppl.toFixed(2)}: as unsure as choosing evenly among that many words`}>
    <span class="dl">perplexity</span>
    {#each [0, 1, 2, 3] as k}
      <span class="die"><i style="width:{Math.max(0, Math.min(1, ppl - k)) * 100}%"></i></span>
    {/each}
    <b class="ppl">{ppl.toFixed(2)}</b>
  </div>

  {#snippet controls()}
    {#each presets as [name, v]}
      <button class="lab-btn" class:on={w.every((x, i) => x === v[i])} aria-pressed={w.every((x, i) => x === v[i])} onclick={() => (w = [...v])}>{name}</button>
    {/each}
  {/snippet}

  {#snippet readout()}
    entropy = Σ p · (−ln p) = <b>{H.toFixed(3)}</b> nats · perplexity = e<sup>{H.toFixed(3)}</sup> = <b>{ppl.toFixed(2)}</b>
    <span class="dim">: as unsure as an even choice among {ppl.toFixed(2)} words</span>
  {/snippet}

  {#snippet legend()}
    <span><i class="sw p"></i>p of each word</span>
    <span><i class="sw die-sw"></i>one equally likely word; the filled part is the perplexity</span>
  {/snippet}
</LabFrame>

<style>
  .rows { display: grid; gap: 0.3rem; }
  .row { display: grid; grid-template-columns: 3.4rem minmax(4rem, 1fr) minmax(4.5rem, 1fr) 5.5rem; gap: 0.5rem; align-items: center; font-size: 0.85rem; }
  .row.head { color: var(--dim); font-size: 0.76rem; font-family: var(--mono); }
  .row input[type='range'] { width: 100%; accent-color: var(--accent); min-height: 2.2rem; }
  .r { text-align: right; }
  .w { font-family: var(--mono); font-weight: 600; }
  .num { font-family: var(--mono); text-align: right; font-variant-numeric: tabular-nums; }
  .bar { position: relative; height: 1.4rem; background: var(--bg); border: 1px solid var(--line); border-radius: 3px; overflow: hidden; }
  .bar i { position: absolute; inset: 0 auto 0 0; background: var(--cat-1); opacity: 0.45; transition: width 0.2s; }
  .bar em { position: relative; font-style: normal; font-family: var(--mono); font-size: 0.78rem; padding-left: 0.3rem; line-height: 1.4rem; font-variant-numeric: tabular-nums; }
  .dice { display: flex; flex-wrap: wrap; align-items: center; gap: 0.4rem; margin-top: 0.8rem; }
  .dl { font-family: var(--mono); font-size: 0.8rem; color: var(--dim); margin-right: 0.2rem; }
  .die { position: relative; width: 2.4rem; height: 1.5rem; border: 1.5px solid var(--cat-1); border-radius: 4px; overflow: hidden; background: var(--bg); }
  .die i { position: absolute; inset: 0 auto 0 0; background: var(--cat-1); opacity: 0.6; transition: width 0.2s; }
  .ppl { font-family: var(--mono); font-size: 1rem; margin-left: 0.3rem; font-variant-numeric: tabular-nums; }
  @media (prefers-reduced-motion: reduce) { .bar i, .die i { transition: none; } }
  .lab-btn.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  .dim { color: var(--dim); font-family: system-ui, -apple-system, sans-serif; }
  .sw { display: inline-block; width: 0.9rem; height: 0.65rem; border-radius: 2px; margin-right: 0.35rem; vertical-align: -0.02rem; }
  .sw.p { background: var(--cat-1); opacity: 0.55; }
  .sw.die-sw { border: 1.5px solid var(--cat-1); background: linear-gradient(to right, color-mix(in srgb, var(--cat-1) 60%, transparent) 60%, transparent 60%); }
  @media (max-width: 480px) { .row { grid-template-columns: 3rem minmax(3.5rem, 1fr) minmax(4rem, 1fr) 3.6rem; gap: 0.35rem; } }
</style>
