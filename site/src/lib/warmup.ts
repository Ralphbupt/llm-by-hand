/**
 * Warm-up (spaced retrieval): two short questions from earlier levels at the top of a level.
 * The page embeds the eligible questions of every earlier level at build time (number, shape, graded predict);
 * the browser picks two with pickWarmup(). Pure: no DOM, no storage.
 */
import type { Exercise, Hint } from './quiz'

export type WarmItem = {
  id: string
  page: string // level slug the question belongs to
  type: 'number' | 'shape' | 'predict'
  prompt: string
  answer: number | number[]
  tol?: number
  unit?: string
  options?: string[]
  reveal?: string // predict only: shown after the right pick
  hints?: Hint[]
  after?: string
}

export type WarmData = {
  levels: { slug: string; level: string; title: string; main?: boolean }[] // earlier levels, in course order; main = not a side branch
  items: WarmItem[]
}

type ProgressLike = Record<string, { at: number; shown?: boolean }>
type StatsLike = { misses: Record<string, number>; solvedAt?: Record<string, number>; missedAt?: Record<string, number> }

/**
 * A question that can't be answered away from its page and lab, or needs the learner's own computer:
 * `warmup: false` in exercises.yaml, `run: local`, or a prompt that asks to run something locally.
 */
export function warmEligible(ex: Exercise): boolean {
  if (ex.type === 'code' || (ex.type === 'predict' && ex.answer === undefined)) return false
  if (ex.warmup === false || ex.run === 'local') return false
  return !/\bon your computer\b|^\s*run\b|\b[\w-]+\.py\b|\bPASS line\b/i.test(ex.prompt)
}

/** An `after` note that points at the page itself ("in the lab", "above") makes no sense in a warm-up. */
export const pointsAtPage = (s: string) => /\b(the lab|this lab|above|below|this page|step back)\b/i.test(s)

export const warmKey = (it: Pick<WarmItem, 'page' | 'id'>) => `${it.page}/${it.id}`

/**
 * Pick up to `n` questions, in this order of priority:
 *  1. missed and not solved since (the oldest miss first)
 *  2. solved on your own, the longest ago first
 *  3. never tried, from the previous two MAIN-line levels (side branches are optional, so an
 *     untouched branch question never shows up here; branch questions only come back via 1 and 2)
 */
export function pickWarmup(data: WarmData, progress: ProgressLike, stats: StatsLike, n = 2): WarmItem[] {
  const solvedAt = stats.solvedAt ?? {}
  const missedAt = stats.missedAt ?? {}
  const lastSolve = (k: string): number | undefined => {
    if (solvedAt[k] !== undefined) return solvedAt[k]
    const e = progress[k]
    return e && !e.shown ? e.at : undefined
  }
  const missedOpen = (k: string) => {
    if (!((stats.misses[k] ?? 0) > 0)) return false
    const s = lastSolve(k)
    return s === undefined || (missedAt[k] ?? 0) > s
  }

  const items = data.items.map((it, i) => ({ it, i, k: warmKey(it) }))
  const byAge = (t: (k: string) => number) => (a: { k: string; i: number }, b: { k: string; i: number }) => t(a.k) - t(b.k) || a.i - b.i

  const p1 = items.filter((x) => missedOpen(x.k)).sort(byAge((k) => missedAt[k] ?? 0))
  const p2 = items.filter((x) => !missedOpen(x.k) && lastSolve(x.k) !== undefined).sort(byAge((k) => lastSolve(k)!))
  const mains = data.levels.filter((l) => l.main !== false)
  const recent = new Set(mains.slice(-2).map((l) => l.slug))
  const p3 = items.filter((x) => recent.has(x.it.page) && !(x.k in progress) && !((stats.misses[x.k] ?? 0) > 0))

  const out: WarmItem[] = []
  const seen = new Set<string>()
  for (const x of [...p1, ...p2, ...p3]) {
    if (out.length >= n) break
    if (seen.has(x.k)) continue
    seen.add(x.k)
    out.push(x.it)
  }
  return out
}
