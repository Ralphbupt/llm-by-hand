<script lang="ts">
  /**
   * Capacity lab: fit a polynomial of degree 0–9 to 10 noisy points (exact least squares).
   * Shows the fitted curve against held-out points, and train vs held-out loss for every degree.
   * With `decay`, a weight-decay slider shrinks the coefficients (constant term excluded).
   */
  import { polyEval, polyFit, truth } from '@lib/training'
  import LabFrame from './LabFrame.svelte'
  import { readable } from '@lib/readable'

  let { decay: withDecay = false }: { decay?: boolean } = $props()

  const D0 = 3
  const DECAYS = [0, 1e-4, 1e-3, 1e-2, 1e-1]
  // 10 to a power, written as on the lesson pages: 10⁻⁴, not 1e-4
  const pow10 = (e: number) => '10' + String(e).replace(/./g, (c) => '⁻⁰¹²³⁴⁵⁶⁷⁸⁹'['-0123456789'.indexOf(c)])
  let d = $state(D0)
  let di = $state(0)
  const lam = $derived(withDecay ? DECAYS[di] : 0)
  const fit = $derived(polyFit(d, lam))
  const all = $derived(Array.from({ length: 10 }, (_, k) => polyFit(k, lam)))

  function reset() {
    d = withDecay ? 9 : D0
    di = 0
  }
  reset()
  const changed = $derived(d !== (withDecay ? 9 : D0) || di !== 0)

  const X = [-1.05, 1.05], Y = [-2, 2]
  const sx = (x: number) => ((x - X[0]) / (X[1] - X[0])) * 100
  const sy = (y: number) => ((Y[1] - Math.max(Y[0] - 1, Math.min(Y[1] + 1, y))) / (Y[1] - Y[0])) * 42
  const curve = (f: (x: number) => number) =>
    Array.from({ length: 121 }, (_, i) => -1 + (2 * i) / 120).map((x) => `${sx(x)},${sy(f(x))}`).join(' ')

  // loss per degree on a log scale (1e-4 … 10): train and held-out as two lines
  const LLO = -4, LHI = 1
  const ly = (v: number) => 2.5 + (1 - (Math.max(LLO, Math.min(LHI, Math.log10(Math.max(v, 1e-12)))) - LLO) / (LHI - LLO)) * 20
  const lx = (k: number) => 12 + k * 9.3
  const bestK = $derived(all.reduce((bi, r, k) => (r.held < all[bi].held ? k : bi), 0))
  const f4 = (v: number) => v.toFixed(4)
</script>

<LabFrame
  title={withDecay ? 'Weight decay makes a degree-9 fit smooth' : 'Too few, just right, too many parameters'}
  hint={withDecay ? 'Raise the weight decay and watch the up-and-down swings and the held-out loss.' : 'Slide the degree. Watch the training loss and the held-out loss.'}
  onreset={reset}
  resetDisabled={!changed}
>
  <svg viewBox="0 0 100 47" class="fitplot" use:readable aria-label="Training points, held-out points and the fitted polynomial">
    <rect x="0" y="0" width="100" height="42" class="plot" />
    <line x1="0" x2="100" y1={sy(0)} y2={sy(0)} class="axis" />
    <defs><clipPath id="cap-plot-{withDecay ? 'd' : 'p'}"><rect x="0" y="0" width="100" height="42" /></clipPath></defs>
    <g clip-path="url(#cap-plot-{withDecay ? 'd' : 'p'})">
      <polyline points={curve(truth)} class="truth" />
      <polyline points={curve((x) => polyEval(fit.c, x))} class="fit" />
      {#each fit.data.heldX as x, i}<circle cx={sx(x)} cy={sy(fit.data.heldY[i])} r="0.8" class="held" />{/each}
      {#each fit.data.trainX as x, i}<circle cx={sx(x)} cy={sy(fit.data.trainY[i])} r="1.3" class="train" />{/each}
    </g>
    {#each [-1, 0, 1] as tx}<text x={sx(tx)} y="46" class="tick mid">{tx === -1 ? '−1' : tx}</text>{/each}
    <text x={sx(0.5)} y="46" class="tick mid name">x</text>
  </svg>

  <svg viewBox="0 0 100 30" class="bars" use:readable aria-label="Train and held-out loss for every degree, log scale">
    {#each [-4, -2, 0] as e}
      <line x1="10" x2="98" y1={ly(10 ** e) + 2} y2={ly(10 ** e) + 2} class="grid" />
      <text x="8.5" y={ly(10 ** e) + 2.8} class="tick end">{e === 0 ? '1' : pow10(e)}</text>
    {/each}
    <text x="1" y="2.6" class="tick name">loss</text>
    <g transform="translate(0 2)">
      <line x1={lx(d)} x2={lx(d)} y1="0" y2="23" class="cur" />
      <polyline points={all.map((r, k) => `${lx(k)},${ly(r.train)}`).join(' ')} class="l-train" />
      <polyline points={all.map((r, k) => `${lx(k)},${ly(r.held)}`).join(' ')} class="l-held" />
      {#each all as r, k}
        <circle cx={lx(k)} cy={ly(r.train)} r={k === d ? 1 : 0.6} class="p-train" />
        <circle cx={lx(k)} cy={ly(r.held)} r={k === d ? 1.1 : 0.7} class="p-held" />
        <text x={lx(k)} y="26.8" class="tick mid" class:curt={k === d}>{k}</text>
      {/each}
      <circle cx={lx(bestK)} cy={ly(all[bestK].held)} r="1.8" class="best" />
      <text x="8.5" y="26.8" class="tick end name">degree</text>
    </g>
  </svg>

  {#snippet controls()}
    <label class="knob">degree <input type="range" min="0" max="9" step="1" bind:value={d} /> <b>{d}</b> <span class="dim">({d + 1} parameters)</span></label>
    {#if withDecay}
      <label class="knob">weight decay <input type="range" min="0" max={DECAYS.length - 1} step="1" bind:value={di} /> <b>{lam === 0 ? '0' : pow10(Math.round(Math.log10(lam)))}</b></label>
    {/if}
  {/snippet}

  {#snippet readout()}Degree {d}: train loss <b>{f4(fit.train)}</b> · held-out loss <b>{f4(fit.held)}</b>{/snippet}

  {#snippet legend()}
    <span><i class="dot train"></i>10 training points</span>
    <span><i class="dot held"></i>40 held-out points</span>
    <span><i class="ln fit"></i>the fit</span>
    <span><i class="ln truth"></i>the true curve sin(πx)</span>
    <span><i class="ln train"></i>train loss</span>
    <span><i class="ln held"></i>held-out loss</span>
    <span><i class="ring"></i>lowest held-out loss (degree {bestK})</span>
  {/snippet}
</LabFrame>

<style>
  svg { width: 100%; display: block; overflow: visible; }
  .plot { fill: var(--bg); stroke: var(--line); stroke-width: 0.3; }
  .bars { margin-top: 0.6rem; background: var(--bg); border: 1px solid var(--line); border-radius: 4px; }
  .axis { stroke: var(--line); stroke-width: 0.3; }
  .truth { fill: none; stroke: var(--ok); stroke-width: 0.45; stroke-dasharray: 1.5 1; }
  .fit { fill: none; stroke: var(--accent); stroke-width: 0.7; }
  .train { fill: var(--cat-5); stroke: var(--bg); stroke-width: 0.3; }
  .held { fill: none; stroke: var(--cat-3); stroke-width: 0.3; }
  .dot { display: inline-block; width: 0.6rem; height: 0.6rem; border-radius: 50%; margin-right: 0.3rem; vertical-align: -0.02rem; }
  .dot.train { background: var(--cat-5); }
  .dot.held { border: 1.5px solid var(--cat-3); }
  .ln { display: inline-block; width: 1rem; height: 0; border-top: 2px solid var(--accent); margin-right: 0.3rem; vertical-align: middle; }
  .ln.truth { border-top: 2px dashed var(--ok); }
  .ln.train { border-top: 2px solid var(--cat-5); }
  .ln.held { border-top: 2px solid var(--cat-3); }
  .ring { display: inline-block; width: 0.65rem; height: 0.65rem; border-radius: 50%; border: 1.5px solid var(--ok); margin-right: 0.3rem; vertical-align: -0.05rem; }
  .knob { display: inline-flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; font-size: 0.85rem; color: var(--dim); min-height: 2.5rem; }
  .knob input { width: 9rem; accent-color: var(--accent); }
  .knob b { color: var(--fg); font-family: var(--mono); }
  .dim { color: var(--dim); }
  .grid { stroke: var(--line); stroke-width: 0.2; }
  .cur { stroke: var(--accent); stroke-width: 0.3; stroke-dasharray: 1 1; opacity: 0.8; }
  .l-train { fill: none; stroke: var(--cat-5); stroke-width: 0.5; }
  .l-held { fill: none; stroke: var(--cat-3); stroke-width: 0.6; }
  .p-train { fill: var(--cat-5); }
  .p-held { fill: var(--cat-3); }
  .best { fill: none; stroke: var(--ok); stroke-width: 0.5; }
  .tick { font-size: 2.3px; fill: var(--dim); font-family: var(--mono); }
  .fitplot .tick { font-size: 2.3px; }
  .tick.name { fill: var(--fg); font-style: italic; }
  .tick.curt { fill: var(--accent); font-weight: 700; }
  .mid { text-anchor: middle; }
  .tick.end { text-anchor: end; }
</style>
