<script lang="ts">
  /**
   * Gate lab (level 19): one hidden unit of a SwiGLU FFN.
   * gate g = a row of W_gate · x, value u = a row of W_up · x, output = SiLU(g) × u.
   * The plot compares SiLU(z) = z·sigmoid(z) with ReLU.
   */
  import { onMount } from 'svelte'
  import LabFrame from './LabFrame.svelte'
  import { readable } from '@lib/readable'
  import { has, subscribe } from '@lib/progress'
  import { silu } from '@lib/modern'

  let { hide }: { hide?: string } = $props()
  let solved = $state(false)
  onMount(() => {
    if (!hide) return
    const sync = () => (solved = has(hide))
    sync()
    return subscribe(sync)
  })
  const masked = $derived(!!hide && !solved)

  let g = $state(-1)
  let u = $state(2)
  const s = $derived(silu(g))
  const hideS = $derived(masked && Math.abs(g - 1) < 1e-9)

  // plot area inside the viewBox, with room for tick labels
  const W = 280, H = 172, L = 22, T = 6, PW = 250, PH = 130, X0 = -4, X1 = 4, Y0 = -1, Y1 = 4
  const sx = (x: number) => L + ((x - X0) / (X1 - X0)) * PW
  const sy = (y: number) => T + PH - ((y - Y0) / (Y1 - Y0)) * PH
  const path = (fn: (x: number) => number) =>
    Array.from({ length: 81 }, (_, i) => X0 + (i / 80) * (X1 - X0)).map((x, i) => `${i ? 'L' : 'M'}${sx(x).toFixed(1)},${sy(fn(x)).toFixed(1)}`).join(' ')
  // the two bars below share one scale: |SiLU(4) × 3| ≈ 11.8 is the largest output
  const BMAX = 12
  const bw = (v: number) => `${(Math.min(Math.abs(v), BMAX) / BMAX) * 50}%`
  const out = $derived(s * u)
</script>

<LabFrame
  title="SwiGLU: a SiLU gate decides how much of the value passes"
  hint="Move the gate g and the value u. Watch the output bar: the gate scales the value."
  onreset={() => { g = -1; u = 2 }} resetDisabled={g === -1 && u === 2}
>
  <div class="wrap">
    <svg use:readable viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`SiLU and ReLU curves; the gate g = ${g.toFixed(1)} is marked`}>
      {#each [-4, -2, 0, 2, 4] as t}
        <line x1={sx(t)} y1={sy(Y0)} x2={sx(t)} y2={sy(Y1)} stroke="var(--line)" stroke-width="0.5" />
        <text x={sx(t)} y={T + PH + 13} class="tick" text-anchor="middle">{t}</text>
      {/each}
      {#each [0, 2, 4] as t}
        <line x1={sx(X0)} y1={sy(t)} x2={sx(X1)} y2={sy(t)} stroke="var(--line)" stroke-width="0.5" />
        <text x={L - 4} y={sy(t) + 3} class="tick" text-anchor="end">{t}</text>
      {/each}
      <line x1={sx(X0)} y1={sy(0)} x2={sx(X1)} y2={sy(0)} stroke="var(--dim)" stroke-width="0.8" />
      <line x1={sx(0)} y1={sy(Y0)} x2={sx(0)} y2={sy(Y1)} stroke="var(--dim)" stroke-width="0.8" />
      <text x={sx(X1)} y={H - 3} class="tick" text-anchor="end">gate g →</text>
      <path d={path((x) => Math.max(0, x))} fill="none" stroke="var(--dim)" stroke-width="1.4" stroke-dasharray="4 3" />
      <path d={path(silu)} fill="none" stroke="var(--fg)" stroke-width="2" />
      {#if !hideS}
        <line x1={sx(g)} y1={sy(Y0)} x2={sx(g)} y2={sy(Y1)} stroke="var(--accent)" stroke-width="1" stroke-dasharray="2 2" />
        <circle cx={sx(g)} cy={sy(s)} r="4.5" fill="var(--accent)" stroke="var(--card)" stroke-width="1.5" />
      {/if}
      <text x={sx(1.2)} y={sy(3.4)} fill="var(--dim)" font-size="10" text-anchor="end">ReLU</text>
      <text x={sx(-3.8)} y={sy(0.45)} fill="var(--fg)" font-size="10" font-weight="600">SiLU</text>
    </svg>

    <div class="flow">
      <div class="bars" role="img" aria-label="the value u and the output, as bars from zero">
        <div class="brow">
          <span class="bl">value u</span>
          <span class="track"><i class:neg={u < 0} style:width={bw(u)}></i></span>
          <span class="bv">{u.toFixed(1)}</span>
        </div>
        <div class="brow">
          <span class="bl">× SiLU(g)</span>
          <span class="mult">{hideS ? '?' : s.toFixed(4)}</span>
        </div>
        <div class="brow">
          <span class="bl"><b>output</b></span>
          <span class="track">{#if hideS}<span class="q">?</span>{:else}<i class:neg={out < 0} style:width={bw(out)}></i>{/if}</span>
          <span class="bv"><b>{hideS ? '?' : out.toFixed(4)}</b></span>
        </div>
      </div>
      <p class="note">Unlike ReLU, a slightly negative gate keeps a small part of the value, with its sign flipped.</p>
    </div>
  </div>

  {#snippet controls()}
    <label class="knob"><span>gate g = <b>{g.toFixed(1)}</b></span><input type="range" min="-4" max="4" step="0.5" value={g} oninput={(e) => (g = +e.currentTarget.value)} /></label>
    <label class="knob"><span>value u = <b>{u.toFixed(1)}</b></span><input type="range" min="-3" max="3" step="0.5" value={u} oninput={(e) => (u = +e.currentTarget.value)} /></label>
  {/snippet}

  {#snippet readout()}
    SiLU(g) = g × sigmoid(g) = <b>{hideS ? '?' : s.toFixed(4)}</b> · output = SiLU(g) × u = <b>{hideS ? '?' : out.toFixed(4)}</b>
  {/snippet}

  {#snippet legend()}
    <span class="lg"><i class="ln"></i>SiLU(z) = z · sigmoid(z)</span>
    <span class="lg"><i class="ln dash"></i>ReLU, for comparison</span>
    <span class="lg"><i class="dot"></i>your gate g</span>
    <span class="lg"><i class="sw" style="background: var(--pos)"></i>positive</span>
    <span class="lg"><i class="sw" style="background: var(--neg)"></i>negative</span>
  {/snippet}
</LabFrame>

<style>
  .wrap { display: grid; grid-template-columns: minmax(0, 300px) minmax(0, 1fr); gap: 1.2rem; align-items: center; }
  svg { width: 100%; height: auto; display: block; }
  .tick { font-size: 9px; fill: var(--dim); font-family: var(--mono); }
  .flow { display: grid; gap: 0.6rem; min-width: 0; }
  .bars { display: grid; gap: 0.35rem; }
  .brow { display: grid; grid-template-columns: 5.6rem minmax(0, 1fr) 4.6rem; gap: 0.5rem; align-items: center; font-family: var(--mono); font-size: 0.85rem; }
  .bl { color: var(--dim); }
  .bl b { color: var(--fg); }
  .bv { text-align: right; font-variant-numeric: tabular-nums; }
  .mult { grid-column: 2 / 4; color: var(--dim); font-variant-numeric: tabular-nums; }
  /* bars grow from the middle (zero): right for positive, left for negative */
  .track { position: relative; height: 0.9rem; background: var(--bg); border: 1px solid var(--line); border-radius: 3px; }
  .track::before { content: ''; position: absolute; left: 50%; top: -2px; bottom: -2px; border-left: 1px solid var(--dim); }
  .track i { position: absolute; left: 50%; top: 1px; bottom: 1px; background: var(--pos); border-radius: 0 2px 2px 0; transition: width 0.2s, left 0.2s; }
  .track i.neg { left: auto; right: 50%; background: var(--neg); border-radius: 2px 0 0 2px; }
  .q { position: absolute; inset: 0; display: grid; place-items: center; color: var(--warn); font-weight: 700; font-size: 0.8rem; line-height: 1; }
  .note { margin: 0; font-size: 0.8rem; color: var(--dim); line-height: 1.5; }
  .knob { display: inline-flex; flex-wrap: wrap; gap: 0.2rem 0.5rem; align-items: center; font-family: var(--mono); font-size: 0.85rem; }
  .knob b { color: var(--accent); }
  .knob input { width: 9rem; accent-color: var(--accent); min-height: 2.1rem; }
  .lg { display: inline-flex; align-items: center; gap: 0.35rem; }
  .ln { display: inline-block; width: 1.1rem; border-top: 2px solid var(--fg); }
  .ln.dash { border-top: 2px dashed var(--dim); }
  .dot { width: 0.6rem; height: 0.6rem; border-radius: 50%; background: var(--accent); display: inline-block; }
  .sw { width: 0.9rem; height: 0.6rem; border-radius: 2px; display: inline-block; }
  @media (prefers-reduced-motion: reduce) { .track i { transition: none; } }
  :global([data-motion='reduce']) .track i { transition: none; }
  @media (max-width: 560px) {
    .wrap { grid-template-columns: minmax(0, 1fr); }
    .knob { width: 100%; justify-content: space-between; }
    .knob input { flex: 1 1 10rem; min-height: 2.5rem; }
  }
</style>
