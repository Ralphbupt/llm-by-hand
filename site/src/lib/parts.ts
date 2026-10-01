/**
 * Small helpers for levels 14–16 (attention, positional encoding, LayerNorm, depth).
 * Everything must match the numbers printed by the levels' demo.py.
 */
import { addMat, attention, matmul, type Mat, type Vec } from './num'

/** Sinusoidal positional encoding: PE[pos][i] = sin or cos(pos / 10000^(2⌊i/2⌋/d)) */
export function positionalEncoding(nPos: number, d: number): Mat {
  return Array.from({ length: nPos }, (_, pos) =>
    Array.from({ length: d }, (_, i) => {
      const angle = pos / 10000 ** ((i - (i % 2)) / d)
      return i % 2 === 0 ? Math.sin(angle) : Math.cos(angle)
    }),
  )
}

/** Self-attention with Q = K = V = X, scaled by sqrt(d). */
export const selfAttention = (X: Mat) => attention(X, X, X, X[0].length)

export const mean = (v: Vec) => v.reduce((a, b) => a + b, 0) / v.length
export const std = (v: Vec) => {
  const m = mean(v)
  return Math.sqrt(v.reduce((a, b) => a + (b - m) ** 2, 0) / v.length)
}
export const norm = (v: Vec) => Math.sqrt(v.reduce((a, b) => a + b * b, 0))

/** LayerNorm of one vector (no learned scale/shift), eps as in the demos. */
export function layerNorm(v: Vec, eps = 1e-5): Vec {
  const m = mean(v)
  const s = Math.sqrt(v.reduce((a, b) => a + (b - m) ** 2, 0) / v.length + eps)
  return v.map((x) => (x - m) / s)
}

/** Normalize each column instead of each row (the wrong axis, for comparison). */
export function normalizeColumns(a: Mat, eps = 1e-5): Mat {
  const cols = a[0].map((_, j) => layerNorm(a.map((r) => r[j]), eps))
  return a.map((r, i) => r.map((_, j) => cols[j][i]))
}

/** Deterministic random numbers (mulberry32 + Box–Muller) so the depth lab is the same on every load. */
export function gaussians(seed: number, n: number): number[] {
  let t = seed >>> 0
  const u = () => {
    t = (t + 0x6d2b79f5) >>> 0
    let r = Math.imul(t ^ (t >>> 15), 1 | t)
    r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296
  }
  const out: number[] = []
  while (out.length < n) {
    const a = Math.max(u(), 1e-12), b = u()
    out.push(Math.sqrt(-2 * Math.log(a)) * Math.cos(2 * Math.PI * b))
  }
  return out
}

export type DepthMode = 'plain' | 'residual' | 'residual+norm'

/**
 * Push a vector through `depth` layers. Each layer is x @ W with W ~ N(0, 1/d) × gain.
 * plain: x ← xW      residual: x ← x + xW      residual+norm: x ← LayerNorm(x + xW)
 * Returns the vector size (norm) after every layer, and the final vector.
 */
export function runDepth(x0: Vec, depth: number, gain: number, mode: DepthMode, seed = 7) {
  const d = x0.length
  const g = gaussians(seed, depth * d * d)
  let x = [...x0]
  const norms = [norm(x)]
  for (let l = 0; l < depth; l++) {
    const W: Mat = Array.from({ length: d }, (_, i) =>
      Array.from({ length: d }, (_, j) => (g[l * d * d + i * d + j] * gain) / Math.sqrt(d)),
    )
    const fx = matmul([x], W)[0]
    if (mode === 'plain') x = fx
    else if (mode === 'residual') x = addMat([x], [fx])[0]
    else x = layerNorm(addMat([x], [fx])[0])
    norms.push(norm(x))
  }
  return { norms, final: x }
}
