import fs from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { AFTER_COURSE, cameFromOutsideLevels, neighbors, OPENS_AFTER, placement, readTrip, stepTrip, tripsAfter, type NavItem } from './nav'

const L = (id: string, order: number, branch?: string): NavItem => ({ id, level: id, title: id, order, branch })
// a small fake course with its own table
const all = [L('one', 1), L('two', 2), L('three', 3), L('four', 4), L('ua', 2.1, 'internals'), L('ub', 2.2, 'internals')]
const T = { ua: 'one', ub: 'three' }

describe('path', () => {
  it('main levels walk the main line only', () => {
    const n = neighbors(all, 'two', T)
    expect(n.prev?.id).toBe('one')
    expect(n.next?.id).toBe('three')
  })
  it('a branch walks itself; its ends lead back to the main line', () => {
    const a = neighbors(all, 'ua', T)
    expect(a.prev?.id).toBe('one')
    expect(a.prevIsBack).toBe(true)
    expect(a.next?.id).toBe('ub')
    expect(a.nextOpensAfter?.id).toBe('three')
    const b = neighbors(all, 'ub', T)
    // ub opens after a different main level than ua, so its Prev leads back to that level, not to ua
    expect(b.prev?.id).toBe('three')
    expect(b.prevIsBack).toBe(true)
    // ... and names ua, so the browser can make Prev the reverse of Next when the learner walked ua → ub
    expect(b.branchPrev?.id).toBe('ua')
    // the first side-trip level has no side-trip level before it
    expect(a.branchPrev).toBeUndefined()
    // the last one continues the main line after the level it opens after, so Prev and Next differ
    expect(b.next?.id).toBe('four')
    expect(b.nextIsContinue).toBe(true)
    const solo = neighbors([L('one', 1), L('two', 2), L('u', 1.1, 'x')], 'u', { u: 'one' })
    expect(solo.prev?.id).toBe('one')
    expect(solo.next?.id).toBe('two')
  })
  it('a side-trip level that opens after the same main level as the one before walks back to it', () => {
    const t = { ua: 'one', ub: 'one' }
    expect(neighbors(all, 'ub', t).prev?.id).toBe('ua')
    expect(neighbors(all, 'ub', t).prevIsBack).toBeUndefined()
    expect(neighbors(all, 'ub', t).branchPrev).toBeUndefined()
  })
  it('a recommended side trip is listed first', () => {
    const t = { ua: 'one', ub: 'one' }
    expect(tripsAfter(all, 'one', t, { ub: 'note' }).map((l) => l.id)).toEqual(['ub', 'ua'])
  })
  it('side trips sit under the level they open after', () => {
    expect(tripsAfter(all, 'one', T).map((l) => l.id)).toEqual(['ua'])
    expect(placement(all, T).map((p) => [p.main.id, p.trips.flatMap((t) => t.levels.map((l) => l.id))])).toEqual([
      ['one', ['ua']], ['two', []], ['three', ['ub']], ['four', []],
    ])
  })
})

describe('the trip (one per tab)', () => {
  // simulate two tabs: each has its own sessionStorage; localStorage (the last main level) is shared
  const tab = () => ({ trip: null as string | null })
  let lastMain: string | null = null
  const visit = (t: { trip: string | null }, id: string, branch: boolean, home?: string, fresh = false) => {
    const next = stepTrip(t.trip, id, branch, lastMain, home, fresh)
    t.trip = next && JSON.stringify(next)
    if (!branch) lastMain = id
    return next
  }
  it('a main level ends the trip; a side trip remembers where it started', () => {
    lastMain = null
    const a = tab()
    visit(a, 'backprop', false)
    expect(visit(a, 'numbers-in-a-computer', true, 'neurons-and-loss')).toEqual({ from: 'backprop', levels: ['numbers-in-a-computer'] })
    expect(visit(a, 'autograd', true, 'backprop')).toEqual({ from: 'backprop', levels: ['numbers-in-a-computer', 'autograd'] })
    // reloading a level does not add it twice
    expect(visit(a, 'autograd', true, 'backprop')?.levels).toEqual(['numbers-in-a-computer', 'autograd'])
    expect(visit(a, 'backprop', false)).toBeNull()
  })
  it('a main level opened in another tab does not change where this trip leads back (B10-1)', () => {
    lastMain = null
    const a = tab(), b = tab()
    visit(a, 'backprop', false)
    visit(a, 'tensors-in-memory', true, 'matrices')
    visit(a, 'numbers-in-a-computer', true, 'neurons-and-loss')
    visit(b, 'generation', false)
    expect(lastMain).toBe('generation')
    expect(visit(a, 'autograd', true, 'backprop')?.from).toBe('backprop')
    // a new tab that opens a side trip directly starts its own trip at the last main level
    expect(visit(tab(), 'autograd', true, 'backprop')).toEqual({ from: 'generation', levels: ['autograd'] })
  })
  it('without any main level visited, the trip starts at the level it opens after', () => {
    lastMain = null
    expect(visit(tab(), 'attention-backward', true, 'full-model')?.from).toBe('full-model')
  })
  it('arriving from a page outside the levels starts a new trip (B10-3)', () => {
    lastMain = null
    const a = tab()
    visit(a, 'full-model', false)
    visit(a, 'debugging', true, 'numpy-to-pytorch')
    expect(visit(a, 'attention-backward', true, 'full-model', true)).toEqual({ from: 'full-model', levels: ['attention-backward'] })
    const o = 'http://localhost:4322'
    expect(cameFromOutsideLevels(`${o}/glossary/`, o)).toBe(true)
    expect(cameFromOutsideLevels(`${o}/`, o)).toBe(true)
    expect(cameFromOutsideLevels(`${o}/review/`, o)).toBe(true)
    expect(cameFromOutsideLevels(`${o}/learn/debugging/`, o)).toBe(false)
    expect(cameFromOutsideLevels(`${o}/learn/debugging/#s2`, o)).toBe(false)
    expect(cameFromOutsideLevels('', o)).toBe(false)
    expect(cameFromOutsideLevels('https://example.com/', o)).toBe(false)
  })
  it('reads the older stored form and ignores junk', () => {
    expect(readTrip('["autograd"]')).toEqual({ levels: ['autograd'] })
    expect(readTrip('{"from":"backprop","levels":["autograd"]}')).toEqual({ from: 'backprop', levels: ['autograd'] })
    expect(readTrip('not json')).toEqual({ levels: [] })
    expect(readTrip(null)).toEqual({ levels: [] })
    expect(readTrip('{"levels":3}')).toEqual({ levels: [] })
  })
})

describe('the real course', () => {
  // read every lesson's frontmatter: slug, branch, order
  const root = path.join(process.cwd(), '..', 'content')
  const levels: NavItem[] = []
  for (const part of fs.readdirSync(root)) {
    const dir = path.join(root, part)
    if (!fs.statSync(dir).isDirectory()) continue
    for (const slug of fs.readdirSync(dir)) {
      const f = path.join(dir, slug, 'lesson.en.mdx')
      if (!fs.existsSync(f)) continue
      const fm = fs.readFileSync(f, 'utf8').split('---')[1] ?? ''
      const get = (k: string) => fm.match(new RegExp(`^${k}:\\s*(.+)$`, 'm'))?.[1].trim()
      levels.push({ id: slug, level: get('level') ?? '', title: slug, order: Number(get('order')), branch: get('branch') })
    }
  }
  it('U3 can lead back to U2; U6 leads back to level 17 unless the learner came through U5', () => {
    const u3 = neighbors(levels, 'autograd')
    expect(u3.prevIsBack).toBe(true)
    expect(u3.branchPrev?.id).toBe('numbers-in-a-computer')
    const u6 = neighbors(levels, 'attention-backward')
    expect(u6.prev?.id).toBe('full-model')
    expect(u6.branchPrev?.id).toBe('debugging')
  })
  it('the side trips offered after the last main level exist and are side trips', () => {
    for (const id of AFTER_COURSE) expect(levels.find((l) => l.id === id)?.branch, id).toBeDefined()
  })
  it('every side-trip level opens after a main level', () => {
    const mains = new Map(levels.filter((l) => !l.branch).map((l) => [l.id, l]))
    for (const l of levels.filter((x) => x.branch)) {
      const m = mains.get(OPENS_AFTER[l.id])
      expect(m, `OPENS_AFTER["${l.id}"]`).toBeDefined()
    }
  })
})
