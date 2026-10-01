import { describe, expect, it } from 'vitest'
import { softmax, topK, topP, topPKeep, cumulative, greedyWithPenalty, repeatLength, followsRules, type Trigram } from './generation'
import { layerNorm, rmsNorm, rotate, dot, silu, kvBytesPerToken } from './modern'
import fs from 'node:fs'

const S = [2.0, 1.5, 1.0, 0.0, -1.0]
const near = (a: number, b: number, tol = 1e-4) => expect(Math.abs(a - b)).toBeLessThan(tol)

describe('generation (numbers from generation/demo.py)', () => {
  it('softmax and greedy', () => near(softmax(S)[0], 0.4631))
  it('temperature', () => { near(softmax(S, 0.5)[0], 0.6562); near(softmax(S, 2)[0], 0.336) })
  it('top-k 2', () => near(topK(softmax(S), 2)[1], 0.3775))
  it('top-p', () => {
    expect(topPKeep(softmax(S), 0.9).filter(Boolean).length).toBe(3)
    expect(topPKeep(softmax(S), 0.5).filter(Boolean).length).toBe(2)
    near(topP(softmax(S), 0.9)[0], 0.5065)
    near(cumulative(softmax(S))[2], 0.9143)
  })
  it('trigram greedy loops, penalty breaks it', () => {
    const m = JSON.parse(fs.readFileSync('public/data/generation/trigram.json', 'utf8')) as Trigram
    const g = greedyWithPenalty(m, ['.', 'the'], 14, 0).words.slice(1)
    expect(g.join(' ')).toBe('the cat sat on the mat . the cat sat on the mat . the')
    expect(repeatLength(g)).toBe(7)
    const p = greedyWithPenalty(m, ['.', 'the'], 14, 1)
    expect(p.words.slice(1).join(' ')).toBe('the cat sat on the mat . the dog ran in the rug . the')
    const s7 = p.steps[7].scores.find((s) => s.word === 'cat')!
    near(s7.score, -1.7752)
    expect(followsRules(g)).toBe(true)
  })
})

describe('modern (numbers from modern-llm/demo.py)', () => {
  it('norms', () => {
    const x = [1, 2, 3, 6]
    near(layerNorm(x).std, 1.8708)
    near(rmsNorm(x).rms, 3.5355)
    near(rmsNorm(x).out[0], 0.2828)
  })
  it('rope keeps only the distance', () => {
    near(rotate([1, 0], 2)[0], 0.5403)
    near(dot(rotate([1, 0], 2), rotate([0, 1], 0)), 0.8415)
    near(dot(rotate([1, 0], 12), rotate([0, 1], 10)), 0.8415)
    near(dot(rotate([1, 0], 0), rotate([0, 1], 2)), -0.8415)
  })
  it('silu and kv bytes', () => {
    near(silu(1), 0.7311)
    expect(kvBytesPerToken(8, 128, 32)).toBe(131072)
  })
})
