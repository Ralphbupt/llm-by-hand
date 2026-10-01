/**
 * Helpers for levels 3–5: activation functions with their derivatives, a seeded spiral dataset,
 * and a small fully connected network trained with Adam (used by the MLP lab).
 * Every formula here matches the numpy demos in content/1-foundations/{activations,mlp}/demo.py.
 */

// ---- activation functions -------------------------------------------------------------

/** erf, Abramowitz–Stegun 7.1.26 (max error 1.5e-7) */
export function erf(x: number): number {
  const s = Math.sign(x)
  const a = Math.abs(x)
  const t = 1 / (1 + 0.3275911 * a)
  const y = 1 - ((((1.061405429 * t - 1.453152027) * t + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-a * a)
  return s * y
}
const Phi = (x: number) => 0.5 * (1 + erf(x / Math.SQRT2)) // standard normal CDF
const phi = (x: number) => Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI) // standard normal density

export type ActName = 'sigmoid' | 'tanh' | 'relu' | 'gelu'

export const ACT: Record<ActName, { f: (x: number) => number; df: (x: number) => number; label: string }> = {
  sigmoid: {
    label: 'sigmoid',
    f: (x) => 1 / (1 + Math.exp(-x)),
    df: (x) => {
      const s = 1 / (1 + Math.exp(-x))
      return s * (1 - s)
    },
  },
  tanh: { label: 'tanh', f: Math.tanh, df: (x) => 1 - Math.tanh(x) ** 2 },
  relu: { label: 'ReLU', f: (x) => Math.max(0, x), df: (x) => (x > 0 ? 1 : 0) },
  gelu: { label: 'GELU', f: (x) => x * Phi(x), df: (x) => Phi(x) + x * phi(x) },
}

// ---- seeded random numbers --------------------------------------------------------------

export function rng(seed: number) {
  let a = seed >>> 0
  const next = () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
  const normal = () => Math.sqrt(-2 * Math.log(next() || 1e-12)) * Math.cos(2 * Math.PI * next())
  return { next, normal }
}

// ---- data: two interleaved spiral arms --------------------------------------------------

/** n points per class. Class 0 and class 1 are the same arm, rotated half a turn. */
export function spiral(n = 100, noise = 0.08, seed = 1): { X: number[][]; y: number[] } {
  const r = rng(seed)
  const X: number[][] = []
  const y: number[] = []
  for (let c = 0; c < 2; c++) {
    for (let i = 0; i < n; i++) {
      const rad = 0.1 + (0.9 * i) / n
      const th = rad * 2.6 * Math.PI + c * Math.PI
      X.push([rad * Math.cos(th) + noise * r.normal(), rad * Math.sin(th) + noise * r.normal()])
      y.push(c)
    }
  }
  return { X, y }
}

// ---- a tiny fully connected network ----------------------------------------------------

export type Net = {
  sizes: number[]         // e.g. [2, 8, 8, 1]
  W: number[][][]         // W[l] has shape (sizes[l], sizes[l+1])
  b: number[][]
  act: ActName            // hidden activation; the output is a sigmoid
  m: { W: number[][][]; b: number[][] }  // Adam first moments
  v: { W: number[][][]; b: number[][] }  // Adam second moments
  t: number
}

export function paramCount(sizes: number[]): number {
  let n = 0
  for (let l = 0; l + 1 < sizes.length; l++) n += sizes[l] * sizes[l + 1] + sizes[l + 1]
  return n
}

const zeros2 = (r: number, c: number) => Array.from({ length: r }, () => new Array(c).fill(0))

export function makeNet(sizes: number[], act: ActName, seed?: number): Net {
  const r = rng(seed ?? (Math.random() * 2 ** 31) | 0)
  const W = sizes.slice(0, -1).map((fi, l) =>
    Array.from({ length: fi }, () => Array.from({ length: sizes[l + 1] }, () => r.normal() / Math.sqrt(fi))),
  )
  const b = sizes.slice(1).map((n) => new Array(n).fill(0))
  const zW = () => sizes.slice(0, -1).map((fi, l) => zeros2(fi, sizes[l + 1]))
  const zb = () => sizes.slice(1).map((n) => new Array(n).fill(0))
  return { sizes, W, b, act, m: { W: zW(), b: zb() }, v: { W: zW(), b: zb() }, t: 0 }
}

/** forward one point; returns every layer's activations (a[0] = input, last = [p]) and pre-activations */
export function forward(net: Net, x: number[]) {
  const a: number[][] = [x]
  const z: number[][] = []
  const L = net.W.length
  for (let l = 0; l < L; l++) {
    const prev = a[l]
    const out = net.b[l].slice()
    for (let i = 0; i < prev.length; i++) {
      const wi = net.W[l][i]
      const pi = prev[i]
      for (let j = 0; j < out.length; j++) out[j] += pi * wi[j]
    }
    z.push(out)
    a.push(l === L - 1 ? out.map(ACT.sigmoid.f) : out.map(ACT[net.act].f))
  }
  return { a, z, p: a[L][0] }
}

/** one full-batch Adam step on binary cross-entropy; returns the loss before the step */
export function trainStep(net: Net, X: number[][], y: number[], lr = 0.02): number {
  const L = net.W.length
  const gW = net.sizes.slice(0, -1).map((fi, l) => zeros2(fi, net.sizes[l + 1]))
  const gb = net.sizes.slice(1).map((n) => new Array(n).fill(0))
  let loss = 0
  const N = X.length
  for (let n = 0; n < N; n++) {
    const { a, z, p } = forward(net, X[n])
    loss -= (y[n] * Math.log(p + 1e-12) + (1 - y[n]) * Math.log(1 - p + 1e-12)) / N
    let d = [(p - y[n]) / N] // dLoss/dz for the output layer (sigmoid + cross-entropy)
    for (let l = L - 1; l >= 0; l--) {
      const prev = a[l]
      for (let i = 0; i < prev.length; i++) for (let j = 0; j < d.length; j++) gW[l][i][j] += prev[i] * d[j]
      for (let j = 0; j < d.length; j++) gb[l][j] += d[j]
      if (l > 0) {
        const nd = new Array(prev.length).fill(0)
        for (let i = 0; i < prev.length; i++) {
          let s = 0
          for (let j = 0; j < d.length; j++) s += net.W[l][i][j] * d[j]
          nd[i] = s * ACT[net.act].df(z[l - 1][i])
        }
        d = nd
      }
    }
  }
  // Adam
  net.t++
  const b1 = 0.9, b2 = 0.999, eps = 1e-8
  const c1 = 1 - b1 ** net.t, c2 = 1 - b2 ** net.t
  const upd = (P: number[], G: number[], M: number[], V: number[]) => {
    for (let k = 0; k < P.length; k++) {
      M[k] = b1 * M[k] + (1 - b1) * G[k]
      V[k] = b2 * V[k] + (1 - b2) * G[k] * G[k]
      P[k] -= (lr * (M[k] / c1)) / (Math.sqrt(V[k] / c2) + eps)
    }
  }
  for (let l = 0; l < L; l++) {
    for (let i = 0; i < net.W[l].length; i++) upd(net.W[l][i], gW[l][i], net.m.W[l][i], net.v.W[l][i])
    upd(net.b[l], gb[l], net.m.b[l], net.v.b[l])
  }
  return loss
}

export function accuracy(net: Net, X: number[][], y: number[]): number {
  let ok = 0
  for (let n = 0; n < X.length; n++) if ((forward(net, X[n]).p > 0.5 ? 1 : 0) === y[n]) ok++
  return ok / X.length
}
