<script lang="ts">
  /**
   * GQA lab (level 20): 8 query heads share fewer K/V heads.
   * Pick how many K/V heads there are; see which query head uses which, and how much K/V
   * a small model (d_head 64, 4 layers, 2 bytes per number) stores per token.
   * Point at, tap or focus a K/V head to light up the query heads that read it (the same group is lit in 3D).
   */
  import { kvBytesPerToken } from '@lib/modern'
  import { readable } from '@lib/readable'
  import Tensors3D from '../viz3d/Tensors3D.svelte'
  import LabFrame from './LabFrame.svelte'

  const NQ = 8, D_HEAD = 64, LAYERS = 4
  let nKv = $state(8)
  let sel = $state(0)
  const group = $derived(NQ / nKv)
  const bytes = $derived(kvBytesPerToken(nKv, D_HEAD, LAYERS))
  const full = kvBytesPerToken(NQ, D_HEAD, LAYERS)
  const name = $derived(nKv === NQ ? `${NQ} K/V heads, one per query head` : nKv === 1 ? '1 K/V head, shared by all query heads' : 'Grouped-query')
  function setKv(v: number) { nKv = v; sel = 0 }
  let view = $state('heads')

  // the heads picture, in viewBox units
  const VW = 400, COL = (VW - 8) / NQ, BW = COL - 6
  const qx = (q: number) => 4 + q * COL + COL / 2
  const kvx = (g: number) => 4 + (g + 0.5) * group * COL
  const kvw = $derived(group * COL - 6)
  const range = (g: number) => (group === 1 ? `Q${g}` : `Q${g * group}–Q${(g + 1) * group - 1}`)

  // 4 tokens, 4 numbers per head in the 3D view: the K and V caches lose depth as heads are shared
  const T3 = 4, D3 = 4
  type P3 = [number, number, number]
  const tensors = $derived([
    { shape: [NQ, T3, D3], title: `Q ×${NQ}`, axes: ['head', 'token', 'd'], highlight: [{ from: [sel * group, 0, 0] as P3, to: [(sel + 1) * group - 1, T3 - 1, D3 - 1] as P3 }] },
    '      ', // a wide gap: the queries on their own, then the cache (K and V side by side); no arrow, Q does not become K
    { shape: [nKv, T3, D3], title: `K ×${nKv}`, axes: ['head', 'token', 'd'], highlight: [{ from: [sel, 0, 0] as P3, to: [sel, T3 - 1, D3 - 1] as P3 }] },
    '  ', // a small gap: K and V are two separate caches, and at 8 heads they would touch
    { shape: [nKv, T3, D3], title: `V ×${nKv}`, axes: ['head', 'token', 'd'], highlight: [{ from: [sel, 0, 0] as P3, to: [sel, T3 - 1, D3 - 1] as P3 }] },
  ])
</script>

<LabFrame
  title="Grouped-query attention: query heads share K/V heads, so the cache shrinks"
  hint="Pick how many K/V heads there are. Point at or tap a K/V head to see which query heads read it."
  views={[{ id: 'heads', label: 'Heads' }, { id: '3d', label: '3D cache' }]} bind:view
  onreset={() => setKv(8)} resetDisabled={nKv === 8 && sel === 0}
>
  <p class="name"><b>{name}</b>{nKv !== NQ && nKv !== 1 ? `: each K/V head serves ${group} query heads` : ''}</p>
  {#if view === 'heads'}
    <svg use:readable viewBox={`0 0 ${VW} 166`} role="group" aria-label={`${NQ} query heads above, ${nKv} K/V heads below; lines show which K/V head each query head reads`}>
      <text x="4" y="10" class="lbl">{NQ} query heads</text>
      {#each Array(nKv) as _, g}
        {#each Array(group) as _, j}
          {@const q = g * group + j}
          <path d={`M${qx(q)},46 C${qx(q)},72 ${kvx(g)},70 ${kvx(g)},96`} class="link" class:on={g === sel} />
        {/each}
      {/each}
      {#each Array(NQ) as _, q}
        {@const g = Math.floor(q / group)}
        <!-- svelte-ignore a11y_no_static_element_interactions, a11y_click_events_have_key_events -->
        <g class="box q" class:on={g === sel} onpointerenter={() => (sel = g)} onclick={() => (sel = g)}>
          <rect x={qx(q) - COL / 2} y="14" width={COL} height="40" class="hit" />
          <rect x={qx(q) - BW / 2} y="20" width={BW} height="26" rx="4" />
          <text x={qx(q)} y="37.5" text-anchor="middle">Q{q}</text>
        </g>
      {/each}
      {#each Array(nKv) as _, g}
        <g class="box kv" class:on={g === sel} role="button" tabindex="0" aria-pressed={g === sel}
          aria-label={`K/V head ${g}, read by ${range(g)}`}
          onpointerenter={() => (sel = g)} onclick={() => (sel = g)} onfocus={() => (sel = g)}
          onkeydown={(e) => { if (e.key === 'ArrowRight') { sel = Math.min(nKv - 1, sel + 1); e.preventDefault() } if (e.key === 'ArrowLeft') { sel = Math.max(0, sel - 1); e.preventDefault() } }}>
          <rect x={kvx(g) - (group * COL) / 2} y="90" width={group * COL} height="56" class="hit" />
          <rect x={kvx(g) - kvw / 2} y="96" width={kvw} height="28" rx="4" />
          <text x={kvx(g)} y="114.5" text-anchor="middle">KV{g}</text>
        </g>
        {#if group > 1}<text x={kvx(g)} y="141" text-anchor="middle" class="sub" class:on={g === sel}>{range(g)}</text>{/if}
      {/each}
      <text x="4" y="162" class="lbl">{nKv} K/V head{nKv > 1 ? 's' : ''}: what the cache stores</text>
    </svg>
  {:else}
    <Tensors3D {tensors} height="260px" keepView ariaLabel="Query heads and the K and V caches as blocks; the caches get thinner as heads are shared" />
    <p class="cap">Q ×8: the query heads. K ×{nKv}, V ×{nKv}: the cache. Highlighted: K/V head {sel} and the query heads that read it ({range(sel)}).</p>
  {/if}

  <div class="size">
    <span class="slbl">K/V cache per token</span>
    <span class="sbar" role="img" aria-label={`${((bytes / full) * 100).toFixed(1)}% of the 8-head size`}><i style:width="{(bytes / full) * 100}%"></i></span>
    <span class="sval"><b>{bytes.toLocaleString()}</b> bytes</span>
  </div>
  <p class="cap">A small model, to keep the picture readable: 8 query heads, dₖ = 64, 4 layers. The questions use 32 query heads and 32 layers, but the sharing works the same way.</p>

  {#snippet controls()}
    <span class="seg" role="group" aria-label="Number of K/V heads">
      <span class="seglbl">K/V heads</span>
      {#each [8, 4, 2, 1] as v}
        <button type="button" class="lab-btn" aria-pressed={nKv === v} onclick={() => setKv(v)}>{v}</button>
      {/each}
    </span>
  {/snippet}

  {#snippet readout()}
    K and V stored per token = 2 × {nKv} heads × {D_HEAD} × {LAYERS} layers × 2 bytes = <b>{bytes.toLocaleString()} bytes</b>
    <span class="dim">({((bytes / full) * 100).toFixed(1)}% of the 8-head size)</span>
  {/snippet}

  {#snippet legend()}
    <span class="lg"><i class="sw on"></i>the group you picked: one K/V head and the query heads that read it</span>
    <span class="lg"><i class="sw"></i>other groups</span>
  {/snippet}
</LabFrame>

<style>
  .name { margin: 0 0 0.3rem; font-size: 0.9rem; }
  svg { width: 100%; height: auto; display: block; max-width: 560px; }
  .lbl { font-size: 10px; fill: var(--dim); font-family: var(--mono); }
  .sub { font-size: 10px; fill: var(--dim); font-family: var(--mono); }
  .sub.on { fill: var(--accent); font-weight: 600; }
  .link { fill: none; stroke: var(--field); stroke-width: 1.3; opacity: 0.6; transition: stroke 0.2s, opacity 0.2s; }
  .link.on { stroke: var(--accent); stroke-width: 2; opacity: 1; }
  .box { cursor: pointer; }
  .box rect.hit { fill: transparent; stroke: none; }
  .box rect:not(.hit) { fill: var(--bg); stroke: var(--field); stroke-width: 1.2; transition: fill 0.2s, stroke 0.2s; }
  .box text { font-size: 11px; font-family: var(--mono); fill: var(--fg); pointer-events: none; }
  .box.kv rect:not(.hit) { fill: color-mix(in srgb, var(--fg) 8%, var(--bg)); }
  .box.kv text { font-weight: 700; }
  .box.on rect:not(.hit) { stroke: var(--accent); stroke-width: 1.8; fill: color-mix(in srgb, var(--accent) 16%, var(--bg)); }
  .box.kv.on rect:not(.hit) { fill: color-mix(in srgb, var(--accent) 30%, var(--bg)); }
  .box.kv:focus { outline: none; }
  .box.kv:focus-visible rect:not(.hit) { stroke: var(--fg); stroke-width: 2.4; }
  .cap { margin: 0.2rem 0 0; font-size: 0.8rem; color: var(--dim); }
  .size { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 0.7rem; align-items: center; margin-top: 0.6rem; font-size: 0.85rem; max-width: 560px; }
  .slbl { color: var(--dim); }
  .sval { font-family: var(--mono); font-variant-numeric: tabular-nums; text-align: right; min-width: 7.5rem; }
  .sbar { height: 0.8rem; border: 1px solid var(--line); border-radius: 3px; background: var(--bg); overflow: hidden; }
  .sbar i { display: block; height: 100%; background: color-mix(in srgb, var(--fg) 45%, var(--bg)); transition: width 0.25s ease-out; }
  .seg { display: inline-flex; align-items: center; gap: 0.35rem; flex-wrap: wrap; }
  .seglbl { font-size: 0.85rem; color: var(--dim); margin-right: 0.2rem; }
  .seg .lab-btn { min-width: 2.6rem; font-family: var(--mono); }
  .dim { color: var(--dim); }
  .lg { display: inline-flex; align-items: center; gap: 0.35rem; }
  .sw { width: 0.9rem; height: 0.7rem; border-radius: 2px; display: inline-block; border: 1.5px solid var(--field); background: var(--bg); }
  .sw.on { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 30%, var(--bg)); }
  @media (prefers-reduced-motion: reduce) { .link, .box rect, .sbar i { transition: none; } }
  @media (max-width: 560px) {
    .size { grid-template-columns: minmax(0, 1fr) auto; }
    .slbl { grid-column: 1 / -1; }
  }
</style>
