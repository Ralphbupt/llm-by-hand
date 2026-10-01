import { describe, expect, it } from 'vitest'
import { normalize, stack, X4 } from './residuals'

// numbers printed by content/1-foundations/residuals-and-norms/demo.py (same generator, same draws)
describe('deep stack (matches demo.py)', () => {
  it('plain, depth 30, scale 0.8: the gradient fades to about 1e-4 of the top', () => {
    const { act, grad } = stack(30, 0.8, false)
    expect(grad[0] / grad[30]).toBeCloseTo(1.32e-4, 5)
    expect(act[30]).toBeLessThan(0.001)
  })
  it('residual, depth 30, scale 0.8: the gradient survives (it grows instead)', () => {
    const { act, grad } = stack(30, 0.8, true)
    expect(grad[0] / grad[30]).toBeCloseTo(11.2, 0)
    expect(act[10]).toBeCloseTo(2.33, 2)
    expect(act[30]).toBeCloseTo(4.39, 2)
  })
})

describe('BatchNorm vs LayerNorm on the 4×4 example', () => {
  it('BatchNorm: column 0 has mean 3, std 2, and X[2][0] becomes 1', () => {
    const r = normalize(X4, 0)
    expect(r.means[0]).toBe(3)
    expect(r.stds[0]).toBe(2)
    expect(r.out[2][0]).toBe(1)
  })
  it('LayerNorm: row 2 becomes [1, −1, 1, −1]', () => {
    const r = normalize(X4, 1)
    expect(r.out[2]).toEqual([1, -1, 1, -1])
  })
})
