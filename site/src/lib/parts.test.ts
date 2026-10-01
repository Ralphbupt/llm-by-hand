import { describe, expect, it } from 'vitest'
import { layerNorm, normalizeColumns, positionalEncoding, runDepth, selfAttention } from './parts'

const close = (a: number, b: number, tol = 1e-3) => expect(Math.abs(a - b)).toBeLessThan(tol)

describe('levels 14–16 helpers (numbers from the demos)', () => {
  it('positional encoding, d = 2: [sin(pos), cos(pos)]', () => {
    const pe = positionalEncoding(3, 2)
    close(pe[1][0], 0.841)
    close(pe[1][1], 0.540)
    close(pe[0][1], 1)
  })
  it('layer norm of [1, 2, 3, 6]', () => {
    const v = layerNorm([1, 2, 3, 6])
    close(v[0], -1.069)
    close(v[3], 1.604)
  })
  it('column normalization is per column', () => {
    const c = normalizeColumns([[1, 10], [3, 30]])
    close(c[0][0], -1)
    close(c[1][1], 1)
  })
  it('cat, dog, car attention', () => {
    const r = selfAttention([[2, 0], [1, 1], [0, 2]])
    close(r.weights[0][0], 0.768)
    close(r.out[0][0], 1.723)
  })
  it('depth: plain with small gain vanishes, residual+norm stays near sqrt(d)', () => {
    const x0 = [1, -1, 0.5, 2, -0.5, 1.5, -2, 0]
    expect(runDepth(x0, 30, 0.5, 'plain').norms.at(-1)!).toBeLessThan(1e-5)
    close(runDepth(x0, 30, 0.5, 'residual+norm').norms.at(-1)!, Math.sqrt(8), 0.01)
  })
})
