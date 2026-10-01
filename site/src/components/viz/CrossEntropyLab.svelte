<script lang="ts">
  /**
   * Cross-entropy lab: three classes, drag any score, pick the correct answer.
   * loss = -log(p of the correct class). The curve on the right is -log p for p in (0, 1].
   */
  import { onMount } from 'svelte'
  import { has, subscribe } from '@lib/progress'
  import LabFrame from './LabFrame.svelte'
  import { readable } from '@lib/readable'

  // A value that a question on the page asks for stays "?" until that question is solved.
  let { hide = {} }: { hide?: Record<string, string | undefined> } = $props()
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
  const locked = (k: string) => !!hide[k] && !solved[hide[k]!]

  const NAMES = ['cat', 'dog', 'car']
  let scores = $state([2.0, 1.0, 0.1])
  let target = $state(0)

  const probs = $derived.by(() => {
    const m = Math.max(...scores)
    const e = scores.map((v) => Math.exp(v - m))
    const s = e.reduce((a, b) => a + b, 0)
    return e.map((v) => v / s)
  })
  const p = $derived(probs[target])
  const loss = $derived(-Math.log(p))

  // curve: x = p in [0.01, 1], y = -log p clipped at 5
  const W = 200, H = 120, YMAX = 5
  const px = (q: number) => q * W
  const py = (y: number) => H - (Math.min(y, YMAX) / YMAX) * H
  const curve = Array.from({ length: 100 }, (_, i) => {
    const q = 0.01 + (i / 99) * 0.99
    return `${px(q).toFixed(1)},${py(-Math.log(q)).toFixed(1)}`
  }).join(' ')

  function setScore(i: number, v: number) {
    const next = [...scores]
    next[i] = v
    scores = next
  }
</script>

<LabFrame
  title="Cross-entropy: the surprise at the correct answer"
  hint="Pick the correct answer with the round buttons. Drag the sliders to change the scores."
  onreset={() => { scores = [2.0, 1.0, 0.1]; target = 0 }}
  resetDisabled={target === 0 && scores[0] === 2 && scores[1] === 1 && scores[2] === 0.1}
>
  <div class="cols">
    <div class="left">
      <div class="row head"><span>correct?</span><span>score</span><span></span><span>p</span></div>
      {#each NAMES as n, i}
        <div class="row" class:tgt={target === i}>
          <label class="radio"><input type="radio" name="ce-target" checked={target === i} onchange={() => (target = i)} /> {n}</label>
          <input type="range" min="-3" max="5" step="0.1" value={scores[i]}
            aria-label={`score for ${n}`}
            oninput={(e) => setScore(i, +(e.currentTarget as HTMLInputElement).value)} />
          <span class="num">{scores[i].toFixed(1)}</span>
          <span class="bar"><i class:t={target === i} style="width:{probs[i] * 100}%"></i><em>{probs[i].toFixed(3)}</em></span>
        </div>
      {/each}
      {#if locked('loss')}<p class="note">The loss number appears once you answer the two questions below.</p>{/if}
    </div>
    <svg viewBox="-30 -12 244 170" class="plot" use:readable aria-label="The loss −log p as a curve over p, with the current p marked">
      <line x1="0" y1={H} x2={W} y2={H} class="axis" />
      <line x1="0" y1="0" x2="0" y2={H} class="axis" />
      {#if !locked('loss')}
        {#each [0, 1, 2, 3, 4, 5] as y}
          <line x1="0" x2={W} y1={py(y)} y2={py(y)} class="grid" />
          <text x="-6" y={py(y) + 3} class="tick" text-anchor="end">{y}</text>
        {/each}
      {/if}
      <text x="5" y="2" class="tick name" text-anchor="start">loss</text>
      {#each [0, 0.5, 1] as q}
        <text x={px(q)} y={H + 13} class="tick" text-anchor="middle">{q}</text>
      {/each}
      <polyline points={curve} class="curve" />
      <line x1={px(p)} x2={px(p)} y1={py(loss)} y2={H} class="guide" />
      <line x1="0" x2={px(p)} y1={py(loss)} y2={py(loss)} class="guide" />
      <circle cx={px(p)} cy={py(loss)} r="4.5" class="dot" />
      {#if !locked('loss')}<text x={Math.min(px(p) + 7, W - 4)} y={py(loss) - 7} class="tick val" text-anchor={px(p) > W - 60 ? 'end' : 'start'}>loss {loss.toFixed(2)}</text>{/if}
      <text x={W / 2} y={H + 28} class="tick name" text-anchor="middle">p of the correct answer</text>
    </svg>
  </div>

  {#snippet readout()}
    correct answer: <b>{NAMES[target]}</b> · p = {p.toFixed(3)} · loss = −log({p.toFixed(3)}) = <b class:ask={locked('loss')}>{locked('loss') ? '?' : loss.toFixed(3)}</b>
  {/snippet}

  {#snippet legend()}
    <span><i class="sw okb"></i>p of the correct answer</span>
    <span><i class="sw oth"></i>p of the other answers</span>
    <span><i class="sw crv"></i>loss = −log p</span>
    <span><i class="sw dt"></i>where you are now</span>
  {/snippet}
</LabFrame>

<style>
  .cols { display: flex; flex-wrap: wrap; gap: 1rem 1.4rem; align-items: center; }
  .left { flex: 1 1 280px; min-width: 0; }
  .row { display: grid; grid-template-columns: 4.6rem minmax(4.5rem, 1fr) 2.6rem minmax(4.5rem, 1fr); gap: 0.5rem; align-items: center; margin: 0.15rem 0; font-size: 0.85rem; }
  .row.head { color: var(--dim); font-size: 0.76rem; margin: 0; }
  .row input[type='range'] { width: 100%; accent-color: var(--accent); }
  .radio { font-family: var(--mono); font-weight: 600; display: flex; gap: 0.4rem; align-items: center; min-height: 2.5rem; cursor: pointer; }
  .radio input { width: 1.1rem; height: 1.1rem; accent-color: var(--ok); margin: 0; }
  .row.tgt .radio { color: var(--ok); }
  .num { font-family: var(--mono); text-align: right; font-variant-numeric: tabular-nums; }
  .bar { position: relative; height: 1.4rem; background: var(--bg); border: 1px solid var(--line); border-radius: 3px; overflow: hidden; }
  .bar i { position: absolute; inset: 0 auto 0 0; background: var(--dim); opacity: 0.3; transition: width 0.2s; }
  .bar i.t { background: var(--ok); opacity: 0.45; }
  @media (prefers-reduced-motion: reduce) { .bar i { transition: none; } }
  .bar em { position: relative; font-style: normal; font-family: var(--mono); font-size: 0.78rem; padding-left: 0.3rem; line-height: 1.4rem; font-variant-numeric: tabular-nums; }
  .ask { color: var(--warn); }
  .note { color: var(--dim); font-size: 0.8rem; margin: 0.4rem 0 0; }
  .plot { width: 100%; max-width: 320px; flex: 0 1 320px; margin: 0 auto; overflow: visible; }
  .axis { stroke: var(--dim); stroke-width: 0.8; }
  .tick { font-size: 9.5px; fill: var(--dim); font-family: var(--mono); }
  .tick.name { fill: var(--fg); }
  .tick.val { fill: var(--accent); font-weight: 700; }
  .grid { stroke: var(--line); stroke-width: 0.5; }
  .guide { stroke: var(--accent); stroke-width: 0.8; stroke-dasharray: 3 3; opacity: 0.7; }
  .curve { fill: none; stroke: var(--fg); stroke-width: 1.5; }
  .dot { fill: var(--accent); stroke: var(--bg); stroke-width: 1.5; }
  .sw { display: inline-block; width: 0.9rem; height: 0.65rem; border-radius: 2px; margin-right: 0.35rem; vertical-align: -0.02rem; }
  .sw.okb { background: var(--ok); opacity: 0.6; }
  .sw.oth { background: var(--dim); opacity: 0.45; }
  .sw.crv { height: 0; border-top: 2px solid var(--fg); border-radius: 0; vertical-align: 0.2rem; }
  .sw.dt { width: 0.65rem; height: 0.65rem; border-radius: 50%; background: var(--accent); }
</style>
