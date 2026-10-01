/**
 * Diffusion helpers for levels D1–D3: noise schedules, 2D shapes, and a tiny MLP
 * (forward pass, backprop, Adam) that runs in the browser.
 *
 * The shapes, time features and network layout match
 * content/2-theory/a2-sampling-and-guidance/export.py, so weights trained there run here unchanged.
 */

// ---------------------------------------------------------------- random numbers
/** Small seeded random generator, so a lab looks the same every time it loads. */
export function rng(seed: number) {
  let a = seed >>> 0
  const uniform = () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
  const normal = () => {
    const u = uniform() || 1e-12
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * uniform())
  }
  return { uniform, normal }
}
export type Rng = ReturnType<typeof rng>

// ---------------------------------------------------------------- schedule
export type Schedule = { T: number; betas: number[]; alphas: number[]; alphaBar: number[] }

/** Index 0 is step t = 1. alphaBar[t-1] = (1 - beta_1)(1 - beta_2)…(1 - beta_t). */
export function schedule(betas: number[]): Schedule {
  const alphas = betas.map((b) => 1 - b)
  const alphaBar: number[] = []
  let p = 1
  for (const a of alphas) alphaBar.push((p *= a))
  return { T: betas.length, betas, alphas, alphaBar }
}

export const linearBetas = (T: number, lo = 1e-3, hi = 0.2) =>
  Array.from({ length: T }, (_, i) => lo + ((hi - lo) * i) / (T - 1))

export const SITE_SCHEDULE = schedule(linearBetas(50))

// ---------------------------------------------------------------- shapes
export type Pt = [number, number]
export const SHAPES = ['spiral', 'ring', 'moons'] as const
export type ShapeName = (typeof SHAPES)[number]

export function makeShape(name: ShapeName, n: number, r: Rng): Pt[] {
  const out: Pt[] = []
  for (let i = 0; i < n; i++) {
    let x: number, y: number
    if (name === 'spiral') {
      const u = r.uniform()
      const a = 0.6 + 3.6 * u * Math.PI
      const rad = 0.25 + 1.55 * u
      x = rad * Math.cos(a); y = rad * Math.sin(a)
    } else if (name === 'ring') {
      const a = r.uniform() * 2 * Math.PI
      x = 1.4 * Math.cos(a); y = 1.4 * Math.sin(a)
    } else {
      const a = r.uniform() * Math.PI
      const top = r.uniform() < 0.5
      x = (top ? Math.cos(a) : 1 - Math.cos(a)) - 0.5
      y = (top ? Math.sin(a) : -Math.sin(a) + 0.5) - 0.25
      x *= 1.3; y *= 1.3
    }
    out.push([x + 0.04 * r.normal(), y + 0.04 * r.normal()])
  }
  return out
}

/** x_t = sqrt(alphaBar)·x0 + sqrt(1 − alphaBar)·eps */
export const addNoise = (x0: Pt, eps: Pt, ab: number): Pt => [
  Math.sqrt(ab) * x0[0] + Math.sqrt(1 - ab) * eps[0],
  Math.sqrt(ab) * x0[1] + Math.sqrt(1 - ab) * eps[1],
]

/** 12 numbers that tell the network which step it is on: sin and cos of t/T at 6 frequencies. */
export function timeFeatures(t: number, T: number): number[] {
  const tn = t / T
  const s: number[] = [], c: number[] = []
  for (let k = 0; k < 6; k++) {
    const f = Math.PI * 2 ** k
    s.push(Math.sin(tn * f)); c.push(Math.cos(tn * f))
  }
  return [...s, ...c]
}

// ---------------------------------------------------------------- tiny MLP
export type Layer = { W: Float32Array; b: Float32Array; nin: number; nout: number }

export function layersFromJson(ls: { W: number[][]; b: number[] }[]): Layer[] {
  return ls.map((l) => ({
    W: Float32Array.from(l.W.flat()), b: Float32Array.from(l.b), nin: l.W.length, nout: l.b.length,
  }))
}

export function initLayers(sizes: number[], r: Rng): Layer[] {
  const out: Layer[] = []
  for (let i = 0; i + 1 < sizes.length; i++) {
    const nin = sizes[i], nout = sizes[i + 1]
    const W = new Float32Array(nin * nout)
    const s = Math.sqrt(2 / nin)
    for (let k = 0; k < W.length; k++) W[k] = r.normal() * s
    out.push({ W, b: new Float32Array(nout), nin, nout })
  }
  return out
}

/** Forward pass for n rows (flat, row-major). ReLU between layers, none after the last. Returns every layer's output. */
export function forward(layers: Layer[], X: Float32Array, n: number): Float32Array[] {
  const acts = [X]
  layers.forEach((L, li) => {
    const inp = acts[acts.length - 1]
    const out = new Float32Array(n * L.nout)
    for (let i = 0; i < n; i++) {
      const o = i * L.nout
      out.set(L.b, o)
      for (let k = 0; k < L.nin; k++) {
        const x = inp[i * L.nin + k]
        if (x === 0) continue
        const w = k * L.nout
        for (let j = 0; j < L.nout; j++) out[o + j] += x * L.W[w + j]
      }
    }
    if (li < layers.length - 1) for (let k = 0; k < out.length; k++) if (out[k] < 0) out[k] = 0
    acts.push(out)
  })
  return acts
}

export type Adam = { m: Float32Array[]; v: Float32Array[]; step: number }
export function adamFor(layers: Layer[]): Adam {
  const z = (a: Float32Array) => new Float32Array(a.length)
  return { m: layers.flatMap((L) => [z(L.W), z(L.b)]), v: layers.flatMap((L) => [z(L.W), z(L.b)]), step: 0 }
}

/** One training step on mean squared error. Returns the loss before the update. */
export function trainStep(layers: Layer[], opt: Adam, X: Float32Array, Y: Float32Array, n: number, lr: number): number {
  const acts = forward(layers, X, n)
  const out = acts[acts.length - 1]
  let loss = 0
  let g = new Float32Array(out.length)
  for (let k = 0; k < out.length; k++) {
    const d = out[k] - Y[k]
    loss += d * d
    g[k] = (2 * d) / out.length
  }
  loss /= out.length

  const grads: Float32Array[] = new Array(layers.length * 2)
  for (let li = layers.length - 1; li >= 0; li--) {
    const L = layers[li], inp = acts[li]
    const gW = new Float32Array(L.W.length), gb = new Float32Array(L.nout)
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < L.nout; j++) gb[j] += g[i * L.nout + j]
      for (let k = 0; k < L.nin; k++) {
        const x = inp[i * L.nin + k]
        if (x === 0) continue
        for (let j = 0; j < L.nout; j++) gW[k * L.nout + j] += x * g[i * L.nout + j]
      }
    }
    grads[li * 2] = gW; grads[li * 2 + 1] = gb
    if (li > 0) {
      const gin = new Float32Array(n * L.nin)
      for (let i = 0; i < n; i++)
        for (let k = 0; k < L.nin; k++) {
          if (inp[i * L.nin + k] <= 0) continue // ReLU: no gradient where it was off
          let s = 0
          for (let j = 0; j < L.nout; j++) s += L.W[k * L.nout + j] * g[i * L.nout + j]
          gin[i * L.nin + k] = s
        }
      g = gin
    }
  }

  opt.step++
  const c1 = 1 - 0.9 ** opt.step, c2 = 1 - 0.999 ** opt.step
  layers.forEach((L, li) => {
    ;[L.W, L.b].forEach((p, pi) => {
      const k = li * 2 + pi, gr = grads[k], m = opt.m[k], v = opt.v[k]
      for (let q = 0; q < p.length; q++) {
        m[q] = 0.9 * m[q] + 0.1 * gr[q]
        v[q] = 0.999 * v[q] + 0.001 * gr[q] * gr[q]
        p[q] -= (lr * (m[q] / c1)) / (Math.sqrt(v[q] / c2) + 1e-8)
      }
    })
  })
  return loss
}

// ---------------------------------------------------------------- denoisers
/** Unconditional denoiser input: [x, y, 12 time features] → 14 numbers. */
export function predictNoise(layers: Layer[], pts: Pt[], t: number, T: number): Pt[] {
  const n = pts.length, tf = timeFeatures(t, T), d = 2 + tf.length
  const X = new Float32Array(n * d)
  pts.forEach((p, i) => { X[i * d] = p[0]; X[i * d + 1] = p[1]; X.set(tf, i * d + 2) })
  const out = forward(layers, X, n).at(-1)!
  return pts.map((_, i) => [out[i * 2], out[i * 2 + 1]])
}

/** Conditional denoiser input: [x, y, 12 time features, one-hot class of 4]. Class 3 means "no class". */
export function predictNoiseCond(layers: Layer[], pts: Pt[], t: number, T: number, cls: number): Pt[] {
  const n = pts.length, tf = timeFeatures(t, T), d = 18
  const X = new Float32Array(n * d)
  pts.forEach((p, i) => { X[i * d] = p[0]; X[i * d + 1] = p[1]; X.set(tf, i * d + 2); X[i * d + 14 + cls] = 1 })
  const out = forward(layers, X, n).at(-1)!
  return pts.map((_, i) => [out[i * 2], out[i * 2 + 1]])
}

/** Guided noise: eps_free + w · (eps_class − eps_free). */
export const guide = (free: Pt, cond: Pt, w: number): Pt => [
  free[0] + w * (cond[0] - free[0]),
  free[1] + w * (cond[1] - free[1]),
]

/**
 * One reverse step, from x_t to x_{t−1}:
 *   mean = (x_t − beta_t / sqrt(1 − alphaBar_t) · eps) / sqrt(alpha_t)
 *   x_{t−1} = mean + sqrt(beta_t) · z      (no z on the last step)
 */
export function reverseStep(x: Pt, eps: Pt, t: number, s: Schedule, z: Pt | null): Pt {
  const b = s.betas[t - 1], a = s.alphas[t - 1], ab = s.alphaBar[t - 1]
  const k = b / Math.sqrt(1 - ab)
  let m: Pt = [(x[0] - k * eps[0]) / Math.sqrt(a), (x[1] - k * eps[1]) / Math.sqrt(a)]
  if (z && t > 1) m = [m[0] + Math.sqrt(b) * z[0], m[1] + Math.sqrt(b) * z[1]]
  return m
}

/** Guess of the clean point from one noisy point: x0 ≈ (x_t − sqrt(1 − alphaBar)·eps) / sqrt(alphaBar) */
export const guessClean = (x: Pt, eps: Pt, ab: number): Pt => [
  (x[0] - Math.sqrt(1 - ab) * eps[0]) / Math.sqrt(ab),
  (x[1] - Math.sqrt(1 - ab) * eps[1]) / Math.sqrt(ab),
]

// ---------------------------------------------------------------- drawing
export type View = { size: number; span: number } // span: world units from center to edge

/** Canvas text size in CSS px that follows the reader's text-size setting (rem-based, never below 11.5px). */
export function canvasFont(rem = 0.75): number {
  const root = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16
  return Math.max(11.5 * (root / 16), rem * root)
}

export function themeColors(el: Element) {
  const cs = getComputedStyle(el)
  const v = (n: string) => cs.getPropertyValue(n).trim()
  return {
    fg: v('--fg'), dim: v('--dim'), line: v('--line'), accent: v('--accent'), ok: v('--ok'), warn: v('--warn'), bg: v('--bg'),
    card: v('--card'), cat1: v('--cat-1'), cat2: v('--cat-2'), cat3: v('--cat-3'), cat4: v('--cat-4'), cat5: v('--cat-5'),
    pos: v('--pos'), neg: v('--neg'), grad: v('--grad'),
  }
}

/** Sets up a canvas for the device's pixel ratio and returns a world → pixel mapper (world is [-span, span] on the short side). */
export function prepCanvas(cv: HTMLCanvasElement, span: number) {
  const css = cv.clientWidth || 320
  const cssH = cv.clientHeight || css
  const dpr = window.devicePixelRatio || 1
  if (cv.width !== Math.round(css * dpr) || cv.height !== Math.round(cssH * dpr)) {
    cv.width = Math.round(css * dpr); cv.height = Math.round(cssH * dpr)
  }
  const ctx = cv.getContext('2d')!
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, css, cssH)
  const side = Math.min(css, cssH)
  const px = (p: Pt): [number, number] => [css / 2 + (p[0] / span) * (side / 2), cssH / 2 - (p[1] / span) * (side / 2)]
  return { ctx, px, css, cssH }
}

export function drawAxes(ctx: CanvasRenderingContext2D, px: (p: Pt) => [number, number], span: number, color: string) {
  ctx.strokeStyle = color
  ctx.lineWidth = 1
  ctx.beginPath()
  const [x0, y0] = px([-span, 0]), [x1, y1] = px([span, 0])
  ctx.moveTo(x0, y0); ctx.lineTo(x1, y1)
  const [a0, b0] = px([0, -span]), [a1, b1] = px([0, span])
  ctx.moveTo(a0, b0); ctx.lineTo(a1, b1)
  ctx.stroke()
}

export function drawPoints(ctx: CanvasRenderingContext2D, px: (p: Pt) => [number, number], pts: Pt[], color: string, r = 2, alpha = 0.75) {
  ctx.fillStyle = color
  ctx.globalAlpha = alpha
  for (const p of pts) {
    const [x, y] = px(p)
    ctx.beginPath(); ctx.arc(x, y, r, 0, 2 * Math.PI); ctx.fill()
  }
  ctx.globalAlpha = 1
}

// ---------------------------------------------------------------- the trained conditional network (A2, A3)
export type CondNet = { layers: Layer[]; s: Schedule; shapes: string[]; NULL: number }
let condNet: Promise<CondNet> | null = null

/** Loads the network trained by content/2-theory/a2-sampling-and-guidance/export.py (once per page). */
export function loadCondNet(): Promise<CondNet> {
  if (!condNet) {
    condNet = fetch('/data/sampling-and-guidance/cond_mlp.json')
      .then((r) => {
        if (!r.ok) throw new Error(`could not load the trained network (${r.status})`)
        return r.json()
      })
      .then((m) => ({ layers: layersFromJson(m.layers), s: schedule(m.betas), shapes: m.shapes, NULL: m.shapes.length }))
  }
  return condNet
}

/** Fraction of samples near the shape, and fraction of the shape that has a sample nearby. */
export function shapeScore(samples: Pt[], ref: Pt[], within = 0.15) {
  const r2 = within * within
  const near = new Array(ref.length).fill(false)
  let on = 0
  for (const p of samples) {
    let hit = false
    for (let j = 0; j < ref.length; j++) {
      const dx = p[0] - ref[j][0], dy = p[1] - ref[j][1]
      if (dx * dx + dy * dy < r2) { hit = true; near[j] = true }
    }
    if (hit) on++
  }
  return { onShape: on / samples.length, covered: near.filter(Boolean).length / ref.length }
}
