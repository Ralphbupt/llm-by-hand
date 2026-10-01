import { describe, expect, it } from 'vitest'
import { ACT, accuracy, makeNet, paramCount, spiral, trainStep } from './foundations'

describe('activation functions (numbers from activations/demo.py)', () => {
  it('sigmoid and its slope at 0', () => {
    expect(ACT.sigmoid.f(0)).toBeCloseTo(0.5, 9)
    expect(ACT.sigmoid.df(0)).toBeCloseTo(0.25, 9)
  })
  it('tanh slope at 0 and at 3', () => {
    expect(ACT.tanh.df(0)).toBeCloseTo(1, 9)
    expect(ACT.tanh.df(3)).toBeCloseTo(0.009866, 5)
  })
  it('ReLU slope is 0 on the negative side', () => {
    expect(ACT.relu.df(-2)).toBe(0)
    expect(ACT.relu.df(2)).toBe(1)
  })
  it('GELU at −1 and its slope', () => {
    expect(ACT.gelu.f(-1)).toBeCloseTo(-0.158655, 5)
    expect(ACT.gelu.df(-1)).toBeCloseTo(-0.083315, 5)
    expect(ACT.gelu.f(2)).toBeCloseTo(1.954500, 5)
  })
  it('derivatives match finite differences', () => {
    for (const k of ['sigmoid', 'tanh', 'gelu'] as const)
      for (const x of [-2.3, -0.4, 0.7, 1.9]) {
        const h = 1e-5
        expect(ACT[k].df(x)).toBeCloseTo((ACT[k].f(x + h) - ACT[k].f(x - h)) / (2 * h), 5)
      }
  })
})

describe('MLP', () => {
  it('parameter counts', () => {
    expect(paramCount([2, 8, 1])).toBe(33)
    expect(paramCount([2, 8, 8, 1])).toBe(105)
  })
  it('a 2→16→16→1 tanh net learns the spiral', () => {
    const { X, y } = spiral(100, 0.08, 1)
    const net = makeNet([2, 16, 16, 1], 'tanh', 3)
    for (let i = 0; i < 1500; i++) trainStep(net, X, y, 0.02)
    expect(accuracy(net, X, y)).toBeGreaterThan(0.95)
  })
  it('a 2→2→1 net cannot', () => {
    const { X, y } = spiral(100, 0.08, 1)
    const net = makeNet([2, 2, 1], 'tanh', 3)
    for (let i = 0; i < 1500; i++) trainStep(net, X, y, 0.02)
    expect(accuracy(net, X, y)).toBeLessThan(0.8)
  })
})
