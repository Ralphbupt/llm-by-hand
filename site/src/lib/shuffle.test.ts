import { describe, expect, it } from 'vitest'
import { optionOrder, seedOf } from './shuffle'

describe('graded Predict option order', () => {
  it('is a permutation, the same every time', () => {
    for (const id of ['kv-total', 'copy-first', 'x', 'a-much-longer-exercise-id']) {
      for (const n of [2, 3, 4, 5]) {
        const o = optionOrder(id, n)
        expect([...o].sort()).toEqual(Array.from({ length: n }, (_, i) => i))
        expect(optionOrder(id, n)).toEqual(o)
      }
    }
  })
  it('seeds by the plain id, so the page, the warm-up and the mistake book agree', () => {
    expect(optionOrder('full-model/copy-first', 4)).toEqual(optionOrder('copy-first', 4))
  })
  it('matches the values scripts/check_exercises.py mirrors', () => {
    expect(seedOf('kv-total')).toBe(4044722364)
    expect(optionOrder('kv-total', 3)).toEqual([1, 0, 2])
    expect(optionOrder('copy-first', 4)).toEqual([3, 2, 1, 0])
  })
  it('keeps the answer findable: the shown place maps back to the yaml index', () => {
    const order = optionOrder('kv-total', 3)
    const answer = 2
    const place = order.indexOf(answer)
    expect(order[place]).toBe(answer)
  })
  it('spreads answers over the places', () => {
    const count = [0, 0, 0]
    for (let k = 0; k < 300; k++) count[optionOrder(`q-${k}`, 3).indexOf(0)]++
    for (const c of count) expect(c).toBeGreaterThan(70)
  })
})
