<script lang="ts">
  /**
   * Deep stacks, plain vs residual: how big the signal stays going up, and how big the gradient stays coming back down.
   * Computed live by stack() in lib/residuals.ts (the same numbers as demo.py).
   */
  import { stack } from '@lib/residuals'
  import { readable } from '@lib/readable'
  import LabFrame from './LabFrame.svelte'

  const D0 = 30, S0 = 0.8
  let depth = $state(D0)
  let scale = $state(S0)

  const plain = $derived(stack(depth, scale, false))
  const res = $derived(stack(depth, scale, true))
  const changed = $derived(depth !== D0 || scale !== S0)

  // log scale from 1e-6 to 1e2
  const LO = -6, HI = 2
  const W = 320, H = 170, PL = 40, PR = 52, PT = 10, PB = 26
  const xOf = (i: number) => PL + (i / Math.max(1, depth)) * (W - PL - PR)
  const yOf = (v: number) => {
    const l = Math.min(HI, Math.max(LO, Math.log10(Math.max(v, 1e-12))))
    return PT + ((HI - l) / (HI - LO)) * (H - PT - PB)
  }
  const line = (vs: number[]) => vs.map((v, i) => `${xOf(i).toFixed(1)},${yOf(v).toFixed(1)}`).join(' ')
  const ticks = [2, 0, -2, -4, -6]
  const tickLabel = (e: number) => (e === 0 ? '1' : e === 2 ? '100' : `1e${e}`)
  const fmt = (v: number) => (v >= 0.01 && v < 1000 ? v.toFixed(v < 1 ? 3 : 2) : v.toExponential(1))
  const ratio = (g: number[]) => g[0] / g[g.length - 1]
  // end labels: keep at least 13 units apart so "plain" and "residual" never overlap
  function ends(pv: number[], rv: number[]) {
    let a = yOf(pv.at(-1)!), b = yOf(rv.at(-1)!)
    const gap = 13
    if (Math.abs(a - b) < gap) {
      const mid = (a + b) / 2
      if (a <= b) { a = mid - gap / 2; b = mid + gap / 2 } else { a = mid + gap / 2; b = mid - gap / 2 }
    }
    return { plain: a + 3, res: b + 3 }
  }
</script>

<LabFrame
  title={`Stack ${depth} tanh layers: how much of the signal and the gradient is left?`}
  hint="Drag depth and weight scale. Compare the plain stack with the residual stack."
  onreset={() => { depth = D0; scale = S0 }}
  resetDisabled={!changed}
>
  <div class="panels">
    {#each [{ key: 'act', name: 'Signal going up', sub: 'std of each layer’s output' }, { key: 'grad', name: 'Gradient coming down', sub: 'std of the gradient reaching each layer' }] as p}
      {@const pv = p.key === 'act' ? plain.act : plain.grad}
      {@const rv = p.key === 'act' ? res.act : res.grad}
      {@const ys = ends(pv, rv)}
      <figure>
        <figcaption><b>{p.name}</b> <span>{p.sub}</span></figcaption>
        <svg use:readable viewBox="0 0 {W} {H}" role="img" aria-label="{p.name}: plain stack vs residual stack, log scale">
          {#each ticks as e}
            <line x1={PL} x2={W - PR} y1={yOf(10 ** e)} y2={yOf(10 ** e)} class="grid" />
            <text x={PL - 4} y={yOf(10 ** e) + 3} class="tick end">{tickLabel(e)}</text>
          {/each}
          <line x1={PL} x2={W - PR} y1={yOf(1)} y2={yOf(1)} class="one" />
          <polyline points={line(pv)} class="plain" />
          <polyline points={line(rv)} class="res" />
          <!-- label each line at its end, so no color lookup is needed -->
          <text x={W - PR + 4} y={ys.plain} class="end-lbl plain-t">plain</text>
          <text x={W - PR + 4} y={ys.res} class="end-lbl res-t">residual</text>
          <text x={PL} y={H - 6} class="tick">0 (input)</text>
          <text x={W - PR} y={H - 6} class="tick end">{depth} (top)</text>
        </svg>
      </figure>
    {/each}
  </div>

  {#snippet controls()}
    <label class="knob">depth <input type="range" min="1" max="50" bind:value={depth} aria-label="depth" /> <b>{depth}</b></label>
    <label class="knob">weight scale <input type="range" min="0.5" max="1.5" step="0.1" bind:value={scale} aria-label="weight scale" /> <b>{scale.toFixed(1)}/√16</b></label>
  {/snippet}

  {#snippet readout()}
    gradient at layer 0 ÷ gradient at the top: plain <b class="p">{fmt(ratio(plain.grad))}</b>, residual <b class="r">{fmt(ratio(res.grad))}</b>
  {/snippet}

  {#snippet legend()}
    <span><i class="sw plain"></i>plain: h ← tanh(h @ W)</span>
    <span><i class="sw res"></i>residual: h ← h + tanh(h @ W)</span>
    <span>log scale; the dashed line is 1</span>
  {/snippet}
</LabFrame>

<style>
  .panels { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.8rem; }
  @media (max-width: 600px) { .panels { grid-template-columns: minmax(0, 1fr); } }
  figure { margin: 0; min-width: 0; }
  figcaption { font-size: 0.85rem; margin-bottom: 0.2rem; }
  figcaption span { color: var(--dim); }
  svg { width: 100%; height: auto; display: block; background: var(--bg); border: 1px solid var(--line); border-radius: 6px; }
  .grid { stroke: var(--line); stroke-width: 0.6; }
  .one { stroke: var(--dim); stroke-dasharray: 3 3; stroke-width: 0.8; }
  .tick { font-size: 10px; fill: var(--dim); font-family: var(--mono); }
  .end { text-anchor: end; }
  .end-lbl { font-size: 10px; font-family: var(--mono); font-weight: 600; }
  polyline { fill: none; stroke-width: 2; stroke-linejoin: round; }
  .plain { stroke: var(--cat-3); }
  .res { stroke: var(--cat-1); }
  .plain-t { fill: var(--cat-3); }
  .res-t { fill: var(--cat-1); }
  .sw { display: inline-block; width: 1rem; height: 3px; vertical-align: 0.25em; margin-right: 0.35rem; }
  .sw.plain { background: var(--cat-3); }
  .sw.res { background: var(--cat-1); }
  .knob { display: inline-flex; gap: 0.4rem; align-items: center; font-size: 0.88rem; color: var(--dim); }
  .knob b { color: var(--fg); font-family: var(--mono); font-weight: 600; }
  input[type='range'] { width: 7rem; min-height: 2rem; accent-color: var(--accent); }
  .p { color: var(--cat-3); }
  .r { color: var(--cat-1); }
</style>
