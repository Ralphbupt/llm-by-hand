import { describe, expect, it } from 'vitest'
import { adamStep, lineGrad, optStart, polyFit, propagate, rng, sgdStep, trainOverfit } from './training'

// expected values are printed by content/1-foundations/{optimization,generalization}/demo.py
describe('training helpers match demo.py', () => {
  it('mini-batch gradients', () => {
    expect(lineGrad(0.5, 0, [0, 1, 2, 3]).gw).toBeCloseTo(-21.5, 12)
    expect(lineGrad(0.5, 0, [2]).gw).toBeCloseTo(-33, 12)
  })
  it('one SGD and one Adam step on the ravine', () => {
    expect(sgdStep(optStart([-4, 1]), 0.03).w).toEqual([-3.88, 0.25].map((v) => expect.closeTo(v, 12)))
    const a = adamStep(optStart([-4, 1]), 0.3).w
    expect(a[0]).toBeCloseTo(-3.7, 6)
    expect(a[1]).toBeCloseTo(0.7, 6)
  })
  it('polynomial fits on the seeded data', () => {
    expect(polyFit(3).held).toBeCloseTo(0.1579, 4)
    expect(polyFit(9).train).toBeCloseTo(0, 6)
    expect(polyFit(9).held).toBeCloseTo(0.8275, 4)
    expect(polyFit(9, 1e-4).held).toBeCloseTo(0.1727, 4)
  })
  it('the generator is deterministic', () => {
    const a = rng(7), b = rng(7)
    expect([a(), a()]).toEqual([b(), b()])
  })
  it('linear layers with std 0.2 and width 100 grow about 2x per layer', () => {
    const { stds } = propagate(100, 3, 0.2, 'none')
    expect(stds[2] / stds[1]).toBeGreaterThan(1.7)
    expect(stds[2] / stds[1]).toBeLessThan(2.3)
  })
  it('dropout helps the 32-unit network on held-out data', () => {
    const plain = trainOverfit({ H: 32, steps: 3000 }).curve.at(-1)!.held
    const drop = trainOverfit({ H: 32, steps: 3000, dropout: 0.3 }).curve.at(-1)!.held
    expect(drop).toBeLessThan(plain)
  })
})
