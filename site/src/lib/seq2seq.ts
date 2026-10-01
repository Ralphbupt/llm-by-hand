/**
 * Level N5 helpers: one attention step over encoder states, in row-vector form.
 *   scores = E @ s          (one score per encoder state)
 *   w      = softmax(scores)
 *   ctx    = w @ E          (weighted average of the encoder states)
 */
export type Step = { scores: number[]; weights: number[]; ctx: number[] }

export function attendStep(E: number[][], s: number[]): Step {
  const scores = E.map((e) => e.reduce((acc, v, k) => acc + v * s[k], 0))
  const m = Math.max(...scores)
  const ex = scores.map((v) => Math.exp(v - m))
  const sum = ex.reduce((a, b) => a + b, 0)
  const weights = ex.map((v) => v / sum)
  const ctx = s.map((_, k) => E.reduce((acc, e, i) => acc + weights[i] * e[k], 0))
  return { scores, weights, ctx }
}

/** Index of the largest entry (ties: the first). */
export const argmax = (xs: number[]) => xs.reduce((best, v, i) => (v > xs[best] ? i : best), 0)
