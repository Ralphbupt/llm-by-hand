/**
 * Helpers for level N2, "Residuals and normalization".
 * The deep-stack simulation uses the same seeded generator as level 7 (lib/training.ts), and demo.py in
 * content/1-foundations/residuals-and-norms mirrors it draw for draw, so the lab and the demo print the same numbers.
 */
import { gauss, rng } from './training'

export const WIDTH = 16
export const BATCH = 32

const std = (xs: number[]) => {
  const m = xs.reduce((a, b) => a + b, 0) / xs.length
  return Math.sqrt(xs.reduce((a, b) => a + (b - m) ** 2, 0) / xs.length)
}

/**
 * Push a batch through `depth` tanh layers (weights ~ N(0, (scale/√WIDTH)²)), then send a random gradient back down.
 * plain:    h ← tanh(h @ W)
 * residual: h ← h + tanh(h @ W)
 * Returns the std of the activations after each layer (index 0 = the input) and the std of the gradient
 * reaching each layer's input (index 0 = what reaches the input, index depth = the gradient at the top).
 * Random draws, in order: the input (BATCH × WIDTH), every layer's W (WIDTH × WIDTH, row by row), the top gradient.
 */
export function stack(depth: number, scale: number, residual: boolean, seed = 5) {
  const r = rng(seed)
  const draw = (rows: number, cols: number, s: number) =>
    Array.from({ length: rows }, () => Array.from({ length: cols }, () => s * gauss(r)))
  let h = draw(BATCH, WIDTH, 1)
  const Ws: number[][][] = []
  const tanhs: number[][][] = [] // tanh(h @ W) for each layer, needed going back
  const act = [std(h.flat())]
  for (let l = 0; l < depth; l++) {
    const W = draw(WIDTH, WIDTH, scale / Math.sqrt(WIDTH))
    Ws.push(W)
    const t = h.map((row) => Array.from({ length: WIDTH }, (_, j) => Math.tanh(row.reduce((s, x, k) => s + x * W[k][j], 0))))
    tanhs.push(t)
    h = residual ? h.map((row, i) => row.map((x, j) => x + t[i][j])) : t
    act.push(std(h.flat()))
  }
  let g = draw(BATCH, WIDTH, 1)
  const grad = new Array(depth + 1).fill(0)
  grad[depth] = std(g.flat())
  for (let l = depth - 1; l >= 0; l--) {
    const W = Ws[l], t = tanhs[l]
    // through tanh: dz = g · (1 − tanh²); through the matmul: dz @ W.T
    const back = g.map((row, i) =>
      Array.from({ length: WIDTH }, (_, k) => row.reduce((s, gj, j) => s + gj * (1 - t[i][j] ** 2) * W[k][j], 0)),
    )
    g = residual ? g.map((row, i) => row.map((x, k) => x + back[i][k])) : back
    grad[l] = std(g.flat())
  }
  return { act, grad }
}

/** The 4×4 example batch used for both norms: rows are examples, columns are features. */
export const X4 = [
  [1, 4, 2, 9],
  [1, 0, 6, 3],
  [5, 1, 5, 1],
  [5, 7, 3, 1],
]

/** Normalize along an axis (0 = down each column, BatchNorm; 1 = across each row, LayerNorm). No ε, population std. */
export function normalize(X: number[][], axis: 0 | 1) {
  const R = X.length, C = X[0].length
  const means: number[] = [], stds: number[] = []
  const groups = axis === 0 ? C : R
  for (let g = 0; g < groups; g++) {
    const xs = axis === 0 ? X.map((row) => row[g]) : X[g]
    const m = xs.reduce((a, b) => a + b, 0) / xs.length
    means.push(m)
    stds.push(Math.sqrt(xs.reduce((a, b) => a + (b - m) ** 2, 0) / xs.length))
  }
  const out = X.map((row, i) => row.map((x, j) => {
    const g = axis === 0 ? j : i
    return stds[g] === 0 ? 0 : (x - means[g]) / stds[g]
  }))
  void R
  return { out, means, stds }
}
