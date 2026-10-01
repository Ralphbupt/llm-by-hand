<script lang="ts">
  import LabFrame from './LabFrame.svelte'
  import { readable } from '@lib/readable'
  /**
   * Gaussian lab: every point is x = mean + std * z, where z comes from a standard normal.
   * The z values are drawn once (fixed seed), so moving a slider moves the same cloud.
   */
  const N = 300
  function rng(seed: number) {
    let s = seed >>> 0
    return () => {
      s = (s + 0x6d2b79f5) >>> 0
      let t = s
      t = Math.imul(t ^ (t >>> 15), t | 1)
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296
    }
  }
  function draws(seed: number) {
    const r = rng(seed)
    return Array.from({ length: N }, () => {
      const u1 = r() || 1e-12, u2 = r()
      const m = Math.sqrt(-2 * Math.log(u1))
      return [m * Math.cos(2 * Math.PI * u2), m * Math.sin(2 * Math.PI * u2)]
    })
  }

  let seed = $state(1)
  let mx = $state(0), my = $state(0), sd = $state(1)
  const Z = $derived(draws(seed))
  const pts = $derived(Z.map(([a, b]) => [mx + sd * a, my + sd * b]))
  const stats = $derived.by(() => {
    const xs = pts.map((p) => p[0])
    const mean = xs.reduce((a, b) => a + b, 0) / N
    const std = Math.sqrt(xs.reduce((a, b) => a + (b - mean) ** 2, 0) / N)
    const in1 = pts.filter((p) => Math.abs(p[0] - mx) <= sd).length / N
    return { mean, std, in1 }
  })

  const D = 6
  const sx = (x: number) => ((x + D) / (2 * D)) * 100
  const sy = (y: number) => 100 - ((y + D) / (2 * D)) * 100
  const first = $derived(Z[0])

  // the x values as a histogram (bins of 0.5 from −6 to 6), with the bell curve of x on top: the density
  // 1/(std·√(2π))·e^(−(x−mean)²/(2·std²)). Bars and curve share the scale, so they should agree.
  const BIN = 0.5, YMAX = 0.8
  const hist = $derived.by(() => {
    const c = new Array(Math.round((2 * D) / BIN)).fill(0)
    for (const p of pts) {
      const k = Math.floor((p[0] + D) / BIN)
      if (k >= 0 && k < c.length) c[k]++
    }
    return c.map((n) => n / (N * BIN))
  })
  const hy = (v: number) => 60 - (Math.min(v, YMAX * 1.02) / YMAX) * 56
  const bell = $derived.by(() => {
    if (sd < 0.05) return ''
    return Array.from({ length: 161 }, (_, i) => {
      const x = -D + (i / 160) * 2 * D
      const v = Math.exp(-((x - mx) ** 2) / (2 * sd * sd)) / (sd * Math.sqrt(2 * Math.PI))
      return `${sx(x).toFixed(2)},${hy(v).toFixed(2)}`
    }).join(' ')
  })
  const changed = $derived(mx !== 0 || my !== 0 || sd !== 1 || seed !== 1)
</script>
<LabFrame
  title="Gaussian noise: x = mean + std × z"
  hint="Move the mean and the std. Every point keeps its own z, so the whole cloud shifts and stretches together."
  onreset={() => { mx = 0; my = 0; sd = 1; seed = 1 }}
  resetDisabled={!changed}
>
  <div class="pics">
    <figure>
      <svg viewBox="-1 -1 102 106" use:readable aria-label="Cloud of sampled points">
        <rect x="0" y="0" width="100" height="100" class="box" />
        {#each [-4, -2, 0, 2, 4] as t}
          <line x1={sx(t)} y1="0" x2={sx(t)} y2="100" class="grid" class:axis={t === 0} />
          <line x1="0" y1={sy(t)} x2="100" y2={sy(t)} class="grid" class:axis={t === 0} />
          <text x={sx(t)} y="104.5" class="tick">{String(t).replace('-', '−')}</text>
        {/each}
        <circle cx={sx(mx)} cy={sy(my)} r={(sd / (2 * D)) * 100} class="ring" />
        {#each pts as p, i}
          {#if i > 0}<circle cx={sx(p[0])} cy={sy(p[1])} r="0.8" class="pt" />{/if}
        {/each}
        <circle cx={sx(mx)} cy={sy(my)} r="1.4" class="mean" />
        <circle cx={sx(pts[0][0])} cy={sy(pts[0][1])} r="2" class="pt first" />
      </svg>
      <figcaption>{N} samples (x, y). The ring is one std from the mean.</figcaption>
    </figure>
    <figure>
      <svg viewBox="-1 -6 102 72" use:readable aria-label="Histogram of the x values with the bell curve on top">
        <defs><clipPath id="gauss-plot"><rect x="0" y="0" width="100" height="60" /></clipPath></defs>
        <rect x="0" y="0" width="100" height="60" class="box" />
        <rect x={sx(mx - sd)} y="0" width={sx(mx + sd) - sx(mx - sd)} height="60" class="band" clip-path="url(#gauss-plot)" />
        <g clip-path="url(#gauss-plot)">
          {#each hist as v, k}
            {#if v > 0}<rect x={sx(-D + k * BIN) + 0.15} y={hy(v)} width={(BIN / (2 * D)) * 100 - 0.3} height={60 - hy(v)} class="hbar" />{/if}
          {/each}
          {#if bell}<polyline points={bell} class="bell" />{/if}
        </g>
        <line x1={sx(pts[0][0])} x2={sx(pts[0][0])} y1="0" y2="60" class="me" />
        {#each [-4, -2, 0, 2, 4] as t}<text x={sx(t)} y="65.5" class="tick">{String(t).replace('-', '−')}</text>{/each}
        <text x="1.5" y="-1.5" class="tick name start">how many land at each x</text>
        <text x={Math.max(14, Math.min(86, sx(mx)))} y="5" class="tick band-t">{(stats.in1 * 100).toFixed(0)}% within one std</text>
      </svg>
      <figcaption>The same points, counted by x only. The curve is the Gaussian’s bell shape for this mean and std.</figcaption>
    </figure>
  </div>

  {#snippet controls()}
    <div class="knobs">
      <label><span>mean x</span> <input type="range" min="-3" max="3" step="0.1" value={mx} oninput={(e) => (mx = +(e.currentTarget as HTMLInputElement).value)} /> <b>{mx.toFixed(1)}</b></label>
      <label><span>mean y</span> <input type="range" min="-3" max="3" step="0.1" value={my} oninput={(e) => (my = +(e.currentTarget as HTMLInputElement).value)} /> <b>{my.toFixed(1)}</b></label>
      <label><span>std</span> <input type="range" min="0" max="3" step="0.1" value={sd} oninput={(e) => (sd = +(e.currentTarget as HTMLInputElement).value)} /> <b>{sd.toFixed(1)}</b></label>
    </div>
    <button class="lab-btn" onclick={() => (seed = seed + 1)}>Draw new noise</button>
  {/snippet}

  {#snippet readout()}
    highlighted point: z = ({first[0].toFixed(2)}, {first[1].toFixed(2)}) → x = {mx.toFixed(1)} + {sd.toFixed(1)} × {first[0].toFixed(2)} = <b>{(mx + sd * first[0]).toFixed(2)}</b>
    <span class="dim">· measured over {N} points: mean of x = {stats.mean.toFixed(2)}, std of x = {stats.std.toFixed(2)}, within one std of the mean (in x): {(stats.in1 * 100).toFixed(0)}%</span>
  {/snippet}

  {#snippet legend()}
    <span><i class="sw hl"></i>the highlighted point, computed in the line above</span>
    <span><i class="sw pt-sw"></i>the other samples</span>
    <span><i class="sw ring-sw"></i>one std from the mean</span>
    <span><i class="sw bar-sw"></i>fraction of points per x</span>
  {/snippet}
</LabFrame>

<style>
  .pics { display: grid; grid-template-columns: minmax(0, 0.85fr) minmax(0, 1fr); gap: 1rem 1.4rem; align-items: start; }
  @media (max-width: 600px) { .pics { grid-template-columns: minmax(0, 1fr); } }
  figure { margin: 0; min-width: 0; }
  figcaption { font-size: 0.8rem; color: var(--dim); margin-top: 0.3rem; }
  svg { width: 100%; display: block; overflow: visible; }
  .box { fill: var(--bg); stroke: var(--line); stroke-width: 0.3; }
  .grid { stroke: var(--line); stroke-width: 0.3; }
  .grid.axis { stroke: var(--dim); stroke-width: 0.5; }
  .tick { font-size: 3px; fill: var(--dim); font-family: var(--mono); text-anchor: middle; }
  .tick.start { text-anchor: start; }
  .tick.name { fill: var(--fg); }
  .tick.band-t { fill: var(--fg); }
  .pt { fill: var(--cat-5); opacity: 0.7; transition: cx 0.15s, cy 0.15s; }
  .pt.first { fill: var(--accent); opacity: 1; stroke: var(--bg); stroke-width: 0.5; }
  .mean { fill: var(--fg); }
  .ring { fill: none; stroke: var(--fg); stroke-width: 0.5; stroke-dasharray: 1.5 1; }
  .band { fill: var(--highlight); }
  .hbar { fill: var(--cat-5); opacity: 0.6; }
  .bell { fill: none; stroke: var(--fg); stroke-width: 0.6; }
  .me { stroke: var(--accent); stroke-width: 0.5; stroke-dasharray: 1 1; }
  .knobs { display: flex; flex-wrap: wrap; gap: 0.2rem 1.2rem; font-size: 0.85rem; color: var(--dim); flex-basis: 100%; }
  .knobs label { display: flex; align-items: center; gap: 0.4rem; min-height: 2.5rem; }
  .knobs input { width: 7.5rem; accent-color: var(--accent); }
  .knobs b { color: var(--fg); font-family: var(--mono); min-width: 2.2rem; font-variant-numeric: tabular-nums; }
  .dim { color: var(--dim); }
  .sw { display: inline-block; width: 0.65rem; height: 0.65rem; border-radius: 50%; margin-right: 0.35rem; vertical-align: -0.02rem; }
  .sw.hl { background: var(--accent); }
  .sw.pt-sw { background: var(--cat-5); opacity: 0.7; width: 0.45rem; height: 0.45rem; }
  .sw.ring-sw { border: 1.5px dashed var(--fg); width: 0.8rem; height: 0.8rem; }
  .sw.bar-sw { border-radius: 2px; background: var(--cat-5); opacity: 0.6; width: 0.9rem; }
  @media (prefers-reduced-motion: reduce) { .pt { transition: none; } }
</style>
