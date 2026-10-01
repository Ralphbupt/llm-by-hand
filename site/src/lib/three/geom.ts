/**
 * Pure helpers for the 3D views: no DOM and no three.js, so they are unit-tested in geom.test.ts.
 * Ticks, camera fitting, the WebGL context budget, label placement, contour lines, tensor see-through rules.
 */

export type V3 = [number, number, number]

// ---- ticks ---------------------------------------------------------------------------------

/** A "nice" step (1, 2, 2.5 or 5 × 10^k) that cuts `span` into about `count` parts. */
export function niceStep(span: number, count = 5): number {
  if (!(span > 0) || !Number.isFinite(span)) return 1
  const raw = span / Math.max(1, count)
  const p = Math.pow(10, Math.floor(Math.log10(raw)))
  const m = raw / p
  return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10) * p
}

/** Nice tick values inside [lo, hi] (inclusive), about `count` steps apart. */
export function niceTicks(lo: number, hi: number, count = 5, step = niceStep(Math.abs(hi - lo), count)): number[] {
  if (!Number.isFinite(lo) || !Number.isFinite(hi)) return []
  if (hi < lo) [lo, hi] = [hi, lo]
  const out: number[] = []
  const first = Math.ceil(lo / step - 1e-9)
  for (let k = first; k * step <= hi + step * 1e-9 && out.length < 50; k++) out.push(Number((k * step).toPrecision(12)) + 0)
  return out
}

/** A tick label: short, with a real minus sign, never "-0". */
export function fmtTick(v: number): string {
  if (Math.abs(v) < 1e-12) return '0'
  return String(Number(v.toPrecision(4))).replace('-', '−')
}

// ---- camera --------------------------------------------------------------------------------

const DEG = Math.PI / 180
const sub = (a: V3, b: V3): V3 => [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
const dot = (a: V3, b: V3) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
const cross = (a: V3, b: V3): V3 => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
const norm = (a: V3): V3 => { const l = Math.hypot(...a) || 1; return [a[0] / l, a[1] / l, a[2] / l] }

/**
 * Unit vector from the target toward the camera. Azimuth (degrees) turns from +z (straight in front) toward +x
 * (the right); elevation (degrees) lifts toward +y.
 */
export function dirFromAngles(azimuth: number, elevation: number): V3 {
  const a = azimuth * DEG, e = elevation * DEG
  return [Math.sin(a) * Math.cos(e), Math.sin(e), Math.cos(a) * Math.cos(e)]
}

export function anglesFromDir(d: V3): { azimuth: number; elevation: number } {
  const [x, y, z] = norm(d)
  return { azimuth: Math.atan2(x, z) / DEG, elevation: Math.asin(Math.max(-1, Math.min(1, y))) / DEG }
}

/**
 * Camera distance (from `center`, along `dir`) at which every point is inside the picture, with `margin` of the
 * half-width kept free on each side. tanH / tanV are the tangents of half the horizontal / vertical field of view.
 * Exact for perspective: points nearer the camera need more room than far ones.
 */
export function fitDistance(points: V3[], center: V3, dir: V3, tanH: number, tanV: number, margin = 0.08): number {
  const back = norm(dir)
  let right = cross([0, 1, 0], back)
  right = Math.hypot(...right) < 1e-6 ? [1, 0, 0] : norm(right)
  const up = cross(back, right)
  const th = tanH * (1 - margin), tv = tanV * (1 - margin)
  let D = 0
  for (const p of points) {
    const q = sub(p, center)
    const z = dot(q, back)
    D = Math.max(D, z + Math.abs(dot(q, right)) / th, z + Math.abs(dot(q, up)) / tv)
  }
  return D
}

/**
 * Where to put the camera so the points fill the picture and sit in its middle: perspective makes near parts look
 * bigger, so the bounding-box center is not the picture center. Returns the look-at point and the distance.
 */
export function fitView(points: V3[], dir: V3, tanH: number, tanV: number, margin = 0.08): { center: V3; distance: number } {
  const [lo, hi] = bounds(points)
  let c: V3 = [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2]
  const back = norm(dir)
  let right = cross([0, 1, 0], back)
  right = Math.hypot(...right) < 1e-6 ? [1, 0, 0] : norm(right)
  const up = cross(back, right)
  let D = fitDistance(points, c, dir, tanH, tanV, margin)
  for (let it = 0; it < 4; it++) {
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity
    for (const p of points) {
      const q = sub(p, c)
      const depth = D - dot(q, back)
      if (depth <= 1e-6) continue
      const sx = dot(q, right) / depth, sy = dot(q, up) / depth
      x0 = Math.min(x0, sx); x1 = Math.max(x1, sx); y0 = Math.min(y0, sy); y1 = Math.max(y1, sy)
    }
    const mx = ((x0 + x1) / 2) * D, my = ((y0 + y1) / 2) * D
    if (Math.abs(mx) + Math.abs(my) < 1e-4 * D) break
    c = [c[0] + right[0] * mx + up[0] * my, c[1] + right[1] * mx + up[1] * my, c[2] + right[2] * mx + up[2] * my]
    D = fitDistance(points, c, dir, tanH, tanV, margin)
  }
  return { center: c, distance: D }
}

/** Axis-aligned bounds of some points: [min, max]. */
export function bounds(points: V3[]): [V3, V3] {
  const lo: V3 = [Infinity, Infinity, Infinity], hi: V3 = [-Infinity, -Infinity, -Infinity]
  for (const p of points) for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], p[k]); hi[k] = Math.max(hi[k], p[k]) }
  return [lo, hi]
}

/** How much two bounds differ, relative to the larger one's biggest side (0 = same; 0.15 = a 15% change). */
export function boundsChange(a: [V3, V3], b: [V3, V3]): number {
  const size = Math.max(...[0, 1, 2].map((k) => Math.max(a[1][k] - a[0][k], b[1][k] - b[0][k])), 1e-9)
  let d = 0
  for (let k = 0; k < 3; k++) d = Math.max(d, Math.abs(a[0][k] - b[0][k]), Math.abs(a[1][k] - b[1][k]))
  return d / size
}

// ---- WebGL context budget ------------------------------------------------------------------

export type Slot = { id: number; live: boolean; visible: boolean; lastSeen: number; pinned?: boolean }

/**
 * Which live views to release so one more (`requester`) fits under `max` live WebGL contexts:
 * offscreen views first, least recently seen first, then the oldest visible ones; never a pinned one (in use).
 */
export function pickVictims(slots: Slot[], requester: number, max: number): number[] {
  const live = slots.filter((s) => s.live && s.id !== requester)
  const need = live.length + 1 - max
  if (need <= 0) return []
  return live
    .filter((s) => !s.pinned)
    .sort((a, b) => Number(a.visible) - Number(b.visible) || a.lastSeen - b.lastSeen)
    .slice(0, need)
    .map((s) => s.id)
}

// ---- labels --------------------------------------------------------------------------------

export type LabelItem = {
  /** top-left corner in px (already offset for the anchor) */
  x: number; y: number; w: number; h: number
  priority: number
  /** may move up/down by its own height to dodge a collision (ticks may not) */
  nudge?: boolean
  /** never hides (e.g. the name of a path, which is its legend): steps further away, up to 3 rows, then stays put */
  keep?: boolean
}
export type Placed = { x: number; y: number; show: boolean }

/**
 * Greedy overlap removal: higher priority places first (ties keep their order); a label that overlaps a placed one
 * tries one step up, then one step down, then hides (a `keep` label tries up to 3 rows each way, then shows anyway).
 * Labels are pushed back inside the W×H view (pad px), and hidden
 * when more than half of them would have to move to fit (their anchor is outside the picture).
 */
export function placeLabels(items: LabelItem[], W: number, H: number, pad = 2, gap = 2): Placed[] {
  const out: Placed[] = items.map(() => ({ x: 0, y: 0, show: false }))
  const order = items.map((_, i) => i).sort((a, b) => items[b].priority - items[a].priority || a - b)
  const taken: { x: number; y: number; w: number; h: number }[] = []
  const hits = (x: number, y: number, w: number, h: number) =>
    taken.some((t) => x < t.x + t.w + gap && x + w + gap > t.x && y < t.y + t.h + gap && y + h + gap > t.y)
  for (const i of order) {
    const it = items[i]
    if (!Number.isFinite(it.x) || !Number.isFinite(it.y)) continue
    const cx = Math.min(Math.max(it.x, pad), Math.max(pad, W - pad - it.w))
    const cy0 = Math.min(Math.max(it.y, pad), Math.max(pad, H - pad - it.h))
    if (Math.abs(cx - it.x) > it.w / 2 + pad || Math.abs(cy0 - it.y) > it.h / 2 + pad) continue
    const row = it.h + gap
    const tries = it.keep ? [0, -row, row, -2 * row, 2 * row, -3 * row, 3 * row] : it.nudge ? [0, -row, row] : [0]
    for (const dy of tries) {
      const cy = cy0 + dy
      if (cy < pad - 0.5 || cy + it.h > H - pad + 0.5) continue
      if (hits(cx, cy, it.w, it.h)) continue
      taken.push({ x: cx, y: cy, w: it.w, h: it.h })
      out[i] = { x: cx, y: cy, show: true }
      break
    }
    if (it.keep && !out[i].show) { taken.push({ x: cx, y: cy0, w: it.w, h: it.h }); out[i] = { x: cx, y: cy0, show: true } }
  }
  return out
}

// ---- contours ------------------------------------------------------------------------------

/**
 * Contour lines of a height grid by marching squares. `vals` has n×n values, row by row (index i*n + j).
 * Returns segments as flat [i0, j0, i1, j1, …] in fractional grid coordinates; non-finite cells are skipped.
 */
export function contourSegments(vals: ArrayLike<number>, n: number, levels: number[]): number[] {
  const out: number[] = []
  const at = (i: number, j: number) => vals[i * n + j]
  for (const L of levels) {
    for (let i = 0; i < n - 1; i++)
      for (let j = 0; j < n - 1; j++) {
        const a = at(i, j), b = at(i, j + 1), c = at(i + 1, j + 1), d = at(i + 1, j)
        if (![a, b, c, d].every(Number.isFinite)) continue
        // crossing points on the four edges (top a-b, right b-c, bottom d-c, left a-d)
        const pts: [number, number][] = []
        const edge = (v0: number, v1: number, p0: [number, number], p1: [number, number]) => {
          if ((v0 < L) === (v1 < L)) return
          const t = (L - v0) / (v1 - v0)
          pts.push([p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t])
        }
        edge(a, b, [i, j], [i, j + 1])
        edge(b, c, [i, j + 1], [i + 1, j + 1])
        edge(d, c, [i + 1, j], [i + 1, j + 1])
        edge(a, d, [i, j], [i + 1, j])
        for (let k = 0; k + 1 < pts.length; k += 2) out.push(pts[k][0], pts[k][1], pts[k + 1][0], pts[k + 1][1])
      }
  }
  return out
}

// ---- tensors -------------------------------------------------------------------------------

/**
 * Should the plain cells of a (depth, rows, cols) block be see-through? Only when a highlighted range starts behind
 * the front slice, where solid cells would hide it. Otherwise everything is drawn solid (cleaner, cheaper).
 */
export function needsSeeThrough(depth: number, highlight: { from: number[] }[] = []): boolean {
  return depth > 1 && highlight.some((r) => (r.from[0] ?? 0) > 0)
}
