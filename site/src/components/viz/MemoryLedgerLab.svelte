<script lang="ts">
  /**
   * Training memory ledger (U6): one fixed model (24 layers, d_model 1000, h 8, 300 million parameters, 2 bytes per
   * saved number). Pick the batch B and the length L, and switch recomputation on or off. One stacked bar shows what
   * training keeps: 16 bytes per parameter, token activations (16 tensors of shape (B, L, d_model) per layer: the count of
   * the question `block-saved`), and the attention weights (B, h, L, L) per layer. With recomputation each layer keeps only its input.
   * The bar has an absolute scale, powers of ten from 1 GB to 1 TB, with a line at one 80 GB GPU, so it grows with L.
   * Each part is drawn from the running total before it to the running total after it, both on the log scale, so every
   * boundary can be read off the scale: the parameters always fill 1 GB → 4.8 GB, and growth shows at the right end.
   * The table under the controls gives each part's share; on a phone this keeps the sliders right under the bar.
   */
  import LabFrame from './LabFrame.svelte'

  const LAYERS = 24, D = 1000, H = 8, PARAMS = 300e6, BYTES = 2, PER_LAYER = 16
  const BS = [1, 2, 4, 8, 16]
  const LS = [500, 1000, 2000, 4000, 8000]
  const B0 = 2, L0 = 1 // indices: B = 4, L = 1000
  // the scale: 10^0 to 10^3 GB
  const DEC = 3, GPU = 80e9
  const at = (bytes: number) => (Math.log10(Math.max(bytes, 1e9) / 1e9) / DEC) * 100
  const TICKS = [{ v: 1e9, t: '1 GB' }, { v: 1e10, t: '10 GB' }, { v: 1e11, t: '100 GB' }, { v: 1e12, t: '1 TB' }]
  let bi = $state(B0)
  let li = $state(L0)
  let recompute = $state(false)
  const B = $derived(BS[bi])
  const L = $derived(LS[li])

  const params = PARAMS * 16
  const acts = $derived((recompute ? 1 : PER_LAYER) * B * L * D * BYTES * LAYERS)
  const attn = $derived(recompute ? 0 : B * H * L * L * BYTES * LAYERS)
  const total = $derived(params + acts + attn)
  const rows = $derived([
    { k: 'params', name: 'Weights, gradients, Adam', how: '16 bytes × 300 million', v: params },
    { k: 'acts', name: 'Token activations', how: recompute ? '1 × (B, L, d_model) × 24 layers' : `${PER_LAYER} × (B, L, d_model) × 24 layers`, v: acts },
    { k: 'attn', name: 'Attention weights', how: recompute ? 'none kept: recomputed' : '(B, h, L, L) × 24 layers', v: attn },
  ])
  const fmt = (b: number) => (b === 0 ? '0' : b < 1e9 ? `${Math.round(b / 1e6).toLocaleString()} MB` : `${(b / 1e9).toFixed(b < 1e11 ? 1 : 0)} GB`)
  const pct = (v: number) => (v / total) * 100
  // the parts as [start, end] on the scale: running totals, so the parameter part is always 1 GB → 4.8 GB
  const segs = $derived.by(() => {
    let cum = 0
    return rows.map((r) => {
      const from = cum
      cum += r.v
      return { ...r, a: from === 0 ? 0 : at(from), b: at(cum) }
    })
  })
  const changed = $derived(bi !== B0 || li !== L0 || recompute)
  const over = $derived(total > GPU)
</script>

<LabFrame
  title="What training keeps in GPU memory, and what grows with L"
  hint="Move B and L, or switch recomputation on. The model stays the same: 24 layers, width 1000, 8 heads, 300 million parameters. Each mark on the scale is 10 times the one before."
  onreset={() => { bi = B0; li = L0; recompute = false }}
  resetDisabled={!changed}
>
  <div class="scale" role="img" aria-label={`${rows.map((r) => `${r.name} ${fmt(r.v)}`).join(', ')}; total ${fmt(total)}, ${over ? 'more than' : 'within'} one 80 GB GPU`}>
    <div class="track">
      <div class="bar" class:over style:width="{at(total)}%">
        {#each segs as r}
          {#if r.v > 0}<i class={r.k} style:left="{(100 * r.a) / at(total)}%" style:width="{(100 * (r.b - r.a)) / at(total)}%"></i>{/if}
        {/each}
      </div>
      <span class="gpu" style:left="{at(GPU)}%"></span>
    </div>
    <div class="gpu-t" style:left="{at(GPU)}%">one 80 GB GPU</div>
    <div class="ticks">
      {#each TICKS as t}<span style:left="{at(t.v)}%">{t.t}</span>{/each}
    </div>
  </div>
  {#snippet controls()}
    <div class="ctl">
      <label>
        <span class="lbl">B = <b>{B}</b> sequences</span>
        <input type="range" min="0" max={BS.length - 1} step="1" bind:value={bi} aria-valuetext={`B = ${B}`} />
      </label>
      <label>
        <span class="lbl">L = <b>{L.toLocaleString()}</b> tokens</span>
        <input type="range" min="0" max={LS.length - 1} step="1" bind:value={li} aria-valuetext={`L = ${L}`} />
      </label>
      <div class="btn-row"><button type="button" class="lab-btn" aria-pressed={recompute} onclick={() => (recompute = !recompute)}>Recomputation</button></div>
    </div>
  {/snippet}

  {#snippet readout()}
    Total <b>{fmt(total)}</b>, {over ? 'more than one 80 GB GPU holds' : 'within one 80 GB GPU'}.
    {#if recompute}At its peak, add one layer’s values while that layer is recomputed. The cost is one more forward pass per step.{:else}The attention weights are {Math.round(pct(attn))}% of it.{/if}
  {/snippet}

  {#snippet after()}
    <table class="ledger">
      <tbody>
        {#each rows as r}
          <tr>
            <td class="name"><i class="sw {r.k}"></i>{r.name}<span class="how2">{r.how}</span></td>
            <td class="how">{r.how}</td>
            <td class="num">{fmt(r.v)}</td>
            <td class="num dim">{Math.round(pct(r.v))}%</td>
          </tr>
        {/each}
      </tbody>
    </table>
    <p class="note">Token activations: the 16 tensors per layer that you counted above. On the scale, each boundary of the bar is the running total so far: the grey part always ends at 4.8 GB.</p>
  {/snippet}
</LabFrame>

<style>
  .scale { position: relative; max-width: 600px; padding-top: 1.2rem; }
  .track { position: relative; height: 1.4rem; border-bottom: 1px solid var(--line); }
  .bar { position: relative; height: 100%; border-radius: 3px; overflow: hidden; transition: width 0.2s ease-out; }
  .bar.over { outline: 2px solid var(--warn); outline-offset: 1px; }
  .bar i { position: absolute; top: 0; display: block; height: 100%; transition: left 0.2s ease-out, width 0.2s ease-out; }
  .gpu { position: absolute; top: 0; bottom: -0.35rem; width: 0; border-left: 2px dashed var(--fg); }
  .gpu-t { position: absolute; top: 0; transform: translateX(-50%); font-size: 0.75rem; color: var(--fg); white-space: nowrap; }
  .ticks { position: relative; height: 1.2rem; margin-top: 0.2rem; }
  .ticks span { position: absolute; transform: translateX(-50%); font-family: var(--mono); font-size: 0.72rem; color: var(--dim); white-space: nowrap; }
  .ticks span:first-child { transform: none; }
  .ticks span:last-child { transform: translateX(-100%); }
  .params { background: var(--dim); }
  .acts { background: var(--cat-2); }
  .attn { background: var(--cat-1); }
  .ledger { width: 100%; max-width: 600px; margin-top: 0; border-collapse: collapse; font-size: 0.85rem; }
  .ledger td { border: none; padding: 0.3rem 0.8rem 0.3rem 0; white-space: nowrap; }
  .ledger tr + tr td { border-top: 1px solid var(--line); }
  .ledger td:last-child { padding-right: 0; }
  .how, .how2 { color: var(--dim); font-family: var(--mono); font-size: 0.78rem; }
  .how2 { display: none; }
  .num { text-align: right; font-family: var(--mono); font-variant-numeric: tabular-nums; }
  .dim { color: var(--dim); }
  .note { margin: 0.4rem 0 0; font-size: 0.8rem; color: var(--dim); max-width: 600px; }
  .sw { display: inline-block; width: 0.8rem; height: 0.8rem; border-radius: 2px; margin-right: 0.4rem; vertical-align: -0.1rem; }
  .ctl { display: flex; flex-wrap: wrap; gap: 0.6rem 1.4rem; align-items: center; }
  label { display: inline-flex; flex-direction: column; gap: 0.2rem; font-size: 0.85rem; }
  .lbl { color: var(--dim); }
  .lbl b { color: var(--fg); font-family: var(--mono); }
  input[type='range'] { width: 11rem; min-height: 2.5rem; accent-color: var(--accent); }
  /* phone: the "how" goes under the name, so the numbers stay on screen; the button gets its own row */
  @media (max-width: 560px) {
    .how { display: none; }
    .how2 { display: block; margin-left: 1.2rem; white-space: normal; }
    .ledger td.name { white-space: normal; }
    .btn-row { flex-basis: 100%; }
  }
  @media (prefers-reduced-motion: reduce) { .bar, .bar i { transition: none; } }
</style>
