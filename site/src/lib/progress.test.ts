import { beforeEach, describe, expect, it, vi } from 'vitest'

describe('progress is per page', () => {
  beforeEach(() => {
    const store: Record<string, string> = {}
    vi.stubGlobal('localStorage', {
      getItem: (k: string) => store[k] ?? null,
      setItem: (k: string, v: string) => { store[k] = v },
      removeItem: (k: string) => { delete store[k] },
    })
    vi.stubGlobal('window', { dispatchEvent: () => true, addEventListener: () => {}, removeEventListener: () => {} })
    vi.stubGlobal('CustomEvent', class { constructor(public type: string, public init?: unknown) {} })
  })
  it('the same id on two pages is two different exercises', async () => {
    const p = await import('./progress')
    vi.stubGlobal('location', { pathname: '/learn/matrices/' })
    p.pass('batch-shape')
    expect(p.hasReal('batch-shape')).toBe(true)
    vi.stubGlobal('location', { pathname: '/learn/write-a-gpt/' })
    expect(p.hasReal('batch-shape')).toBe(false)
    expect(p.hasReal('matrices/batch-shape')).toBe(true)
  })
})

describe('misses, skips and stars', () => {
  beforeEach(() => {
    const store: Record<string, string> = {}
    vi.stubGlobal('localStorage', {
      getItem: (k: string) => store[k] ?? null,
      setItem: (k: string, v: string) => { store[k] = v },
      removeItem: (k: string) => { delete store[k] },
    })
    vi.stubGlobal('window', { dispatchEvent: () => true, addEventListener: () => {}, removeEventListener: () => {} })
    vi.stubGlobal('CustomEvent', class { constructor(public type: string, public init?: unknown) {} })
    vi.stubGlobal('location', { pathname: '/learn/matrices/' })
  })

  it('counts wrong attempts per page and lists them', async () => {
    const p = await import('./progress')
    p.recordMiss('c-0-1')
    p.recordMiss('c-0-1')
    p.recordMiss('write-a-gpt/seq-len')
    expect(p.missCount('c-0-1')).toBe(2)
    expect(p.missCount('matrices/c-0-1')).toBe(2)
    expect(p.allMisses()).toEqual({ 'matrices/c-0-1': 2, 'write-a-gpt/seq-len': 1 })
  })

  it('gives 3, 2 or 1 stars', async () => {
    const p = await import('./progress')
    const ids = ['a', 'b', 'c']
    expect(p.levelScore('matrices', ids, 'c').stars).toBe(0)
    p.pass('a'); p.pass('b'); p.pass('c')
    expect(p.levelScore('matrices', ids, 'c')).toMatchObject({ solved: 3, shown: 0, stars: 3, cleared: true })
    p.reset()
    p.pass('a'); p.pass('b', { shown: true }); p.pass('c')
    expect(p.levelScore('matrices', ids, 'c')).toMatchObject({ solved: 2, shown: 1, stars: 2 })
    p.reset()
    p.recordSkip('a'); p.pass('c')
    expect(p.levelScore('matrices', ids, 'c')).toMatchObject({ solved: 1, skipped: 1, stars: 1 })
    p.pass('a')
    expect(p.levelScore('matrices', ids, 'c').skipped).toBe(0)
  })

  it('needs every mustSolve boss part solved before the checkpoint clears the level', async () => {
    const p = await import('./progress')
    p.reset()
    p.recordSkip('b'); p.pass('c')
    expect(p.levelScore('matrices', ['a', 'b', 'c'], 'c', ['b']).cleared).toBe(false)
    p.pass('b')
    expect(p.levelScore('matrices', ['a', 'b', 'c'], 'c', ['b']).cleared).toBe(true)
  })

  it('says which mustSolve part is missing, and the end card names its section', async () => {
    const p = await import('./progress')
    const { endCardText } = await import('./marks')
    p.reset()
    p.pass('a'); p.pass('c')
    const sc = p.levelScore('matrices', ['a', 'b', 'c'], 'c', ['b'])
    expect(sc).toMatchObject({ cleared: false, checkpointDone: true, missing: ['b'], stars: 0 })
    expect(endCardText(sc, { b: 'Step 2: the forward shape' }).note).toContain('“Step 2: the forward shape”')
    expect(endCardText(sc).note).toContain('b')
  })

  it('optional questions never cost a star', async () => {
    const p = await import('./progress')
    const { endCardText } = await import('./marks')
    p.reset()
    const ids = ['a', 'gauss', 'c']
    p.pass('a'); p.pass('c')
    const sc = p.levelScore('matrices', ids, 'c', [], ['gauss'])
    expect(sc).toMatchObject({ total: 2, solved: 2, unsolved: [], optionalTotal: 1, optionalSolved: 0, stars: 3 })
    expect(endCardText(sc).nums).toBe('Solved yourself: 2 · With the answer shown: 0 · Optional: 0 of 1')
    expect(endCardText(sc).note).toBe('Every required question solved on your own')
    // without the flag the same progress is one star, and the card says what is unsolved (no "Skipped parts: 0")
    const one = p.levelScore('matrices', ids, 'c')
    expect(one).toMatchObject({ stars: 1, unsolved: ['gauss'] })
    expect(endCardText(one).note).toBe('Cleared, with 1 question still unsolved')
    expect(endCardText(one).nums).not.toContain('Skipped')
    // the checkpoint is never optional
    expect(p.levelScore('matrices', ids, 'c', [], ['c']).total).toBe(3)
  })

  it('export and import carry the stats without breaking the old shape', async () => {
    const p = await import('./progress')
    p.pass('a')
    p.recordMiss('a')
    const dump = p.exportAll()
    p.reset()
    expect(p.hasReal('a')).toBe(false)
    p.importAll(dump)
    expect(p.hasReal('a')).toBe(true)
    expect(p.missCount('a')).toBe(1)
    expect(p.hasReal('~stats')).toBe(false)
  })
})

describe('reading mode and test-outs', () => {
  let store: Record<string, string>
  beforeEach(() => {
    store = {}
    vi.stubGlobal('localStorage', {
      getItem: (k: string) => store[k] ?? null,
      setItem: (k: string, v: string) => { store[k] = v },
      removeItem: (k: string) => { delete store[k] },
    })
    vi.stubGlobal('window', { dispatchEvent: () => true, addEventListener: () => {}, removeEventListener: () => {} })
    vi.stubGlobal('CustomEvent', class { constructor(public type: string, public init?: unknown) {} })
    vi.stubGlobal('location', { pathname: '/learn/matrices/' })
  })
  const reading = (on: boolean) => { store['llmbh-settings'] = JSON.stringify({ reading: on }) }

  it('reading mode opens everything and records nothing', async () => {
    const p = await import('./progress')
    expect(p.has('c-0-1')).toBe(false)
    reading(true)
    expect(p.has('c-0-1')).toBe(true)
    expect(p.has('write-a-gpt/seq-len')).toBe(true)
    p.pass('c-0-1'); p.recordMiss('shape-3x4'); p.recordSkip('c-0-1'); p.recordTestOut('matrices')
    expect(p.hasReal('c-0-1')).toBe(false)
    expect(p.missCount('shape-3x4')).toBe(0)
    expect(p.testedOut('matrices')).toBe(false)
    reading(false)
    expect(p.has('c-0-1')).toBe(false)
  })

  it('a test-out clears the level with three stars and opens its gates only', async () => {
    const p = await import('./progress')
    p.pass('a')
    expect(p.levelScore('matrices', ['a', 'b', 'c'], 'c')).toMatchObject({ cleared: false, stars: 0, testedOut: false })
    p.recordTestOut('matrices')
    expect(p.levelScore('matrices', ['a', 'b', 'c'], 'c')).toMatchObject({ cleared: true, stars: 3, testedOut: true })
    expect(p.has('b')).toBe(true) // a gate on this page
    expect(p.hasReal('b')).toBe(false) // but b is not marked solved
    expect(p.has('write-a-gpt/b')).toBe(false) // other levels stay locked
    const dump = p.exportAll()
    p.reset()
    expect(p.testedOut('matrices')).toBe(false)
    p.importAll(dump)
    expect(p.testedOut('matrices')).toBe(true)
  })

  it('stamps solve and miss times, additively', async () => {
    const p = await import('./progress')
    store['llmbh-stats-v1'] = JSON.stringify({ misses: { 'matrices/x': 2 }, skips: {} }) // old data
    p.recordMiss('a')
    p.pass('a')
    const { stats } = p.snapshot()
    expect(stats.misses).toEqual({ 'matrices/x': 2, 'matrices/a': 1 })
    expect(stats.missedAt['matrices/a']).toBeGreaterThan(0)
    expect(stats.solvedAt['matrices/a']).toBeGreaterThanOrEqual(stats.missedAt['matrices/a'])
    p.pass('b', { shown: true })
    expect(p.snapshot().stats.solvedAt['matrices/b']).toBeUndefined()
  })
})
