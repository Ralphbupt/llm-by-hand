<script lang="ts">
  /**
   * Tensors as blocks of cells, side by side, with operators between them: X (2,5,4) @ W (4,8) = Y (2,5,8).
   * Use it for shapes: batches, broadcasting (faded "ghost" copies), splitting d_model into heads,
   * convolution feature maps. A shape has 1–3 numbers: (cols), (rows, cols) or (depth, rows, cols).
   * Highlight ranges are inclusive [depth, row, col] index ranges.
   *
   * Drawing: each block is one instanced mesh (one draw call; ghost copies and see-through cells add one each),
   * cell edges are drawn in the shader, all cells share one box geometry. When `tensors` changes, only the blocks
   * whose shape changed are rebuilt; the rest are recolored in place.
   */
  import type { Snippet } from 'svelte'
  import * as THREE from 'three'
  import Stage3D from './Stage3D.svelte'
  import type { Palette, Stage, ViewAngles } from '@lib/three/stage'
  import { cellGeometry, cellMaterial, cellMesh, isDarkPalette, mix, toneColor, type CellMaterial, type Tone } from '@lib/three/kit'
  import { needsSeeThrough, type V3 } from '@lib/three/geom'

  type Range = { from: [number, number, number]; to: [number, number, number]; tone?: Tone }
  type T = {
    shape: number[]
    name?: string
    /** replaces the default "name (shape)" label above the block, e.g. "mask (2, 1, 4) → (2, 4, 4)" */
    title?: string
    /** axis names, same length as shape, e.g. ['B', 'L', 'D'] */
    axes?: string[]
    highlight?: Range[]
    /** cells that are broadcast copies (drawn faded) */
    ghost?: Range[]
    /** optional brightness 0..1 per cell, same nesting as the shape (e.g. pixel values), shading each cell */
    values?: number[] | number[][] | number[][][]
    /** keep the block's place (and the camera) but don't draw it yet, e.g. before an `explode` lands there */
    hidden?: boolean
  }
  /**
   * Copies of the cells of block `to` fly from where they come from in block `from` (`map` gives, for a cell
   * [d, i, j] of `to`, its source cell in `from`) to their own place, as `t` goes 0 → 1. Slabs leave one after
   * another. Nothing flies at t ≤ 0 or t ≥ 1: hide `to` (hidden: true) until it has landed. Block indexes skip operators.
   */
  type Explode = { from: number; to: number; t: number; map: (d: number, i: number, j: number) => [number, number, number] }
  type Props = {
    tensors: (T | string)[]; ariaLabel?: string; height?: string
    /** kept for older labs: the camera now refits only when the blocks' size changes (never on highlight changes) */
    keepView?: boolean
    /** camera angle instead of the default three-quarter view */
    view?: ViewAngles
    /** shown instead of the 3D view when the browser has no WebGL */
    fallback?: Snippet
    /** an animation step: cells flying from one block into another (see Explode) */
    explode?: Explode | null
  }
  let { tensors, ariaLabel = 'Tensors in 3D', height = '320px', view, fallback, explode = null }: Props = $props()

  let stage: Stage | null = null
  const group = new THREE.Group()
  const C = 0.16 // cell pitch
  const GAP = 0.02
  const geo = cellGeometry(C - GAP)

  // shared materials (recolored on theme change)
  const fg0 = new THREE.Color()
  const mat = {
    solid: cellMaterial({ edge: 0.34, edgeColor: fg0 }),
    solidV: cellMaterial({ edge: 0.1, edgeColor: fg0 }),
    glass: cellMaterial({ edge: 0.3, edgeColor: fg0, opacity: 0.4 }),
    glassV: cellMaterial({ edge: 0.08, edgeColor: fg0, opacity: 0.45 }),
    ghost: cellMaterial({ edge: 0.7, edgeColor: fg0, opacity: 0.1, edgeAlpha: 0.4 }),
  }
  function themeMaterials(pal: Palette) {
    const dark = isDarkPalette(pal)
    for (const m of Object.values(mat) as CellMaterial[]) m.userData.uEdgeColor.value.copy(pal.fg)
    mat.ghost.opacity = dark ? 0.12 : 0.07
    mat.ghost.userData.uEdgeAlpha.value = dark ? 0.5 : 0.32
  }

  const as3 = (s: number[]): [number, number, number] =>
    s.length === 1 ? [1, 1, s[0]] : s.length === 2 ? [1, s[0], s[1]] : [s[0], s[1], s[2]]
  function cellValue(t: T, d: number, i: number, j: number): number | null {
    const v = t.values as any
    if (!v) return null
    const x = t.shape.length === 1 ? v[j] : t.shape.length === 2 ? v[i]?.[j] : v[d]?.[i]?.[j]
    return typeof x === 'number' && Number.isFinite(x) ? Math.min(1, Math.max(0, x)) : null
  }
  const inR = (r: Range, d: number, i: number, j: number) =>
    d >= r.from[0] && d <= r.to[0] && i >= r.from[1] && i <= r.to[1] && j >= r.from[2] && j <= r.to[2]

  type Rec = { D: number; R: number; K: number; obj: THREE.Group; solid: THREE.InstancedMesh; glass: THREE.InstancedMesh; ghost: THREE.InstancedMesh }
  let recs: Rec[] = []

  function makeRec(D: number, R: number, K: number): Rec {
    const n = D * R * K
    const obj = new THREE.Group()
    const solid = cellMesh(geo, mat.solid, n)
    const glass = cellMesh(geo, mat.glass, n)
    const ghost = cellMesh(geo, mat.ghost, n)
    glass.renderOrder = 1
    ghost.renderOrder = 2
    obj.add(solid, glass, ghost)
    return { D, R, K, obj, solid, glass, ghost }
  }
  function dropRec(r: Rec) {
    for (const m of [r.solid, r.glass, r.ghost]) m.dispose() // instance buffers; geometry and materials are shared
    r.obj.removeFromParent()
  }

  /** The color of one cell (and whether it is a broadcast ghost). */
  function cellColor(t: T, d: number, i: number, j: number, pal: Palette, col: THREE.Color) {
    const hi = t.highlight?.find((x) => inR(x, d, i, j))
    const ghost = !hi && !!t.ghost?.some((x) => inR(x, d, i, j))
    const v = cellValue(t, d, i, j)
    const base = hi ? toneColor(pal, hi.tone ?? 'accent') : mix(pal.card, pal.fg, 0.14)
    // with values: dark cells stay near the card color, bright cells go toward the text color
    if (v === null) col.copy(ghost ? mix(pal.card, pal.fg, 0.3) : base)
    else if (hi) col.copy(base).lerp(pal.fg, v * 0.55)
    else col.copy(pal.card).lerp(pal.fg, 0.06 + v * 0.9)
    return { hi, ghost }
  }

  /** Write every cell of one block into its meshes (positions, colors, which mesh). */
  function fillRec(r: Rec, t: T, pal: Palette) {
    const { D, R, K } = r
    const see = needsSeeThrough(D, t.highlight)
    const hasV = !!t.values
    r.solid.material = hasV ? mat.solidV : mat.solid
    r.glass.material = hasV ? mat.glassV : mat.glass
    const M = new THREE.Matrix4()
    const col = new THREE.Color()
    let ns = 0, ng = 0, nh = 0
    for (let d = 0; d < D; d++)
      for (let i = 0; i < R; i++)
        for (let j = 0; j < K; j++) {
          const { hi, ghost } = cellColor(t, d, i, j, pal, col)
          // cols → +x, rows → −y, depth → −z (so the first slice faces the camera)
          M.makeTranslation(j * C, -i * C, -d * C)
          const m = ghost ? r.ghost : see && !hi ? r.glass : r.solid
          const k = ghost ? ng++ : see && !hi ? nh++ : ns++
          m.setMatrixAt(k, M)
          m.setColorAt(k, col)
        }
    for (const [m, n] of [[r.solid, ns], [r.glass, nh], [r.ghost, ng]] as [THREE.InstancedMesh, number][]) {
      m.count = n
      m.visible = n > 0
      m.instanceMatrix.needsUpdate = true
      if (m.instanceColor) m.instanceColor.needsUpdate = true
    }
  }

  let lastKey = ''
  function build(pal: Palette, force = false) {
    if (!stage) return
    const key = JSON.stringify(tensors) + (narrow ? `|${viewW}` : '')
    if (!force && key === lastKey) return
    lastKey = key
    const L = stage.labels
    L.begin('t')
    const blocks = tensors.filter((t): t is T => typeof t !== 'string')
    // reuse blocks whose shape did not change; rebuild the rest
    blocks.forEach((t, k) => {
      const [D, R, K] = as3(t.shape)
      const old = recs[k]
      if (old && old.D === D && old.R === R && old.K === K) return
      if (old) dropRec(old)
      recs[k] = makeRec(D, R, K)
      group.add(recs[k].obj)
    })
    for (const r of recs.slice(blocks.length)) dropRec(r)
    recs.length = blocks.length

    // widths first, so a long chain can wrap into rows on a narrow screen
    const titleOf = (t: T) => t.title ?? `${t.name ? t.name + ' ' : ''}(${t.shape.join(', ')})`
    // a block's slot is also wide enough for its title (titles are a fixed size on screen,
    // so in a small view they take up more of the world: 0.08 per letter on a wide view, 0.13 on a phone)
    // the row-axis name: "L↓" upright (short), "L_q↓" written across (short with a subscript), else turned a quarter
    const rowName = (t: T) => (t.axes ? (t.axes.length === 1 ? '' : t.axes.length === 2 ? t.axes[0] : t.axes[1]) : '')
    const rowKind = (n: string) => (!n ? 'none' : n.length <= 3 && !n.includes('_') ? 'upright' : n.length <= 4 ? 'across' : 'turned')
    // a name written across needs room on the block's left, clear of an operator before it
    const rowPad = (t: T) => (rowKind(rowName(t)) === 'across' ? (narrow ? 0.11 : 0.07) * (rowName(t).length + 1) : 0)
    const widthOf = (t: T | string) => (typeof t === 'string' ? Math.min(1.6, Math.max(0.6, 0.45 + 0.085 * t.length))
      : rowPad(t) + Math.max(as3(t.shape)[2] * C + 0.12, titleOf(t).length * (narrow ? 0.13 : 0.08)))
    const heightOf = (t: T | string) => (typeof t === 'string' ? 0 : as3(t.shape)[1] * C)
    const total = tensors.reduce((a, t) => a + widthOf(t), 0)
    const tallest = Math.max(0.3, ...tensors.map(heightOf))
    // pack into rows (cutting only before an operator) no wider than the screen can show with readable labels
    let rows: (T | string)[][] = [tensors]
    if (narrow && blocks.length >= 3 && total / tallest > 2.5) {
      const maxRow = Math.max(viewW / 75, total / 2.6, ...tensors.map(widthOf))
      rows = [[]]
      let acc = 0
      tensors.forEach((t, i) => {
        const wt = widthOf(t)
        const next = tensors[i + 1]
        // break before this operator when it and half of the next block would overflow the row
        if (typeof t === 'string' && acc > 0 && acc + wt + (next ? widthOf(next) / 2 : 0) > maxRow) { rows.push([]); acc = 0 }
        rows[rows.length - 1].push(t)
        acc += wt
      })
    }
    const rowW = rows.map((r) => r.reduce((a, t) => a + widthOf(t), 0))
    const rowH = rows.map((r) => Math.max(0.3, ...r.map(heightOf)))

    let k = 0
    const pts: V3[] = []
    const opAt: [number, number, string][] = []
    rows.forEach((row, ri) => {
      let x = (Math.max(...rowW) - rowW[ri]) / 2
      // row 0 is centered on y = 0; each next row sits under the last, leaving room for the axis names and its titles
      let y0 = 0
      for (let q = 1; q <= ri; q++) y0 -= rowH[q - 1] / 2 + 1.05 + rowH[q] / 2
      for (const t of row) {
        if (typeof t === 'string') {
          const gap = widthOf(t)
          opAt.push([x + gap / 2 - 0.06, y0, t])
          pts.push([x + 0.1, y0, 0]) // an operator can start a wrapped row: keep it in the view
          x += gap
          continue
        }
        const r = recs[k]
        fillRec(r, t, pal)
        r.obj.visible = !t.hidden
        const { D, R, K } = r
        const w = K * C, h = R * C, dep = D * C
        const pad = rowPad(t)
        const slot = widthOf(t) - pad
        x += pad + (slot - (w + 0.12)) / 2 // centered in its slot (after the room for an across row name)
        // block spans x..x+w, y y0−h/2..y0+h/2, z −dep/2..dep/2
        r.obj.position.set(x + C / 2, y0 + h / 2 - C / 2, dep / 2 - C / 2)
        const cx = x + w / 2
        const top = y0 + h / 2, bot = y0 - h / 2
        pts.push([x, bot, -dep / 2], [x + w, top, dep / 2], [x, top, -dep / 2], [x + w, bot, dep / 2])
        // labels: name and shape above, axis names along the edges (anchors padded into the fit, so labels have room)
        const title = titleOf(t)
        if (t.hidden) { pts.push([cx, top + 0.2, -dep / 2], [cx, bot - 0.18, dep / 2], [x - 0.22, y0, dep / 2]); k++; x += w + 0.12 + (slot - (w + 0.12)) / 2; continue }
        L.set('t', `${k}:title`, title, [cx, top, -dep / 2], { role: 'name', anchor: 'above', parent: group })
        pts.push([cx, top + 0.2, -dep / 2])
        if (t.axes) {
          const ax = t.axes.length === 1 ? ['', '', t.axes[0]] : t.axes.length === 2 ? ['', t.axes[0], t.axes[1]] : t.axes
          if (ax[2]) { L.set('t', `${k}:cols`, `${ax[2]} →`, [cx, bot, dep / 2], { role: 'axis', anchor: 'below', parent: group }); pts.push([cx, bot - 0.18, dep / 2]) }
          // the row-axis name reads downward along the left edge (vertical text, never a squeezed sprite);
          // short names stand upright ("L" over "↓"); a short name with a subscript ("L_q") is written across, never
          // turned or stacked letter by letter (neither would read); longer ones are turned a quarter (the arrow then points down)
          if (ax[1]) {
            const kind = rowKind(ax[1])
            L.set('t', `${k}:rows`, kind === 'turned' ? `${ax[1]} →` : `${ax[1]}↓`, [x, y0, dep / 2], { role: 'axis', anchor: 'left', vertical: kind === 'upright' ? 'upright' : kind === 'turned', parent: group })
            pts.push([x - (kind === 'across' ? pad : 0.22), y0, dep / 2])
          }
          if (ax[0] && D > 1) { L.set('t', `${k}:depth`, `${ax[0]} ↗`, [x + w, top, -dep / 2], { role: 'axis', anchor: 'right', parent: group }); pts.push([x + w + 0.12 + 0.06 * ax[0].length, top, -dep / 2]) }
        }
        k++
        x += w + 0.12 + (slot - (w + 0.12)) / 2
      }
    })
    opAt.forEach(([ox, oy, text], i) => L.set('t', `op${i}`, text, [ox, oy, 0], { role: 'op', parent: group }))
    L.end('t')

    // center everything
    const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity]
    for (const p of pts) for (let a = 0; a < 3; a++) { lo[a] = Math.min(lo[a], p[a]); hi[a] = Math.max(hi[a], p[a]) }
    const c = [0, 1, 2].map((a) => (lo[a] + hi[a]) / 2)
    group.position.set(-c[0], -c[1], -c[2])
    stage.fit(pts.map((p) => [p[0] - c[0], p[1] - c[1], p[2] - c[2]] as V3))
    flyKey = ''
    fly(pal)
    stage.render()
  }

  // ---- explode: copies of cells flying from one block to another ----
  let flyers: THREE.InstancedMesh | null = null
  let flyKey = ''
  const ease = (u: number) => u * u * (3 - 2 * u)
  function fly(pal: Palette) {
    if (!stage) return
    const ex = explode
    const blocks = tensors.filter((t): t is T => typeof t !== 'string')
    const on = !!ex && ex.t > 0 && ex.t < 1 && !!recs[ex.from] && !!recs[ex.to] && !!blocks[ex.to]
    if (!on) { if (flyers) flyers.visible = false; return }
    const A = recs[ex!.from], B = recs[ex!.to], tb = blocks[ex!.to]
    const n = B.D * B.R * B.K
    if (!flyers || flyers.instanceMatrix.count < n) {
      if (flyers) { flyers.dispose(); flyers.removeFromParent() }
      flyers = cellMesh(geo, mat.solidV, n)
      group.add(flyers)
    }
    const key = `${ex!.from}>${ex!.to}|${n}`
    const recolor = key !== flyKey
    flyKey = key
    const M = new THREE.Matrix4()
    const col = new THREE.Color()
    const at = (r: Rec, d: number, i: number, j: number) => new THREE.Vector3(j * C, -i * C, -d * C).add(r.obj.position)
    let m = 0
    for (let d = 0; d < B.D; d++) {
      // slab d leaves a little after slab d − 1; all land by t = 1
      const u = ease(Math.min(1, Math.max(0, (ex!.t - 0.45 * (B.D > 1 ? d / (B.D - 1) : 0)) / 0.55)))
      for (let i = 0; i < B.R; i++)
        for (let j = 0; j < B.K; j++) {
          const [sd, si, sj] = ex!.map(d, i, j)
          const p0 = at(A, sd, si, sj), p1 = at(B, d, i, j)
          const p = p0.lerp(p1, u)
          p.z += Math.sin(Math.PI * u) * 0.35 // lift toward the viewer on the way, so copies don't pass through blocks
          M.makeTranslation(p.x, p.y, p.z)
          flyers.setMatrixAt(m, M)
          if (recolor) { cellColor(tb, d, i, j, pal, col); flyers.setColorAt(m, col) }
          m++
        }
    }
    flyers.count = m
    flyers.visible = true
    flyers.instanceMatrix.needsUpdate = true
    if (flyers.instanceColor) flyers.instanceColor.needsUpdate = true
  }
  $effect(() => {
    void explode?.t; void explode?.from; void explode?.to
    if (stage) { fly(stage.palette()); stage.render() }
  })

  /** under 480 px a long chain wraps into rows */
  let viewW = $state(0)
  const narrow = $derived(viewW > 0 && viewW < 480)
  function setup(s: Stage) {
    stage = s
    s.scene.add(group)
    const measure = () => { viewW = Math.round(s.dom.clientWidth / 20) * 20 }
    const ro = new ResizeObserver(measure)
    ro.observe(s.dom)
    measure()
    const pal = s.palette()
    themeMaterials(pal)
    build(pal, true)
    s.onTheme((p) => { themeMaterials(p); build(p, true) })
    return () => {
      ro.disconnect()
      if (flyers) { flyers.dispose(); flyers = null }
      for (const r of recs) dropRec(r)
      recs = []
      geo.dispose()
      for (const m of Object.values(mat)) m.dispose()
      stage = null
      lastKey = ''
    }
  }

  $effect(() => {
    void JSON.stringify(tensors)
    void viewW
    if (stage) build(stage.palette())
  })
</script>

<Stage3D opts={{ kind: 'tensors', view }} {ariaLabel} {height} {fallback} onready={setup} />
