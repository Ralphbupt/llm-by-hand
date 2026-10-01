<script lang="ts">
  /**
   * Residuals and LayerNorm, as two labs (one idea each).
   * Lab 1: LayerNorm one word's numbers (mean 0, spread 1), and which axis it uses.
   * Lab 2: stack many layers. Without help the numbers vanish or explode; residual + LayerNorm keeps them steady.
   */
  import { layerNorm, mean, normalizeColumns, runDepth, std, type DepthMode } from '@lib/parts'
  import MatrixGrid from './MatrixGrid.svelte'
  import LabFrame from './LabFrame.svelte'
  import { readable } from '@lib/readable'
  import { onMount } from 'svelte'
  import { has, subscribe } from '@lib/progress'

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

  let v = $state([[1, 2, 3, 6]])
  const ln = $derived(layerNorm(v[0]))
  const M = [[1, 2, 3, 6], [10, 10, 12, 8], [-1, 0, 1, 0]]
  let byRow = $state(true)
  const normed = $derived(byRow ? M.map((r) => layerNorm(r)) : normalizeColumns(M))

  const x0 = [1, -1, 0.5, 2, -0.5, 1.5, -2, 0]
  let mode = $state<DepthMode>('plain')
  let gain = $state(0.5)
  let depth = $state(30)
  const run = $derived(runDepth(x0, depth, gain, mode))
  const last = $derived(run.norms[run.norms.length - 1])

  // chart: log10 of the size per layer, clipped to [-8, 8]
  const W = 560, H = 200, PADL = 46, PADR = 10, PADT = 14, PADB = 28
  const cx = (i: number) => PADL + (i / Math.max(depth, 1)) * (W - PADL - PADR)
  const lg = (n: number) => Math.max(-8, Math.min(8, Math.log10(Math.max(n, 1e-12))))
  const cy = (l: number) => PADT + ((8 - l) / 16) * (H - PADT - PADB)
  const path = $derived(run.norms.map((n, i) => `${i ? 'L' : 'M'}${cx(i).toFixed(1)},${cy(lg(n)).toFixed(1)}`).join(' '))
  const yTicks: [number, string][] = [[8, '10⁸'], [4, '10⁴'], [0, '1'], [-4, '10⁻⁴'], [-8, '10⁻⁸']]
  const xTicks = $derived(depth >= 4 ? [0, Math.round(depth / 2)] : [0])
  // toFixed can print "-0.00"; show it as 0.00
  const f = (x: number, d = 2) => { const s = x.toFixed(d); return /^-0\.?0*$/.test(s) ? s.slice(1) : s }
  const big = (x: number) => (x === 0 ? '0' : Math.abs(Math.log10(Math.abs(x))) > 3 ? x.toExponential(1) : x.toFixed(2))
  // diverging bars: half-width 3rem on each side of zero
  const bar = (x: number, perUnit: number) => Math.min(3, Math.abs(x) * perUnit)
  // ln: the LayerNorm results stay "?" until the question asking for one is solved
  const lnLocked = $derived(locked('ln'))
  const verdict = $derived(last < 1e-3 ? 'the signal vanished' : last > 1e3 ? 'the numbers grew very large' : 'steady')
  const changed1 = $derived(!byRow || v[0].some((x, i) => x !== [1, 2, 3, 6][i]))
  const changed2 = $derived(mode !== 'plain' || gain !== 0.5 || depth !== 30)
</script>

<LabFrame
  title="LayerNorm: each word’s numbers rescaled to mean 0, std 1"
  hint="Edit the word’s numbers. Then switch the axis to see why it is done per word."
  onreset={() => { v = [[1, 2, 3, 6]]; byRow = true }}
  resetDisabled={!changed1}
>
  <div class="stack">
  <div class="one">
    <MatrixGrid value={v} label="one word’s 4 numbers (edit them)" editable decimals={1} onchange={(x) => (v = x)} />
    <div class="bars">
      <div>
        <div class="label">before: mean {f(mean(v[0]))}, std {f(std(v[0]))}</div>
        {#each v[0] as x}
          <div class="b"><span class="track"><span class="bar" class:neg={x < 0} style:width="{bar(x, 0.25)}rem"></span></span><code>{f(x)}</code></div>
        {/each}
      </div>
      <div>
        <div class="label">after: mean {f(mean(ln), 2)}, std {f(std(ln))}</div>
        {#each ln as x}
          <div class="b"><span class="track"><span class="bar" class:neg={x < 0} style:width="{lnLocked ? 0 : bar(x, 1.5)}rem"></span></span><code class:q={lnLocked}>{lnLocked ? '?' : f(x, 3)}</code></div>
        {/each}
      </div>
    </div>
  </div>
  <div class="pair">
    <MatrixGrid value={M} label="3 words × 4 numbers" rowLabels={['w0', 'w1', 'w2']} />
    <div class="op" aria-hidden="true">→</div>
    <MatrixGrid value={normed} label={byRow ? 'normalized per word' : 'normalized per column'} rowLabels={['w0', 'w1', 'w2']} masked={lnLocked ? [{ i: 0, j: 3 }] : []} />
  </div>
  </div>

  {#snippet controls()}
    <span class="seg" role="radiogroup" aria-label="Normalize along">
      <label class:on={byRow}><input type="radio" bind:group={byRow} value={true} /> each row, one word (LayerNorm)</label>
      <label class:on={!byRow}><input type="radio" bind:group={byRow} value={false} /> each column (wrong axis)</label>
    </span>
  {/snippet}

  {#snippet readout()}
    <span class="prose">{byRow ? 'Each word is normalized with its own mean and std. Change one word and the others don’t move.' : 'Per column, every word’s result depends on the other words in the batch. Word w1 is 10s everywhere, so it is still large in every column.'}</span>
  {/snippet}

  {#snippet legend()}
    <span class="key"><i class="pos"></i>positive</span>
    <span class="key"><i class="neg"></i>negative</span>
  {/snippet}
</LabFrame>

<LabFrame
  title={`Stack ${depth} layers: does the signal survive?`}
  hint="Pick how each layer updates x, then slide the gain and the number of layers."
  onreset={() => { mode = 'plain'; gain = 0.5; depth = 30 }}
  resetDisabled={!changed2}
>
  <div class="label">size of x after each layer (log scale)</div>
  <svg viewBox="0 0 {W} {H}" use:readable role="img" aria-label={`Size of x after each of ${depth} layers, on a log scale: ${verdict}.`}>
    {#each yTicks as [l, t]}
      <line x1={PADL} y1={cy(l)} x2={W - PADR} y2={cy(l)} class={l === 0 ? 'one-line' : 'gl'} />
      <text x={PADL - 4} y={cy(l) + 3} class="tk end">{t}</text>
    {/each}
    {#each xTicks as t}<text x={cx(t)} y={H - 9} class="tk mid">{t}</text>{/each}
    <text x={W - PADR} y={H - 9} class="tk end ax">layer {depth}</text>
    <line x1={PADL} y1={PADT} x2={PADL} y2={H - PADB} class="axis" />
    <path d={path} class="curve" class:bad={verdict !== 'steady'} />
    <circle cx={cx(depth)} cy={cy(lg(last))} r="4.5" class="end-dot" class:bad={verdict !== 'steady'} />
  </svg>
  <div class="label">final values of x (bar height = size; a flat row means they all vanished)</div>
  <div class="hist">
    {#each run.final as x}<span class="col" class:neg={x < 0} style:height="{Math.max(0.12, Math.min(2.5, Math.abs(x) * 0.625))}rem" title={big(x)}></span>{/each}
  </div>

  {#snippet controls()}
    <span class="modes" role="radiogroup" aria-label="Each layer does">
      {#each [['plain', 'x ← f(x)'], ['residual', 'x ← x + f(x)'], ['residual+norm', 'x ← LayerNorm(x + f(x))']] as [m, label]}
        <label class:on={mode === m}><input type="radio" bind:group={mode} value={m} /> <code>{label}</code></label>
      {/each}
    </span>
    <label class="sl"><span>layers</span><input type="range" min="1" max="60" bind:value={depth} /><b>{depth}</b></label>
    <label class="sl"><span>gain of f</span><input type="range" min="0.3" max="2" step="0.05" bind:value={gain} /><b>{f(gain)}</b></label>
  {/snippet}

  {#snippet readout()}
    size after {depth} layers: <b class="res" class:bad={verdict !== 'steady'}>{big(last)}</b> · {verdict}
  {/snippet}

  {#snippet legend()}
    <span class="key"><i class="ln-sw"></i>size of x (vector length), stable</span>
    <span class="key"><i class="ln-sw bad"></i>vanished or grew very large</span>
    <span class="key"><i class="dash-sw"></i>size 1</span>
    <span class="key"><i class="pos"></i><i class="neg"></i>final values: positive / negative</span>
  {/snippet}
</LabFrame>

<style>
  .stack { display: flex; flex-direction: column; gap: 1.1rem; }
  .prose { font-family: system-ui, -apple-system, sans-serif; }
  .one { display: flex; flex-wrap: wrap; gap: 1rem 2rem; align-items: flex-start; }
  .label { font-size: 0.78rem; color: var(--dim); font-family: var(--mono); margin-bottom: 0.25rem; }
  .bars { display: flex; flex-wrap: wrap; gap: 1rem 2rem; }
  .b { display: flex; align-items: center; gap: 0.5rem; height: 1.4rem; font-size: 0.82rem; }
  .b code { font-variant-numeric: tabular-nums; min-width: 3.5rem; text-align: right; }
  .b code.q { color: var(--warn); font-weight: 700; }
  /* zero in the middle: positive grows right, negative grows left */
  .track { position: relative; width: 6rem; height: 0.75rem; flex: none; }
  .track::before { content: ''; position: absolute; left: 50%; top: -0.2rem; bottom: -0.2rem; border-left: 1px solid var(--dim); }
  .bar { position: absolute; left: 50%; top: 0; bottom: 0; background: var(--pos); border-radius: 0 2px 2px 0; transition: width 0.2s; }
  .bar.neg { left: auto; right: 50%; background: var(--neg); border-radius: 2px 0 0 2px; }
  .pair { display: flex; flex-wrap: wrap; gap: 0.8rem 1.2rem; align-items: center; }
  .op { color: var(--dim); font-family: var(--mono); }
  .seg, .modes { display: inline-flex; flex-wrap: wrap; gap: 0.35rem; }
  .seg label, .modes label { display: inline-flex; align-items: center; gap: 0.4rem; font-size: 0.85rem; min-height: 2.5rem; padding: 0 0.7rem;
    border: 1px solid var(--field); border-radius: 6px; background: var(--bg); cursor: pointer; }
  /* the shared "on" style of .lab-btn[aria-pressed] */
  .seg label.on, .modes label.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  .seg input, .modes input { accent-color: var(--accent); margin: 0; }
  .modes code { font-size: 0.82rem; }
  .sl { display: inline-flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; min-height: 2.5rem; flex: 1 1 15rem; padding-right: 1rem; }
  .sl span { color: var(--dim); font-family: var(--mono); min-width: 5rem; }
  .sl input { flex: 1; min-width: 5rem; accent-color: var(--accent); }
  .sl b { font-family: var(--mono); min-width: 2.5rem; text-align: right; font-variant-numeric: tabular-nums; }
  svg { width: 100%; max-width: 40rem; height: auto; display: block; border: 1px solid var(--line); border-radius: 6px; background: var(--bg); }
  .gl { stroke: var(--line); stroke-width: 1; }
  .one-line { stroke: var(--dim); stroke-width: 1; stroke-dasharray: 4 4; }
  .axis { stroke: var(--dim); stroke-width: 1; }
  .tk { font-size: 10.5px; fill: var(--dim); font-family: var(--mono); }
  .tk.end { text-anchor: end; }
  .tk.mid { text-anchor: middle; }
  .curve { fill: none; stroke: var(--ok); stroke-width: 2.5; stroke-linejoin: round; }
  .curve.bad { stroke: var(--warn); }
  .end-dot { fill: var(--ok); stroke: var(--bg); stroke-width: 1; }
  .end-dot.bad { fill: var(--warn); }
  .res { color: var(--ok); }
  .res.bad { color: var(--warn); }
  .hist { display: flex; align-items: flex-end; gap: 0.25rem; height: 2.6rem; }
  .col { width: 0.9rem; background: var(--pos); border-radius: 2px 2px 0 0; transition: height 0.2s; }
  .col.neg { background: var(--neg); }
  .key { display: inline-flex; align-items: center; gap: 0.35rem; }
  .key i { width: 0.8rem; height: 0.8rem; border-radius: 2px; flex: none; }
  .key i.pos { background: var(--pos); }
  .key i.neg { background: var(--neg); }
  .key i.ln-sw { height: 0; width: 1.1rem; border-top: 2px solid var(--ok); border-radius: 0; }
  .key i.ln-sw.bad { border-top-color: var(--warn); }
  .key i.dash-sw { height: 0; width: 1.1rem; border-top: 1.5px dashed var(--dim); border-radius: 0; }
  @media (prefers-reduced-motion: reduce) { .bar, .col { transition: none; } }
  @media (max-width: 560px) { .op { display: none; } }
</style>
