/**
 * Net3D's pure part (no three.js, unit-tested): the spec format, the layout (where every node, neuron and cell
 * sits), edge sampling, and what each step shows. Net3D (WebGL) and Net2D (SVG) both draw from `layoutNet`.
 *
 * Coordinates are layout units: data flows along +x, a layer's neurons stand along y. A tensor faces the reader:
 * its columns run along +x, its rows along −y, its channels go back along −z (channel 0 in front).
 */
export type V3 = [number, number, number]
export type NetLayout = 'row' | 'hourglass' | 'unrolled' | 'encdec' | 'stack'
export type NetTone = 'accent' | 'ok' | 'warn' | 'fg' | 'dim' | 'pos' | 'neg' | 'grad' | 'cat-1' | 'cat-2' | 'cat-3' | 'cat-4' | 'cat-5'

export type NetNode = {
  id: string
  /** short name shown in the picture, e.g. "h" or "conv 1" */
  label: string
  /** neurons: a column of discs; tensor: a block of cells; op: a small "+" style disc; block: one solid box */
  kind: 'neurons' | 'tensor' | 'op' | 'block'
  /** the real shape, e.g. [3] or [4, 26, 26] */
  shape: number[]
  /** one name per axis, e.g. ['channels', 'rows', 'cols'] */
  axes?: string[]
  /** the drawn shape when the real one is too big (labels keep the real shape) */
  draw?: number[]
  /** a manual position in layout units (unrolled and encdec specs set it) */
  at?: V3
  /** shared-weight group: nodes and edges in one group share a color and light up together */
  group?: string
  /** number of parameters, shown when the layer is selected */
  params?: number
  /** a longer name for the layer list and the panel, e.g. "hidden layer (sigmoid)" */
  title?: string
  /** the role the node plays, in a few words, for the panel */
  note?: string
  /** neurons: lay the discs out along x (a sequence of positions) instead of along y */
  along?: 'x' | 'y'
  /** one short label per drawn disc (tokens, words, time steps) */
  names?: string[]
  /**
   * how its values color the fill. Default: signed data (pos/neg, stronger with size). 'none': never (token ids are
   * labels, not amounts). 'progress': 0 = not reached yet (left hollow), more = further along (gray)
   */
  fill?: 'none' | 'progress'
}

export type NetEdge = {
  id: string
  from: string
  to: string
  kind: 'dense' | 'conv' | 'recurrent' | 'residual' | 'attention' | 'copy'
  /** dense: weights[i][j] from item i of `from` to item j of `to` (the (in, out) layout of X @ W); attention: weight of
   * query position i (in `from`) on key position j (in `to`) */
  weights?: number[][]
  /** conv: the receptive field of one output cell */
  window?: { size: number; stride: number }
  /** shared-weight group (the same color as its nodes) */
  shared?: string
  label?: string
}

export type NetValues = number[] | number[][] | number[][][]
export type NetStep = {
  id: string
  title: string
  text?: string
  dir: 'forward' | 'backward'
  /** node and edge ids that light up in this step */
  active: string[]
  /** values per node id (forward) */
  values?: Record<string, NetValues>
  /** attention / dense edges: light up only the links out of this one item of `from` (e.g. one output word) */
  focus?: Record<string, number>
  /** gradients per node id (∂L/∂a) or edge id (∂L/∂W, same layout as its weights) */
  grads?: Record<string, NetValues>
  loss?: number
}

export type Net3DSpec = {
  id: string
  layout: NetLayout
  nodes: NetNode[]
  edges: NetEdge[]
  steps?: NetStep[]
  caps?: { maxCellsPerNode?: number; maxEdgesPerLink?: number }
  /** camera angle in degrees when the default (azimuth 20, elevation 14) hides the point */
  view?: { azimuth?: number; elevation?: number }
  /** spacing: `gap` between layers (default 1.15), `cell` the largest cell pitch (default 0.16) */
  scale?: { gap?: number; cell?: number }
  /**
   * wide screens: the first `fold` nodes stand in a column above node `fold` (data comes down into the row), so a
   * long strip of blocks folds into an L instead of one thin line. Phones (vertical) ignore it.
   */
  fold?: number
}

// ---- shapes -----------------------------------------------------------------------------------

export const prod = (s: number[]) => s.reduce((a, b) => a * b, 1)
export const fmtShape = (s: number[]) => `(${s.join(', ')})`

/** A 1D length as a near-square grid (rows, cols): 784 → (28, 28), 128 → (8, 16), 16 → (4, 4). */
export function squareish(n: number): [number, number] {
  let r = Math.floor(Math.sqrt(n))
  while (r > 1 && n % r) r--
  return [r, n / r]
}

/** The drawn block of a tensor node as (D, R, K) = (channels, rows, cols), capped at `maxCells`. */
export function blockDims(n: NetNode, maxCells = 4096): [number, number, number] {
  const s = n.draw ?? n.shape
  let d: [number, number, number]
  if (s.length === 1) d = s[0] <= 32 ? [1, s[0], 1] : [1, ...squareish(s[0])]
  else if (s.length === 2) d = [1, s[0], s[1]]
  else d = [s[s.length - 3], s[s.length - 2], s[s.length - 1]]
  // cap: shrink the largest axis until it fits
  while (d[0] * d[1] * d[2] > maxCells) {
    const k = d.indexOf(Math.max(...d))
    d[k] = Math.max(1, Math.floor(d[k] / 2))
  }
  return d
}

/** How many discs a neurons node draws. */
export const drawnNeurons = (n: NetNode) => Math.max(1, Math.min(n.draw?.[0] ?? prod(n.shape), 24))

// ---- layout -----------------------------------------------------------------------------------

export type ItemKind = 'disc' | 'cell' | 'box'
export type LaidNode = {
  node: NetNode
  index: number
  center: V3
  /** half sizes of the node's box (x, y, z) */
  half: V3
  kind: ItemKind
  /** one position per drawn neuron / cell (row-major over D, R, K for tensors) */
  items: V3[]
  /** disc radius or cell pitch */
  size: number
  /** tensors: the drawn (D, R, K) */
  dims?: [number, number, number]
  /** in the folded column (see Net3DSpec.fold): its name goes on the left, not above */
  column?: boolean
}
export type NetLayoutResult = { nodes: LaidNode[]; byId: Map<string, LaidNode>; lo: V3; hi: V3 }

const GAP = 1.15

/** Where every node, neuron and cell goes. Pure: the same spec always gives the same layout. */
/**
 * Lay the net out along +x. `vertical`: the caller will turn the picture a quarter (data flows down, on phones),
 * which maps layout (x, y) to screen (y, −x) and would put item 0 of a column on the right. So each neuron
 * column is mirrored first: after the turn, item 0 is on the left and a vector reads in order (x = [2, 1] → 2, 1)
 */
export function layoutNet(spec: Net3DSpec, o: { vertical?: boolean } = {}): NetLayoutResult {
  const maxCells = spec.caps?.maxCellsPerNode ?? 4096
  // hourglass: one cell pitch for every block, so a block's size shows how many numbers it holds
  let shared = 0
  if (spec.layout === 'hourglass') {
    const ps = spec.nodes.filter((n) => n.kind === 'tensor').map((n) => cellPitch(blockDims(n, maxCells), spec.scale?.cell))
    shared = ps.length ? Math.min(...ps) : 0
  }
  const out: LaidNode[] = []
  let x = 0
  spec.nodes.forEach((node, index) => {
    const ln = laidShape(node, index, maxCells, shared, spec.scale?.cell)
    // (and spread a little wider: on a phone the column lies across the screen, where there is room, and each
    // disc's number sits under it)
    if (o.vertical && node.kind === 'neurons' && node.along !== 'x' && ln.items.length > 1) {
      ln.items = ln.items.map((p) => [p[0], -p[1] * 1.7, p[2]])
      ln.half = [ln.half[0], (ln.half[1] - ln.size) * 1.7 + ln.size, ln.half[2]]
    }
    if (node.at) ln.center = [...node.at]
    else {
      if (index > 0) x += ln.half[0]
      ln.center = [x, 0, 0]
      x += ln.half[0] + (spec.scale?.gap ?? GAP)
    }
    out.push(ln)
  })
  // fold: lay the row out from node `fold` (at x = 0), then stack the nodes before it upward above that node
  const fold = !o.vertical && spec.fold ? Math.min(spec.fold, out.length - 1) : 0
  if (fold > 0) {
    const x0 = out[fold].center[0]
    for (const ln of out) if (!ln.node.at) ln.center = [ln.center[0] - x0, ln.center[1], ln.center[2]]
    let top = out[fold].center[1] + out[fold].half[1]
    out[fold].column = true
    for (let i = fold - 1; i >= 0; i--) {
      const ln = out[i]
      ln.center = [0, top + (spec.scale?.gap ?? GAP) + ln.half[1], 0]
      top = ln.center[1] + ln.half[1]
      ln.column = true
    }
  }
  for (const ln of out) ln.items = ln.items.map((p) => [p[0] + ln.center[0], p[1] + ln.center[1], p[2] + ln.center[2]])
  const lo: V3 = [Infinity, Infinity, Infinity], hi: V3 = [-Infinity, -Infinity, -Infinity]
  for (const n of out)
    for (let a = 0; a < 3; a++) {
      lo[a] = Math.min(lo[a], n.center[a] - n.half[a])
      hi[a] = Math.max(hi[a], n.center[a] + n.half[a])
    }
  return { nodes: out, byId: new Map(out.map((n) => [n.node.id, n])), lo, hi }
}

/** Cell pitch for a block: the face fits ~2.4 units, the depth ~2, never bigger than 0.16. */
export const cellPitch = (d: [number, number, number], max = 0.16) => Math.min(max, 2.4 / Math.max(d[1], d[2]), 2 / Math.max(1, d[0]))

function laidShape(node: NetNode, index: number, maxCells: number, sharedPitch: number, maxPitch?: number): LaidNode {
  if (node.kind === 'neurons') {
    const n = drawnNeurons(node)
    const s = n <= 8 ? 0.42 : Math.min(0.42, 3.2 / n)
    const r = Math.min(0.13, s * 0.34)
    if (node.along === 'x') {
      const items: V3[] = Array.from({ length: n }, (_, i) => [(i - (n - 1) / 2) * s * 1.6, 0, 0])
      return { node, index, center: [0, 0, 0], half: [((n - 1) / 2) * s * 1.6 + r, r, r], kind: 'disc', items, size: r }
    }
    const items: V3[] = Array.from({ length: n }, (_, i) => [0, ((n - 1) / 2 - i) * s, 0])
    return { node, index, center: [0, 0, 0], half: [r, ((n - 1) / 2) * s + r, r], kind: 'disc', items, size: r }
  }
  if (node.kind === 'op') return { node, index, center: [0, 0, 0], half: [0.1, 0.1, 0.1], kind: 'disc', items: [[0, 0, 0]], size: 0.1 }
  if (node.kind === 'block') return { node, index, center: [0, 0, 0], half: [0.3, 0.42, 0.3], kind: 'box', items: [[0, 0, 0]], size: 0.6 }
  const dims = blockDims(node, maxCells)
  const [D, R, K] = dims
  const p = sharedPitch || cellPitch(dims, maxPitch)
  const items: V3[] = []
  for (let d = 0; d < D; d++)
    for (let i = 0; i < R; i++)
      for (let j = 0; j < K; j++) items.push([(j - (K - 1) / 2) * p, ((R - 1) / 2 - i) * p, ((D - 1) / 2 - d) * p])
  return { node, index, center: [0, 0, 0], half: [(K * p) / 2, (R * p) / 2, (D * p) / 2], kind: 'cell', items, size: p, dims }
}

// ---- edges ------------------------------------------------------------------------------------

export type Pair = { i: number; j: number; w: number }
/**
 * The pairs of a dense or attention link to draw: only pairs whose ends are drawn, the `max` largest |w| first.
 * Without weights every pair counts (w = 1).
 */
export function samplePairs(nFrom: number, nTo: number, weights: number[][] | undefined, max: number): Pair[] {
  const all: Pair[] = []
  for (let i = 0; i < nFrom; i++) for (let j = 0; j < nTo; j++) all.push({ i, j, w: weights ? weights[i]?.[j] ?? 0 : 1 })
  if (all.length <= max) return all
  return all.sort((a, b) => Math.abs(b.w) - Math.abs(a.w)).slice(0, max)
}

/** Line width in px for a weight: 0.5 px at 0, 2.5 px at the link's largest |w| (spec §7.3). */
export const widthFor = (w: number, maxAbs: number) => 0.5 + 2 * Math.min(1, Math.abs(w) / (maxAbs || 1))
/** Three width buckets (one draw call each): 0, 1, 2. */
export const bucketFor = (w: number, maxAbs: number) => {
  const px = widthFor(w, maxAbs)
  return px < 1.1 ? 0 : px < 1.8 ? 1 : 2
}
export const BUCKET_PX = [0.75, 1.5, 2.5]

/** A conv edge's funnel: the window of input cells (rows r0..r1, cols c0..c1) behind output cell (row, col). */
export function convWindow(row: number, col: number, w: { size: number; stride: number }) {
  const r0 = row * w.stride, c0 = col * w.stride
  return { r0, r1: r0 + w.size - 1, c0, c1: c0 + w.size - 1 }
}

/** A curved arc from a to b (quadratic, bulging by `lift` toward the reader, +z), as `n + 1` points. */
export function arcPoints(a: V3, b: V3, lift: number, n = 12): V3[] {
  const m: V3 = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2 + lift]
  const pts: V3[] = []
  for (let k = 0; k <= n; k++) {
    const t = k / n, u = 1 - t
    pts.push([0, 1, 2].map((q) => u * u * a[q] + 2 * u * t * m[q] + t * t * b[q]) as V3)
  }
  return pts
}

// ---- steps ------------------------------------------------------------------------------------

export type NetState = {
  step: NetStep | null
  dir: 'forward' | 'backward' | null
  active: Set<string>
  values: Record<string, NetValues>
  grads: Record<string, NetValues>
  loss?: number
}

/** What the picture shows at step k (−1 = before the first step): values and gradients add up over the steps so far. */
export function stateAt(spec: Net3DSpec, k: number): NetState {
  const steps = spec.steps ?? []
  const values: Record<string, NetValues> = {}
  const grads: Record<string, NetValues> = {}
  let loss: number | undefined
  for (let s = 0; s <= Math.min(k, steps.length - 1); s++) {
    Object.assign(values, steps[s].values ?? {})
    Object.assign(grads, steps[s].grads ?? {})
    if (steps[s].loss !== undefined) loss = steps[s].loss
  }
  const step = k >= 0 && k < steps.length ? steps[k] : null
  return { step, dir: step?.dir ?? null, active: new Set(step?.active ?? []), values, grads, loss }
}

export const flat = (v: NetValues | undefined): number[] => (v ? (v as any[]).flat(2) : [])
/** The largest |value| a node or edge ever takes over all steps (so colors keep their meaning between steps). */
export function scales(spec: Net3DSpec): { value: Record<string, number>; grad: Record<string, number> } {
  const value: Record<string, number> = {}, grad: Record<string, number> = {}
  for (const s of spec.steps ?? []) {
    for (const [id, v] of Object.entries(s.values ?? {})) value[id] = Math.max(value[id] ?? 0, ...flat(v).map(Math.abs))
    for (const [id, v] of Object.entries(s.grads ?? {})) grad[id] = Math.max(grad[id] ?? 0, ...flat(v).map(Math.abs))
  }
  return { value, grad }
}

/** Parameter count of a node: its own `params`, else the weights (+ biases) of dense edges coming into it. */
export function paramsOf(spec: Net3DSpec, id: string): number | undefined {
  const n = spec.nodes.find((x) => x.id === id)
  if (n?.params !== undefined) return n.params
  const into = spec.edges.filter((e) => e.to === id && e.kind === 'dense')
  if (!into.length || !n) return undefined
  const out = prod(n.shape)
  return into.reduce((a, e) => a + prod(spec.nodes.find((x) => x.id === e.from)!.shape) * out, 0) + out
}

/** A fixed color for each shared-weight group, in order of first use. */
export function groupTones(spec: Net3DSpec): Record<string, NetTone> {
  const t: Record<string, NetTone> = {}
  let k = 0
  for (const g of [...spec.nodes.map((n) => n.group), ...spec.edges.map((e) => e.shared)])
    if (g && !t[g]) t[g] = (['cat-2', 'cat-1', 'cat-3', 'cat-4', 'cat-5'] as NetTone[])[k++ % 5]
  return t
}

/** Round like the demos: up to 4 decimals, no trailing zeros, a real minus sign. */
export function fmtNum(v: number, dp = 4): string {
  if (!Number.isFinite(v)) return String(v)
  const s = (Math.round(v * 10 ** dp) / 10 ** dp).toString()
  return (s === '-0' ? '0' : s).replace('-', '−')
}

// ---- segments: every line the picture draws (shared by Net3D and Net2D) ------------------------

export type Seg = { e: NetEdge; a: V3; b: V3; w: number; i: number; j: number; dense: boolean; arc?: boolean }
export type Rail = { e: NetEdge; a: V3; b: V3 }
export type Item = { ln: LaidNode; k: number }

/** Split the laid-out nodes into discs and cells (boxes count as cells), in draw order. */
export function itemsOf(L: NetLayoutResult): { discs: Item[]; cells: Item[] } {
  const discs: Item[] = [], cells: Item[] = []
  for (const ln of L.nodes) ln.items.forEach((_, k) => (ln.kind === 'disc' ? discs : cells).push({ ln, k }))
  return { discs, cells }
}

/** The rail's height: a little under the lowest node. */
export const railY = (L: NetLayoutResult) => L.lo[1] - 0.3

/**
 * Line segments for every edge: dense pairs (sampled, `max` per link), attention arcs (12 pieces each, weights
 * under 0.04 skipped), the conv funnel (window corners → the middle output cell, plus the window outline),
 * recurrent / copy links (one line), and residual rails (drawn as bands, returned separately).
 */
export function segmentsOf(spec: Net3DSpec, L: NetLayoutResult, max: number): { segs: Seg[]; rails: Rail[] } {
  const segs: Seg[] = [], rails: Rail[] = []
  for (const e of spec.edges) {
    const A = L.byId.get(e.from), B = L.byId.get(e.to)
    if (!A || !B) continue
    if (e.kind === 'dense') {
      for (const p of samplePairs(A.items.length, B.items.length, e.weights, max))
        segs.push({ e, a: A.items[p.i], b: B.items[p.j], w: p.w, i: p.i, j: p.j, dense: true })
    } else if (e.kind === 'attention') {
      const lift = 0.3 + 0.2 * Math.abs(A.center[1] - B.center[1])
      for (const p of samplePairs(A.items.length, B.items.length, e.weights, max)) {
        if (Math.abs(p.w) < 0.04) continue
        const pts = arcPoints(A.items[p.i], B.items[p.j], lift)
        for (let k = 0; k + 1 < pts.length; k++) segs.push({ e, a: pts[k], b: pts[k + 1], w: p.w, i: p.i, j: p.j, dense: false, arc: true })
      }
    } else if (e.kind === 'conv' && A.dims && B.dims) {
      const w = e.window ?? { size: 3, stride: 1 }
      const row = Math.floor((B.dims[1] - 1) / 2), col = Math.floor((B.dims[2] - 1) / 2)
      const win = convWindow(row, col, w)
      const at = (ln: LaidNode, d: number, r: number, k: number): V3 => {
        const [D, R, K] = ln.dims!
        return ln.items[Math.min(D - 1, d) * R * K + Math.min(R - 1, r) * K + Math.min(K - 1, k)]
      }
      // on the front faces: the window's 4 corners in the input, the middle cell of the output
      const out = at(B, 0, row, col)
      const zA = A.center[2] + A.half[2]
      const corner = (r: number, k: number, dr: number, dk: number): V3 => {
        const p = at(A, 0, r, k)
        return [p[0] + dk * A.size * 0.5, p[1] + dr * A.size * 0.5, zA]
      }
      const cs = [corner(win.r0, win.c0, 1, -1), corner(win.r0, win.c1, 1, 1), corner(win.r1, win.c1, -1, 1), corner(win.r1, win.c0, -1, -1)]
      const tgt: V3 = [out[0], out[1], B.center[2] + B.half[2]]
      cs.forEach((p, k) => {
        segs.push({ e, a: p, b: tgt, w: 1, i: 0, j: 0, dense: false })
        segs.push({ e, a: p, b: cs[(k + 1) % 4], w: 1, i: 0, j: 0, dense: false })
      })
    } else if (e.kind === 'residual') {
      rails.push({ e, a: A.center, b: B.center })
    } else {
      // recurrent / copy: one line between the facing sides of the two nodes
      const dx = B.center[0] - A.center[0]
      if (Math.abs(dx) > 1e-6) {
        const s = Math.sign(dx)
        segs.push({ e, a: [A.center[0] + s * A.half[0], A.center[1], A.center[2]], b: [B.center[0] - s * B.half[0], B.center[1], B.center[2]], w: 1, i: 0, j: 0, dense: false })
      } else {
        const s = Math.sign(B.center[1] - A.center[1]) || 1
        segs.push({ e, a: [A.center[0], A.center[1] + s * A.half[1], A.center[2]], b: [B.center[0], B.center[1] - s * B.half[1], B.center[2]], w: 1, i: 0, j: 0, dense: false })
      }
    }
  }
  return { segs, rails }
}

// ---- looks: what color each thing gets at a step (renderer-neutral) ----------------------------

/** A color as "mix `amt` of `tone` into `base`", optionally followed by a second mix (`over`). */
export type Look = { base: 'card' | 'bg'; tone: NetTone; amt: number; over?: { tone: NetTone; amt: number } }
export type RingLook = Look & { r: number }
/** hide: not drawn at all (an attention arc of a step that has not happened yet) */
export type LineLook = Look & { bucket: number; hide?: boolean }
export type Looks = { discs: Look[]; rings: RingLook[]; cells: Look[]; lines: LineLook[]; railOn: boolean; back: boolean; state: NetState }

/**
 * The colors of one step. Forward: values in pos/neg (strength = |v| over the node's largest |v|), the active
 * layer ringed in accent, active links at full strength, the rest faded. Backward: rings become `grad` halos that
 * grow with |∂L/∂a|; links with a gradient switch to `grad`, their width to |∂L/∂w|.
 */
export function looksAt(spec: Net3DSpec, items: { discs: Item[]; cells: Item[] }, segs: Seg[], rails: Rail[], step: number, selected: string | null): Looks {
  const st = stateAt(spec, step)
  const back = st.dir === 'backward'
  const sc = scales(spec)
  const tones = groupTones(spec)
  const fillOf = new Map(spec.nodes.map((n) => [n.id, n.fill]))
  const value = (id: string, v: number | undefined, gt: NetTone | null): Look => {
    const fill = fillOf.get(id)
    if (fill === 'progress' && v !== undefined && Number.isFinite(v)) return { base: 'card', tone: 'fg', amt: v > 0 ? 0.12 + 0.3 * Math.min(1, v) : 0 }
    if (fill === 'none' || v === undefined || !Number.isFinite(v)) return gt ? { base: 'card', tone: gt, amt: 0.35 } : { base: 'card', tone: 'fg', amt: 0.08 }
    const t = Math.min(1, Math.abs(v) / (sc.value[id] || 1))
    return { base: 'card', tone: v >= 0 ? 'pos' : 'neg', amt: 0.18 + 0.82 * t }
  }
  // a step that focuses one item of a node (e.g. the word being written) rings only that item, not the whole layer
  const current: Record<string, number> = {}
  for (const [eid, k] of Object.entries(st.step?.focus ?? {})) {
    const e = spec.edges.find((x) => x.id === eid)
    if (e) current[e.from] = k
  }
  const discs: Look[] = [], rings: RingLook[] = []
  for (const d of items.discs) {
    const id = d.ln.node.id
    const gt = d.ln.node.group ? tones[d.ln.node.group] : null
    discs.push(d.ln.node.kind === 'op' ? { base: 'card', tone: 'fg', amt: 0.2 } : value(id, flat(st.values[id])[d.k], gt))
    const on = st.active.has(id) && (current[id] === undefined || current[id] === d.k)
    const gr = flat(st.grads[id])[d.k]
    let ring: RingLook = { base: 'card', tone: gt ?? 'fg', amt: gt ? 1 : 0.45, r: 1.2 }
    if (back && gr !== undefined) ring = { base: 'bg', tone: 'grad', amt: on ? 1 : 0.55, r: 1.22 + 0.55 * Math.min(1, Math.abs(gr) / (sc.grad[id] || 1)) }
    else if (on) ring = { base: 'bg', tone: 'accent', amt: 1, r: 1.32 }
    if (selected === id) ring = { ...ring, base: 'bg', tone: 'accent', amt: 1, r: Math.max(ring.r, 1.36) }
    rings.push(ring)
  }
  const cells: Look[] = []
  for (const d of items.cells) {
    const id = d.ln.node.id
    const vals = flat(st.values[id])
    const gt = d.ln.node.group ? tones[d.ln.node.group] : null
    let c: Look = d.ln.kind === 'box' ? (gt ? { base: 'card', tone: gt, amt: 0.45 } : { base: 'card', tone: 'fg', amt: 0.14 })
      : vals.length ? value(id, vals[d.k], gt) : gt ? { base: 'card', tone: gt, amt: 0.35 } : { base: 'card', tone: 'fg', amt: 0.14 }
    const shown = vals.length > 0 && fillOf.get(id) !== 'none' // the fill shows numbers: keep them readable under the accent
    if (st.active.has(id) || selected === id) c = { ...c, over: { tone: back ? 'grad' : 'accent', amt: shown ? 0.35 : 0.6 } }
    cells.push(c)
  }
  const maxW: Record<string, number> = {}
  for (const s of segs) if (s.dense) maxW[s.e.id] = Math.max(maxW[s.e.id] ?? 0, Math.abs(s.w))
  const lines: LineLook[] = segs.map((s) => {
    const on = st.active.has(s.e.id)
    const g = back && st.grads[s.e.id] ? (st.grads[s.e.id] as number[][])[s.i]?.[s.j] : undefined
    const gt = s.e.shared ? tones[s.e.shared] : null
    if (s.dense) {
      if (g !== undefined) return { base: 'bg', tone: 'grad', amt: on ? 1 : 0.45, bucket: bucketFor(g, sc.grad[s.e.id] || 1) }
      // shared weights keep their group color strong in both themes (the caption says "look at the color")
      if (gt) return { base: 'bg', tone: gt, amt: on ? 1 : 0.9, bucket: 2 }
      const tone: NetTone = s.w >= 0 ? 'pos' : 'neg'
      return { base: 'bg', tone, amt: on ? 1 : st.step ? 0.25 : 0.6, bucket: bucketFor(s.w, maxW[s.e.id] || 1) }
    }
    if (s.arc) {
      const f = st.step?.focus?.[s.e.id]
      const lit = on && (f === undefined || f === s.i)
      // a later step's arcs are not drawn yet: its word is still hollow ("not computed yet"), so its weights don't exist
      if (on && f !== undefined && s.i > f) return { base: 'bg', tone: 'fg', amt: 0, bucket: 3, hide: true }
      // the same before the first step: an arc from a "progress" item (a decoder step) exists only once that item is done
      if (fillOf.get(s.e.from) === 'progress' && !(on && f === s.i) && !(flat(st.values[s.e.from])[s.i] > 0)) return { base: 'bg', tone: 'fg', amt: 0, bucket: 3, hide: true }
      return { base: 'bg', tone: lit ? 'accent' : 'fg', amt: Math.min(1, Math.abs(s.w)) * (lit ? 1 : f !== undefined && on ? 0.15 : 0.5), bucket: lit && Math.abs(s.w) > 0.5 ? 2 : 3 }
    }
    // accent means "this step": a conv funnel not in this step is drawn in plain ink (a little stronger than other links)
    const tone: NetTone = on ? (back ? 'grad' : 'accent') : gt ?? 'fg'
    return { base: 'bg', tone, amt: on ? 1 : gt ? 0.9 : s.e.kind === 'conv' ? 0.6 : 0.5, bucket: on || !gt ? 3 : 2 }
  })
  return { discs, rings, cells, lines, railOn: rails.some((r) => st.active.has(r.e.id)), back, state: st }
}
