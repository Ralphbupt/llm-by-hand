<script lang="ts">
  /**
   * The flat twin of Net3D: the same spec, layout and colors (`looksAt`), drawn as SVG in a fixed oblique view.
   * Used as the "Flat" view, without WebGL, when printing, and with reduced data. Renders on the server too, so
   * it is also what shows before the script loads. Tensors are drawn as three faces with their average color.
   */
  import {
    BUCKET_PX, flat, fmtNum, fmtShape, groupTones, itemsOf, layoutNet, looksAt, railY, segmentsOf,
    type Look, type Net3DSpec, type V3,
  } from '@lib/three/net'

  type Props = {
    spec: Net3DSpec
    step?: number
    selected?: string | null
    onselect?: (id: string | null) => void
    ariaLabel?: string
    numbers?: boolean
  }
  let { spec, step = -1, selected = null, onselect, ariaLabel = 'A network, drawn flat', numbers }: Props = $props()

  let width = $state(800)
  const vertical = $derived(width < 520)

  const L = $derived(layoutNet(spec, { vertical }))
  // px per layout unit: small nets drawn big enough to read, big ones capped (the frame scrolls when wider)
  // on phones (vertical) the net's width must fit the screen: leave ~130px for the names beside it
  const U = $derived(vertical
    ? Math.max(28, Math.min(140, 640 / Math.max(1, L.hi[0] - L.lo[0]), (width - 130) / Math.max(0.5, L.hi[1] - L.lo[1] + 0.42 * (L.hi[2] - L.lo[2]))))
    : Math.max(48, Math.min(140, 640 / Math.max(1, L.hi[0] - L.lo[0]))))
  const items = $derived(itemsOf(L))
  const parts = $derived(segmentsOf(spec, L, 128))
  const lk = $derived(looksAt(spec, items, parts.segs, parts.rails, step, selected))
  const tones = $derived(groupTones(spec))
  const showNumbers = $derived(numbers ?? spec.nodes.filter((n) => n.kind === 'neurons').reduce((a, n) => a + Math.min(24, n.shape.reduce((x, y) => x * y, 1)), 0) <= 24)

  /** oblique projection: depth (−z) goes up and to the right; on phones the whole net turns so data flows down */
  function P(p: V3): [number, number] {
    let [x, y, z] = p
    if (vertical) [x, y] = [y, -x]
    return [(x - 0.42 * z) * U, (-y + 0.3 * z) * U]
  }
  const css = (l: Look) => {
    const c = `color-mix(in oklab, var(--${l.tone}) ${Math.round(l.amt * 100)}%, var(--${l.base}))`
    return l.over ? `color-mix(in oklab, var(--${l.over.tone}) ${Math.round(l.over.amt * 100)}%, ${c})` : c
  }
  const poly = (pts: V3[]) => pts.map((p) => P(p).join(',')).join(' ')

  // tensors and boxes: three faces in the mean color of their cells
  const blocks = $derived.by(() => {
    const out: { id: string; faces: string[]; fill: string; on: boolean }[] = []
    let n = 0
    for (const ln of L.nodes) {
      if (ln.kind === 'disc') continue
      const looks = lk.cells.slice(n, n + ln.items.length)
      n += ln.items.length
      // the middle cell's look stands for the block (values: the cell with the largest |look|)
      const pick = looks.reduce((a, b) => (b.amt > a.amt ? b : a), looks[0])
      const [x, y, z] = ln.center, [hx, hy, hz] = ln.half
      const front: V3[] = [[x - hx, y - hy, z + hz], [x + hx, y - hy, z + hz], [x + hx, y + hy, z + hz], [x - hx, y + hy, z + hz]]
      const top: V3[] = [[x - hx, y + hy, z + hz], [x + hx, y + hy, z + hz], [x + hx, y + hy, z - hz], [x - hx, y + hy, z - hz]]
      const side: V3[] = [[x + hx, y - hy, z + hz], [x + hx, y - hy, z - hz], [x + hx, y + hy, z - hz], [x + hx, y + hy, z + hz]]
      out.push({ id: ln.node.id, faces: [poly(front), poly(top), poly(side)], fill: css(pick), on: !!pick.over })
    }
    return out
  })

  const box = $derived.by(() => {
    const pts: [number, number][] = []
    for (const ln of L.nodes) {
      const [x, y, z] = ln.center, [hx, hy, hz] = ln.half
      for (const sx of [-1, 1]) for (const sy of [-1, 1]) for (const sz of [-1, 1]) pts.push(P([x + sx * hx, y + sy * hy, z + sz * hz]))
    }
    if (parts.rails.length) pts.push(P([L.lo[0], railY(L) - 0.2, 0]))
    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1])
    const colNames = Math.max(0, ...spec.nodes.filter((n) => n.names && n.along !== 'x').map((n) => Math.max(...n.names!.map((t) => t.length)) * 7.4 + 16))
    const padR = showNumbers && !vertical ? 96 : Math.max(28, colNames)
    // a row of named items (a sentence) has its name at its start, outside the picture: leave room for it
    const rowName = Math.max(0, ...spec.nodes.filter((n) => n.along === 'x').map((n) => n.label.length * 7.4 + 14))
    const padL = Math.max(colSide < 0 && spec.nodes.some((n) => n.names && n.along !== 'x') ? 60 : 28, vertical ? 0 : rowName)
    const b = { x0: Math.min(...xs) - padL, y0: Math.min(...ys) - (vertical && rowName ? 44 : showNumbers && !vertical ? 48 : 34), x1: Math.max(...xs) + padR, y1: Math.max(...ys) + (vertical && showNumbers ? 30 : spec.nodes.some((n) => n.names) ? 30 : 22) }
    // never cut a label off: grow the box to hold every placed label
    for (const t of laid.boxes) { b.x0 = Math.min(b.x0, t.x0 - 6); b.x1 = Math.max(b.x1, t.x1 + 6); b.y0 = Math.min(b.y0, t.y0 - 4); b.y1 = Math.max(b.y1, t.y1 + 4) }
    return b
  })

  const labelAt = (id: string): [number, number] => {
    const ln = L.byId.get(id)!
    const [x, y, z] = ln.center
    return vertical ? P([x, y + ln.half[1], z]) : P([x, y + ln.half[1], z - ln.half[2]])
  }
  /** a row of items (a sentence): its name goes at the row's start, outside the arcs; on phones above the column */
  const rowLabel = (ln: (typeof L.nodes)[number]): { x: number; y: number; anchor: string } | null => {
    if (ln.node.along !== 'x' || !ln.items.length) return null
    const c = P(ln.items[0]), r = ln.size * U
    return vertical ? { x: c[0], y: c[1] - r - 12, anchor: 'middle' } : { x: c[0] - r - 8, y: c[1] + 4, anchor: 'end' }
  }
  // with numbers above the discs, names and link labels sit one line higher
  const lift = $derived(showNumbers && !vertical ? 22 : 8)
  // a column's item names (e.g. the digits 0–9 of a score column) go on its right, unless the numbers sit there
  const colSide = $derived(showNumbers && !vertical ? -1 : 1)

  /** where a disc's own name goes: under it in a row (and in a column turned flat on phones), else beside it */
  const itemPos = (d: { ln: (typeof L.nodes)[number] }, c: [number, number]): { x: number; y: number; anchor: 'start' | 'middle' | 'end' } => {
    const r = d.ln.size * U
    // a row lies along the screen unless the phone turned it upright (and a column turns flat)
    if ((d.ln.node.along === 'x') !== vertical) return { x: c[0], y: c[1] + r + 13, anchor: 'middle' }
    if (vertical) return { x: c[0] + r + 5, y: c[1], anchor: 'start' }
    return { x: c[0] + colSide * (r + 5), y: c[1], anchor: colSide > 0 ? 'start' : 'end' }
  }

  // ---- names and link labels: placed so they never sit on each other, on a disc or on an item name ----
  type Box = { x0: number; y0: number; x1: number; y1: number }
  type Placed = { x: number; y: number; text: string; anchor: 'start' | 'middle' | 'end'; cls: string; on: boolean; fill?: string }
  const textBox = (x: number, y: number, text: string, anchor: string, px: number): Box => {
    const w = text.length * px * 0.6
    const x0 = anchor === 'middle' ? x - w / 2 : anchor === 'end' ? x - w : x
    return { x0: x0 - 2, y0: y - px - 1, x1: x0 + w + 2, y1: y + 3 }
  }
  const hit = (a: Box, b: Box) => a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1
  const laid = $derived.by(() => {
    const taken: Box[] = []
    // fixed: every disc and every item name
    for (const d of items.discs) {
      const c = P(d.ln.items[d.k]), r = d.ln.size * U
      taken.push({ x0: c[0] - r, y0: c[1] - r, x1: c[0] + r, y1: c[1] + r })
      const nm = d.ln.node.names?.[d.k]
      if (nm) { const ip = itemPos(d, c); taken.push(textBox(ip.x, ip.y + 4, nm, ip.anchor, 12)) }
    }
    // the numbers next to the discs (room for a typical one, so the layout does not jump between steps)
    if (showNumbers) for (const d of items.discs) {
      if (d.ln.node.kind !== 'neurons') continue
      const c = P(d.ln.items[d.k]), r = d.ln.size * U
      taken.push(vertical ? textBox(c[0], c[1] + r + 18, '0.0000', 'middle', 11.5) : textBox(c[0] + r * 0.6 + 4, c[1] - r - 4, '0.0000', 'start', 11.5))
    }
    const out: Placed[] = []
    const tryPlace = (cands: Omit<Placed, 'text' | 'cls' | 'on' | 'fill'>[], rest: Pick<Placed, 'text' | 'cls' | 'on' | 'fill'>, px: number, force: boolean) => {
      for (const c of cands) {
        const bx = textBox(c.x, c.y, rest.text, c.anchor, px)
        if (!taken.some((t) => hit(t, bx))) { taken.push(bx); out.push({ ...c, ...rest }); return }
      }
      // a layer name always shows (first spot); a link label that finds no free spot is left out
      if (force) { const c = cands[0]; taken.push(textBox(c.x, c.y, rest.text, c.anchor, px)); out.push({ ...c, ...rest }) }
    }
    // layer names first: they matter most
    for (const ln of L.nodes) {
      if (ln.node.kind === 'op') continue
      const at = labelAt(ln.node.id)
      const rl = rowLabel(ln)
      const on = selected === ln.node.id || lk.state.active.has(ln.node.id)
      const text = ln.node.kind === 'tensor' ? `${ln.node.label} ${fmtShape(ln.node.shape)}` : ln.node.label
      // a block in a folded column (lines run in above and below it): its name on its left
      const colAt = ln.column ? P([ln.center[0] - ln.half[0], ln.center[1], ln.center[2] + ln.half[2]]) : null
      const base = rl ? { x: rl.x, y: rl.y, anchor: rl.anchor as Placed['anchor'] }
        : colAt ? { x: colAt[0] - 10, y: colAt[1] + 4, anchor: 'end' as Placed['anchor'] }
        : { x: at[0] + (vertical ? 10 : 0), y: at[1] - (vertical ? 0 : lift), anchor: (vertical ? 'start' : 'middle') as Placed['anchor'] }
      // second choice: one line higher; third: the name's right end at the block's center (it leans left)
      tryPlace([base, { ...base, y: base.y - 16 }, ...(rl || vertical ? [] : [{ x: at[0], y: base.y, anchor: 'end' as const }, { x: at[0], y: base.y - 16, anchor: 'end' as const }])],
        { text, cls: 'name', on }, 13, true)
    }
    // then the link labels: above the link, or under it, or not at all
    for (const e of spec.edges) {
      if (!e.label || e.kind === 'residual') continue
      const A = L.byId.get(e.from), B = L.byId.get(e.to)
      if (!A || !B) continue
      const same = Math.abs(A.center[0] - B.center[0]) < 1e-6
      const on = lk.state.active.has(e.id)
      const fill = !on && e.shared ? `var(--${tones[e.shared]})` : undefined
      if (same) {
        const m = P([A.center[0], (A.center[1] + B.center[1]) / 2, 0])
        tryPlace([{ x: m[0] + 8, y: m[1], anchor: 'start' }, { x: m[0] - 8, y: m[1], anchor: 'end' }], { text: e.label, cls: 'link', on, fill }, 12, false)
      } else {
        const m = P([(A.center[0] + B.center[0]) / 2, Math.max(A.center[1] + A.half[1], B.center[1] + B.half[1]), 0])
        // under the link: below the lower of the two layers' bottoms, in the gap between them
        const lo = P([(A.center[0] + B.center[0]) / 2, Math.min(A.center[1] - A.half[1], B.center[1] - B.half[1]), 0])
        const above = { x: m[0], y: m[1] - lift, anchor: 'middle' as const }, under = { x: lo[0], y: lo[1] + 15, anchor: 'middle' as const }
        // between blocks the names sit on top, so link labels go under (all of them, so they read as one row)
        const blocky = A.kind !== 'disc' || B.kind !== 'disc'
        tryPlace(blocky ? [under, above] : [above, { ...above, y: above.y - 15 }, under],
          { text: e.label, cls: 'link', on, fill }, 12, false)
      }
    }
    return { labels: out, boxes: taken }
  })
  const placed = $derived(laid.labels)

  const sel = (id: string) => onselect?.(selected === id ? null : id)
</script>

<div class="net2d" bind:clientWidth={width}>
  <svg viewBox="{box.x0} {box.y0} {box.x1 - box.x0} {box.y1 - box.y0}" role="img" aria-label={ariaLabel}
    style:min-width={vertical ? undefined : `${Math.min(box.x1 - box.x0, 640) * 0.7}px`} style:max-width="{box.x1 - box.x0}px">
    {#each parts.rails as r}
      {@const a = P([r.a[0], railY(L), 0])}
      {@const b = P([r.b[0], railY(L), 0])}
      <line x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} class="rail" class:on={lk.railOn} />
    {/each}
    <!-- lines fade toward the frame's own color (--card), so a faint line is lighter than the frame in dark mode, not darker -->
    {#each parts.segs as s, n}
      {@const a = P(s.a)}
      {@const b = P(s.b)}
      {#if !lk.lines[n].hide}<line x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} stroke={css({ ...lk.lines[n], base: 'card' })} stroke-width={lk.lines[n].bucket < 3 ? BUCKET_PX[lk.lines[n].bucket] : 1.5} stroke-linecap="round" />{/if}
    {/each}
    {#each blocks as bl}
      <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
      <g class="pick" onclick={() => sel(bl.id)}>
        <polygon points={bl.faces[0]} fill={bl.fill} />
        <polygon points={bl.faces[1]} fill="color-mix(in oklab, {bl.fill} 80%, var(--bg))" />
        <polygon points={bl.faces[2]} fill="color-mix(in oklab, {bl.fill} 78%, var(--fg))" />
        {#each bl.faces as f}<polygon points={f} class="edge" />{/each}
      </g>
    {/each}
    {#each items.discs as d, n}
      {@const c = P(d.ln.items[d.k])}
      {@const ring = lk.rings[n]}
      <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
      <circle class="pick" cx={c[0]} cy={c[1]} r={d.ln.size * U} fill={css(lk.discs[n])} stroke={css(ring)}
        stroke-width={1.5 + (ring.r - 1.2) * 9} onclick={() => sel(d.ln.node.id)} />
      {#if d.ln.node.names?.[d.k]}
        {@const row = d.ln.node.along === 'x'}
        {@const ip = itemPos(d, c)}
        <text x={ip.x} y={ip.y} class="item" text-anchor={ip.anchor}>{d.ln.node.names[d.k]}</text>
      {/if}
      {#if d.ln.node.kind === 'op'}<text x={c[0]} y={c[1]} class="op">{d.ln.node.label}</text>{/if}
      {#if showNumbers && d.ln.node.kind === 'neurons'}
        {@const v = flat(lk.state.values[d.ln.node.id])[d.k]}
        {@const gr = lk.back ? flat(lk.state.grads[d.ln.node.id])[d.k] : undefined}
        {#if v !== undefined || gr !== undefined}
          <!-- above and to the right of the disc: lines leave a disc sideways, so the number stays off them -->
          <text x={c[0] + (vertical ? 0 : d.ln.size * U * 0.6 + 4)} y={c[1] + (vertical ? d.ln.size * U + 12 : -d.ln.size * U - 4)} class="num" class:grad={gr !== undefined}
            text-anchor={vertical ? 'middle' : 'start'}>{[v !== undefined ? fmtNum(v) : '', gr !== undefined ? `∂ ${fmtNum(gr)}` : ''].filter(Boolean).join(' · ')}</text>
        {/if}
      {/if}
    {/each}
    {#each placed as t}
      <text x={t.x} y={t.y} class={t.cls} class:on={t.on} class:back={t.on && lk.back} text-anchor={t.anchor}
        style:fill={t.fill}>{t.text}</text>
    {/each}
  </svg>
</div>

<style>
  .net2d { width: 100%; overflow-x: auto; }
  svg { display: block; width: 100%; height: auto; margin: 0 auto; font-family: var(--mono, ui-monospace, monospace); }
  .rail { stroke: color-mix(in oklab, var(--fg) 30%, var(--bg)); stroke-width: 5; stroke-linecap: round; }
  .rail.on { stroke: var(--accent); }
  .edge { fill: none; stroke: color-mix(in oklab, var(--fg) 35%, transparent); stroke-width: 0.75; }
  .pick { cursor: pointer; }
  .name { fill: var(--fg); font-size: 13px; font-family: var(--sans, system-ui, sans-serif); dominant-baseline: auto; }
  .name.on { fill: var(--accent); font-weight: 600; }
  .name.on.back { fill: var(--grad); }
    /* a halo in the frame's color, so a number never sits on a line */
  .num, .item, .name, .link { paint-order: stroke; stroke: var(--card); stroke-width: 5px; stroke-linejoin: round; }
  .num { fill: var(--fg); font-size: 11.5px; dominant-baseline: middle; font-variant-numeric: tabular-nums; }
  .num.grad { fill: var(--grad); }
  .item { fill: var(--fg); font-size: 12px; dominant-baseline: middle; font-family: var(--sans, system-ui, sans-serif); }
  .op { fill: var(--fg); font-size: 14px; text-anchor: middle; dominant-baseline: central; pointer-events: none; }
  .link { fill: var(--dim); font-size: 12px; font-style: italic; }
  .link.on { fill: var(--accent); }
  .link.on.back { fill: var(--grad); }
</style>
