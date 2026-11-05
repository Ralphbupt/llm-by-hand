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
  import { provideLang, useT } from '@lib/i18nSvelte'
  import type { Lang } from '@lib/i18n'

  let { lang = 'en' }: { lang?: Lang } = $props()
  provideLang(lang)
  const t = useT({
    '{n} K/V heads, one per query head': '{n} 个 K/V 头，每个查询头一个',
    '1 K/V head, shared by all query heads': '1 个 K/V 头，所有查询头共用',
    'Grouped-query': '分组查询',
    'head': '头',
    'Grouped-query attention: query heads share K/V heads, so the cache shrinks': '分组查询注意力：查询头共用 K/V 头，缓存就变小了',
    'Pick how many K/V heads there are. Point at or tap a K/V head to see which query heads read it.': '选择 K/V 头的个数。指向或点一下某个 K/V 头，看看哪些查询头读它。',
    'Heads': '头',
    '3D cache': '3D 缓存',
    ': each K/V head serves {n} query heads': '：每个 K/V 头服务 {n} 个查询头',
    '{q} query heads above, {k} K/V heads below; lines show which K/V head each query head reads': '上面 {q} 个查询头，下面 {k} 个 K/V 头；连线表示每个查询头读哪个 K/V 头',
    '{n} query heads': '{n} 个查询头',
    'K/V head {g}, read by {r}': 'K/V 头 {g}，由 {r} 读取',
    '{n} K/V heads: what the cache stores': '{n} 个 K/V 头：缓存存的东西',
    '1 K/V head: what the cache stores': '1 个 K/V 头：缓存存的东西',
    'Query heads and the K and V caches as blocks; the caches get thinner as heads are shared': '查询头以及 K 缓存和 V 缓存，画成方块；头共用得越多，缓存越薄',
    'Q ×8: the query heads. K ×{k}, V ×{k}: the cache. Highlighted: K/V head {s} and the query heads that read it ({r}).': 'Q ×8：查询头。K ×{k}、V ×{k}：缓存。高亮的是 K/V 头 {s} 和读它的查询头（{r}）。',
    'K/V cache per token': '每个 token 的 K/V 缓存',
    '{p}% of the 8-head size': '8 个头时大小的 {p}%',
    'bytes': '字节',
    'A small model, to keep the picture readable: 8 query heads, dₖ = 64, 4 layers. The questions use 32 query heads and 32 layers, but the sharing works the same way.': '为了让图看得清，这里用一个小模型：8 个查询头，dₖ = 64，4 层。题目里用的是 32 个查询头和 32 层，但共用的方式一样。',
    'Number of K/V heads': 'K/V 头的个数',
    'K/V heads': 'K/V 头',
    'K and V stored per token = 2 × {k} heads × {d} × {l} layers × 2 bytes =': '每个 token 存的 K 和 V = 2 × {k} 个头 × {d} × {l} 层 × 2 字节 =',
    '({p}% of the 8-head size)': '（8 个头时大小的 {p}%）',
    'the group you picked: one K/V head and the query heads that read it': '你选的组：一个 K/V 头和读它的查询头',
    'other groups': '其他组',
  })

  const NQ = 8, D_HEAD = 64, LAYERS = 4
  let nKv = $state(8)
  let sel = $state(0)
  const group = $derived(NQ / nKv)
  const bytes = $derived(kvBytesPerToken(nKv, D_HEAD, LAYERS))
  const full = kvBytesPerToken(NQ, D_HEAD, LAYERS)
  const name = $derived(nKv === NQ ? t('{n} K/V heads, one per query head', { n: NQ }) : nKv === 1 ? t('1 K/V head, shared by all query heads') : t('Grouped-query'))
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
    { shape: [NQ, T3, D3], title: `Q ×${NQ}`, axes: [t('head'), 'token', 'd'], highlight: [{ from: [sel * group, 0, 0] as P3, to: [(sel + 1) * group - 1, T3 - 1, D3 - 1] as P3 }] },
    '      ', // a wide gap: the queries on their own, then the cache (K and V side by side); no arrow, Q does not become K
    { shape: [nKv, T3, D3], title: `K ×${nKv}`, axes: [t('head'), 'token', 'd'], highlight: [{ from: [sel, 0, 0] as P3, to: [sel, T3 - 1, D3 - 1] as P3 }] },
    '  ', // a small gap: K and V are two separate caches, and at 8 heads they would touch
    { shape: [nKv, T3, D3], title: `V ×${nKv}`, axes: [t('head'), 'token', 'd'], highlight: [{ from: [sel, 0, 0] as P3, to: [sel, T3 - 1, D3 - 1] as P3 }] },
  ])
</script>

<LabFrame
  title={t('Grouped-query attention: query heads share K/V heads, so the cache shrinks')}
  hint={t('Pick how many K/V heads there are. Point at or tap a K/V head to see which query heads read it.')}
  views={[{ id: 'heads', label: t('Heads') }, { id: '3d', label: t('3D cache') }]} bind:view
  onreset={() => setKv(8)} resetDisabled={nKv === 8 && sel === 0}
>
  <p class="name"><b>{name}</b>{nKv !== NQ && nKv !== 1 ? t(': each K/V head serves {n} query heads', { n: group }) : ''}</p>
  {#if view === 'heads'}
    <svg use:readable viewBox={`0 0 ${VW} 166`} role="group" aria-label={t('{q} query heads above, {k} K/V heads below; lines show which K/V head each query head reads', { q: NQ, k: nKv })}>
      <text x="4" y="10" class="lbl">{t('{n} query heads', { n: NQ })}</text>
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
          aria-label={t('K/V head {g}, read by {r}', { g, r: range(g) })}
          onpointerenter={() => (sel = g)} onclick={() => (sel = g)} onfocus={() => (sel = g)}
          onkeydown={(e) => { if (e.key === 'ArrowRight') { sel = Math.min(nKv - 1, sel + 1); e.preventDefault() } if (e.key === 'ArrowLeft') { sel = Math.max(0, sel - 1); e.preventDefault() } }}>
          <rect x={kvx(g) - (group * COL) / 2} y="90" width={group * COL} height="56" class="hit" />
          <rect x={kvx(g) - kvw / 2} y="96" width={kvw} height="28" rx="4" />
          <text x={kvx(g)} y="114.5" text-anchor="middle">KV{g}</text>
        </g>
        {#if group > 1}<text x={kvx(g)} y="141" text-anchor="middle" class="sub" class:on={g === sel}>{range(g)}</text>{/if}
      {/each}
      <text x="4" y="162" class="lbl">{nKv > 1 ? t('{n} K/V heads: what the cache stores', { n: nKv }) : t('1 K/V head: what the cache stores')}</text>
    </svg>
  {:else}
    <Tensors3D {tensors} height="260px" keepView ariaLabel={t('Query heads and the K and V caches as blocks; the caches get thinner as heads are shared')} />
    <p class="cap">{t('Q ×8: the query heads. K ×{k}, V ×{k}: the cache. Highlighted: K/V head {s} and the query heads that read it ({r}).', { k: nKv, s: sel, r: range(sel) })}</p>
  {/if}

  <div class="size">
    <span class="slbl">{t('K/V cache per token')}</span>
    <span class="sbar" role="img" aria-label={t('{p}% of the 8-head size', { p: ((bytes / full) * 100).toFixed(1) })}><i style:width="{(bytes / full) * 100}%"></i></span>
    <span class="sval"><b>{bytes.toLocaleString()}</b> {t('bytes')}</span>
  </div>
  <p class="cap">{t('A small model, to keep the picture readable: 8 query heads, dₖ = 64, 4 layers. The questions use 32 query heads and 32 layers, but the sharing works the same way.')}</p>

  {#snippet controls()}
    <span class="seg" role="group" aria-label={t('Number of K/V heads')}>
      <span class="seglbl">{t('K/V heads')}</span>
      {#each [8, 4, 2, 1] as v}
        <button type="button" class="lab-btn" aria-pressed={nKv === v} onclick={() => setKv(v)}>{v}</button>
      {/each}
    </span>
  {/snippet}

  {#snippet readout()}
    {t('K and V stored per token = 2 × {k} heads × {d} × {l} layers × 2 bytes =', { k: nKv, d: D_HEAD, l: LAYERS })} <b>{bytes.toLocaleString()} {t('bytes')}</b>
    <span class="dim">{t('({p}% of the 8-head size)', { p: ((bytes / full) * 100).toFixed(1) })}</span>
  {/snippet}

  {#snippet legend()}
    <span class="lg"><i class="sw on"></i>{t('the group you picked: one K/V head and the query heads that read it')}</span>
    <span class="lg"><i class="sw"></i>{t('other groups')}</span>
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
