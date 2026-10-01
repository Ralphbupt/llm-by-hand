import { describe, expect, it } from 'vitest'
import { conv2d, convOut, gradThroughTime, lstmCell, maxPool2, pad, receptiveField, rnnScalar } from './classic'

const line5 = [0, 0, 0, 0, 0].map(() => [0, 0, 1, 0, 0])
const vEdge = [[-1, 0, 1], [-1, 0, 1], [-1, 0, 1]]
const hEdge = [[-1, -1, -1], [0, 0, 0], [1, 1, 1]]

describe('classic networks helpers (numbers from the demos)', () => {
  it('vertical edge kernel on a vertical line', () => {
    expect(conv2d(line5, vEdge)).toEqual([[3, 0, -3], [3, 0, -3], [3, 0, -3]])
  })
  it('horizontal edge kernel sees nothing on a vertical line', () => {
    expect(conv2d(line5, hEdge).flat().every((v) => v === 0)).toBe(true)
  })
  it('output size formula', () => {
    expect(convOut(5, 3)).toBe(3)
    expect(convOut(28, 5)).toBe(24)
    expect(convOut(28, 3, 2, 1)).toBe(14)
    expect(conv2d(line5, vEdge, 1, 1).length).toBe(5)
    expect(pad([[1]], 1)).toEqual([[0, 0, 0], [0, 1, 0], [0, 0, 0]])
  })
  it('max pooling and receptive field', () => {
    expect(maxPool2([[1, 3, 0, 2], [4, 2, 1, 1], [0, 0, 5, 6], [1, 2, 7, 0]])).toEqual([[4, 2], [2, 7]])
    expect(receptiveField(2)).toBe(5)
    expect(receptiveField(3)).toBe(7)
  })
  it('scalar RNN fades the first input', () => {
    const hs = rnnScalar([1, 0, 0, 0], 1, 0.5, 0)
    expect(hs.map((h) => +h.toFixed(4))).toEqual([0.7616, 0.3634, 0.1797, 0.0896])
    const g = gradThroughTime(hs, 0.5)
    expect(+g[3].toFixed(4)).toBe(0.1041)
  })
  it('LSTM cell', () => {
    const r = lstmCell(1, 0.9, 0.5, 0.8, 0.6)
    expect(+r.c.toFixed(4)).toBe(1.3)
    expect(+r.h.toFixed(4)).toBe(0.517)
  })
})
