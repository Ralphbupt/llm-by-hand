<script lang="ts">
  /**
   * The gradient through time: how much does a nudge to h_1 still move h_t?
   * d h_t / d h_1 = product over steps of w_h × act'(z). Plotted on a log scale for 30 steps.
   */
  import { gradThroughTime, rnnScalar } from '@lib/classic'
  import { readable } from '@lib/readable'
  import LabFrame from './LabFrame.svelte'

  const T = 30
  let wh = $state(0.5)
  let act = $state<'tanh' | 'none'>('tanh')
  const changed = $derived(wh !== 0.5 || act !== 'tanh')
  const xs = [1, ...new Array(T - 1).fill(0)]
  const hs = $derived(rnnScalar(xs, 1, wh, 0, 0, act))
  const g = $derived(gradThroughTime(hs, wh, act).map(Math.abs))

  // chart: log10 from 1e-12 to 1e6
  const W = 360, H = 218, L = 44, R = 14, TOP = 28, B = 26
  const LO = -12, HI = 6
  const x = (t: number) => L + ((t - 1) / (T - 1)) * (W - L - R)
  const y = (v: number) => {
    const l = Math.max(LO, Math.min(HI, Math.log10(Math.max(v, 1e-300))))
    return TOP + ((HI - l) / (HI - LO)) * (H - TOP - B)
  }
  const path = $derived(g.map((v, i) => `${i ? 'L' : 'M'}${x(i + 1).toFixed(1)},${y(v).toFixed(1)}`).join(' '))
  const ticks = [6, 3, 0, -3, -6, -9, -12]
  const last = $derived(g[T - 1])
  // the line's color says what is happening: --warn when the signal vanishes or explodes, --ok when it survives
  const tone = $derived(last < 1e-3 ? 'bad' : last > 1e3 ? 'bad' : 'good')
  const fmt = (v: number) => (v === 0 ? '0' : v >= 1e4 || v < 1e-3 ? v.toExponential(2) : v.toFixed(4))
</script>

<LabFrame
  title="How much does step 1 still matter at step t?"
  hint="Drag w_h and switch the activation. The line is the gradient d h_t / d h_1 over 30 steps."
  onreset={() => { wh = 0.5; act = 'tanh' }}
  resetDisabled={!changed}
>
  <svg use:readable viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="size of d h_t / d h_1 against t, log scale">
    <!-- zones: below 1e-3 the early input is forgotten, above 1e3 it explodes -->
    <rect x={L} y={y(10 ** -3)} width={W - L - R} height={y(10 ** LO) - y(10 ** -3)} class="zone" />
    <rect x={L} y={y(10 ** HI)} width={W - L - R} height={y(10 ** 3) - y(10 ** HI)} class="zone" />
    <text x={W - R - 4} y={y(10 ** -11)} class="zone-t" text-anchor="end">vanishing</text>
    <text x={W - R - 4} y={y(10 ** 5)} class="zone-t" text-anchor="end">exploding</text><!-- en-ok: explod (the term) -->
    <text x={L + 4} y={15} class="lab-t">d h_t / d h_1 (log scale)</text>
    {#each ticks as tk}
      <line x1={L} x2={W - R} y1={y(10 ** tk)} y2={y(10 ** tk)} class="grid" />
      <text x={L - 4} y={y(10 ** tk) + 3} class="lab-t" text-anchor="end">1e{tk}</text>
    {/each}
    <line x1={L} x2={W - R} y1={y(1)} y2={y(1)} class="one" />
    {#each [1, 10, 20, 30] as t}<text x={x(t)} y={H - 6} class="lab-t" text-anchor={t === 30 ? 'end' : t === 1 ? 'start' : 'middle'}>t={t}</text>{/each}
    <path d={path} class="line {tone}" />
    <circle cx={x(T)} cy={y(last)} r="4" class="dot {tone}" />
  </svg>

  {#snippet controls()}
    <label class="knob">w_h <b>{wh.toFixed(2)}</b> <input type="range" min="0.1" max="2" step="0.05" bind:value={wh} aria-label="w_h" /></label>
    <span class="opts" role="radiogroup" aria-label="Activation">
      <label><input type="radio" bind:group={act} value="tanh" /> tanh</label>
      <label><input type="radio" bind:group={act} value="none" /> no activation</label>
    </span>
  {/snippet}

  {#snippet readout()}
    at t = 30, d h_30 / d h_1 = <b>{fmt(last)}</b>{#if last < 1e-3}: the first input has almost no say, so training does not see that it matters{:else if last > 1e3}: tiny changes early grow very large, so training jumps around{:else}: the signal survives{/if}
  {/snippet}

  {#snippet legend()}
    <span>input 1 at step 1, then 0; w_x = 1, b = 0</span>
    <span>each step multiplies by w_h × (slope of the activation); tanh’s slope is at most 1</span>
    <span><i class="sw zone-sw"></i>vanishing or exploding</span><!-- en-ok: explod (the term) -->
  {/snippet}
</LabFrame>

<style>
  .knob { display: inline-flex; align-items: center; gap: 0.4rem; font-size: 0.88rem; font-family: var(--mono); color: var(--dim); }
  .knob b { color: var(--fg); min-width: 2.6rem; }
  .knob input { width: 8rem; min-height: 2rem; accent-color: var(--accent); }
  .opts { display: inline-flex; gap: 0.9rem; color: var(--dim); font-size: 0.88rem; }
  .opts label { display: inline-flex; align-items: center; gap: 0.3rem; min-height: 2rem; }
  .chart { width: 100%; max-width: 34rem; display: block; background: var(--bg); border: 1px solid var(--line); border-radius: 6px; }
  .grid { stroke: var(--line); stroke-width: 1; }
  .one { stroke: var(--dim); stroke-dasharray: 3 3; }
  .lab-t { fill: var(--dim); font-size: 11px; font-family: var(--mono); }
  .zone { fill: var(--warn); opacity: 0.08; }
  .zone-t { fill: var(--warn); font-size: 11px; }
  .line { fill: none; stroke-width: 2.5; transition: stroke 0.2s; }
  .line.good { stroke: var(--ok); } .line.bad { stroke: var(--warn); }
  .dot.good { fill: var(--ok); } .dot.bad { fill: var(--warn); }
  .sw { display: inline-block; width: 0.8rem; height: 0.8rem; border-radius: 2px; vertical-align: -0.1em; margin-right: 0.3rem; }
  .zone-sw { background: color-mix(in srgb, var(--warn) 25%, transparent); }
  @media (prefers-reduced-motion: reduce) { .line { transition: none; } }
</style>
