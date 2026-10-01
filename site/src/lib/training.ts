/**
 * Helpers for the "Optimization" level (mini-batches, optimizers, initialization) and the
 * "Generalization" level (overfitting and regularization). Everything is deterministic (seeded), and
 * demo.py in content/1-foundations/optimization and content/1-foundations/generalization uses the same
 * random generator and the same formulas, so the lab and the demo print the same numbers.
 */

// ---------------------------------------------------------------- random numbers

/** mulberry32: a tiny seeded generator. Returns floats in [0, 1). Mirrored in demo.py. */
export function rng(seed: number): () => number {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/** One standard normal sample (Box–Muller, cosine branch only). */
export function gauss(r: () => number): number {
  const u1 = 1 - r() // in (0, 1], so log is finite
  const u2 = r()
  return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2)
}

/** Fisher–Yates shuffle of [0, n) */
export function shuffled(n: number, r: () => number): number[] {
  const a = Array.from({ length: n }, (_, i) => i)
  for (let i = n - 1; i > 0; i--) {
    const j = Math.floor(r() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

// ---------------------------------------------------------------- 1. mini-batches

export const LINE_X = [1, 2, 3, 4]
export const LINE_Y = [3, 3, 7, 7] // roughly y = 2x, with noise; best line w = 1.6, b = 1

/** Loss and gradient of mean((w·x + b − y)²) over the chosen points */
export function lineGrad(w: number, b: number, idx: number[]) {
  let loss = 0, gw = 0, gb = 0
  for (const i of idx) {
    const err = w * LINE_X[i] + b - LINE_Y[i]
    loss += err * err
    gw += 2 * err * LINE_X[i]
    gb += 2 * err
  }
  const n = idx.length
  return { loss: loss / n, gw: gw / n, gb: gb / n }
}

export const ALL = [0, 1, 2, 3]

// ---------------------------------------------------------------- 2. optimizers on a ravine

/** f(w1, w2) = 0.5·(w1² + 25·w2²): gentle along w1, steep along w2 */
export const ravine = (w1: number, w2: number) => 0.5 * (w1 * w1 + 25 * w2 * w2)
export const ravineGrad = (w1: number, w2: number): [number, number] => [w1, 25 * w2]

export type OptState = { w: [number, number]; m: [number, number]; v: [number, number]; t: number }
export const optStart = (w: [number, number]): OptState => ({ w: [...w], m: [0, 0], v: [0, 0], t: 0 })

/** One SGD step: w ← w − lr·g */
export function sgdStep(s: OptState, lr: number): OptState {
  const g = ravineGrad(...s.w)
  return { ...s, w: [s.w[0] - lr * g[0], s.w[1] - lr * g[1]], t: s.t + 1 }
}

/** One momentum step: v ← β·v + g, w ← w − lr·v  (m holds the velocity) */
export function momentumStep(s: OptState, lr: number, beta: number): OptState {
  const g = ravineGrad(...s.w)
  const m: [number, number] = [beta * s.m[0] + g[0], beta * s.m[1] + g[1]]
  return { ...s, m, w: [s.w[0] - lr * m[0], s.w[1] - lr * m[1]], t: s.t + 1 }
}

/** One Adam step with bias correction */
export function adamStep(s: OptState, lr: number, b1 = 0.9, b2 = 0.999, eps = 1e-8): OptState {
  const g = ravineGrad(...s.w)
  const t = s.t + 1
  const m: [number, number] = [b1 * s.m[0] + (1 - b1) * g[0], b1 * s.m[1] + (1 - b1) * g[1]]
  const v: [number, number] = [b2 * s.v[0] + (1 - b2) * g[0] ** 2, b2 * s.v[1] + (1 - b2) * g[1] ** 2]
  const step = (k: 0 | 1) => {
    const mh = m[k] / (1 - b1 ** t)
    const vh = v[k] / (1 - b2 ** t)
    return (lr * mh) / (Math.sqrt(vh) + eps)
  }
  return { w: [s.w[0] - step(0), s.w[1] - step(1)], m, v, t }
}

// ---------------------------------------------------------------- 3. initialization

export type Act = 'none' | 'tanh' | 'relu'

/**
 * Push a batch of random inputs (std 1) through `layers` square layers of size `width`.
 * Weights ~ N(0, std²). Returns the std of the activations after each layer, plus a
 * coarse histogram of each layer's values.
 */
export function propagate(width: number, layers: number, std: number, act: Act, seed = 1, batch = 40) {
  const r = rng(seed)
  let h: number[][] = Array.from({ length: batch }, () => Array.from({ length: width }, () => gauss(r)))
  const stds: number[] = []
  const hists: number[][] = []
  for (let l = 0; l < layers; l++) {
    const W = Array.from({ length: width }, () => Array.from({ length: width }, () => std * gauss(r)))
    const next: number[][] = []
    for (const row of h) {
      const out = new Array(width).fill(0)
      for (let k = 0; k < width; k++) {
        const x = row[k]
        if (x === 0) continue
        const Wk = W[k]
        for (let j = 0; j < width; j++) out[j] += x * Wk[j]
      }
      next.push(out.map((z) => (act === 'tanh' ? Math.tanh(z) : act === 'relu' ? Math.max(0, z) : z)))
    }
    h = next
    const flat = h.flat()
    const mean = flat.reduce((a, b) => a + b, 0) / flat.length
    const sd = Math.sqrt(flat.reduce((a, b) => a + (b - mean) ** 2, 0) / flat.length)
    stds.push(sd)
    hists.push(histogram(flat, sd))
  }
  return { stds, hists }
}

/** 15 bins over ±3 of the layer's own std (so the shape is visible at any scale) */
function histogram(xs: number[], sd: number): number[] {
  const bins = new Array(15).fill(0)
  const span = 3 * (sd || 1)
  for (const x of xs) {
    const k = Math.floor(((x + span) / (2 * span)) * 15)
    if (k >= 0 && k < 15) bins[k]++
  }
  const max = Math.max(...bins, 1)
  return bins.map((b) => b / max)
}

// ---------------------------------------------------------------- 4–5. overfitting

export const truth = (x: number) => Math.sin(Math.PI * x)

/** 10 noisy training points and 40 held-out points from the same curve */
export function overfitData(seed = 7, noise = 0.3, nTrain = 10) {
  const r = rng(seed)
  const trainX = Array.from({ length: nTrain }, (_, i) => -1 + (2 * i) / (nTrain - 1))
  const trainY = trainX.map((x) => truth(x) + noise * gauss(r))
  const heldX = Array.from({ length: 40 }, (_, i) => -1 + (2 * (i + 0.5)) / 40)
  const heldY = heldX.map((x) => truth(x) + noise * gauss(r))
  return { trainX, trainY, heldX, heldY }
}

export type Net = { W1: number[]; b1: number[]; W2: number[]; b2: number }

/** 1 → H → 1 network with tanh. W1 ~ N(0, 1) (fan-in 1), W2 ~ N(0, 1/H) (fan-in H). */
export function initNet(H: number, seed = 3, w1 = 1): Net {
  const r = rng(seed)
  const W1 = Array.from({ length: H }, () => w1 * gauss(r))
  const W2 = Array.from({ length: H }, () => gauss(r) / Math.sqrt(H))
  return { W1, b1: new Array(H).fill(0), W2, b2: 0 }
}

export const paramCount = (H: number) => 3 * H + 1

export function predict(net: Net, x: number): number {
  let y = net.b2
  for (let j = 0; j < net.W1.length; j++) y += net.W2[j] * Math.tanh(net.W1[j] * x + net.b1[j])
  return y
}

export function mse(net: Net, xs: number[], ys: number[]): number {
  let s = 0
  for (let i = 0; i < xs.length; i++) s += (predict(net, xs[i]) - ys[i]) ** 2
  return s / xs.length
}

export type TrainOpts = { H: number; steps: number; lr?: number; decay?: number; dropout?: number; every?: number; seed?: number; noise?: number; dataSeed?: number; w1?: number; snapshots?: boolean }

/**
 * Full-batch Adam on mean squared error (+ decay·Σw² over the weights, not the biases).
 * Dropout (inverted, on the hidden units) is applied only while training.
 * Records train and held-out loss every `every` steps; with `snapshots`, also the network's curve
 * on SNAP_X at each record (for drawing the fit as it trains).
 */
/** x positions where snapshots sample the network's curve */
export const SNAP_X = Array.from({ length: 61 }, (_, i) => -1 + i / 30)

export function trainOverfit(opts: TrainOpts) {
  const { H, steps, lr = 0.01, decay = 0, dropout = 0, every = 20, seed = 3, noise = 0.3, dataSeed = 7, w1 = 1, snapshots = false } = opts
  const d = overfitData(dataSeed, noise)
  const net = initNet(H, seed, w1)
  const dropRng = rng(seed + 100)
  // flat parameter view: [W1..., b1..., W2..., b2]
  const P = 3 * H + 1
  const m = new Float64Array(P), v = new Float64Array(P)
  const b1 = 0.9, b2 = 0.999, eps = 1e-8
  const curve: { step: number; train: number; held: number }[] = []
  const snaps: number[][] = []
  const record = (s: number) => {
    curve.push({ step: s, train: mse(net, d.trainX, d.trainY), held: mse(net, d.heldX, d.heldY) })
    if (snapshots) snaps.push(SNAP_X.map((x) => predict(net, x)))
  }
  record(0)
  const n = d.trainX.length
  for (let s = 1; s <= steps; s++) {
    const g = new Float64Array(P)
    for (let i = 0; i < n; i++) {
      const x = d.trainX[i]
      const a: number[] = [], keep: number[] = []
      let y = net.b2
      for (let j = 0; j < H; j++) {
        a[j] = Math.tanh(net.W1[j] * x + net.b1[j])
        keep[j] = dropout > 0 ? (dropRng() >= dropout ? 1 / (1 - dropout) : 0) : 1
        y += net.W2[j] * a[j] * keep[j]
      }
      const dy = (2 * (y - d.trainY[i])) / n
      for (let j = 0; j < H; j++) {
        const dh = dy * net.W2[j] * keep[j] * (1 - a[j] * a[j])
        g[j] += dh * x // W1
        g[H + j] += dh // b1
        g[2 * H + j] += dy * a[j] * keep[j] // W2
      }
      g[3 * H] += dy // b2
    }
    for (let j = 0; j < H; j++) {
      g[j] += 2 * decay * net.W1[j]
      g[2 * H + j] += 2 * decay * net.W2[j]
    }
    for (let k = 0; k < P; k++) {
      m[k] = b1 * m[k] + (1 - b1) * g[k]
      v[k] = b2 * v[k] + (1 - b2) * g[k] * g[k]
      const upd = (lr * (m[k] / (1 - b1 ** s))) / (Math.sqrt(v[k] / (1 - b2 ** s)) + eps)
      if (k < H) net.W1[k] -= upd
      else if (k < 2 * H) net.b1[k - H] -= upd
      else if (k < 3 * H) net.W2[k - 2 * H] -= upd
      else net.b2 -= upd
    }
    if (s % every === 0) record(s)
  }
  let best = curve[0]
  for (const c of curve) if (c.held < best.held) best = c
  return { curve, net, best, data: d, snaps }
}

// ---------------------------------------------------------------- polynomial fits (closed form)

/** Solve A·x = b by Gaussian elimination with partial pivoting (A is small and square). */
export function solve(A: number[][], b: number[]): number[] {
  const n = b.length
  const M = A.map((row, i) => [...row, b[i]])
  for (let c = 0; c < n; c++) {
    let p = c
    for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r
    ;[M[c], M[p]] = [M[p], M[c]]
    for (let r = c + 1; r < n; r++) {
      const f = M[r][c] / M[c][c]
      for (let k = c; k <= n; k++) M[r][k] -= f * M[c][k]
    }
  }
  const x = new Array(n).fill(0)
  for (let r = n - 1; r >= 0; r--) {
    let s = M[r][n]
    for (let k = r + 1; k < n; k++) s -= M[r][k] * x[k]
    x[r] = s / M[r][r]
  }
  return x
}

export const polyEval = (c: number[], x: number) => c.reduce((s, ck, k) => s + ck * x ** k, 0)

/**
 * Fit y ≈ c0 + c1·x + … + cd·x^d to the 10 training points by minimizing
 * mean(err²) + decay·(c1² + … + cd²). The constant c0 is not decayed. Same as demo.py.
 */
export function polyFit(d: number, decay = 0) {
  const data = overfitData()
  const { trainX: xs, trainY: ys } = data
  const n = xs.length
  const A = Array.from({ length: d + 1 }, (_, i) =>
    Array.from({ length: d + 1 }, (_, j) => xs.reduce((s, x) => s + x ** (i + j), 0) / n + (i === j && i > 0 ? decay : 0)),
  )
  const rhs = Array.from({ length: d + 1 }, (_, i) => xs.reduce((s, x, k) => s + x ** i * ys[k], 0) / n)
  const c = solve(A, rhs)
  const loss = (X: number[], Y: number[]) => X.reduce((s, x, k) => s + (polyEval(c, x) - Y[k]) ** 2, 0) / X.length
  return { c, train: loss(xs, ys), held: loss(data.heldX, data.heldY), data }
}
