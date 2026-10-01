/**
 * Progress lives in the browser's localStorage; there are no accounts.
 * Islands talk through a CustomEvent: a Blank is solved → broadcast → the Gate on the same page opens.
 *
 * Debug mode (local dev server only): everything counts as solved, so every Gate opens and every
 * masked lab value shows, and the quiz components print their answers. The real progress is untouched.
 */
import { readingMode, setSettings } from './settings'
import { pageCheckpoint, track } from './analytics'

const KEY = 'llmbh-progress-v2'
const EVENT = 'quiz:progress'

type Entry = { at: number; shown?: boolean }
type State = Record<string, Entry>

function read(): State {
  if (typeof localStorage === 'undefined') return {}
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? '{}') as State
  } catch {
    return {}
  }
}

function write(s: State) {
  try {
    localStorage.setItem(KEY, JSON.stringify(s))
  } catch {
    /* private mode can't write; ignore */
  }
}

/**
 * Two local debug switches (dev server only):
 *   open    — every Gate opens and every masked lab value shows (all hidden content visible)
 *   answers — each exercise prints its answer
 */
export type DebugFlag = 'open' | 'answers'
const debugKey = (f: DebugFlag) => `llmbh-debug-${f}`

export function debugOn(f: DebugFlag = 'open'): boolean {
  if (!import.meta.env.DEV || typeof localStorage === 'undefined') return false
  try {
    return localStorage.getItem(debugKey(f)) === '1'
  } catch {
    return false
  }
}

export function setDebug(f: DebugFlag, on: boolean) {
  try {
    if (on) localStorage.setItem(debugKey(f), '1')
    else localStorage.removeItem(debugKey(f))
  } catch {
    /* ignore */
  }
  window.dispatchEvent(new CustomEvent(EVENT, { detail: { id: null } }))
}

/** Has the learner really solved this? (Ignores debug mode; used by the quiz components themselves.) */
/**
 * Exercise ids are only unique within a page, so progress is stored as "<page slug>/<id>".
 * A plain id is qualified with the current page; an id that already contains "/" is used as is
 * (the map and the sidebar ask about other pages' checkpoints that way).
 */
export function qualify(id: string): string {
  if (id.includes('/')) return id
  const slug = typeof location === 'undefined' ? '' : location.pathname.replace(/^\/+|\/+$/g, '').split('/').pop() ?? ''
  return `${slug}/${id}`
}

export function hasReal(id: string): boolean {
  return qualify(id) in read()
}

/** The page slug of an id ("matrices/c-0-1" → "matrices"; a plain id → the current page). */
const pageOf = (id: string) => qualify(id).split('/')[0]

/**
 * Is this unlocked? Used by Gates and labs. Everything is unlocked in debug "open" mode, in reading mode,
 * and on a level the learner tested out of.
 */
export function has(id: string): boolean {
  return debugOn('open') || readingMode() || hasReal(id) || testedOut(pageOf(id))
}

export { readingMode }

/** Turn reading mode on or off (a setting), and tell every Gate and lab to look again. */
export function setReadingMode(on: boolean) {
  setSettings({ reading: on })
  window.dispatchEvent(new CustomEvent(EVENT, { detail: { id: null } }))
}

/**
 * Mark solved. `shown` = the learner looked at the answer instead of solving it (it still unlocks what follows).
 * Reading mode records nothing. A real solve also stamps stats.solvedAt (every time, for the warm-up).
 */
export function pass(id: string, opts: { shown?: boolean } = {}) {
  if (readingMode()) return
  const s = read()
  const key = qualify(id)
  if (!opts.shown) {
    const st = readStats()
    st.solvedAt[key] = Date.now()
    writeStats(st)
  }
  if (key in s) return
  s[key] = opts.shown ? { at: Date.now(), shown: true } : { at: Date.now() }
  write(s)
  if (opts.shown) track('answer_reveal', { exercise_id: id })
  else if (key === pageCheckpoint()) track('checkpoint_pass', { exercise_id: id })
  window.dispatchEvent(new CustomEvent(EVENT, { detail: { id } }))
}

export function reset(prefix?: string) {
  const s = read()
  for (const k of Object.keys(s)) if (!prefix || k.startsWith(prefix)) delete s[k]
  write(s)
  const st = readStats()
  for (const bag of [st.misses, st.skips, st.solvedAt, st.missedAt]) for (const k of Object.keys(bag)) if (!prefix || k.startsWith(prefix)) delete bag[k]
  for (const k of Object.keys(st.testOuts)) if (!prefix || `${k}/`.startsWith(prefix) || k.startsWith(prefix)) delete st.testOuts[k]
  writeStats(st)
  window.dispatchEvent(new CustomEvent(EVENT, { detail: { id: null } }))
}

/** Subscribe to any progress change; returns the unsubscribe function. */
export function subscribe(fn: () => void): () => void {
  if (typeof window === 'undefined') return () => {}
  const h = () => fn()
  window.addEventListener(EVENT, h)
  window.addEventListener('storage', h) // stay in sync with other tabs
  return () => {
    window.removeEventListener(EVENT, h)
    window.removeEventListener('storage', h)
  }
}

// export keeps the old shape (one key per solved exercise) and carries the stats under one reserved key
const STATS_IN_EXPORT = '~stats'
export const exportAll = () => JSON.stringify({ ...read(), [STATS_IN_EXPORT]: readStats() })
export function importAll(json: string) {
  const parsed = JSON.parse(json) as State & { [STATS_IN_EXPORT]?: Stats }
  const stats = parsed[STATS_IN_EXPORT]
  delete parsed[STATS_IN_EXPORT]
  write({ ...read(), ...parsed })
  if (stats) {
    const st = readStats()
    for (const [k, v] of Object.entries(stats.misses ?? {})) st.misses[k] = Math.max(st.misses[k] ?? 0, v)
    for (const [k, v] of Object.entries(stats.skips ?? {})) st.skips[k] = Math.max(st.skips[k] ?? 0, v)
    for (const bag of ['testOuts', 'solvedAt', 'missedAt'] as const)
      for (const [k, v] of Object.entries(stats[bag] ?? {})) st[bag][k] = Math.max(st[bag][k] ?? 0, v)
    writeStats(st)
  }
  window.dispatchEvent(new CustomEvent(EVENT, { detail: { id: null } }))
}

/** Did the learner look at the answer for this one? */
export function wasShown(id: string): boolean {
  return !!read()[qualify(id)]?.shown
}

// "Show answer" asks for confirmation unless the learner ticked "Don't ask me again".
const NOASK = 'llmbh-reveal-noask'
export function revealNeedsConfirm(): boolean {
  try {
    return localStorage.getItem(NOASK) !== '1'
  } catch {
    return true
  }
}
export function setRevealNeedsConfirm(ask: boolean) {
  try {
    if (ask) localStorage.removeItem(NOASK)
    else localStorage.setItem(NOASK, '1')
  } catch {
    /* ignore */
  }
}

/* ---------------------------------------------------------------------------------------------
 * Stats: wrong attempts per exercise and skipped parts per gate. Stored next to the progress
 * (not inside it, so "id in progress" keeps meaning "solved").
 * ------------------------------------------------------------------------------------------- */
const STATS_KEY = 'llmbh-stats-v1'
/**
 * misses: qualified id → wrong attempts · skips: "<slug>/gate:<id>" → "Skip for now" presses.
 * Added later (absent in old data, so every reader defaults them):
 * testOuts: level slug → when it was tested out · solvedAt / missedAt: qualified id → last real solve / last miss (ms).
 */
export type Stats = {
  misses: Record<string, number>
  skips: Record<string, number>
  testOuts: Record<string, number>
  solvedAt: Record<string, number>
  missedAt: Record<string, number>
}
const emptyStats = (): Stats => ({ misses: {}, skips: {}, testOuts: {}, solvedAt: {}, missedAt: {} })

function readStats(): Stats {
  if (typeof localStorage === 'undefined') return emptyStats()
  try {
    const v = JSON.parse(localStorage.getItem(STATS_KEY) ?? '{}')
    return { misses: v.misses ?? {}, skips: v.skips ?? {}, testOuts: v.testOuts ?? {}, solvedAt: v.solvedAt ?? {}, missedAt: v.missedAt ?? {} }
  } catch {
    return emptyStats()
  }
}
function writeStats(s: Stats) {
  try {
    localStorage.setItem(STATS_KEY, JSON.stringify(s))
  } catch {
    /* ignore */
  }
}

/** One wrong attempt at an exercise. */
export function recordMiss(id: string) {
  if (readingMode()) return
  const s = readStats()
  const k = qualify(id)
  s.misses[k] = (s.misses[k] ?? 0) + 1
  s.missedAt[k] = Date.now()
  writeStats(s)
  // a wrong try shows the next rung of the hint ladder (rung 1 = first hint)
  track('hint_open', { exercise_id: id, rung: s.misses[k] })
  window.dispatchEvent(new CustomEvent(EVENT, { detail: { id } }))
}

/** The learner pressed "Skip for now" on the gate that waits for exercise `requires`. */
export function recordSkip(requires: string) {
  if (readingMode()) return
  const s = readStats()
  const k = qualify(`gate:${requires}`)
  s.skips[k] = (s.skips[k] ?? 0) + 1
  writeStats(s)
  window.dispatchEvent(new CustomEvent(EVENT, { detail: { id: null } }))
}

/** Did the learner test out of this level (solve its test-out questions on their own)? */
export function testedOut(slug: string): boolean {
  return slug in readStats().testOuts
}

/** The level `slug` was tested out of: it counts as cleared with three stars, and every Gate on it opens. */
export function recordTestOut(slug: string) {
  if (readingMode()) return
  const s = readStats()
  if (slug in s.testOuts) return
  s.testOuts[slug] = Date.now()
  writeStats(s)
  track('test_out_pass')
  window.dispatchEvent(new CustomEvent(EVENT, { detail: { id: null } }))
}

/** A read-only copy of everything stored, for pure helpers (the warm-up picker, the test-out check). */
export function snapshot(): { progress: State; stats: Stats } {
  return { progress: read(), stats: readStats() }
}
export type Progress = State

export function missCount(id: string): number {
  return readStats().misses[qualify(id)] ?? 0
}

/** Every exercise with at least one wrong attempt: qualified id → misses. */
export function allMisses(): Record<string, number> {
  return Object.fromEntries(Object.entries(readStats().misses).filter(([, n]) => n > 0))
}

export type LevelScore = {
  total: number // questions that count toward the stars (optional ones left out)
  solved: number // of those, solved on their own
  shown: number // of those, solved after "Show answer"
  unsolved: string[] // of those, the ids not solved yet
  skipped: number // parts skipped whose question is still unsolved
  optionalTotal: number
  optionalSolved: number
  checkpointDone: boolean // the clearing exercise is solved (the level may still wait for a mustSolve part)
  missing: string[] // mustSolve parts not solved yet (the level is not cleared until they are)
  cleared: boolean
  testedOut: boolean // cleared by testing out (counts as solved on your own: three stars)
  stars: 0 | 1 | 2 | 3
}

/**
 * Score for one level. `ids` are the page's exercise ids (plain), `checkpoint` the clearing exercise,
 * `mustSolve` the boss parts that must be solved too (a skipped Gate can't stand in for them),
 * `optional` the ids that never cost a star (an optional section, a Stuck or Deeper box).
 * ★★★ every non-optional exercise solved without help · ★★ all solved, some answers shown · ★ cleared, but some unsolved.
 * A level the learner tested out of is cleared with ★★★.
 */
export function levelScore(slug: string, ids: string[], checkpoint: string, mustSolve: string[] = [], optional: string[] = []): LevelScore {
  const p = read()
  const st = readStats()
  const opt = new Set(optional)
  const done = (id: string) => `${slug}/${id}` in p
  let solved = 0, shown = 0, optionalTotal = 0, optionalSolved = 0
  const unsolved: string[] = []
  for (const id of ids) {
    const e = p[`${slug}/${id}`]
    if (opt.has(id) && id !== checkpoint && !mustSolve.includes(id)) {
      optionalTotal++
      if (e) optionalSolved++
      continue
    }
    if (!e) unsolved.push(id)
    else if (e.shown) shown++
    else solved++
  }
  const skipped = Object.keys(st.skips).filter((k) => k.startsWith(`${slug}/gate:`) && !(`${slug}/${k.slice(slug.length + 6)}` in p)).length
  const testedOut = slug in st.testOuts
  const checkpointDone = done(checkpoint)
  const missing = mustSolve.filter((id) => !done(id))
  const cleared = (checkpointDone && missing.length === 0) || testedOut
  const total = solved + shown + unsolved.length
  const stars = testedOut ? 3 : !cleared ? 0 : unsolved.length === 0 && shown === 0 ? 3 : unsolved.length === 0 ? 2 : 1
  return { total, solved, shown, unsolved, skipped, optionalTotal, optionalSolved, checkpointDone, missing, cleared, testedOut, stars }
}
