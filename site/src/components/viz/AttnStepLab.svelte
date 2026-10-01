<script lang="ts">
  /**
   * One attention step, as the decoder of level N5 takes it: drag the decoder state s and the three encoder states.
   * scores = E @ s, weights = softmax(scores), context = weights @ E. The context arrow is the weighted average.
   * Values that answer a question on the page stay "?" until it is solved (props `hide`).
   */
  import { onMount } from 'svelte'
  import { has, subscribe } from '@lib/progress'
  import { attendStep, argmax } from '@lib/seq2seq'
  import { readable } from '@lib/readable'
  import LabFrame from './LabFrame.svelte'

  let { hide = {} }: { hide?: { score?: string; weight?: string; ctx?: string } } = $props()
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
  const locked = (k: 'score' | 'weight' | 'ctx') => !!hide[k] && !solved[hide[k]!]

  const E0 = [[1, 0], [0, 1], [0, -1]]
  const S0 = [2, 0]
  let E = $state(E0.map((r) => [...r]))
  let s = $state([...S0])
  const r = $derived(attendStep(E, s))
  const changed = $derived(JSON.stringify(E) !== JSON.stringify(E0) || JSON.stringify(s) !== JSON.stringify(S0))
  const top = $derived(argmax(r.weights))

  function reset() {
    E = E0.map((row) => [...row])
    s = [...S0]
  }

  // plane: −3 … 3 on both axes
  const D = 3
  const px = (x: number) => 50 + (x / D) * 46
  const py = (y: number) => 50 - (y / D) * 46
  const snap = (v: number) => Math.max(-D, Math.min(D, Math.round(v * 2) / 2))
  let svg: SVGSVGElement
  let drag = $state<number | null>(null) // 0..2 encoder states, 3 = s
  function set(k: number, v: number[]) {
    if (k === 3) s = v
    else E[k] = v
  }
  const get = (k: number) => (k === 3 ? s : E[k])
  function grab(k: number, e: PointerEvent) {
    drag = k
    svg.setPointerCapture(e.pointerId)
  }
  function move(e: PointerEvent) {
    if (drag === null) return
    const b = svg.getBoundingClientRect()
    const x = snap((((e.clientX - b.left) / b.width) * 100 - 50) / 46 * D)
    const y = snap(-(((e.clientY - b.top) / b.height) * 100 - 50) / 46 * D)
    set(drag, [x, y])
  }
  // keyboard: arrow keys move the focused point by 0.5 (Shift: 1)
  function nudge(k: number, e: KeyboardEvent) {
    const d = ({ ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, 1], ArrowDown: [0, -1] } as Record<string, number[]>)[e.key]
    if (!d) return
    e.preventDefault()
    const step = e.shiftKey ? 1 : 0.5
    const v = get(k)
    set(k, [snap(v[0] + d[0] * step), snap(v[1] + d[1] * step)])
  }
  const f2 = (v: number) => (Math.abs(v) < 0.005 ? '0' : v.toFixed(2))
  const f1 = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(1))
  const names = ['h₀', 'h₁', 'h₂']
  const uid = Math.random().toString(36).slice(2, 8)
</script>

<LabFrame
  title="One attention step: the decoder state s looks at the encoder states"
  hint="Drag s or h₀, h₁, h₂ (or focus one and use the arrow keys). Thicker arrows get more weight."
  onreset={reset}
  resetDisabled={!changed}
>
  <div class="row">
    <svg
      bind:this={svg} use:readable viewBox="0 0 100 100" class="plane" role="group"
      aria-label="Encoder states h₀, h₁, h₂, the decoder state s, and the context vector"
      onpointermove={move} onpointerup={() => (drag = null)} onpointercancel={() => (drag = null)}
    >
      <defs>
        <marker id="ah-fg-{uid}" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="4" markerHeight="4" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="m-fg" /></marker>
      </defs>
      {#each [-2, -1, 1, 2] as g}
        <line x1={px(g)} x2={px(g)} y1="4" y2="96" class="grid" />
        <line y1={py(g)} y2={py(g)} x1="4" x2="96" class="grid" />
      {/each}
      <line x1="4" x2="96" y1="50" y2="50" class="axis" />
      <line y1="4" y2="96" x1="50" x2="50" class="axis" />
      <text x="95" y="48" class="tick" text-anchor="end">3</text>
      <text x="52" y="8" class="tick">3</text>

      {#each E as e, i}
        <line x1="50" y1="50" x2={px(e[0])} y2={py(e[1])} class="enc" class:top={i === top}
          style="stroke-width:{0.6 + r.weights[i] * 2.4}" />
      {/each}
      <line x1="50" y1="50" x2={px(s[0])} y2={py(s[1])} class="dec" />
      {#if !locked('ctx')}
        <line x1="50" y1="50" x2={px(r.ctx[0])} y2={py(r.ctx[1])} class="ctx" marker-end="url(#ah-fg-{uid})" />
        <text x={px(r.ctx[0]) + 3} y={py(r.ctx[1]) + 7} class="lbl ctx-l">context</text>
      {/if}

      {#each E as e, i}
        <g class="h" role="slider" tabindex="0" aria-label={`${names[i]}: drag, or use the arrow keys`}
          aria-valuenow={e[0]} aria-valuetext={`[${f1(e[0])}, ${f1(e[1])}]`}
          onpointerdown={(ev) => grab(i, ev)} onkeydown={(ev) => nudge(i, ev)}>
          <circle cx={px(e[0])} cy={py(e[1])} r="8" class="hit" />
          <circle cx={px(e[0])} cy={py(e[1])} r={drag === i ? 4.2 : 3.4} class="vis enc-h" class:top={i === top} />
        </g>
        <text x={px(e[0]) + 4} y={py(e[1]) - 4} class="lbl" class:strong={i === top}>{names[i]}</text>
      {/each}
      <g class="h" role="slider" tabindex="0" aria-label="s, the decoder state: drag, or use the arrow keys"
        aria-valuenow={s[0]} aria-valuetext={`[${f1(s[0])}, ${f1(s[1])}]`}
        onpointerdown={(ev) => grab(3, ev)} onkeydown={(ev) => nudge(3, ev)}>
        <circle cx={px(s[0])} cy={py(s[1])} r="8" class="hit" />
        <circle cx={px(s[0])} cy={py(s[1])} r={drag === 3 ? 4.4 : 3.6} class="vis dec-h" />
      </g>
      <text x={px(s[0]) + 4} y={py(s[1]) - 4} class="lbl dec-l">s</text>
    </svg>

    <div class="nums">
      <table>
        <thead><tr><th scope="col">state</th><th scope="col">h</th><th scope="col">score h·s</th><th scope="col">weight</th></tr></thead>
        <tbody>
          {#each E as e, i}
            <tr class:top={i === top && !locked('weight')}>
              <th scope="row">{names[i]}</th>
              <td>[{f1(e[0])}, {f1(e[1])}]</td>
              <td>{#if locked('score')}<span class="q">?</span>{:else}{f2(r.scores[i])}{/if}</td>
              <td class="wcell">
                {#if locked('weight')}<span class="q">?</span>{:else}
                  <span class="bar"><i style="width:{r.weights[i] * 100}%"></i></span>{f2(r.weights[i])}
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
      <p class="formula">s = [{f1(s[0])}, {f1(s[1])}]</p>
      <p class="formula">context = weights @ E =
        {#if locked('ctx')}<span class="q">?</span>{:else}<b>[{f2(r.ctx[0])}, {f2(r.ctx[1])}]</b>{/if}</p>
    </div>
  </div>

  {#snippet readout()}
    {#if locked('weight')}
      <span class="idle">Drag s or the encoder states. Thicker arrows get more weight.</span>
    {:else}
      s looks at {names[top]} with weight {f2(r.weights[top])}. The context is the weighted average of h₀, h₁, h₂.
    {/if}
  {/snippet}

  {#snippet legend()}
    <span><i class="ln acc"></i>s, the decoder state</span>
    <span><i class="ln enc-sw"></i>encoder states (thicker = more weight)</span>
    <span><i class="ln ctx-sw"></i>context, the weighted average</span>
  {/snippet}
</LabFrame>

<style>
  .row { display: grid; grid-template-columns: minmax(0, 18rem) minmax(0, 1fr); gap: 1rem 1.2rem; align-items: start; }
  @media (max-width: 600px) { .row { grid-template-columns: minmax(0, 1fr); } }
  .plane { width: 100%; max-width: 18rem; aspect-ratio: 1; display: block; background: var(--bg); border: 1px solid var(--line); border-radius: 6px; touch-action: none; user-select: none; -webkit-user-select: none; }
  .grid { stroke: var(--line); stroke-width: 0.3; }
  .axis { stroke: var(--dim); stroke-width: 0.4; }
  .tick { font-size: 3.6px; fill: var(--dim); font-family: var(--mono); }
  .enc { stroke: var(--dim); }
  .enc.top { stroke: var(--fg); }
  .dec { stroke: var(--accent); stroke-width: 1.8; }
  .ctx { stroke: var(--fg); stroke-width: 1.3; stroke-dasharray: 2 1.5; }
  .m-fg { fill: var(--fg); }
  .h { cursor: grab; outline: none; touch-action: none; }
  .hit { fill: transparent; }
  .vis { stroke: var(--bg); stroke-width: 0.8; transition: r 0.12s; }
  .h:focus-visible .vis { stroke: var(--fg); stroke-width: 1.2; }
  .enc-h { fill: var(--dim); }
  .enc-h.top { fill: var(--fg); }
  .dec-h { fill: var(--accent); }
  .lbl { font-size: 5px; font-family: var(--mono); fill: var(--dim); pointer-events: none; paint-order: stroke; stroke: var(--bg); stroke-width: 1.2px; }
  .lbl.strong { fill: var(--fg); font-weight: 700; }
  .dec-l { fill: var(--accent); font-weight: 700; }
  .ctx-l { fill: var(--fg); }

  .nums { min-width: 0; }
  table { border-collapse: collapse; font-family: var(--mono); font-size: 0.85rem; width: auto; }
  th, td { border: 1px solid var(--line); padding: 0.3rem 0.5rem; text-align: right; white-space: nowrap; }
  thead th { color: var(--dim); font-weight: 400; font-family: system-ui, -apple-system, sans-serif; font-size: 0.8rem; }
  tbody th { color: var(--fg); font-weight: 400; }
  tr.top td, tr.top th { background: var(--highlight); }
  .wcell { min-width: 6.5rem; }
  .bar { display: inline-block; width: 2.6rem; height: 0.45rem; margin-right: 0.4rem; background: var(--bg); border: 1px solid var(--line); border-radius: 3px; vertical-align: middle; overflow: hidden; }
  .bar i { display: block; height: 100%; background: var(--accent); transition: width 0.2s; }
  .q { color: var(--warn); font-weight: 700; }
  .formula { font-family: var(--mono); font-size: 0.85rem; margin: 0.5rem 0 0; }
  .formula + .formula { margin-top: 0.2rem; }
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
  .ln { display: inline-block; width: 1rem; height: 0; border-top: 2px solid; vertical-align: middle; margin-right: 0.35rem; }
  .ln.acc { border-color: var(--accent); }
  .ln.enc-sw { border-color: var(--dim); }
  .ln.ctx-sw { border-top: 2px dashed var(--fg); }
  @media (max-width: 400px) { th, td { padding: 0.3rem 0.35rem; } .wcell { min-width: 0; } }
  @media (prefers-reduced-motion: reduce) { .bar i, .vis { transition: none; } }
</style>
