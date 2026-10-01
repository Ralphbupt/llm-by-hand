/**
 * 小矩阵运算 —— 页面上拖滑块时实时重算用的就是这些。
 * 规则:每个函数都必须和 numpy 的结果一致到 1e-6,
 * 由 export/export_goldens.py 导出的对拍数据在 num.test.ts 里保证。
 */
export type Mat = number[][]
export type Vec = number[]

export const shape = (a: Mat): [number, number] => [a.length, a[0]?.length ?? 0]

export function matmul(a: Mat, b: Mat): Mat {
  const [n, k] = shape(a)
  const [k2, m] = shape(b)
  if (k !== k2) throw new Error(`Shapes do not match: (${n},${k}) @ (${k2},${m})`)
  const out: Mat = []
  for (let i = 0; i < n; i++) {
    const row = new Array(m).fill(0)
    for (let j = 0; j < m; j++) {
      let s = 0
      for (let t = 0; t < k; t++) s += a[i][t] * b[t][j]
      row[j] = s
    }
    out.push(row)
  }
  return out
}

export const transpose = (a: Mat): Mat =>
  a[0].map((_, j) => a.map((row) => row[j]))

export const scale = (a: Mat, s: number): Mat => a.map((r) => r.map((v) => v * s))

export const addMat = (a: Mat, b: Mat): Mat =>
  a.map((r, i) => r.map((v, j) => v + b[i][j]))

export const relu = (a: Mat): Mat => a.map((r) => r.map((v) => Math.max(0, v)))

/** 每一行各自 softmax(= numpy 的 axis=-1) */
export function softmaxRows(a: Mat): Mat {
  return a.map((row) => {
    const mx = Math.max(...row)
    const e = row.map((v) => Math.exp(v - mx))
    const s = e.reduce((p, c) => p + c, 0)
    return e.map((v) => v / s)
  })
}

/** 把 mask 为 true 的格子置 -Infinity,再 softmax(= 17 里 masked_fill 的效果) */
export function maskedSoftmaxRows(a: Mat, mask: boolean[][]): Mat {
  return softmaxRows(a.map((r, i) => r.map((v, j) => (mask[i][j] ? -Infinity : v))))
}

/** 逐行 LayerNorm(= nn.LayerNorm 默认沿最后一维) */
export function layerNormRows(a: Mat, eps = 1e-5): Mat {
  return a.map((row) => {
    const n = row.length
    const mu = row.reduce((p, c) => p + c, 0) / n
    const v = row.reduce((p, c) => p + (c - mu) ** 2, 0) / n
    const sd = Math.sqrt(v + eps)
    return row.map((x) => (x - mu) / sd)
  })
}

/** 缩放点积注意力:返回权重和输出,和 08/09 打印的中间量一一对应 */
export function attention(
  Q: Mat, K: Mat, V: Mat, dk: number, mask?: boolean[][],
): { scores: Mat; weights: Mat; out: Mat } {
  const scores = scale(matmul(Q, transpose(K)), 1 / Math.sqrt(dk))
  const weights = mask ? maskedSoftmaxRows(scores, mask) : softmaxRows(scores)
  return { scores, weights, out: matmul(weights, V) }
}

export const causalMask = (L: number): boolean[][] =>
  Array.from({ length: L }, (_, i) => Array.from({ length: L }, (_, j) => j > i))

export function allClose(a: unknown, b: unknown, tol = 1e-6): boolean {
  if (Array.isArray(a) && Array.isArray(b)) {
    return a.length === b.length && a.every((v, i) => allClose(v, b[i], tol))
  }
  if (typeof a === 'number' && typeof b === 'number') {
    return Number.isNaN(a) && Number.isNaN(b) ? true : Math.abs(a - b) <= tol
  }
  return Object.is(a, b)
}
