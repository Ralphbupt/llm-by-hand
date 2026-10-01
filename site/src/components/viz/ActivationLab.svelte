<script lang="ts">
  /**
   * Activation lab: sigmoid, tanh, ReLU and GELU side by side, each with its slope (derivative).
   * Drag on any panel (or the slider) to move x; every panel reads f(x) and f'(x) at the same x.
   * Below: the slope multiplied through n layers, which is what a gradient meets on its way back.
   */
  import { onMount } from 'svelte'
  import { has, subscribe } from '@lib/progress'
  import { ACT, type ActName } from '@lib/foundations'
  import LabFrame from './LabFrame.svelte'
  import { readable } from '@lib/readable'

  // GELU's numbers stay "?" until the GELU question is solved
  let { hide = {} }: { hide?: { gelu?: string } } = $props()
  let solved = $state(false)
  onMount(() => {
    if (!hide.gelu) return
    const sync = () => (solved = has(hide.gelu!))
    sync()
    return subscribe(sync)
  })
  const masked = (k: ActName) => k === 'gelu' && !!hide.gelu && !solved

  const X0 = 1
  const N0 = 5
  let x = $state(X0)
  let n = $state(N0)
  const NAMES: ActName[] = ['sigmoid', 'tanh', 'relu', 'gelu']

  // plot box: x in [-4, 4], y in [-1.2, 2.2] for f; slopes share the axis
  const W = 200, H = 130, XL = -4, XR = 4, YB = -1.2, YT = 2.2
  const px = (v: number) => ((v - XL) / (XR - XL)) * W
  const py = (v: number) => H - ((v - YB) / (YT - YB)) * H
  const path = (fn: (v: number) => number) => {
    // leave the plot instead of drawing a fake flat line where the curve goes off the top
    const pts: string[] = []
    let pen = false
    for (let i = 0; i <= 160; i++) {
      const v = XL + ((XR - XL) * i) / 160
      const f = fn(v)
      if (f > YT || f < YB) { pen = false; continue }
      pts.push(`${pen ? 'L' : 'M'}${px(v).toFixed(1)},${py(f).toFixed(1)}`)
      pen = true
    }
    return pts.join('')
  }
  const curves = NAMES.map((k) => ({ k, f: path(ACT[k].f), df: path(ACT[k].df) }))

  const fmt = (v: number) => (Math.abs(v) < 1e-4 && v !== 0 ? v.toExponential(2) : v.toFixed(4))

  let dragging = false
  function setFromEvent(e: PointerEvent) {
    const svg = e.currentTarget as SVGSVGElement
    const r = svg.getBoundingClientRect()
    const v = XL + ((e.clientX - r.left) / r.width) * (XR - XL)
    x = Math.round(Math.max(XL, Math.min(XR, v)) * 10) / 10
  }
  const down = (e: PointerEvent) => {
    dragging = true
    ;(e.currentTarget as Element).setPointerCapture(e.pointerId)
    setFromEvent(e)
  }
  const move = (e: PointerEvent) => dragging && setFromEvent(e)
  const up = () => (dragging = false)
  // arrow keys move x by 0.1 (Shift: 1)
  function key(e: KeyboardEvent) {
    const d = e.key === 'ArrowLeft' || e.key === 'ArrowDown' ? -1 : e.key === 'ArrowRight' || e.key === 'ArrowUp' ? 1 : 0
    if (!d) return
    e.preventDefault()
    x = Math.round(Math.max(XL, Math.min(XR, x + d * (e.shiftKey ? 1 : 0.1))) * 10) / 10
  }

  const changed = $derived(x !== X0 || n !== N0)
  function reset() {
    x = X0
    n = N0
  }
</script>

<LabFrame
  title="Four activation functions and their slopes"
  hint="Drag across any panel, or use the arrow keys, to move x. All four panels read the same x."
  onreset={reset}
  resetDisabled={!changed}
>
  <div class="panels">
    {#each curves as c}
      <div class="panel">
        <div class="ttl">{ACT[c.k].label}</div>
        <svg viewBox="0 0 {W} {H}" use:readable role="slider" aria-label="{ACT[c.k].label}: drag or use the arrow keys to move x" aria-valuenow={x} aria-valuemin={XL} aria-valuemax={XR} tabindex="0"
          onpointerdown={down} onpointermove={move} onpointerup={up} onpointercancel={up} onkeydown={key}>
          <line x1="0" x2={W} y1={py(0)} y2={py(0)} class="axis" />
          <line x1={px(0)} x2={px(0)} y1="0" y2={H} class="axis" />
          <line x1="0" x2={W} y1={py(1)} y2={py(1)} class="grid" />
          <text x={px(-4) + 2} y={py(0) - 3} class="tick">−4</text>
          <text x={px(4) - 2} y={py(0) - 3} class="tick" text-anchor="end">4</text>
          <text x={px(0) + 3} y={py(1) - 3} class="tick">1</text>
          <path d={c.df} class="df" />
          <path d={c.f} class="f" />
          <line x1={px(x)} x2={px(x)} y1="0" y2={H} class="mark" />
          {#if ACT[c.k].f(x) <= YT && ACT[c.k].f(x) >= YB}<circle cx={px(x)} cy={py(ACT[c.k].f(x))} r="3.5" class="dotf" />{/if}
          {#if ACT[c.k].df(x) <= YT && ACT[c.k].df(x) >= YB}<circle cx={px(x)} cy={py(ACT[c.k].df(x))} r="3.5" class="dotdf" />{/if}
        </svg>
        <div class="read">
          <span class="fl">f({x.toFixed(1)}) = {masked(c.k) ? '?' : fmt(ACT[c.k].f(x))}</span>
          <span class="dl">f′({x.toFixed(1)}) = {masked(c.k) ? '?' : fmt(ACT[c.k].df(x))}</span>
        </div>
      </div>
    {/each}
  </div>

  <div class="depth">
    <p class="dim">If every layer sits at this x, the gradient that reaches the first layer is multiplied by f′(x) once per layer: f′(x)<sup>n</sup>.</p>
    <div class="scroll">
      <table>
        <thead><tr><th></th>{#each NAMES as k}<th>{ACT[k].label}</th>{/each}</tr></thead>
        <tbody>
          <tr><td>f′({x.toFixed(1)})</td>{#each NAMES as k}<td>{masked(k) ? '?' : fmt(ACT[k].df(x))}</td>{/each}</tr>
          <tr><td>f′<sup>{n}</sup></td>{#each NAMES as k}<td class:tiny={Math.abs(ACT[k].df(x) ** n) < 1e-3}>{masked(k) ? '?' : fmt(ACT[k].df(x) ** n)}</td>{/each}</tr>
        </tbody>
      </table>
    </div>
  </div>

  {#snippet controls()}
    <label class="knob">x <input type="range" min="-4" max="4" step="0.1" bind:value={x} aria-label="input x" /> <b>{x.toFixed(1)}</b></label>
    <label class="knob">layers n <input type="range" min="1" max="20" step="1" bind:value={n} aria-label="number of layers" /> <b>{n}</b></label>
  {/snippet}

  {#snippet legend()}
    <span class="key"><i class="k-f"></i>f(x)</span>
    <span class="key"><i class="k-df"></i>slope f′(x)</span>
    <span class="key"><i class="k-one"></i>y = 1</span>
    <span class="key"><i class="k-tiny"></i>a gradient below 0.001: it has almost vanished</span>
  {/snippet}
</LabFrame>

<style>
  .panels { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.8rem; }
  @media (max-width: 560px) { .panels { grid-template-columns: minmax(0, 1fr); } }
  .panel { border: 1px solid var(--line); border-radius: 6px; padding: 0.4rem 0.5rem; background: var(--bg); min-width: 0; }
  .ttl { font-family: var(--mono); font-size: 0.85rem; font-weight: 700; }
  svg { width: 100%; height: auto; display: block; touch-action: pan-y; cursor: ew-resize; border-radius: 4px; }
  svg:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .axis { stroke: var(--dim); stroke-width: 0.8; opacity: 0.6; }
  .grid { stroke: var(--line); stroke-width: 0.8; stroke-dasharray: 2 3; }
  .f { fill: none; stroke: var(--accent); stroke-width: 2; }
  .df { fill: none; stroke: var(--fg); stroke-opacity: 0.75; stroke-width: 1.6; stroke-dasharray: 4 3; }
  .mark { stroke: var(--fg); stroke-width: 0.8; opacity: 0.4; }
  .dotf { fill: var(--accent); }
  .dotdf { fill: var(--fg); }
  .tick { fill: var(--dim); font-size: 8px; font-family: var(--mono); }
  .read { display: flex; flex-wrap: wrap; gap: 0.2rem 0.8rem; font-family: var(--mono); font-size: 0.82rem; }
  .fl { color: var(--accent); }
  .dl { color: var(--fg); }
  .depth { margin-top: 0.9rem; border-top: 1px solid var(--line); padding-top: 0.7rem; }
  .dim { color: var(--dim); font-size: 0.85rem; margin: 0 0 0.4rem; }
  .scroll { overflow-x: auto; }
  table { font-family: var(--mono); font-size: 0.82rem; width: auto; }
  td, th { text-align: right; padding: 0.2rem 0.5rem; }
  th { color: var(--dim); font-weight: 400; }
  td.tiny { color: var(--warn); }
  .knob { display: inline-flex; align-items: center; gap: 0.45rem; font-size: 0.88rem; color: var(--dim); margin-right: 0.8rem; }
  .knob input { width: min(11rem, 40vw); accent-color: var(--accent); }
  .knob b { color: var(--fg); font-family: var(--mono); min-width: 2.2em; }
  .key { display: inline-flex; align-items: center; gap: 0.4rem; }
  .key i { flex: none; display: inline-block; width: 1rem; }
  .k-f { border-top: 2px solid var(--accent); }
  .k-df { border-top: 2px dashed var(--fg); }
  .k-one { border-top: 1px dashed var(--line); }
  .k-tiny { height: 0.8rem; width: 0.8rem !important; background: var(--warn); border-radius: 2px; }
</style>
