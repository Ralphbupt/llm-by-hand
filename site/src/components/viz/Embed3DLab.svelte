<script lang="ts">
  /**
   * Word vectors with three numbers each, drawn as arrows in 3D (level 13).
   * Pick two words: the first is blue (accent), the second has its own color. The arc between them is the angle
   * (its cosine is in the readout, not in the picture, so only the words and axes are named there), and the thick dark piece is the second word's shadow on the first word's line:
   * dot product = that shadow's length × the first word's length.
   * The list on the right ranks every word by its dot product with the first word you picked.
   * Without WebGL it draws the flat plane through the two picked arrows instead: the angle and the shadow are exact there.
   */
  import Points3D from '../viz3d/Points3D.svelte'
  import LabFrame from './LabFrame.svelte'

  const WORDS: [string, [number, number, number]][] = [
    ['cat', [2, 1, 0]],
    ['dog', [2, 0, 1]],
    ['lion', [2, 2, -1]],
    ['car', [0, -1, 2]],
    ['truck', [-2, 0, 1]],   // vehicles spread apart so their labels don't sit on top of each other
    ['bus', [0, 1, 2]],
  ]
  let a = $state(0)
  let b = $state(1)

  function choose(i: number) {
    // first click sets the first word; clicking it again swaps roles; otherwise set the second word
    if (i === a) return
    b = i
  }
  const dot = (x: number[], y: number[]) => x[0] * y[0] + x[1] * y[1] + x[2] * y[2]
  const len = (x: number[]) => Math.hypot(...x)
  const va = $derived(WORDS[a][1])
  const vb = $derived(WORDS[b][1])
  const d = $derived(dot(va, vb))
  const cos = $derived(d / (len(va) * len(vb)))
  const ranking = $derived(
    WORDS.map(([w, v], i) => ({ w, i, d: dot(va, v) })).filter((r) => r.i !== a).sort((p, q) => q.d - p.d),
  )
  // only names that have room: a gray word whose tip is near a picked word's tip (cat and lion, cat and dog) stays
  // unnamed, so the two picked names never sit in a cluster of other names. Picking it names it.
  const near = (v: number[], u: number[]) => Math.hypot(v[0] - u[0], v[1] - u[1], v[2] - u[2]) < 1.6
  const points = $derived(
    WORDS.map(([w, v], i) => ({
      p: v,
      label: i === a || i === b || (!near(v, va) && !near(v, vb)) ? w : undefined,
      tone: (i === a ? 'accent' : i === b ? 'cat-2' : 'dim') as 'accent' | 'cat-2' | 'dim',
    })),
  )
  // the second word's shadow on the first word's line; its signed length times |first| is the dot product
  const shadow = $derived(d / len(va))
  // in 3D the arc and the shadow carry no text: their numbers sit in the readout under the picture (a label beside
  // them always crowded the picked words' names). Only the axes and the words have names in the picture.
  const arc = $derived({ a, b, tone: 'dim' as const })
  const proj = $derived({ of: b, onto: a, tone: 'fg' as const })

  // flat fallback: the plane through both arrows. The first word lies along the x axis, the second at the true angle.
  let has3d = $state(true)
  const ang = $derived(Math.acos(Math.max(-1, Math.min(1, cos))))
  const S = 30 // svg units per vector unit
  const A2 = $derived([len(va) * S, 0])
  const B2 = $derived([len(vb) * Math.cos(ang) * S, -len(vb) * Math.sin(ang) * S])
  const arcR = 18
  const arcPath = $derived(`M ${arcR} 0 A ${arcR} ${arcR} 0 0 0 ${arcR * Math.cos(ang)} ${-arcR * Math.sin(ang)}`)
  const term = (x: number, y: number) => `${x < 0 ? `(${x})` : x}×${y < 0 ? `(${y})` : y}`
</script>

<LabFrame
  title={has3d ? 'Word vectors in 3D' : 'Two word vectors, the angle and the shadow'}
  hint={has3d ? 'Pick two words. Drag the picture to turn it (select it first to zoom).' : 'Pick two words. The picture is the flat plane through both arrows.'}
  bind:has3d
  onreset={() => { a = 0; b = 1 }}
  resetDisabled={a === 0 && b === 1}
>
  <div class="cols">
    <div class="pic">
      {#if has3d}
        <Points3D {points} arrows range={2.05} height="min(300px, 80vw)" axes={['1st', '2nd', '3rd']} highlight={a} angleArc={arc} projection={proj}
          ariaLabel="Six word vectors drawn as arrows in three dimensions; the two picked words are colored, with the angle between them and the second word's shadow on the first" />
      {:else}
        <svg class="flat" viewBox="-100 -100 200 120" role="img"
          aria-label="The plane through the two picked arrows: {WORDS[a][0]} along the bottom line, {WORDS[b][0]} at angle with cosine {cos.toFixed(2)}, and its shadow of length {shadow.toFixed(2)} on {WORDS[a][0]}'s line">
          <line x1="-96" x2="96" y1="0" y2="0" class="base" />
          <line x1={B2[0]} y1={B2[1]} x2={B2[0]} y2="5" class="drop" />
          <line x1="0" y1="5" x2={shadow * S} y2="5" class="shadow" />
          <path d={arcPath} class="arcl" />
          <line x1="0" y1="0" x2={A2[0]} y2={A2[1]} class="vec a" />
          <line x1="0" y1="0" x2={B2[0]} y2={B2[1]} class="vec b" />
          <circle cx={A2[0]} cy={A2[1]} r="2.6" class="tip a" />
          <circle cx={B2[0]} cy={B2[1]} r="2.6" class="tip b" />
          <text x={A2[0] + 4} y="-4" class="t a">{WORDS[a][0]}</text>
          <text x={B2[0] + (B2[0] < 0 ? -4 : 4)} y={B2[1] - 4} class="t b" text-anchor={B2[0] < 0 ? 'end' : 'start'}>{WORDS[b][0]}</text>
          <text x={arcR + 4} y="-10" class="t dim">cos {cos.toFixed(2)}</text>
          <text x={shadow * S / 2} y="15" class="t" text-anchor="middle">shadow {shadow.toFixed(2)}</text>
        </svg>
      {/if}
    </div>
    <div class="panel">
      <p class="sec"><i class="sw a"></i>First word</p>
      <div class="chips" role="group" aria-label="First word">{#each WORDS as [w], i}<button type="button" class:on={i === a} aria-pressed={i === a} onclick={() => { a = i; if (b === i) b = (i + 1) % WORDS.length }}>{w}</button>{/each}</div>
      <p class="sec"><i class="sw b"></i>Second word</p>
      <div class="chips" role="group" aria-label="Second word">{#each WORDS as [w], i}<button type="button" class:on={i === b} aria-pressed={i === b} disabled={i === a} onclick={() => choose(i)}>{w}</button>{/each}</div>
      <p class="sec">Dot product with {WORDS[a][0]}, biggest first</p>
      <ol class="rank">
        {#each ranking as r}
          <li class:hl={r.i === b}><span>{r.w}</span><span class="bar" class:negbar={r.d < 0} style="--w:{Math.abs(r.d) / 8}"></span><b class:neg={r.d < 0} class:pos={r.d > 0}>{r.d}</b></li>
        {/each}
      </ol>
    </div>
  </div>

  {#snippet readout()}
    <span class="line">{WORDS[a][0]} · {WORDS[b][0]} = {term(va[0], vb[0])} + {term(va[1], vb[1])} + {term(va[2], vb[2])} = <b class:neg={d < 0} class:pos={d > 0}>{d}</b></span>
    <span class="line also">= shadow {shadow.toFixed(2)} × length of {WORDS[a][0]} {len(va).toFixed(2)}</span>
    <span class="line also">cos(angle) = {cos.toFixed(2)}</span>
  {/snippet}

  {#snippet legend()}
    <span><i class="sw a"></i>first word</span>
    <span><i class="sw b"></i>second word</span>
    <span><i class="sw s"></i>its shadow on the first word’s line</span>
    {#if has3d}<span>The small arc marks the angle between the two words; its cosine and the shadow’s length are in the box above. Gray arrows are the other words; one that sits close to a picked word is not named, so pick it to see which it is.</span>{/if}
    <span>The 1st, 2nd and 3rd numbers of each word are its x, y and z. Animals point one way and vehicles another:
      same direction gives a big dot product, a right angle gives 0 (no shadow), opposite directions go negative (the shadow falls behind the start).</span>
  {/snippet}
</LabFrame>

<style>
  .cols { display: flex; flex-wrap: wrap; gap: 1rem; }
  .pic { flex: 1 1 300px; min-width: 0; }
  .panel { flex: 1 1 220px; min-width: 0; }
  .sec { margin: 0.5rem 0 0.35rem; font-size: 0.82rem; color: var(--dim); }
  .chips { display: flex; flex-wrap: wrap; gap: 0.35rem; }
  button { font: inherit; font-family: var(--mono); font-size: 0.85rem; padding: 0.25rem 0.7rem; min-height: 2.2rem; border: 1px solid var(--field); border-radius: 999px; background: var(--bg); color: var(--fg); cursor: pointer; }
  button.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  button:disabled { opacity: 0.35; cursor: default; }
  button:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
  .neg { color: var(--neg); }
  .line { display: block; }
  .also { color: var(--dim); }
  .flat { display: block; width: 100%; max-width: 420px; margin: 0 auto; overflow: visible; }
  .flat .base { stroke: var(--line); stroke-width: 0.8; }
  .flat .drop { stroke: var(--dim); stroke-width: 0.7; stroke-dasharray: 2 2; }
  .flat .shadow { stroke: var(--fg); stroke-width: 3.2; stroke-linecap: round; }
  .flat .arcl { fill: none; stroke: var(--dim); stroke-width: 0.9; }
  .flat .vec { stroke-width: 1.8; }
  .flat .vec.a, .flat .tip.a { stroke: var(--accent); fill: var(--accent); }
  .flat .vec.b, .flat .tip.b { stroke: var(--cat-2); fill: var(--cat-2); }
  .flat .t { font-family: var(--mono); font-size: 7px; fill: var(--fg); }
  .flat .t.a { fill: var(--accent); } .flat .t.b { fill: var(--cat-2); } .flat .t.dim { fill: var(--dim); }
  .sw { display: inline-block; width: 0.9rem; height: 0.3rem; border-radius: 2px; margin-right: 0.35rem; vertical-align: 0.15rem; }
  .sw.a { background: var(--accent); } .sw.b { background: var(--cat-2); } .sw.s { background: var(--fg); height: 0.45rem; }
  .pos { color: var(--pos); }
  .rank { margin: 0; padding-left: 1.3rem; font-family: var(--mono); font-size: 0.85rem; }
  .rank li { display: grid; grid-template-columns: 3.6rem 1fr 2rem; align-items: center; gap: 0.4rem; padding: 0.1rem 0.25rem; border-radius: 3px; }
  .rank li.hl { background: var(--highlight); }
  .rank b { text-align: right; }
  .bar { display: block; height: 0.5rem; width: calc(var(--w) * 100%); background: var(--pos); border-radius: 2px; transition: width 0.2s; }
  .bar.negbar { background: var(--neg); }
  @media (prefers-reduced-motion: reduce) { .bar { transition: none; } }
</style>
