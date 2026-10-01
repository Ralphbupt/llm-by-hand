/**
 * Math for the Classic networks branch: convolution, pooling, a scalar RNN, one LSTM cell.
 * Every function matches the numpy in that branch's demo.py files (see classic.test.ts).
 */
export type Grid = number[][]

/** Output side length of a convolution: floor((n − k + 2p) / s) + 1 */
export const convOut = (n: number, k: number, s = 1, p = 0) => Math.floor((n - k + 2 * p) / s) + 1

/** Pad a grid with p rings of zeros. */
export function pad(img: Grid, p: number): Grid {
  if (p === 0) return img
  const w = img[0].length + 2 * p
  const zero = () => new Array(w).fill(0)
  return [
    ...Array.from({ length: p }, zero),
    ...img.map((r) => [...new Array(p).fill(0), ...r, ...new Array(p).fill(0)]),
    ...Array.from({ length: p }, zero),
  ]
}

/** 2D convolution as used in neural networks (no kernel flip): out[i][j] = sum(window · kernel). */
export function conv2d(img: Grid, k: Grid, stride = 1, padding = 0): Grid {
  const x = pad(img, padding)
  const kh = k.length, kw = k[0].length
  const oh = convOut(img.length, kh, stride, padding), ow = convOut(img[0].length, kw, stride, padding)
  const out: Grid = []
  for (let i = 0; i < oh; i++) {
    const row: number[] = []
    for (let j = 0; j < ow; j++) {
      let s = 0
      for (let a = 0; a < kh; a++) for (let b = 0; b < kw; b++) s += x[i * stride + a][j * stride + b] * k[a][b]
      row.push(s)
    }
    out.push(row)
  }
  return out
}

/** The (row, col) of the top-left input pixel (in padded coordinates) that output (i, j) reads. */
export const windowAt = (i: number, j: number, stride: number) => ({ r: i * stride, c: j * stride })

/** 2×2 max pooling with stride 2 (drops a last odd row/column). */
export function maxPool2(img: Grid): Grid {
  const out: Grid = []
  for (let i = 0; i + 1 < img.length; i += 2) {
    const row: number[] = []
    for (let j = 0; j + 1 < img[0].length; j += 2)
      row.push(Math.max(img[i][j], img[i][j + 1], img[i + 1][j], img[i + 1][j + 1]))
    out.push(row)
  }
  return out
}

/** Receptive field of L stacked k×k convolutions (stride 1): 1 + L·(k − 1). */
export const receptiveField = (layers: number, k = 3) => 1 + layers * (k - 1)

/** Scalar RNN: h_t = act(wx·x_t + wh·h_{t−1} + b). Returns h_1..h_T. */
export function rnnScalar(xs: number[], wx: number, wh: number, b: number, h0 = 0, act: 'tanh' | 'none' = 'tanh'): number[] {
  const hs: number[] = []
  let h = h0
  for (const x of xs) {
    const z = wx * x + wh * h + b
    h = act === 'tanh' ? Math.tanh(z) : z
    hs.push(h)
  }
  return hs
}

/**
 * How much a change in h_1 moves h_t, for every t: d h_t / d h_1 = Π_{s=2..t} wh · act'(z_s).
 * For tanh, act'(z_s) = 1 − h_s². Entry 0 is 1 (h_1 itself).
 */
export function gradThroughTime(hs: number[], wh: number, act: 'tanh' | 'none' = 'tanh'): number[] {
  const g = [1]
  for (let t = 1; t < hs.length; t++) g.push(g[t - 1] * wh * (act === 'tanh' ? 1 - hs[t] ** 2 : 1))
  return g
}

export const sigmoid = (z: number) => 1 / (1 + Math.exp(-z))

/** One scalar LSTM cell step with the gate values given directly. */
export function lstmCell(cPrev: number, f: number, i: number, g: number, o: number) {
  const c = f * cPrev + i * g
  return { c, h: o * Math.tanh(c) }
}

/** The text rules of the LSTM boss: 'ok' | 'color' (right shape, colors differ) | 'broken'. */
export const RULES = {
  colors: ['red', 'blue', 'green', 'gold', 'pink', 'gray'],
  animals: ['fox', 'cat', 'owl', 'bee', 'yak', 'dog'],
  verbs: ['sees', 'hides', 'finds', 'wants', 'keeps', 'likes'],
  things: ['box', 'cup', 'hat', 'map', 'key', 'bag'],
}
