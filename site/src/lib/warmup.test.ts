import { describe, expect, it } from 'vitest'
import { pickWarmup, type WarmData, type WarmItem } from './warmup'

const item = (page: string, id: string): WarmItem => ({ page, id, type: 'number', prompt: id, answer: 1 })
const data: WarmData = {
  levels: [
    { slug: 'one', level: '1', title: 'One' },
    { slug: 'two', level: '2', title: 'Two' },
    { slug: 'three', level: '3', title: 'Three' },
  ],
  items: [item('one', 'a'), item('one', 'b'), item('two', 'c'), item('two', 'd'), item('three', 'e'), item('three', 'f')],
}
const ids = (xs: WarmItem[]) => xs.map((x) => `${x.page}/${x.id}`)

describe('warm-up picking', () => {
  it('nothing tried: unseen questions from the previous two levels', () => {
    expect(ids(pickWarmup(data, {}, { misses: {} }))).toEqual(['two/c', 'two/d'])
  })
  it('missed and not solved since comes first, then the oldest solve', () => {
    const progress = { 'one/a': { at: 100 }, 'one/b': { at: 50 }, 'two/c': { at: 300 } }
    const stats = { misses: { 'two/d': 1, 'two/c': 2 }, missedAt: { 'two/d': 400, 'two/c': 200 }, solvedAt: { 'one/a': 100, 'one/b': 50, 'two/c': 300 } }
    // two/d missed, never solved → first. two/c was missed but solved after → not "missed". Oldest solve: one/b (50)
    expect(ids(pickWarmup(data, progress, stats))).toEqual(['two/d', 'one/b'])
  })
  it('a miss after the last solve counts as missed again; a shown answer is not a solve', () => {
    const progress = { 'one/a': { at: 100 }, 'one/b': { at: 120, shown: true } }
    const stats = { misses: { 'one/a': 1, 'one/b': 1 }, missedAt: { 'one/a': 500, 'one/b': 110 }, solvedAt: { 'one/a': 100 } }
    expect(ids(pickWarmup(data, progress, stats))).toEqual(['one/b', 'one/a'])
  })
  it('old data without timestamps: solve time comes from progress', () => {
    const progress = { 'two/c': { at: 900 }, 'one/a': { at: 10 } }
    expect(ids(pickWarmup(data, progress, { misses: {} }, 3))).toEqual(['one/a', 'two/c', 'two/d'])
  })
  it('never repeats and respects n', () => {
    expect(pickWarmup(data, {}, { misses: {} }, 1)).toHaveLength(1)
    expect(pickWarmup({ levels: [], items: [] }, {}, { misses: {} })).toEqual([])
  })
})

describe('warm-up skips untouched side branches', () => {
  it('never-tried questions come only from the last two main-line levels', () => {
    const data = {
      levels: [
        { slug: 'backprop', level: '6', title: 'B', main: true },
        { slug: 'data-pipeline', level: 'U4', title: 'D', main: false },
        { slug: 'debugging', level: 'U5', title: 'G', main: false },
      ],
      items: [
        { id: 'a', page: 'data-pipeline', type: 'number' as const, prompt: '', answer: 1 },
        { id: 'b', page: 'debugging', type: 'number' as const, prompt: '', answer: 1 },
        { id: 'c', page: 'backprop', type: 'number' as const, prompt: '', answer: 1 },
      ],
    }
    const out = pickWarmup(data, {}, { misses: {} }, 2)
    expect(out.map((x) => x.page)).toEqual(['backprop'])
  })
})

describe('warm-up eligibility', async () => {
  const { warmEligible, pointsAtPage } = await import('./warmup')
  it('keeps plain questions, drops local runs and opted-out ones', () => {
    expect(warmEligible({ type: 'number', prompt: 'What is 2 × 3?', answer: 6 })).toBe(true)
    expect(warmEligible({ type: 'number', prompt: 'Run first_run.py on your computer. What loss?', answer: 0.4 })).toBe(false)
    expect(warmEligible({ type: 'number', prompt: 'What does it print?', answer: 1, run: 'local' })).toBe(false)
    expect(warmEligible({ type: 'number', prompt: 'Back to the stroke', answer: 1, warmup: false })).toBe(false)
    expect(warmEligible({ type: 'code', prompt: 'x', template: '', tests: [] })).toBe(false)
  })
  it('drops after-notes that point at the page', () => {
    expect(pointsAtPage('Check the table in the lab.')).toBe(true)
    expect(pointsAtPage('Each row adds up to 1.')).toBe(false)
  })
})
