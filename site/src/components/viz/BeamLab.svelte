<script lang="ts">
  /**
   * Beam lab (level 18): a two-step tree of next-word probabilities.
   * Pick a beam width, then step: keep the best `width` first words, expand them, keep the best sequence.
   */
  import { onMount } from 'svelte'
  import LabFrame from './LabFrame.svelte'
  import { readable } from '@lib/readable'
  import { has, subscribe } from '@lib/progress'

  // sequence totals stay "?" until the question about the best sequence is solved
  let { hide }: { hide?: string } = $props()
  let solved = $state(false)
  onMount(() => {
    if (!hide) return
    const sync = () => (solved = has(hide))
    sync()
    return subscribe(sync)
  })
  const masked = $derived(!!hide && !solved)

  const FIRST: [string, number][] = [['a', 0.5], ['the', 0.4], ['one', 0.1]]
  const SECOND: Record<string, [string, number][]> = {
    a: [['dog', 0.4], ['cat', 0.3], ['fox', 0.3]],
    the: [['dog', 0.9], ['cat', 0.05], ['fox', 0.05]],
    one: [['dog', 0.5], ['cat', 0.25], ['fox', 0.25]],
  }

  let width = $state(1)
  let step = $state(0) // 0: start, 1: first words kept, 2: second words added, best chosen

  const keptFirst = $derived(FIRST.slice(0, width).map(([w]) => w)) // FIRST is already sorted
  const finals = $derived(
    keptFirst.flatMap((w1) => {
      const p1 = FIRST.find(([w]) => w === w1)![1]
      return SECOND[w1].map(([w2, p2]) => ({ w1, w2, p: p1 * p2, lp: Math.log(p1) + Math.log(p2) }))
    }),
  )
  const best = $derived(finals.reduce((a, b) => (b.lp > a.lp ? b : a), finals[0]))

  const ROOT_Y = 165
  // two layouts in viewBox units: the wide one, and a compact one for phones, so the labels stay readable
  // (the `readable` action enlarges small text; a shrunken wide tree would overlap)
  let cw = $state(0)
  const narrow = $derived(cw > 0 && cw < 500)
  const G = $derived(narrow
    ? { vw: 340, root: 12, e0: 19, p1x: 24, b1x: 50, b1w: 50, ep2x: 121, b2x: 168, b2w: 86, totx: 336, hd1: 50, hd2: 168, start: false }
    : { vw: 460, root: 40, e0: 48, p1x: 80, b1x: 112, b1w: 62, ep2x: 226, b2x: 262, b2w: 104, totx: 452, hd1: 118, hd2: 268, start: true })
  function setWidth(w: number) { width = w; step = 0 }
  const isKept = (w1: string) => step >= 1 && keptFirst.includes(w1)
  const isBest = (w1: string, w2: string) => step >= 2 && best.w1 === w1 && best.w2 === w2
</script>

<LabFrame
  title="Beam search: keep the best few partial answers"
  hint="Choose a beam width, then press Next step to keep the best first words and then the best two-word sequence."
  onreset={() => setWidth(1)}
  resetDisabled={width === 1 && step === 0}
>
  <div class="treewrap" bind:clientWidth={cw}>
  <svg class="tree" use:readable viewBox="0 0 {G.vw} 300" role="img" aria-label="Beam search tree: first words, then two-word sequences, with the kept beams highlighted">
    {#if G.start}<text x="8" y="14" class="hd">start</text>{/if}
    <text x={G.hd1} y="14" class="hd">first word</text>
    <text x={G.hd2} y="14" class="hd">second word</text>
    <text x={G.totx} y="14" class="hd end">{narrow ? 'p(seq.)' : 'p(sequence)'}</text>
    {#each FIRST as [w1, p1], i}
      {@const y1 = 30 + i * 90 + 45}
      <!-- root → first word -->
      <path d={`M${G.e0},${ROOT_Y} C${G.e0 + (G.b1x - G.e0) * 0.58},${ROOT_Y} ${G.b1x - (G.b1x - G.e0) * 0.5},${y1} ${G.b1x},${y1}`} class="edge"
        class:kept={isKept(w1)} class:cut={step >= 1 && !isKept(w1)} class:win={step >= 2 && best.w1 === w1} />
      <text x={G.p1x} y={(ROOT_Y + y1) / 2 - 3} class="ep" class:cut={step >= 1 && !isKept(w1)}>{p1}</text>
      <g class="node" class:kept={isKept(w1)} class:cut={step >= 1 && !isKept(w1)}>
        <rect x={G.b1x} y={y1 - 13} width={G.b1w} height="26" rx="5" />
        <text x={G.b1x + G.b1w / 2} y={y1 + 4} class="w mid">{w1}</text>
      </g>
      {#if step >= 1 && !isKept(w1)}
        {#if narrow}<text x={G.b1x + G.b1w / 2} y={y1 + 28} class="x mid">dropped</text>
        {:else}<text x="182" y={y1 + 4} class="x">dropped</text>{/if}
      {/if}
      {#each SECOND[w1] as [w2, p2], j}
        {@const y2 = 30 + i * 90 + j * 30 + 0}
        {@const live = step >= 2 && isKept(w1)}
        {@const b1r = G.b1x + G.b1w}
        {@const mx = (b1r + G.b2x) / 2}
        <path d={`M${b1r},${y1} C${mx},${y1} ${mx},${y2 + 15} ${G.b2x},${y2 + 15}`} class="edge thin"
          class:kept={live} class:cut={step >= 1 && !isKept(w1)} class:win={isBest(w1, w2)} />
        <text x={G.ep2x} y={y2 + 12} class="ep small" class:cut={step >= 1 && !isKept(w1)}>×{p2}</text>
        <g class="node second" class:kept={live} class:cut={step >= 1 && !isKept(w1)} class:win={isBest(w1, w2)}>
          <rect x={G.b2x} y={y2 + 3} width={G.b2w} height="24" rx="5" />
          <text x={G.b2x + 7} y={y2 + 19} class="w">{w1} {w2}</text>
        </g>
        {#if live}
          <text x={G.totx} y={y2 + 19} class="tot end" class:win={isBest(w1, w2)}>{masked ? '?' : (p1 * p2).toFixed(2)}</text>
        {/if}
      {/each}
    {/each}
    <circle cx={G.root} cy={ROOT_Y} r="7" class="root" />
  </svg>
  </div>

  {#snippet controls()}
    <div class="widths" role="group" aria-label="Beam width">
      <span class="wl">beam width</span>
      {#each [1, 2, 3] as w}
        <button type="button" class:on={width === w} aria-pressed={width === w} onclick={() => setWidth(w)}>{w}{w === 1 ? ' (greedy)' : ''}</button>
      {/each}
    </div>
    <button type="button" class="lab-btn" onclick={() => (step = Math.max(0, step - 1))} disabled={step === 0}>‹ Back</button>
    <button type="button" class="lab-btn primary" onclick={() => (step = Math.min(2, step + 1))} disabled={step === 2}>Next step ›</button>
  {/snippet}

  {#snippet readout()}
    {#if step === 0}
      Press “Next step”. Beam width {width} keeps the {width} most likely first word{width > 1 ? 's' : ''}.
    {:else if step === 1}
      Kept: <b>{keptFirst.join(', ')}</b>. The others are dropped and never come back. Next: try every second word after each kept one.
    {:else}
      Best kept sequence: <b>{best.w1} {best.w2}</b>{masked ? '' : `, p = ${best.p.toFixed(2)}`}.
      {width === 1 ? 'Greedy never looked at “the”, so it never saw “the dog”.' : ''}
    {/if}
    {#if masked && step === 2}<span class="idle"> Sequence totals show “?” until you answer the question below.</span>{/if}
  {/snippet}

  {#snippet legend()}
    <span class="lg"><i class="k"></i>kept beam</span><span class="lg"><i class="c"></i>dropped</span><span class="lg"><i class="b"></i>best sequence</span><span>p(sequence) = p(first) × p(second)</span>
  {/snippet}
</LabFrame>

<style>
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
  .widths { display: inline-flex; align-items: center; gap: 0; border: 1px solid var(--field); border-radius: 999px; overflow: hidden; }
  .wl { font-size: 0.82rem; color: var(--dim); padding: 0 0.6rem; }
  .widths button { font: inherit; font-size: 0.82rem; padding: 0.25rem 0.75rem; min-height: 2.1rem; border: 0; border-left: 1px solid var(--field); background: var(--bg); color: var(--fg); cursor: pointer; }
  .widths button.on { color: var(--accent); background: var(--highlight); }
  .widths button:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
  .tree { width: 100%; height: auto; display: block; max-width: 640px; }
  .hd { font-size: 10px; fill: var(--dim); font-family: var(--mono); letter-spacing: 0.04em; }
  .end { text-anchor: end; }
  .mid { text-anchor: middle; }
  .edge { fill: none; stroke: var(--line); stroke-width: 2; transition: stroke 0.2s, opacity 0.2s, stroke-width 0.2s; }
  .edge.thin { stroke-width: 1.4; }
  .edge.kept { stroke: var(--accent); }
  .edge.win { stroke: var(--ok); stroke-width: 3; }
  .edge.cut { opacity: 0.3; stroke-dasharray: 4 3; }
  .ep { font-size: 10px; fill: var(--dim); font-family: var(--mono); transition: opacity 0.2s; }
  .ep.small { font-size: 9.5px; }
  .ep.cut { opacity: 0.35; }
  .node rect { fill: var(--bg); stroke: var(--field); stroke-width: 1.2; transition: stroke 0.2s, opacity 0.2s; }
  .node .w { font-size: 12px; fill: var(--fg); font-family: var(--mono); font-weight: 600; }
  .node.second .w { font-weight: 400; font-size: 11.5px; }
  .node.kept rect { stroke: var(--accent); stroke-width: 1.8; }
  .node.win rect { stroke: var(--ok); stroke-width: 2.2; }
  .node.win .w { fill: var(--ok); font-weight: 700; }
  .node.cut { opacity: 0.35; }
  .x { font-size: 10px; fill: var(--dim); font-family: var(--mono); font-style: italic; }
  .tot { font-size: 12px; fill: var(--fg); font-family: var(--mono); }
  .tot.win { fill: var(--ok); font-weight: 700; }
  .root { fill: var(--fg); }
  .lg { display: inline-flex; align-items: center; gap: 0.35rem; }
  .lg i { display: inline-block; width: 16px; height: 0; border-top: 2px solid var(--accent); }
  .lg .c { border-top: 2px dashed var(--field); }
  .lg .b { border-top: 3px solid var(--ok); }
  @media (prefers-reduced-motion: reduce) { .edge, .node rect, .ep { transition: none; } }
  /* phones: touch targets at least 40px tall; 16px fields so iOS does not zoom */
  @media (max-width: 760px) { .widths button { min-height: 2.5rem; min-width: 2.5rem; } }
</style>
