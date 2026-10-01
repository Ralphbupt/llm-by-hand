<script lang="ts">
  /**
   * Where embedding vectors come from (level 13): count which words appear within 2 words of each other in a corpus
   * our own rules wrote, compare the rows of counts (cosine), and draw the 12 rows in 2D (the two directions in which
   * they differ most). Data: content/2-theory/vectors/demo.py --export.
   */
  import { onMount } from 'svelte'
  import { readable } from '@lib/readable'
  import LabFrame from './LabFrame.svelte'

  type Data = {
    groups: Record<string, string[]>
    coords: Record<string, [number, number]>
    neighbors: Record<string, [string, number][]>
    closest: Record<string, [number, string][]>
    sample: string[]
    sentences: number
  }
  const START = 'cat'
  let data = $state<Data | null>(null)
  let failed = $state(false)
  let pick = $state(START)
  onMount(() => {
    fetch('/data/vectors/word2vec.json').then((r) => r.json()).then((d) => (data = d)).catch(() => (failed = true))
  })

  const groupNames = $derived(data ? Object.keys(data.groups) : [])
  const CAT = ['var(--cat-1)', 'var(--cat-2)', 'var(--cat-4)']
  const colorOf = (g: string) => CAT[groupNames.indexOf(g) % CAT.length]
  const words = $derived(data ? Object.values(data.groups).flat() : [])
  const groupOf = (w: string) => (data ? Object.keys(data.groups).find((g) => data!.groups[g].includes(w)) ?? '' : '')

  // the 2D picture
  const W = 320, H = 230, PAD = 26
  const xs = $derived(words.map((w) => data!.coords[w][0]))
  const ys = $derived(words.map((w) => data!.coords[w][1]))
  const sx = (v: number) => PAD + ((v - Math.min(...xs)) / (Math.max(...xs) - Math.min(...xs) || 1)) * (W - 2 * PAD)
  const sy = (v: number) => H - PAD - ((v - Math.min(...ys)) / (Math.max(...ys) - Math.min(...ys) || 1)) * (H - 2 * PAD)
  const P = (w: string) => [sx(data!.coords[w][0]), sy(data!.coords[w][1])]
  // words of a group sit close together: stack their labels beside the group (kept inside the picture);
  // a word far from its group (fish, used two ways) gets its own label next to its point
  const centerOf = (g: string) => {
    const pts = data!.groups[g].map(P)
    return [pts.reduce((a, p) => a + p[0], 0) / pts.length, pts.reduce((a, p) => a + p[1], 0) / pts.length]
  }
  const isLoner = (w: string) => {
    // no other word of its group within 18 units: it gets its own label
    const p = P(w)
    return data!.groups[groupOf(w)].filter((o) => o !== w).every((o) => Math.hypot(P(o)[0] - p[0], P(o)[1] - p[1]) > 18)
  }
  const groupLabel = (g: string) => {
    const members = data!.groups[g].filter((w) => !isLoner(w))
    const pts = members.map(P)
    const cx = pts.reduce((a, p) => a + p[0], 0) / pts.length
    const cy = pts.reduce((a, p) => a + p[1], 0) / pts.length
    const right = cx < W * 0.6
    const h = 12 + 11 * members.length
    const top = Math.min(Math.max(cy - h / 2, 14), H - h - 2)
    return { x: right ? cx + 14 : cx - 14, y: top + 12, anchor: right ? 'start' : 'end', members }
  }
  const near = $derived(data ? data.closest[pick].map(([, o]) => o) : [])
  const maxN = $derived(data ? Math.max(...data.neighbors[pick].map((n) => n[1])) : 1)
</script>

<LabFrame
  title="Words placed by their neighbors"
  hint="Pick a word. Lines join it to the 3 words whose rows of counts are most alike."
  onreset={() => (pick = START)}
  resetDisabled={pick === START}
>
  {#if failed}
    <p class="state">Could not load the vectors. Reload the page to try again.</p>
  {:else if !data}
    <p class="state">Loading the vectors…</p>
  {:else}
    <div class="grid">
      <svg viewBox="0 0 {W} {H}" class="map" use:readable role="img" aria-label="The 12 words as points in 2D, grouped as animals, foods and vehicles">
        {#each near as o}
          <line x1={P(pick)[0]} y1={P(pick)[1]} x2={P(o)[0]} y2={P(o)[1]} class="link" />
        {/each}
        {#each words as w}
          <circle cx={P(w)[0]} cy={P(w)[1]} r={w === pick ? 6 : 4} fill={colorOf(groupOf(w))} class:picked={w === pick} class:near={near.includes(w)} />
        {/each}
        {#each groupNames as g}
          {@const L = groupLabel(g)}
          <text x={L.x} y={L.y - 12} text-anchor={L.anchor} class="gname" fill={colorOf(g)}>{g}s</text>
          {#each L.members as w, k}
            <text x={L.x} y={L.y + k * 11} text-anchor={L.anchor} class="wname" class:on={w === pick} class:nearw={near.includes(w)}>{w}</text>
          {/each}
          {#each data.groups[g].filter(isLoner) as w}
            <text x={P(w)[0] + 9} y={P(w)[1] + 3.5} class="wname" class:on={w === pick} class:nearw={near.includes(w)}>{w}</text>
          {/each}
        {/each}
      </svg>

      <div class="panel">
        <div class="chips" role="group" aria-label="Pick a word">
          {#each groupNames as g}
            <div class="crow">
              {#each data.groups[g] as w}
                <button type="button" class:on={w === pick} aria-pressed={w === pick} style="--c: {colorOf(g)}" onclick={() => (pick = w)}>{w}</button>
              {/each}
            </div>
          {/each}
        </div>
        <p class="h">Most frequent neighbors of “{pick}” (within 2 words)</p>
        <ul class="bars">
          {#each data.neighbors[pick] as [n, c]}
            <li><span class="w">{n}</span><span class="bar"><i style="width:{(c / maxN) * 100}%"></i></span><span class="c">{c}</span></li>
          {/each}
        </ul>
      </div>
    </div>
    <details class="sample"><summary>A few of the {data.sentences.toLocaleString('en-US')} sentences</summary>
      <ul>{#each data.sample as s}<li>{s}</li>{/each}</ul>
    </details>
  {/if}

  {#snippet readout()}
    {#if data}
      closest to “{pick}”: {data.closest[pick].map(([s, o]) => `${o} ${s.toFixed(2)}`).join(' · ')}
    {:else}
      <span class="idle">Similarities appear when the vectors have loaded.</span>
    {/if}
  {/snippet}

  {#snippet legend()}
    {#if data}
      {#each groupNames as g}<span><i class="dot" style="background: {colorOf(g)}"></i>{g}s</span>{/each}
      <span>Similarity is measured on the full rows of counts; the picture keeps the 2 directions in which the 12 rows differ most.</span>
    {/if}
  {/snippet}
</LabFrame>

<style>
  .state { min-height: 14rem; display: grid; place-items: center; margin: 0; color: var(--dim); font-size: 0.9rem; }
  .grid { display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr); gap: 1rem; align-items: start; }
  @media (max-width: 680px) { .grid { grid-template-columns: minmax(0, 1fr); } }
  .map { width: 100%; height: auto; display: block; border: 1px solid var(--line); border-radius: 6px; background: var(--bg); }
  .map circle { stroke: var(--bg); stroke-width: 1.5; transition: r 0.15s; }
  .map circle.picked { stroke: var(--accent); stroke-width: 2.5; }
  .link { stroke: var(--accent); stroke-width: 1.4; stroke-dasharray: 3 2; }
  .gname { font-size: 10px; font-weight: 700; font-family: system-ui, sans-serif; }
  .wname { font-size: 9px; fill: var(--dim); font-family: var(--mono); }
  .wname.nearw { fill: var(--fg); }
  .wname.on { fill: var(--accent); font-weight: 700; }
  @media (prefers-reduced-motion: reduce) { .map circle { transition: none; } }
  .panel { min-width: 0; }
  .chips { display: grid; gap: 0.35rem; }
  .crow { display: flex; flex-wrap: wrap; gap: 0.35rem; }
  .chips button { font: inherit; font-size: 0.85rem; padding: 0.25rem 0.7rem; min-height: 2.2rem; border: 1px solid var(--line); border-left: 3px solid var(--c);
    border-radius: 6px; background: var(--bg); color: var(--fg); cursor: pointer; }
  .chips button.on { border-color: var(--accent); border-left-color: var(--c); background: var(--highlight); font-weight: 600; }
  .chips button:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
  .h { font-size: 0.82rem; color: var(--dim); margin: 0.8rem 0 0.35rem; }
  .bars { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.25rem; font-size: 0.85rem; }
  .bars li { display: grid; grid-template-columns: 4.6rem 1fr 2.6rem; gap: 0.4rem; align-items: center; }
  .bars .w { font-family: var(--mono); }
  .bar { height: 0.55rem; background: var(--bg); border: 1px solid var(--line); border-radius: 3px; overflow: hidden; }
  .bar i { display: block; height: 100%; background: var(--cat-5); }
  .c { text-align: right; font-family: var(--mono); color: var(--dim); }
  .sample { font-size: 0.85rem; color: var(--dim); }
  .sample summary { cursor: pointer; }
  .sample ul { margin: 0.3rem 0 0; padding-left: 1.2rem; font-family: var(--mono); }
  .dot { display: inline-block; width: 0.7rem; height: 0.7rem; border-radius: 50%; margin-right: 0.3rem; vertical-align: -1px; }
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
</style>
