/**
 * Browser side of level scoring: reads the build-time level index embedded in the page
 * (<script type="application/json" id="level-index">) and marks levels with stars.
 */
import { allMisses, levelScore, type LevelScore } from './progress'
import type { LevelIndex } from './score'

let cached: LevelIndex | null = null
export function readLevelIndex(): LevelIndex {
  if (cached) return cached
  try {
    cached = JSON.parse(document.getElementById('level-index')?.textContent ?? '{}') as LevelIndex
  } catch {
    cached = {}
  }
  return cached
}

export function scoreOf(slug: string): LevelScore | null {
  const e = readLevelIndex()[slug]
  return e ? levelScore(slug, e.ids, e.checkpoint, e.mustSolve, e.optional) : null
}

export const starText = (n: number) => '★'.repeat(n) + '☆'.repeat(3 - n)

export const STAR_NOTE = {
  3: 'Every question solved on your own',
  2: 'All solved, some with the answer shown',
  1: 'Cleared, with some questions unsolved',
} as const

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`

/**
 * The end card's two lines for a level: `note` (what the stars mean here, or what is still missing) and `nums`.
 * `mustWhere` names the section of each mustSolve part (from the level index). HTML-free plain text.
 */
export function endCardText(sc: LevelScore, mustWhere: Record<string, string> = {}): { note: string; nums: string } {
  const opt = sc.optionalTotal ? ` · Optional: ${sc.optionalSolved} of ${sc.optionalTotal}` : ''
  const skip = sc.skipped ? ` · Skipped parts: ${sc.skipped}` : ''
  if (!sc.cleared && sc.missing.length) {
    const where = [...new Set(sc.missing.map((id) => (mustWhere[id] ? `“${mustWhere[id]}”` : id)))]
    const parts = `${sc.missing.length === 1 ? 'the boss part' : `the ${sc.missing.length} boss parts`} in ${where.join(' and ')}`
    return { note: `Not cleared yet: solve ${parts} too. Skip for now can't pass ${sc.missing.length === 1 ? 'it' : 'them'}.`, nums: `Solved yourself: ${sc.solved} · With the answer shown: ${sc.shown}${skip}` }
  }
  let note: string
  if (sc.testedOut) note = 'Skipped with the short test: you solved its questions on your own'
  else if (sc.stars === 1) note = `Cleared, with ${plural(sc.unsolved.length, 'question', 'questions')} still unsolved`
  // optional questions left: "every question" would not be true
  else if (sc.stars === 3 && sc.optionalSolved < sc.optionalTotal) note = 'Every required question solved on your own'
  else note = STAR_NOTE[(sc.stars || 1) as 1 | 2 | 3]
  const unsolved = sc.unsolved.length ? ` · Unsolved: ${sc.unsolved.length}` : ''
  return { note, nums: `Solved yourself: ${sc.solved} · With the answer shown: ${sc.shown}${unsolved}${skip}${opt}` }
}

/**
 * Mark every element with data-level="<slug>": class "done" when cleared,
 * data-stars ("★★☆") and data-grade ("3" own, "2" with answers, "1" with skips) for styling.
 */
export function markLevels(root: ParentNode = document): number {
  let cleared = 0
  root.querySelectorAll<HTMLElement>('[data-level]').forEach((el) => {
    const s = scoreOf(el.dataset.level!)
    const ok = !!s?.cleared
    el.classList.toggle('done', ok)
    if (ok && s) {
      cleared++
      el.dataset.stars = starText(s.stars)
      el.dataset.grade = String(s.stars)
      el.title = `${STAR_NOTE[s.stars as 1 | 2 | 3]}`
    } else {
      delete el.dataset.stars
      delete el.dataset.grade
      el.removeAttribute('title')
    }
  })
  return cleared
}

/** How many exercises have a wrong attempt and are still worth redoing (all of them, solved or not). */
export const mistakeCount = () => Object.keys(allMisses()).length
