<script lang="ts">
  /**
   * Points (and optional arrows from the origin, and trails) in 3D, with labels.
   * Used for word vectors in 3D, point clouds that move over time (diffusion), and any 3-number data.
   * Drag to orbit, scroll or pinch to zoom. Coordinates are data units; `range` sets the visible cube.
   * Data (x, y, z) maps to world (x, z, −y): data z is "up".
   *
   * Drawing: all dots are one instanced mesh (moved in place when only positions change, e.g. a time slider),
   * trails are one or two screen-width line batches, arrows are solid shafts with cones.
   */
  import type { Snippet } from 'svelte'
  import * as THREE from 'three'
  import Stage3D from './Stage3D.svelte'
  import type { Palette, Stage, ViewAngles } from '@lib/three/stage'
  import { arrow3, clearGroup, dots as dotsMesh, fatLine, fatSegments, floorGrid, hairlines, mix, setDots, toneColor, type Tone } from '@lib/three/kit'
  import { fmtTick, niceStep, niceTicks, type V3 } from '@lib/three/geom'

  type Pt = { p: [number, number, number]; tone?: Tone; color?: string; label?: string; size?: number }
  type Props = {
    points: Pt[]
    /** draw each point as an arrow from the origin (vectors) instead of a dot */
    arrows?: boolean
    /** polylines, e.g. one point's path through time; colored trails (not dim/fg) are drawn thicker */
    trails?: { pts: [number, number, number][]; tone?: Tone; color?: string }[]
    range?: number
    axes?: [string, string, string]
    highlight?: number | null
    ariaLabel?: string
    height?: string
    /** floor grid spacing in data units (default: a round step, so integer data sits on grid lines) */
    gridStep?: number
    /**
     * data z of the floor grid. Default: 0, or the bottom of the cube when the data sits on it (time as the third
     * axis starting at t = 0 at the bottom)
     */
    floorAt?: number
    /** dashed lines from each point down to the floor (default: on for arrows) */
    dropLines?: boolean
    /** tick numbers on the floor axes (default on) */
    ticks?: boolean
    /** an arc between two points' arrows (indices into `points`), labeled at its middle, e.g. "cos 0.80" */
    angleArc?: { a: number; b: number; label?: string; tone?: Tone } | null
    /**
     * the shadow of point `of` on the line through point `onto`: a dashed drop from `of` square onto that line,
     * and a thick segment from the origin to the foot (its signed length is of · onto / |onto|)
     */
    projection?: { of: number; onto: number; label?: string; tone?: Tone } | null
    /** camera angle in degrees instead of the default three-quarter view */
    view?: ViewAngles
    /** shown instead of the 3D view when the browser has no WebGL */
    fallback?: Snippet
  }
  let {
    points, arrows = false, trails = [], range = 1, axes = ['x', 'y', 'z'], highlight = null,
    ariaLabel = '3D points', height = '360px', gridStep, floorAt, dropLines, ticks = true, view, fallback,
    angleArc = null, projection = null,
  }: Props = $props()

  let stage: Stage | null = null
  const content = new THREE.Group()
  const trailGroup = new THREE.Group()
  const frameGroup = new THREE.Group()
  const overlayGroup = new THREE.Group()
  const S = 1.2 // world half-size of the cube
  const w = (v: number) => (v / range) * S
  const toV = (p: [number, number, number]) => new THREE.Vector3(w(p[0]), w(p[2]), -w(p[1]))
  const sphere = new THREE.SphereGeometry(1, 16, 12)
  let dotMesh: THREE.InstancedMesh | null = null

  function colorOf(pal: Palette, tone?: Tone, color?: string) {
    return color ? new THREE.Color(color) : toneColor(pal, tone ?? 'accent')
  }

  /** data z of the floor */
  function floorZ(): number {
    if (floorAt !== undefined) return floorAt
    let lo = Infinity
    for (const pt of points) lo = Math.min(lo, pt.p[2])
    for (const t of trails) for (const p of t.pts) lo = Math.min(lo, p[2])
    return Number.isFinite(lo) && lo <= -range * 0.98 ? -range : 0
  }

  let lastFrameKey = ''
  function drawFrame(pal: Palette, force = false) {
    if (!stage) return
    const fz = floorZ()
    const key = `${fz}|${range}|${gridStep}|${axes.join()}|${ticks}`
    if (!force && key === lastFrameKey) return
    lastFrameKey = key
    clearGroup(frameGroup)
    const y = w(fz)
    // floor grid at round data values
    const st = gridStep ?? niceStep(2 * range, 5)
    const gv = niceTicks(-range, range, 5, st)
    frameGroup.add(floorGrid(gv.map(w), gv.map((v) => -w(v)), { x0: -S, x1: S, z0: -S, z1: S }, y, mix(pal.bg, pal.line, 1)))
    // axes: x and y on the floor, z up through the origin
    const zLo = fz === 0 ? (arrows ? Math.min(0, ...points.map((pt) => toV(pt.p).y)) - 0.1 : -S) : y
    frameGroup.add(fatLine([new THREE.Vector3(-S, y, 0), new THREE.Vector3(S, y, 0)], pal.dim, 1.25))
    frameGroup.add(fatLine([new THREE.Vector3(0, y, S), new THREE.Vector3(0, y, -S)], pal.dim, 1.25))
    frameGroup.add(fatLine([new THREE.Vector3(0, zLo, 0), new THREE.Vector3(0, S, 0)], pal.dim, 1.25))
    const L = stage.labels
    L.begin('axes')
    L.set('axes', 'ax', axes[0], [S * 1.12, y, 0], { role: 'axis', anchor: 'right', offset: [4, 0] })
    L.set('axes', 'ay', axes[1], [0, y, -S * 1.08], { role: 'axis', anchor: 'above' })
    L.set('axes', 'az', axes[2], [0, S * 1.06, 0], { role: 'axis', anchor: 'above' })
    if (ticks)
      for (const v of gv) {
        if (Math.abs(v) < 1e-9 || Math.abs(v) > range) continue
        L.set('axes', `tx${v}`, fmtTick(v), [w(v), y, 0], { role: 'tick', anchor: 'below' })
        L.set('axes', `ty${v}`, fmtTick(v), [0, y, -w(v)], { role: 'tick', anchor: 'left' })
      }
    L.end('axes')
  }

  let lastTrailKey = ''
  function drawTrails(pal: Palette, force = false) {
    const key = trails.map((t) => `${t.pts.length}:${t.tone}:${t.color}:${t.pts[0]?.join()}:${t.pts.at(-1)?.join()}`).join('|')
    if (!force && key === lastTrailKey) return
    lastTrailKey = key
    clearGroup(trailGroup)
    // two batches: emphasized trails (a semantic tone other than dim/fg) thick, context trails thin
    const batches = { thick: { p: [] as number[], c: [] as number[] }, thin: { p: [] as number[], c: [] as number[] } }
    for (const t of trails) {
      if (t.pts.length < 2) continue
      const strong = !t.color && t.tone !== undefined && t.tone !== 'dim' && t.tone !== 'fg'
      // context trails are blended toward the background instead of being transparent (no sorting, same look)
      const c = strong ? colorOf(pal, t.tone) : mix(pal.bg, colorOf(pal, t.tone, t.color), 0.6)
      const b = strong ? batches.thick : batches.thin
      for (let i = 0; i + 1 < t.pts.length; i++) {
        const a = toV(t.pts[i]), z = toV(t.pts[i + 1])
        b.p.push(a.x, a.y, a.z, z.x, z.y, z.z)
        b.c.push(c.r, c.g, c.b, c.r, c.g, c.b)
      }
    }
    if (batches.thin.p.length) trailGroup.add(fatSegments(batches.thin.p, batches.thin.c, pal.dim, 1.25))
    if (batches.thick.p.length) { const l = fatSegments(batches.thick.p, batches.thick.c, pal.accent, 2.75); l.renderOrder = 1; trailGroup.add(l) }
  }

  let lastArrowKey = ''
  function drawContent(pal: Palette, force = false) {
    if (!stage) return
    const L = stage.labels
    L.begin('pts')
    const fy = w(floorZ())
    // dots: one instanced mesh, updated in place when the count is unchanged
    const ds = arrows ? [] : points.map((pt, i) => ({ at: toV(pt.p), r: (pt.size ?? 0.035) * (highlight === i ? 1.8 : 1), color: colorOf(pal, pt.tone, pt.color) }))
    if (dotMesh && (force || dotMesh.instanceMatrix.count < ds.length || !ds.length)) { dotMesh.removeFromParent(); clearGroup(dotMesh); dotMesh = null }
    if (ds.length) {
      if (dotMesh) setDots(dotMesh, ds)
      else { dotMesh = dotsMesh(ds, sphere); stage.scene.add(dotMesh) }
    }
    // arrows and drop lines: few objects, rebuilt only when they change
    const aKey = `${arrows}|${highlight}|${dropLines}|${fy}|` + points.map((p) => `${p.p.join()}:${p.tone}:${p.color}`).join(';')
    if (force || aKey !== lastArrowKey) {
      lastArrowKey = aKey
      clearGroup(content)
      const drops: number[] = []
      points.forEach((pt, i) => {
        const v = toV(pt.p)
        if (arrows && v.length() > 1e-6) content.add(arrow3(new THREE.Vector3(), v, colorOf(pal, pt.tone, pt.color), highlight === i ? 0.022 : 0.012))
        if (dropLines ?? arrows) drops.push(v.x, fy, v.z, v.x, v.y, v.z)
      })
      if (drops.length) content.add(hairlines(drops, pal.dim, { dashed: true }))
    }
    points.forEach((pt, i) => {
      if (!pt.label) return
      const hi = highlight === i
      L.set('pts', `p${i}`, pt.label, toV(pt.p), { role: hi ? 'name' : 'callout', anchor: 'above', tone: pt.color ? undefined : (pt.tone ?? 'accent'), color: pt.color, priority: hi ? 45 : pt.tone === 'dim' ? 30 : 38 })
    })
    // an arrow whose name is left out still has a tip: an axis name or tick must not sit on it (it would read as its name)
    stage.labels.obstacles = arrows ? points.filter((pt) => !pt.label).map((pt) => ({ at: toV(pt.p), r: 7 })) : []
    L.end('pts')
  }

  let lastOverlayKey = ''
  function drawOverlays(pal: Palette, force = false) {
    if (!stage) return
    const key = JSON.stringify([angleArc, projection, angleArc && points[angleArc.a]?.p, angleArc && points[angleArc.b]?.p,
      projection && points[projection.of]?.p, projection && points[projection.onto]?.p])
    if (!force && key === lastOverlayKey) return
    lastOverlayKey = key
    clearGroup(overlayGroup)
    const L = stage.labels
    L.begin('over')
    if (angleArc && points[angleArc.a] && points[angleArc.b]) {
      const A = toV(points[angleArc.a].p), B = toV(points[angleArc.b].p)
      const la = A.length(), lb = B.length()
      if (la > 1e-6 && lb > 1e-6) {
        const ua = A.clone().normalize(), ub = B.clone().normalize()
        const ang = ua.angleTo(ub)
        // the arc turns from a toward b in their common plane (any perpendicular when they point opposite ways)
        let n = ua.clone().cross(ub)
        if (n.length() < 1e-6) n = Math.abs(ua.y) < 0.9 ? ua.clone().cross(new THREE.Vector3(0, 1, 0)) : ua.clone().cross(new THREE.Vector3(1, 0, 0))
        n.normalize()
        const r = Math.min(la, lb) * 0.38
        const arc: THREE.Vector3[] = []
        const N = Math.max(8, Math.round(ang * 24))
        for (let i = 0; i <= N; i++) arc.push(ua.clone().applyAxisAngle(n, (ang * i) / N).multiplyScalar(r))
        const c = toneColor(pal, angleArc.tone ?? 'fg')
        if (ang > 1e-3) overlayGroup.add(fatLine(arc, c, 2))
        if (angleArc.label) {
          // just outside the arc, at its middle
          const mid = ua.clone().applyAxisAngle(n, ang / 2).multiplyScalar(r * 1.25)
          L.set('over', 'arc', angleArc.label, mid, { role: 'callout', anchor: 'above', tone: angleArc.tone ?? 'fg', priority: 34, keep: true })
        }
      }
    }
    if (projection && points[projection.of] && points[projection.onto]) {
      const P = toV(points[projection.of].p), O = toV(points[projection.onto].p)
      const lo2 = O.lengthSq()
      if (lo2 > 1e-9) {
        const foot = O.clone().multiplyScalar(P.dot(O) / lo2)
        const c = toneColor(pal, projection.tone ?? 'fg')
        // the shadow along the onto-line (behind the origin when the dot product is negative)
        if (foot.length() > 1e-6) {
          // drawn over the arrow it lies on (otherwise the shaft hides it)
          const l = fatLine([new THREE.Vector3(), foot], c, 3.5)
          l.material.depthTest = false
          l.renderOrder = 3
          overlayGroup.add(l)
        }
        overlayGroup.add(fatLine([P, foot], c, 1.5, { dashed: true }))
        // the label under the middle of the shadow, not at its end (where the arrow tips and their names crowd)
        if (projection.label) L.set('over', 'proj', projection.label, foot.clone().multiplyScalar(0.5), { role: 'callout', anchor: 'below', offset: [0, 10], tone: projection.tone ?? 'fg', priority: 33 })
      }
    }
    L.end('over')
  }

  function redraw(force = false) {
    if (!stage) return
    const pal = stage.palette()
    drawFrame(pal, force)
    drawTrails(pal, force)
    drawContent(pal, force)
    drawOverlays(pal, force)
    stage.render()
  }

  function setup(s: Stage) {
    stage = s
    s.scene.add(frameGroup, trailGroup, content, overlayGroup)
    const pts: V3[] = []
    // arrows from the origin: frame the floor, the top of the up axis and the arrow tips (not the empty bottom half
    // of the cube)
    const yLo = arrows ? w(floorZ()) : -S
    for (const x of [-S, S]) for (const y of [yLo, S]) for (const z of [-S, S]) pts.push([x, y, z])
    if (arrows) for (const pt of points) { const v = toV(pt.p); pts.push([v.x, v.y - 0.1, v.z]) }
    pts.push([S * 1.15, 0, 0], [0, S * 1.15, 0], [0, 0, -S * 1.15])
    s.fit(pts)
    s.onTheme(() => redraw(true))
    redraw(true)
    s.renderNow()
    return () => {
      dotMesh = null
      sphere.dispose()
      stage = null
      lastFrameKey = lastTrailKey = lastArrowKey = lastOverlayKey = ''
    }
  }

  $effect(() => {
    void points.map((p) => p.p.join(',') + (p.color ?? '') + (p.tone ?? '')).join(';')
    void trails.map((t) => t.pts.length).join(',')
    void highlight
    void JSON.stringify([angleArc, projection])
    if (stage) redraw()
  })
</script>

<Stage3D opts={{ kind: 'points', view }} {ariaLabel} {height} {fallback} onready={setup} />
