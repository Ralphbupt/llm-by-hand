<script lang="ts">
  /**
   * Vector canvas: drag an arrow's tip to change its numbers; the source of every downstream table.
   * Works with mouse, touch (a 44px invisible grab area around each tip) and keyboard (arrow keys move one step,
   * Shift + arrow two steps). Page scroll still works when you start a swipe away from a tip.
   */
  import { readable } from '@lib/readable'
  type Props = {
    value: number[][]           // n × 2
    labels?: string[]
    hi?: number[]               // 高亮哪几个
    domain?: [number, number]
    step?: number
    onchange?: (v: number[][]) => void
  }
  let {
    value, labels, hi = [], domain = [-1.5, 6], step = 0.5, onchange,
  }: Props = $props()

  let svg: SVGSVGElement
  let dragging = $state<number | null>(null)

  const [d0, d1] = domain
  const sx = (x: number) => ((x - d0) / (d1 - d0)) * 100
  const sy = (y: number) => 100 - ((y - d0) / (d1 - d0)) * 100
  const snap = (v: number) => Math.min(d1, Math.max(d0, Math.round(v / step) * step))

  function move(e: PointerEvent) {
    if (dragging === null) return
    const r = svg.getBoundingClientRect()
    const x = snap(d0 + ((e.clientX - r.left) / r.width) * (d1 - d0))
    const y = snap(d1 - ((e.clientY - r.top) / r.height) * (d1 - d0))
    const next = value.map((v) => [...v])
    next[dragging] = [x, y]
    onchange?.(next)
  }

  function grab(i: number, e: PointerEvent) {
    dragging = i
    svg.setPointerCapture(e.pointerId)
  }

  function key(i: number, e: KeyboardEvent) {
    const d = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, 1], ArrowDown: [0, -1] }[e.key]
    if (!d) return
    e.preventDefault()
    const k = (e.shiftKey ? 2 : 1) * step
    const next = value.map((v) => [...v])
    next[i] = [snap(next[i][0] + d[0] * k), snap(next[i][1] + d[1] * k)]
    onchange?.(next)
  }
  // categorical colors from the site palette (--cat-1 … --cat-5)
  const cat = (i: number) => `var(--cat-${(i % 5) + 1})`

  const ticks = [0, 1, 2, 3, 4, 5]
</script>

<svg
  bind:this={svg}
  use:readable
  viewBox="0 0 100 100"
  onpointermove={move}
  onpointerup={() => (dragging = null)}
  onpointercancel={() => (dragging = null)}
  role="application"
  aria-label="Draggable vector canvas"
>
  <!-- 网格 -->
  {#each ticks as t}
    <line x1={sx(t)} y1="0" x2={sx(t)} y2="100" class="grid" />
    <line x1="0" y1={sy(t)} x2="100" y2={sy(t)} class="grid" />
  {/each}
  <line x1={sx(d0)} y1={sy(0)} x2={sx(d1)} y2={sy(0)} class="axis" />
  <line x1={sx(0)} y1={sy(d0)} x2={sx(0)} y2={sy(d1)} class="axis" />

  {#each value as v, i}
    {@const on = hi.length === 0 || hi.includes(i)}
    <line
      x1={sx(0)} y1={sy(0)} x2={sx(v[0])} y2={sy(v[1])}
      class="vec" class:off={!on} style="--c: {cat(i)}"
    />
    <circle cx={sx(v[0])} cy={sy(v[1])} r="3.2" class="dot" class:off={!on} class:drag={dragging === i} style="--c: {cat(i)}" />
    <!-- invisible grab area, ~44px on a phone-width canvas -->
    <circle
      cx={sx(v[0])} cy={sy(v[1])} r="8"
      class="hit"
      onpointerdown={(e) => grab(i, e)}
      onkeydown={(e) => key(i, e)}
      role="slider" tabindex="0"
      aria-label={`${labels?.[i] ?? `vector ${i}`}: arrow keys move it`}
      aria-valuetext={`[${v[0]}, ${v[1]}]`}
      aria-valuenow={v[0]}
    />
    <text x={sx(v[0]) + 4} y={sy(v[1]) - 3} class="tag" class:off={!on}>
      {labels?.[i] ?? i}
    </text>
  {/each}
</svg>

<p class="tip">Drag a dot, or focus it and use the arrow keys (steps of {step}).</p>

<style>
  svg {
    width: 100%; max-width: 300px; aspect-ratio: 1; touch-action: pan-y;
    border: 1px solid var(--line); border-radius: 6px; background: var(--bg);
  }
  .grid { stroke: var(--line); stroke-width: 0.3; }
  .axis { stroke: var(--dim); stroke-width: 0.6; }
  .vec { stroke: var(--c); stroke-width: 1.4; stroke-linecap: round; }
  .dot { fill: var(--c); pointer-events: none; }
  .dot.drag { r: 4.2; }
  .hit { fill: transparent; cursor: grab; touch-action: none; outline: none; }
  .hit:active { cursor: grabbing; }
  .hit:focus-visible { stroke: var(--accent); stroke-width: 0.8; stroke-dasharray: 1.5 1.5; }
  .tag { font-size: 4px; fill: var(--dim); font-family: var(--mono); }
  .off { opacity: 0.2; }
  .tip { margin: 0.3rem 0 0; font-size: 0.75rem; color: var(--dim); }
</style>
