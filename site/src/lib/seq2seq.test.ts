import { describe, expect, it } from 'vitest'
import { argmax, attendStep } from './seq2seq'

describe('one attention step (numbers from seq2seq-attention/demo.py)', () => {
  it('the hand example: E = [[1,0],[0,1],[0,-1]], s = [2,0]', () => {
    const r = attendStep([[1, 0], [0, 1], [0, -1]], [2, 0])
    expect(r.scores).toEqual([2, 0, 0])
    expect(r.weights[0]).toBeCloseTo(0.787, 3)
    expect(r.weights[1]).toBeCloseTo(0.1065, 4)
    expect(r.ctx[0]).toBeCloseTo(0.787, 3)
    expect(r.ctx[1]).toBeCloseTo(0, 9)
  })
  it('the boss test case: E = [[2,0],[0,2],[1,1]], s = [1,0]', () => {
    const r = attendStep([[2, 0], [0, 2], [1, 1]], [1, 0])
    expect(r.weights.map((w) => +w.toFixed(4))).toEqual([0.6652, 0.09, 0.2447])
    expect(r.ctx.map((c) => +c.toFixed(4))).toEqual([1.5752, 0.4248])
  })
  it('weights add up to 1 and argmax picks the biggest', () => {
    const r = attendStep([[3, 1], [-1, 2], [0, 0], [1, 1]], [0.5, -2])
    expect(r.weights.reduce((a, b) => a + b, 0)).toBeCloseTo(1, 12)
    expect(argmax([0.1, 0.7, 0.2])).toBe(1)
  })
})
