<script lang="ts">
  /**
   * A 3D surface z = f(x, y) with an optional path and current point on it.
   * Used for loss surfaces: drag to orbit, scroll or pinch to zoom, click the surface to pick a point.
   * World axes: x → right, y (the second input) → depth, height = f.
   * The floor is a flat card with a grid at the tick values and contour lines of the surface (like the 2D map).
   */
  import { onMount, type Snippet } from 'svelte'
  import * as THREE from 'three'
  import Stage3D from './Stage3D.svelte'
  import { webglAvailable, type Palette, type Stage, type ViewAngles } from '@lib/three/stage'
  import {
    arrow3, clearGroup, dots as dotsMesh, fatLine, floorGrid, hairlines, matte, mix, ramp, toneColor, type RampKind, type Tone,
  } from '@lib/three/kit'
  import { contourSegments, fmtTick, niceTicks, type V3 } from '@lib/three/geom'

  type P = { x: number; y: number }
  // semantic tones (AUTHORING.md "Color tokens"); 'cat-N' are plain categories, e.g. two classes
  type Tone3 = Tone
  type Props = {
    f: (x: number, y: number) => number
    xRange: [number, number]
    yRange: [number, number]
    /** reshape heights before drawing, e.g. Math.log1p for losses that span orders of magnitude */
    zTransform?: (z: number) => number
    res?: number
    path?: P[]
    /** several paths at once (e.g. optimizers racing); each gets its own color, and its label sits at its head */
    paths?: { points: P[]; color?: Tone3; label?: string }[]
    point?: P | null
    best?: P | null
    /** a name for `best` (e.g. "minimum"): the minimum then also gets a ring that stays visible under the paths */
    bestLabel?: string
    /** where the paths started: a small ring on the surface */
    start?: P | null
    axes?: { x: string; y: string; z: string }
    /**
     * the height axis caption, when it is not just axes.z. Default: axes.z, or "ln(1 + <axes.z>)" when
     * zTransform is Math.log1p (the height is then not the value itself, and the caption must say so)
     */
    zCaption?: string
    height?: number
    onpick?: (x: number, y: number) => void
    /**
     * with a mouse, show the value under the pointer: "w 1.2 · b −0.4 · loss 0.83" (the real value, not the
     * transformed height). Turn it off while a question on the page asks for a value it would show.
     */
    hover?: boolean
    ariaLabel?: string
    /** legacy: a camera position; only its direction is used (the distance is fitted). Prefer `view`. */
    camera?: [number, number, number]
    /** camera angle in degrees instead of the default three-quarter view */
    view?: ViewAngles
    /** an arrow on the surface from `point` to `step` (e.g. where one gradient step lands) */
    step?: P | null
    /** data points drawn on the surface (e.g. training examples), colored by tone */
    dots?: { x: number; y: number; tone?: Tone3 }[]
    /** fixed height range instead of the sampled min/max (keeps the scale steady while f changes) */
    zRange?: [number, number]
    /** change this number to rebuild the surface (when f itself changes, e.g. a network training) */
    rebuildKey?: number
    /** colors for the lowest and highest heights (overrides `ramp`) */
    tones?: { low: Tone3; high: Tone3 }
    /**
     * color ramp: 'seq' (sizes, losses: card → gray), 'div' (signed values: neg ← card → pos, 0 at the middle),
     * 'prob' (cat-3 ← → cat-1). Default 'auto': 'div' when the heights have both signs, else 'seq'.
     */
    ramp?: RampKind | 'auto'
    /** shown instead of the 3D view when the browser has no WebGL */
    fallback?: Snippet
    /**
     * depth : width of the floor. Default 1 (square). Pass the real ratio of the two ranges when the shape of the
     * floor matters, e.g. a narrow valley: (yRange span) / (xRange span)
     */
    aspect?: number
    /** a short note on a backing plate, floating just above the surface at (x, y) (e.g. "Untrained: … Press Train.") */
    note?: { text: string; x: number; y: number } | null
  }
  let {
    f, xRange, yRange, zTransform = (z) => z, res = 56, path = [], paths = [], point = null, best = null, bestLabel,
    start = null, axes = { x: 'x', y: 'y', z: 'z' }, zCaption, height = 1.3, onpick, hover = true, ariaLabel = '3D surface', camera, view,
    step = null, dots = [], zRange, rebuildKey = 0, tones, ramp: rampKind = 'auto', fallback, aspect = 1, note = null,
  }: Props = $props()

  let has3d = $state(true)
  onMount(() => { has3d = webglAvailable() })

  const SIZE = 2.4 // world width and depth of the surface
  const E = SIZE / 2
  // depth of the floor (the y input); E is half the width, D half the depth
  const DEPTH = $derived(SIZE * Math.min(1, Math.max(0.2, aspect)))
  const D = $derived(DEPTH / 2)
  const FLOOR = -0.06 // the floor card sits a little under the lowest point
  let stage: Stage | null = null
  let zMin = 0, zMax = 1

  // world <-> data
  const wx = (x: number) => ((x - xRange[0]) / (xRange[1] - xRange[0]) - 0.5) * SIZE
  const wz = (y: number) => (0.5 - (y - yRange[0]) / (yRange[1] - yRange[0])) * DEPTH
  const hOf = (v: number) => (Number.isFinite(v) ? ((Math.min(Math.max(v, zMin), zMax) - zMin) / (zMax - zMin || 1)) * height : height)
  const hz = (x: number, y: number) => hOf(zTransform(f(x, y)))
  const ok = (p: P | null | undefined): p is P => !!p && Number.isFinite(p.x) && Number.isFinite(p.y)

  const surfaceGroup = new THREE.Group()
  const pathGroup = new THREE.Group()
  const pointGroup = new THREE.Group()
  let mesh: THREE.Mesh | null = null
  const sphere = new THREE.SphereGeometry(1, 18, 12)

  function buildSurface(pal: Palette) {
    if (!stage) return
    clearGroup(surfaceGroup)
    const n = res + 1
    // sample once: row i runs from the far edge (y = yRange[1]) to the near edge, like PlaneGeometry's vertices
    const vals = new Float64Array(n * n)
    for (let i = 0; i < n; i++)
      for (let j = 0; j < n; j++) {
        const x = xRange[0] + (j / res) * (xRange[1] - xRange[0])
        const y = yRange[1] - (i / res) * (yRange[1] - yRange[0])
        vals[i * n + j] = zTransform(f(x, y))
      }
    let lo = Infinity, hi = -Infinity
    for (const v of vals) if (Number.isFinite(v)) { lo = Math.min(lo, v); hi = Math.max(hi, v) }
    if (!Number.isFinite(lo)) { lo = 0; hi = 1 }
    zMin = zRange ? zRange[0] : lo
    zMax = zRange ? zRange[1] : hi
    const kind: RampKind = rampKind === 'auto' ? (zMin < 0 && zMax > 0 ? 'div' : 'seq') : rampKind
    const colorAt = ramp(pal, kind, tones ? { low: toneColor(pal, tones.low), high: toneColor(pal, tones.high) } : undefined)
    // a signed ramp puts 0 at its middle color
    const tOf = (v: number) => {
      if (kind === 'div' && !tones) { const m = Math.max(Math.abs(zMin), Math.abs(zMax)) || 1; return 0.5 + (Math.min(Math.max(v, -m), m) / m) * 0.5 }
      return Number.isFinite(v) ? (Math.min(Math.max(v, zMin), zMax) - zMin) / (zMax - zMin || 1) : 1
    }

    const geo = new THREE.PlaneGeometry(SIZE, DEPTH, res, res)
    geo.rotateX(-Math.PI / 2) // plane now lies in x/z; y = height
    const pos = geo.attributes.position as THREE.BufferAttribute
    const colors = new Float32Array(pos.count * 3)
    for (let k = 0; k < pos.count; k++) {
      pos.setY(k, hOf(vals[k]))
      const c = colorAt(tOf(vals[k]))
      colors[k * 3] = c.r; colors[k * 3 + 1] = c.g; colors[k * 3 + 2] = c.b
    }
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    geo.computeVertexNormals()
    // solid (no see-through ghosts on steep walls); pushed back a little so the grid lines on it always win
    mesh = new THREE.Mesh(geo, new THREE.MeshLambertMaterial({ vertexColors: true, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 }))
    surfaceGroup.add(mesh)
    stage.labels.occluders = [mesh] // labels behind a hill fade

    // grid lines on the surface every few cells
    const every = Math.max(1, Math.round(res / 10))
    const lp: number[] = []
    for (let i = 0; i <= res; i += every)
      for (let j = 0; j < res; j++) { const a = i * n + j; lp.push(pos.getX(a), pos.getY(a), pos.getZ(a), pos.getX(a + 1), pos.getY(a + 1), pos.getZ(a + 1)) }
    for (let j = 0; j <= res; j += every)
      for (let i = 0; i < res; i++) { const a = i * n + j, b = a + n; lp.push(pos.getX(a), pos.getY(a), pos.getZ(a), pos.getX(b), pos.getY(b), pos.getZ(b)) }
    surfaceGroup.add(hairlines(lp, mix(pal.bg, pal.fg, 0.28)))

    // floor: an opaque card under the surface, with the tick grid and the surface's contour lines
    const pad = 0.04
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(SIZE + 2 * pad, DEPTH + 2 * pad).rotateX(-Math.PI / 2),
      new THREE.MeshBasicMaterial({ color: pal.card, polygonOffset: true, polygonOffsetFactor: 2, polygonOffsetUnits: 2 }))
    floor.position.y = FLOOR
    surfaceGroup.add(floor)
    const xt = niceTicks(xRange[0], xRange[1], 4), yt = niceTicks(yRange[0], yRange[1], 4)
    surfaceGroup.add(floorGrid(xt.map(wx), yt.map(wz), { x0: -E, x1: E, z0: -D, z1: D }, FLOOR, pal.line))
    const levels = Array.from({ length: 8 }, (_, k) => zMin + ((k + 0.5) / 8) * (zMax - zMin))
    const seg = contourSegments(vals, n, levels)
    const cp: number[] = []
    for (let s = 0; s < seg.length; s += 2) cp.push(-E + (seg[s + 1] / res) * SIZE, FLOOR, -D + (seg[s] / res) * DEPTH)
    if (cp.length) surfaceGroup.add(hairlines(cp, mix(pal.card, pal.dim, 0.6)))

    // axes: x along the near edge, y along the left edge, height up the near-left corner
    const axisC = pal.dim
    surfaceGroup.add(fatLine([new THREE.Vector3(-E, FLOOR, D), new THREE.Vector3(E, FLOOR, D)], axisC, 1.25))
    surfaceGroup.add(fatLine([new THREE.Vector3(-E, FLOOR, D), new THREE.Vector3(-E, FLOOR, -D)], axisC, 1.25))
    surfaceGroup.add(fatLine([new THREE.Vector3(-E, FLOOR, D), new THREE.Vector3(-E, height + 0.12, D)], axisC, 1.25))
    // tick marks
    const tk: number[] = []
    for (const v of xt) tk.push(wx(v), FLOOR, D, wx(v), FLOOR, D + 0.05)
    for (const v of yt) tk.push(-E, FLOOR, wz(v), -E - 0.05, FLOOR, wz(v))
    const zt = niceTicks(zMin, zMax, 3)
    for (const v of zt) tk.push(-E, hOf(v), D, -E - 0.05, hOf(v), D + 0.05)
    surfaceGroup.add(hairlines(tk, axisC))

    // labels: tick values and axis captions (HTML, see labels.ts)
    const L = stage.labels
    L.begin('axes')
    xt.forEach((v) => L.set('axes', `x${v}`, fmtTick(v), [wx(v), FLOOR, D + 0.06], { role: 'tick', anchor: 'below' }))
    yt.forEach((v) => L.set('axes', `y${v}`, fmtTick(v), [-E - 0.06, FLOOR, wz(v)], { role: 'tick', anchor: 'left' }))
    zt.forEach((v) => L.set('axes', `z${v}`, fmtTick(v), [-E - 0.06, hOf(v), D + 0.06], { role: 'tick', anchor: 'left' }))
    const zCap = zCaption ?? (zTransform === Math.log1p ? `ln(1 + ${axes.z})` : axes.z)
    L.set('axes', 'cx', axes.x, [E + 0.08, FLOOR, D], { role: 'axis', anchor: 'right' })
    // the depth axis name sits between its two nearest ticks, outside the floor: its far end is often behind the surface
    const yNear = yt.length > 1 ? (wz(yt[0]) + wz(yt[1])) / 2 : D
    L.set('axes', 'cy', axes.y, [-E - 0.06, FLOOR, yNear], { role: 'axis', anchor: 'left' })
    L.set('axes', 'cz', zCap, [-E, height + 0.12, D], { role: 'axis', anchor: 'left' })
    L.end('axes')
  }

  function marker(p: P, color: THREE.Color, r: number) {
    const g = new THREE.Group()
    const y = hz(p.x, p.y)
    const s = new THREE.Mesh(sphere, matte(color))
    s.userData.sharedGeometry = true
    s.scale.setScalar(r)
    s.position.set(wx(p.x), y + r * 0.6, wz(p.y))
    g.add(s)
    // a dashed drop line to the floor and a dot there: where the point is on the map
    g.add(hairlines([wx(p.x), FLOOR, wz(p.y), wx(p.x), y, wz(p.y)], color, { dashed: true }))
    const dot = new THREE.Mesh(new THREE.CircleGeometry(r * 0.7, 20).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color }))
    dot.position.set(wx(p.x), FLOOR, wz(p.y))
    g.add(dot)
    return g
  }

  function addPath(points: P[], color: THREE.Color, px: number, head: boolean, label: string | undefined, k: number, tone?: Tone) {
    const pts = points.filter(ok)
    if (pts.length < 1 || !stage) return
    // lifted a little off the surface (a path lies on the surface, it does not sink into it)
    const lift = 0.02 * height + 0.01
    const v = pts.map((p) => new THREE.Vector3(wx(p.x), hz(p.x, p.y) + lift, wz(p.y)))
    if (v.length >= 2) {
      // where a fold of the surface hides the path, it still shows through as a faint, dashed line: the true
      // path stays readable from any angle, and the solid part is the part really in front
      const ghost = fatLine(v, color, Math.max(1.5, px - 1), { dashed: true })
      const gm = ghost.material
      gm.depthTest = false
      gm.transparent = true
      gm.opacity = 0.5
      ghost.renderOrder = 2
      pathGroup.add(ghost, fatLine(v, color, px))
    }
    const stepN = Math.max(1, Math.ceil(v.length / 60))
    const ds = v.filter((_, i) => i % stepN === 0).map((at) => ({ at, r: 0.02, color }))
    pathGroup.add(dotsMesh(ds, sphere))
    if (head) {
      // the head (where each runner is now) is never hidden
      const hm = dotsMesh([{ at: v[v.length - 1], r: 0.05, color }], sphere)
      const hmat = hm.material as THREE.MeshLambertMaterial
      hmat.depthTest = false
      hm.renderOrder = 3
      pathGroup.add(hm)
    }
    if (label) stage.labels.set('paths', `p${k}`, label, v[v.length - 1], { role: 'callout', anchor: (['above', 'below', 'right', 'left'] as const)[Math.max(0, k) % 4], tone, occlude: !head, priority: 45, keep: true })
  }

  function drawPath(pal: Palette) {
    if (!stage) return
    clearGroup(pathGroup)
    stage.labels.begin('paths')
    addPath(path, pal.fg, 2, false, undefined, -1)
    paths.forEach((p, k) => addPath(p.points, toneColor(pal, p.color ?? 'accent'), 3, true, p.label, k, p.color ?? 'accent'))
    stage.labels.end('paths')
  }

  function drawPoints(pal: Palette) {
    if (!stage) return
    clearGroup(pointGroup)
    stage.labels.begin('pts')
    if (ok(best)) pointGroup.add(marker(best, pal.ok, 0.045))
    if (ok(best) && bestLabel) {
      // the paths end on the minimum and would cover its marker: a wider ring around it, drawn on top
      const ring = new THREE.Mesh(new THREE.TorusGeometry(0.1, 0.01, 8, 36), new THREE.MeshBasicMaterial({ color: pal.ok, depthTest: false }))
      ring.rotation.x = -Math.PI / 2
      ring.renderOrder = 4
      const at = new THREE.Vector3(wx(best.x), hz(best.x, best.y) + 0.03, wz(best.y))
      ring.position.copy(at)
      pointGroup.add(ring)
      stage.labels.set('pts', 'best', bestLabel, at.clone().add(new THREE.Vector3(0, 0, 0.1)), { role: 'callout', anchor: 'below', tone: 'ok', occlude: false, priority: 40, keep: true })
    }
    if (ok(start)) {
      const ring = new THREE.Mesh(new THREE.TorusGeometry(0.07, 0.012, 8, 28), matte(pal.fg))
      ring.rotation.x = -Math.PI / 2
      const at = new THREE.Vector3(wx(start.x), hz(start.x, start.y) + 0.03, wz(start.y))
      ring.position.copy(at)
      pointGroup.add(ring)
      stage.labels.set('pts', 'start', 'start', at, { role: 'callout', anchor: 'below' })
    }
    if (ok(point)) pointGroup.add(marker(point, pal.accent, 0.065))
    if (ok(point) && ok(step)) {
      const from = new THREE.Vector3(wx(point.x), hz(point.x, point.y) + 0.08, wz(point.y))
      const to = new THREE.Vector3(wx(step.x), hz(step.x, step.y) + 0.08, wz(step.y))
      if (from.distanceTo(to) > 1e-3) pointGroup.add(arrow3(from, to, pal.accent, 0.011))
    }
    if (note && Number.isFinite(note.x) && Number.isFinite(note.y))
      stage.labels.set('pts', 'note', note.text, new THREE.Vector3(wx(note.x), hz(note.x, note.y) + 0.12, wz(note.y)), { role: 'callout', anchor: 'above', priority: 45 })
    if (dots.length) pointGroup.add(dotsMesh(dots.map((d) => ({ at: new THREE.Vector3(wx(d.x), hz(d.x, d.y) + 0.03, wz(d.y)), r: 0.03, color: toneColor(pal, d.tone ?? 'fg') })), sphere))
    // axis names and ticks must not sit on the learner's point or the minimum (they would read as its label)
    stage.labels.obstacles = [
      ...(ok(point) ? [{ at: new THREE.Vector3(wx(point.x), hz(point.x, point.y) + 0.04, wz(point.y)), r: 11 }] : []),
      ...(ok(best) ? [{ at: new THREE.Vector3(wx(best.x), hz(best.x, best.y) + 0.03, wz(best.y)), r: 8 }] : []),
    ]
    stage.labels.end('pts')
  }

  function frame() {
    if (!stage) return
    const pts: V3[] = []
    for (const x of [-E - 0.1, E + 0.1]) for (const z of [-D - 0.1, D + 0.1]) for (const y of [FLOOR, height + 0.15]) pts.push([x, y, z])
    stage.fit(pts)
  }

  function redrawAll() {
    if (!stage) return
    const pal = stage.palette()
    buildSurface(pal)
    drawPath(pal)
    drawPoints(pal)
    stage.renderNow()
    stage.render()
  }

  function setup(s: Stage) {
    stage = s
    s.scene.add(surfaceGroup, pathGroup, pointGroup)
    s.onTheme(() => redrawAll())
    frame()
    redrawAll()

    // click (not drag) on the surface → pick (x, y)
    let downAt: { x: number; y: number } | null = null
    const el = s.dom
    const ray = new THREE.Raycaster()
    const onDown = (e: PointerEvent) => (downAt = { x: e.clientX, y: e.clientY })
    const onUp = (e: PointerEvent) => {
      if (!onpick || !downAt || !mesh || !stage || !stage.pickReady()) return
      if (Math.hypot(e.clientX - downAt.x, e.clientY - downAt.y) > 5) return
      const r = el.getBoundingClientRect()
      ray.setFromCamera(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1), stage.camera)
      const hit = ray.intersectObject(mesh)[0]
      if (!hit) return
      const x = xRange[0] + (hit.point.x / SIZE + 0.5) * (xRange[1] - xRange[0])
      const y = yRange[0] + (0.5 - hit.point.z / DEPTH) * (yRange[1] - yRange[0])
      onpick(x, y)
    }
    // hover readout (mouse only, not while dragging), at most once a frame
    const tip = new THREE.Mesh(sphere, matte(new THREE.Color()))
    tip.visible = false
    s.scene.add(tip)
    let raf = 0
    const fmt = (v: number) => (!Number.isFinite(v) ? '∞' : Math.abs(v) >= 100 ? v.toFixed(0) : Math.abs(v) >= 10 ? v.toFixed(1) : v.toFixed(2)).replace('-', '−')
    const clearTip = () => {
      if (!stage) return
      if (tip.visible) { tip.visible = false; stage.labels.begin('hover'); stage.labels.end('hover'); stage.render() }
    }
    const onMove = (e: PointerEvent) => {
      if (!hover || e.pointerType !== 'mouse' || e.buttons) { clearTip(); return }
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        if (!mesh || !stage) return
        const r = el.getBoundingClientRect()
        ray.setFromCamera(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1), stage.camera)
        const hit = ray.intersectObject(mesh)[0]
        if (!hit) { clearTip(); return }
        const x = xRange[0] + (hit.point.x / SIZE + 0.5) * (xRange[1] - xRange[0])
        const y = yRange[0] + (0.5 - hit.point.z / DEPTH) * (yRange[1] - yRange[0])
        const pal = stage.palette()
        ;(tip.material as THREE.MeshLambertMaterial).color.copy(pal.fg)
        tip.scale.setScalar(0.022)
        tip.position.set(wx(x), hz(x, y) + 0.01, wz(y))
        tip.visible = true
        stage.labels.begin('hover')
        stage.labels.set('hover', 'tip', `${axes.x} ${fmt(x)} · ${axes.y} ${fmt(y)} · ${axes.z} ${fmt(f(x, y))}`, tip.position.clone(),
          { role: 'callout', anchor: 'above', priority: 60 })
        stage.labels.end('hover')
        stage.render()
      })
    }
    el.addEventListener('pointerdown', onDown)
    el.addEventListener('pointerup', onUp)
    el.addEventListener('pointermove', onMove)
    el.addEventListener('pointerleave', clearTip)
    return () => {
      cancelAnimationFrame(raf)
      el.removeEventListener('pointermove', onMove)
      el.removeEventListener('pointerleave', clearTip)
      tip.material.dispose()
      el.removeEventListener('pointerdown', onDown)
      el.removeEventListener('pointerup', onUp)
      sphere.dispose()
      stage = null
    }
  }

  // path and point change often; the surface only when the function or ranges change
  $effect(() => {
    void path.length; void path.at(-1)?.x; void path.at(-1)?.y
    for (const p of paths) { void p.points.length; void p.points.at(-1)?.x; void p.points.at(-1)?.y }
    if (stage) { drawPath(stage.palette()); stage.render() }
  })
  $effect(() => {
    void rebuildKey
    if (stage && rebuildKey) redrawAll()
  })
  $effect(() => {
    void step?.x; void step?.y; void dots.length
    void point?.x; void point?.y; void best?.x; void start?.x; void start?.y; void note?.text
    if (stage) { drawPoints(stage.palette()); stage.render() }
  })
</script>

<Stage3D opts={{ kind: 'surface', view, camera, target: [0, height / 2, 0] }} {ariaLabel} aspect="4 / 3" maxHeight="420px" {fallback} onready={setup} />
{#if onpick && has3d}<p class="hint3d">Your first click or tap selects the view. After that, a click or tap on the surface moves the point there.</p>{/if}

<style>
  .hint3d { margin: 0.1rem 0 0; font-size: 0.75rem; color: var(--dim); }
</style>
