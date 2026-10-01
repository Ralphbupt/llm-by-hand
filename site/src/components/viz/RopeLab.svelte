<script lang="ts">
  /**
   * RoPE lab (level 19): one pair of numbers. q is rotated by m × θ, k by n × θ (θ = 0.5 rad).
   * The score q·k only depends on m − n: move both positions together and it does not change.
   */
  import { onMount } from 'svelte'
  import LabFrame from './LabFrame.svelte'
  import { readable } from '@lib/readable'
  import { has, subscribe } from '@lib/progress'
  import { rotate, dot } from '@lib/modern'

  let { hide = {} }: { hide?: { qx?: string; score?: string } } = $props()
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
  const locked = (k: 'qx' | 'score') => !!hide[k] && !solved[hide[k]!]

  const Q: [number, number] = [1, 0]
  const K: [number, number] = [0, 1]
  const THETA = 0.5
  let m = $state(0)
  let n = $state(0)

  const qr = $derived(rotate(Q, m, THETA))
  const kr = $derived(rotate(K, n, THETA))
  const score = $derived(dot(qr, kr))
  const hideQ = $derived(m === 2 && locked('qx'))
  const hideScore = $derived(Math.abs(m - n) === 2 && locked('score'))

  const R = 80, C = 100
  const px = (v: [number, number]) => [C + v[0] * R, C - v[1] * R]
  const f = (v: number) => v.toFixed(4)
  // the angle between q and k after rotating: it depends only on m − n, and the score is its cosine
  const aq = $derived(Math.atan2(qr[1], qr[0]))
  const between = $derived.by(() => {
    let d = Math.atan2(kr[1], kr[0]) - aq
    while (d > Math.PI) d -= 2 * Math.PI
    while (d < -Math.PI) d += 2 * Math.PI
    return d
  })
  const arc = $derived.by(() => {
    const r = 30, a0 = aq, a1 = aq + between
    const p0 = [C + r * Math.cos(a0), C - r * Math.sin(a0)], p1 = [C + r * Math.cos(a1), C - r * Math.sin(a1)]
    const sweep = between > 0 ? 0 : 1
    return { d: `M${p0[0]},${p0[1]} A${r},${r} 0 0 ${sweep} ${p1[0]},${p1[1]}`, lx: C + (r + 12) * Math.cos(a0 + between / 2), ly: C - (r + 12) * Math.sin(a0 + between / 2) }
  })
  function shift(d: number) { if (m + d >= 0 && n + d >= 0 && m + d <= 12 && n + d <= 12) { m += d; n += d } }
</script>

<LabFrame
  title="RoPE turns q and k by their positions; the score depends only on m − n"
  hint="Move the two positions. Then use “both +1” and watch the score stay the same."
  onreset={() => { m = 0; n = 0 }} resetDisabled={m === 0 && n === 0}
>
  <div class="wrap">
    <svg use:readable viewBox="0 0 200 200" role="img" aria-label={`q at position ${m} and k at position ${n}, rotated on the unit circle`}>
      <circle cx={C} cy={C} r={R} fill="none" stroke="var(--line)" />
      <line x1={C - R - 8} y1={C} x2={C + R + 8} y2={C} stroke="var(--line)" />
      <line x1={C} y1={C - R - 8} x2={C} y2={C + R + 8} stroke="var(--line)" />
      <line x1={C} y1={C} x2={px(Q)[0]} y2={px(Q)[1]} stroke="var(--cat-1)" stroke-dasharray="3 3" opacity="0.55" />
      <line x1={C} y1={C} x2={px(K)[0]} y2={px(K)[1]} stroke="var(--cat-3)" stroke-dasharray="3 3" opacity="0.55" />
      <line x1={C} y1={C} x2={px(qr)[0]} y2={px(qr)[1]} stroke="var(--cat-1)" stroke-width="3" stroke-linecap="round" />
      <line x1={C} y1={C} x2={px(kr)[0]} y2={px(kr)[1]} stroke="var(--cat-3)" stroke-width="3" stroke-linecap="round" />
      {#if Math.abs(between) > 0.02}
        <path d={arc.d} fill="none" stroke="var(--fg)" stroke-width="1.2" opacity="0.7" />
        {#if !hideScore}<text x={arc.lx} y={arc.ly + 3} fill="var(--fg)" font-size="11" text-anchor="middle" class="mono">{Math.abs(between).toFixed(2)}</text>{/if}
      {/if}
      <circle cx={px(qr)[0]} cy={px(qr)[1]} r="4" fill="var(--cat-1)" />
      <circle cx={px(kr)[0]} cy={px(kr)[1]} r="4" fill="var(--cat-3)" />
      <text x={px(qr)[0] + 6} y={px(qr)[1] - 4} fill="var(--cat-1)" font-size="12" font-weight="700">q</text>
      <text x={px(kr)[0] + 6} y={px(kr)[1] - 4} fill="var(--cat-3)" font-size="12" font-weight="700">k</text>
    </svg>

    <div class="nums">
      <div class="row" style:--c="var(--cat-1)">
        <span class="nm">q</span>
        <span class="mono">[1, 0] turned by {m} × 0.5 = {hideQ ? '?' : (m * THETA).toFixed(1)} rad</span>
        <span class="mono res">→ [{hideQ ? '?' : f(qr[0])}, {hideQ ? '?' : f(qr[1])}]</span>
      </div>
      <div class="row" style:--c="var(--cat-3)">
        <span class="nm">k</span>
        <span class="mono">[0, 1] turned by {n} × 0.5 = {(n * THETA).toFixed(1)} rad</span>
        <span class="mono res">→ [{f(kr[0])}, {f(kr[1])}]</span>
      </div>
      <p class="note">The arc is the angle between q and k (in radians); the score is its cosine, so it only changes when m − n does.
        Without RoPE the score is always [1, 0]·[0, 1] = 0, wherever the words are.</p>
    </div>
  </div>

  {#snippet controls()}
    <label class="knob" style:--c="var(--cat-1)"><span>q’s position m = <b>{m}</b></span><input type="range" min="0" max="12" step="1" value={m} oninput={(e) => (m = +e.currentTarget.value)} /></label>
    <label class="knob" style:--c="var(--cat-3)"><span>k’s position n = <b>{n}</b></span><input type="range" min="0" max="12" step="1" value={n} oninput={(e) => (n = +e.currentTarget.value)} /></label>
    <span class="pair" role="group" aria-label="Move both positions">
      <button type="button" class="lab-btn primary" onclick={() => shift(1)} disabled={m >= 12 || n >= 12}>both +1</button>
      <button type="button" class="lab-btn" onclick={() => shift(-1)} disabled={m <= 0 || n <= 0}>both −1</button>
    </span>
  {/snippet}

  {#snippet readout()}
    score q·k = <b>{hideScore ? '?' : f(score)}</b> <span class="dim">· distance m − n = {m - n}</span>
  {/snippet}

  {#snippet legend()}
    <span class="lg"><i class="ln" style="border-color: var(--cat-1)"></i>q, turned by m × 0.5</span>
    <span class="lg"><i class="ln" style="border-color: var(--cat-3)"></i>k, turned by n × 0.5</span>
    <span class="lg"><i class="ln dash"></i>before turning</span>
  {/snippet}
</LabFrame>

<style>
  .wrap { display: grid; grid-template-columns: minmax(0, 220px) minmax(0, 1fr); gap: 1.2rem; align-items: center; }
  svg { width: 100%; height: auto; display: block; }
  .mono { font-family: var(--mono); }
  .nums { display: grid; gap: 0.6rem; min-width: 0; }
  .row { display: grid; grid-template-columns: 1.4rem minmax(0, 1fr); gap: 0.1rem 0.5rem; font-size: 0.85rem; padding-left: 0.5rem; border-left: 3px solid var(--c); }
  .row .nm { grid-row: span 2; font-weight: 700; color: var(--c); font-family: var(--mono); font-size: 1rem; }
  .row .res { font-variant-numeric: tabular-nums; }
  .note { margin: 0.2rem 0 0; font-size: 0.8rem; color: var(--dim); line-height: 1.5; }
  .knob { display: inline-flex; flex-wrap: wrap; gap: 0.2rem 0.5rem; align-items: center; font-family: var(--mono); font-size: 0.85rem; }
  .knob b { color: var(--c); }
  .knob input { width: 9rem; accent-color: var(--c); min-height: 2.1rem; }
  .pair { display: inline-flex; gap: 0.4rem; }
  .dim { color: var(--dim); }
  .lg { display: inline-flex; align-items: center; gap: 0.35rem; }
  .ln { display: inline-block; width: 1.1rem; border-top: 3px solid; }
  .ln.dash { border-top: 2px dashed var(--dim); }
  @media (max-width: 560px) {
    .wrap { grid-template-columns: minmax(0, 1fr); }
    svg { max-width: 240px; margin: 0 auto; }
    .knob { width: 100%; justify-content: space-between; }
    .knob input { flex: 1 1 10rem; min-height: 2.5rem; }
  }
</style>
