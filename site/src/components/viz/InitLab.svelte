<script lang="ts">
  /**
   * Initialization lab: 40 random inputs (std 1) go through 10 layers of width 100.
   * Pick the weight std and the activation; see each layer's activation std and histogram.
   */
  import { propagate, type Act } from '@lib/training'
  import LabFrame from './LabFrame.svelte'
  import { readable } from '@lib/readable'

  const WIDTH = 100, LAYERS = 10
  const STD0 = 0.05, ACT0: Act = 'none'

  let std = $state(STD0)
  let act = $state<Act>(ACT0)
  let seed = $state(1)
  const res = $derived(propagate(WIDTH, LAYERS, std, act, seed))

  // log scale for the std bars: 1e-12 … 1e4
  const LO = -12, HI = 4
  const bar = (v: number) => (Math.max(LO, Math.min(HI, Math.log10(Math.max(v, 1e-300)))) - LO) / (HI - LO)
  const fmt = (v: number) => (v === 0 ? '0' : v < 0.01 || v >= 1000 ? v.toExponential(1) : String(Number(v.toFixed(3))))

  function reset() {
    std = STD0
    act = ACT0
    seed = 1
  }
  const changed = $derived(std !== STD0 || act !== ACT0 || seed !== 1)
  const growth = $derived(Math.sqrt(WIDTH) * std)

  // ---- chart: log10(std) per layer, layer 0 = the inputs (std 1)
  const CX = (l: number) => 10 + (l / LAYERS) * 86
  const CY = (v: number) => 3 + (1 - bar(v)) * 29
  const pts = $derived([1, ...res.stds])
  const line = $derived(pts.map((v, l) => `${CX(l)},${CY(v)}`).join(' '))
  const health = (v: number) => (v < 1e-3 ? 'low' : v > 1e3 ? 'high' : v < 0.1 || v > 10 ? 'drift' : 'ok')
  const final = $derived(res.stds[LAYERS - 1])
  const verdict = $derived(
    health(final) === 'low' ? 'The layer outputs have almost vanished: the last layer’s outputs are nearly all 0.'
      : health(final) === 'high' ? 'The layer outputs have grown very large: the last layer’s outputs are huge.'
      : health(final) === 'drift' ? 'The layer outputs are moving away from std 1. More layers would make it worse.'
      : 'The layer outputs keep a good size (std about 1) through every layer.',
  )
</script>

<LabFrame
  title="Ten layers deep: do the layer outputs keep their size?"
  hint="Pick an activation and a weight std. Each layer’s outputs should stay near std 1."
  onreset={reset}
  resetDisabled={!changed}
>
  <svg viewBox="-4 0 104 38" class="chart" use:readable aria-label="Standard deviation of each layer's outputs, on a log scale">
    <rect x="10" y={CY(10)} width="86" height={CY(0.1) - CY(10)} class="band ok" />
    <rect x="10" y={CY(1e4)} width="86" height={CY(1e3) - CY(1e4)} class="band bad" />
    <rect x="10" y={CY(1e-3)} width="86" height={CY(1e-12) - CY(1e-3)} class="band bad" />
    {#each [-12, -8, -4, 0, 4] as e}
      <line x1="10" x2="96" y1={CY(10 ** e)} y2={CY(10 ** e)} class="grid" />
      <text x="8.5" y={CY(10 ** e) + 0.7} class="tick end">{e === 0 ? '1' : `1e${e}`}</text>
    {/each}
    {#each pts as _, l}<text x={CX(l)} y="37" class="tick mid">{l === 0 ? 'in' : l}</text>{/each}
    <polyline points={line} class="curve" />
    {#each pts as v, l}<circle cx={CX(l)} cy={CY(v)} r="0.8" class="pt {health(v)}" />{/each}
    <text x="95" y={CY(10) - 1} class="tick end okt">good: about 1</text>
  </svg>
  <p class="cap">The standard deviation of each layer’s outputs (layer 0 = the inputs, std 1), on a log scale from 10⁻¹² to 10⁴.</p>

  <div class="layers">
    {#each res.stds as s, l}
      <div class="layer">
        <span class="name">layer {l + 1}</span>
        <span class="track"><i style="width: {bar(s) * 100}%" class:low={s < 1e-3} class:high={s > 1e3}></i><b class="one" style="left: {bar(1) * 100}%"></b></span>
        <span class="val">{fmt(s)}</span>
        <svg viewBox="0 0 30 10" class="hist" aria-hidden="true" preserveAspectRatio="none">
          {#each res.hists[l] as h, k}<rect x={k * 2} y={10 - h * 10} width="1.8" height={h * 10} />{/each}
        </svg>
      </div>
    {/each}
  </div>

  {#snippet controls()}
    <span class="knob" role="group" aria-label="activation">activation
      {#each ['none', 'tanh', 'relu'] as a}
        <button class="lab-btn seg" class:on={act === a} aria-pressed={act === a} onclick={() => (act = a as Act)}>{a === 'none' ? 'none (linear)' : a === 'relu' ? 'ReLU' : a}</button>
      {/each}
    </span>
    <span class="knob">
      <label class="knob">weight std <input type="range" min="0.01" max="0.3" step="0.01" bind:value={std} /> <b>{std.toFixed(2)}</b></label>
      <button class="lab-btn" onclick={() => (std = 0.1)}>1/√100 = 0.1</button>
      <button class="lab-btn" onclick={() => (std = 0.14)}>√(2/100) ≈ 0.14</button>
    </span>
    <button class="lab-btn" onclick={() => (seed += 1)}>New random weights</button>
  {/snippet}

  {#snippet readout()}
    <span class:okc={health(final) === 'ok'} class:badc={health(final) === 'low' || health(final) === 'high'}>{verdict}</span>
    {#if act === 'none'}Without an activation, each layer multiplies the std by about √100 × {std.toFixed(2)} = <b>{growth.toFixed(2)}</b>.{/if}
  {/snippet}

  {#snippet legend()}
    <span><i class="sw bar"></i>std of a layer’s outputs</span>
    <span><i class="sw one"></i>std = 1 on each bar</span>
    <span><i class="sw badb"></i>vanished or grew very large</span>
    <span><i class="sw hst"></i>the shape of each layer’s values, scaled to its own std</span>
  {/snippet}
</LabFrame>

<style>
  .knob { display: inline-flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; font-size: 0.85rem; color: var(--dim); }
  .knob b { color: var(--fg); font-family: var(--mono); }
  .knob input[type='range'] { width: 8rem; accent-color: var(--accent); }
  .seg.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  .chart { width: 100%; display: block; background: var(--bg); border: 1px solid var(--line); border-radius: 4px; overflow: visible; }
  .cap { margin: 0.3rem 0 0.7rem; font-size: 0.8rem; color: var(--dim); }
  .band.ok { fill: var(--ok); opacity: 0.12; }
  .band.bad { fill: var(--warn); opacity: 0.08; }
  .grid { stroke: var(--line); stroke-width: 0.2; }
  .tick { font-size: 2px; fill: var(--dim); font-family: var(--mono); }
  .tick.okt { fill: var(--ok); }
  .mid { text-anchor: middle; }
  .end { text-anchor: end; }
  .curve { fill: none; stroke: var(--accent); stroke-width: 0.4; stroke-linejoin: round; }
  .pt { fill: var(--accent); transition: cy 0.2s; }
  .pt.low, .pt.high { fill: var(--warn); }
  .okc { color: var(--ok); }
  .badc { color: var(--warn); }
  .layers { display: grid; gap: 0.3rem; }
  .layer { display: grid; grid-template-columns: 4.6rem minmax(0, 1fr) 4.4rem 3.2rem; gap: 0.5rem; align-items: center; font-family: var(--mono); font-size: 0.78rem; font-variant-numeric: tabular-nums; }
  @media (max-width: 480px) { .layer { grid-template-columns: 4.2rem minmax(0, 1fr) 4rem 2.2rem; gap: 0.35rem; } }
  .name { color: var(--dim); white-space: nowrap; }
  .track { position: relative; height: 0.65rem; background: var(--bg); border: 1px solid var(--line); border-radius: 3px; overflow: hidden; }
  .track i { display: block; height: 100%; background: var(--accent); transition: width 0.2s; }
  .track .one { position: absolute; top: 0; bottom: 0; width: 2px; margin-left: -1px; background: var(--ok); }
  @media (prefers-reduced-motion: reduce) { .track i, .pt { transition: none; } }
  .track i.low, .track i.high { background: var(--warn); }
  .val { text-align: right; }
  .hist { width: 100%; height: 1rem; }
  .hist rect { fill: var(--dim); }
  .sw { display: inline-block; width: 0.9rem; height: 0.6rem; border-radius: 2px; margin-right: 0.35rem; vertical-align: -0.02rem; }
  .sw.bar { background: var(--accent); }
  .sw.one { width: 2px; height: 0.8rem; background: var(--ok); }
  .sw.badb { background: var(--warn); }
  .sw.hst { background: linear-gradient(to top, var(--dim) 40%, transparent 40%), linear-gradient(to right, transparent 30%, var(--dim) 30% 60%, transparent 60%); }
</style>
