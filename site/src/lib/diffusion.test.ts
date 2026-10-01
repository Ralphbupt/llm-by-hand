import { describe, expect, it } from 'vitest'
import fs from 'node:fs'
import {
  schedule, addNoise, guessClean, reverseStep, guide, layersFromJson, predictNoiseCond,
  initLayers, adamFor, trainStep, rng, forward,
} from './diffusion'

const close = (a: number[], b: number[], tol = 1e-4) =>
  a.forEach((v, i) => expect(Math.abs(v - b[i])).toBeLessThan(tol))

describe('diffusion: the page examples', () => {
  const toy = schedule([0.1, 0.2, 0.5])
  it('alpha-bar of the toy schedule', () => close(toy.alphaBar, [0.9, 0.72, 0.36], 1e-12))
  it('A1: x_3 and back', () => {
    const x3 = addNoise([1, 2], [0.5, -1], 0.36)
    close(x3, [1.0, 0.4], 1e-12)
    close(guessClean(x3, [0.5, -1], 0.36), [1, 2], 1e-12)
  })
  it('A2: one reverse step', () => {
    close(reverseStep([1, 0.4], [0.5, -1], 3, toy, null), [0.97227, 1.44957], 1e-5)
    close(reverseStep([1, 0.4], [0.5, -1], 3, toy, [0.2, -0.4]), [1.11369, 1.16673], 1e-5)
  })
  it('A2: guidance mix', () => close(guide([0.2, 0], [0.6, -0.4], 3), [1.4, -1.2], 1e-12))
})

describe('diffusion: the trained network matches numpy', () => {
  const m = JSON.parse(fs.readFileSync('public/data/sampling-and-guidance/cond_mlp.json', 'utf8'))
  const layers = layersFromJson(m.layers)
  const x: [number, number][] = [[0.3, -1.2], [1.5, 0.7]]
  // reference values printed by numpy from the same JSON
  const cases: [number, number, number[][]][] = [
    [25, 0, [[0.354376, -1.003573], [1.530893, 0.714537]]],
    [50, 3, [[0.305423, -1.200126], [1.527556, 0.670963]]],
    [1, 2, [[-0.441514, -2.035682], [0.388787, 2.014139]]],
  ]
  for (const [t, c, want] of cases) {
    it(`t=${t} class=${c}`, () => predictNoiseCond(layers, x, t, m.T, c).forEach((p, i) => close(p, want[i], 1e-4)))
  }
})

describe('diffusion: training lowers the loss', () => {
  it('fits y = 2x on a tiny net', () => {
    const r = rng(0)
    const net = initLayers([1, 8, 1], r)
    const opt = adamFor(net)
    const X = Float32Array.from([-1, -0.5, 0, 0.5, 1]), Y = X.map((v) => 2 * v)
    const first = trainStep(net, opt, X, Y, 5, 0.01)
    let last = first
    for (let i = 0; i < 500; i++) last = trainStep(net, opt, X, Y, 5, 0.01)
    expect(last).toBeLessThan(first / 20)
    expect(forward(net, X, 5).at(-1)!.length).toBe(5)
  })
})
