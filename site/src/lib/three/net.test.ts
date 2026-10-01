import { describe, expect, it } from 'vitest'
import {
  blockDims, bucketFor, convWindow, itemsOf, layoutNet, looksAt, paramsOf, samplePairs, scales, segmentsOf, squareish, stateAt,
  type Net3DSpec,
} from './net'
import { backpropNumbers, backpropSpec, denseForward, MLP_EXAMPLE, mlpSpec, seededNet } from './netSpecs'
import { netSpecs } from './netLessons'

const close = (a: number, b: number) => expect(a).toBeCloseTo(b, 4)

describe('shapes and layout', () => {
  it('turns long vectors into near-square blocks', () => {
    expect(squareish(784)).toEqual([28, 28])
    expect(squareish(128)).toEqual([8, 16])
    expect(blockDims({ id: 'a', label: 'a', kind: 'tensor', shape: [4, 26, 26] })).toEqual([4, 26, 26])
    expect(blockDims({ id: 'a', label: 'a', kind: 'tensor', shape: [6] })).toEqual([1, 6, 1])
    const capped = blockDims({ id: 'a', label: 'a', kind: 'tensor', shape: [64, 64, 64] }, 4096)
    expect(capped[0] * capped[1] * capped[2]).toBeLessThanOrEqual(4096)
  })
  it('lays layers left to right, neurons centered on y = 0', () => {
    const L = layoutNet(backpropSpec())
    const xs = L.nodes.map((n) => n.center[0])
    expect([...xs].sort((a, b) => a - b)).toEqual(xs)
    const h = L.byId.get('h')!
    expect(h.items).toHaveLength(3)
    close(h.items[0][1] + h.items[2][1], 0)
  })
  it('vertical (phones): after the quarter turn, item 0 of each column is on the left', () => {
    const L = layoutNet(backpropSpec(), { vertical: true })
    // the views turn layout (x, y) into screen (y, -x): screen x is the layout y
    for (const n of L.nodes.filter((n) => n.node.kind === 'neurons' && n.items.length > 1)) {
      const sx = n.items.map((p) => p[1])
      expect([...sx].sort((a, b) => a - b)).toEqual(sx)
    }
  })
  it('keeps manual positions', () => {
    const spec: Net3DSpec = { id: 't', layout: 'unrolled', nodes: [{ id: 'a', label: 'a', kind: 'op', shape: [1], at: [3, -2, 0] }], edges: [] }
    expect(layoutNet(spec).nodes[0].center).toEqual([3, -2, 0])
  })
  it('hourglass blocks share one cell pitch, so size shows the count', () => {
    const s = netSpecs.autoencoder()
    const L = layoutNet(s)
    const pitches = new Set(L.nodes.filter((n) => n.kind === 'cell').map((n) => n.size))
    expect(pitches.size).toBe(1)
  })
})

describe('edges', () => {
  it('samples the largest |w| first', () => {
    const p = samplePairs(2, 2, [[0.1, -3], [2, 0.5]], 2)
    expect(p.map((x) => x.w)).toEqual([-3, 2])
    expect(samplePairs(3, 4, undefined, 100)).toHaveLength(12)
  })
  it('puts weights into three widths', () => {
    expect(bucketFor(0, 1)).toBe(0)
    expect(bucketFor(1, 1)).toBe(2)
  })
  it('finds a conv window', () => {
    expect(convWindow(2, 3, { size: 3, stride: 1 })).toEqual({ r0: 2, r1: 4, c0: 3, c1: 5 })
    expect(convWindow(1, 1, { size: 2, stride: 2 })).toEqual({ r0: 2, r1: 3, c0: 2, c1: 3 })
  })
})

describe('steps', () => {
  it('values add up over the steps, gradients only show going back', () => {
    const s = backpropSpec()
    expect(stateAt(s, -1).step).toBeNull()
    const f = stateAt(s, 3)
    expect(Object.keys(f.values).sort()).toEqual(['L', 'a', 'h', 'x'])
    expect(f.dir).toBe('forward')
    const b = stateAt(s, 7)
    expect(b.dir).toBe('backward')
    expect(Object.keys(b.grads)).toContain('W1')
  })
  it('looks: forward is accent, backward is grad; lines switch to |∂L/∂w|', () => {
    const s = backpropSpec()
    const L = layoutNet(s)
    const items = itemsOf(L)
    const { segs, rails } = segmentsOf(s, L, 512)
    const fwd = looksAt(s, items, segs, rails, 1, null)
    const hRing = fwd.rings[items.discs.findIndex((d) => d.ln.node.id === 'h')]
    expect(hRing.tone).toBe('accent')
    const back = looksAt(s, items, segs, rails, 7, null)
    const w1 = segs.findIndex((x) => x.e.id === 'W1')
    expect(back.lines[w1].tone).toBe('grad')
    const hBack = back.rings[items.discs.findIndex((d) => d.ln.node.id === 'h')]
    expect(hBack.tone).toBe('grad')
    expect(hBack.r).toBeGreaterThan(1.22) // the halo grows with |∂L/∂h|
  })
})

describe('backprop lesson numbers', () => {
  it('hidden neuron 1 is section 1’s neuron, and the output starts the same way', () => {
    const k = backpropNumbers()
    close(k.z1[0], 0)
    close(k.h[0], 0.5)
    close(k.z2, 0)
    close(k.a, 0.5)
    close(k.L, 0.25)
    close(k.dA, -1)
    close(k.dZ2, -0.25)
  })
  it('matches a hand-checked backward pass', () => {
    const k = backpropNumbers()
    k.dW2.map((r) => r[0]).forEach((v, i) => close(v, [-0.125, -0.182765, -0.067235][i]))
    k.dH.forEach((v, i) => close(v, [-0.5, -0.25, -0.25][i]))
    k.dW1[0].forEach((v, i) => close(v, [-0.25, -0.098306, -0.098306][i]))
    k.dW1[1].forEach((v, i) => close(v, [-0.125, -0.049153, -0.049153][i]))
  })
  it('agrees with a numeric gradient', () => {
    const base = { x: [2, 1], y: 1, W1: [[0.5, 1, -1], [0, -1, 1]], b1: [-1, 0, 0], W2: [[2], [1], [1]], b2: [-2] }
    const k = backpropNumbers(base)
    const eps = 1e-5
    for (let i = 0; i < 2; i++)
      for (let j = 0; j < 3; j++) {
        const up = structuredClone(base), dn = structuredClone(base)
        up.W1[i][j] += eps
        dn.W1[i][j] -= eps
        close((backpropNumbers(up).L - backpropNumbers(dn).L) / (2 * eps), k.dW1[i][j])
      }
  })
  it('counts parameters', () => {
    const s = backpropSpec()
    expect(paramsOf(s, 'h')).toBe(9)
    expect(paramsOf(s, 'a')).toBe(4)
  })
})

describe('mlp lesson numbers', () => {
  it('the hand example: H = [2, 0], p = sigmoid(4.5)', () => {
    const a = denseForward(MLP_EXAMPLE, MLP_EXAMPLE.x)
    expect(a[1]).toEqual([2, 0])
    close(a[2][0], 1 / (1 + Math.exp(-4.5)))
  })
  it('random nets are the same every time and count parameters like the lesson', () => {
    expect(seededNet(8, 2)).toEqual(seededNet(8, 2))
    const s = mlpSpec(seededNet(8, 2), [0.5, -0.5], 'm')
    const total = s.nodes.reduce((a, n) => a + (paramsOf(s, n.id) ?? 0), 0)
    expect(total).toBe(2 * 8 + 8 + 8 * 8 + 8 + 8 + 1)
  })
})

describe('every lesson spec is drawable', () => {
  for (const [name, make] of Object.entries(netSpecs)) {
    it(name, () => {
      const s = make()
      const ids = new Set(s.nodes.map((n) => n.id))
      expect(ids.size).toBe(s.nodes.length)
      for (const e of s.edges) {
        expect(ids.has(e.from), `${e.id} from`).toBe(true)
        expect(ids.has(e.to), `${e.id} to`).toBe(true)
      }
      for (const st of s.steps ?? []) for (const id of st.active) expect(ids.has(id) || s.edges.some((e) => e.id === id), `${st.id}: ${id}`).toBe(true)
      const L = layoutNet(s)
      const { cells, discs } = itemsOf(L)
      expect(cells.length + discs.length).toBeLessThan(20000)
      const { segs } = segmentsOf(s, L, 512)
      expect(segs.length).toBeLessThan(8000)
      scales(s)
    })
  }
})

describe('rnn lesson numbers', () => {
  it('matches the lab: h1 = tanh(1), and ∂h4/∂h1 = 0.1041 as in RnnGradLab', async () => {
    const { rnnNumbers } = await import('./netLessons')
    const { gradThroughTime } = await import('../classic')
    const { hs, g } = rnnNumbers()
    close(hs[0], Math.tanh(1))
    expect(+g[0].toFixed(4)).toBe(0.1041)
    expect(+g[0].toFixed(4)).toBe(+gradThroughTime(hs, 0.5)[3].toFixed(4))
  })
})
