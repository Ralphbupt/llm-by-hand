/**
 * Browser side of level scoring: reads the build-time level index embedded in the page
 * (<script type="application/json" id="level-index">) and marks levels with stars.
 */
import { allMisses, levelScore, type LevelScore } from './progress'
import type { LevelIndex } from './score'
import { translator, type Lang } from './i18n'

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


/**
 * The end card's two lines for a level: `note` (what the stars mean here, or what is still missing) and `nums`.
 * `mustWhere` names the section of each mustSolve part (from the level index). HTML-free plain text.
 */
export function endCardText(sc: LevelScore, mustWhere: Record<string, string> = {}, lang: Lang = 'en'): { note: string; nums: string } {
  const t = translator(lang)
  const opt = sc.optionalTotal ? t(' · Optional: {a} of {b}', { a: sc.optionalSolved, b: sc.optionalTotal }) : ''
  const skip = sc.skipped ? t(' · Skipped parts: {n}', { n: sc.skipped }) : ''
  const solved = t('Solved yourself: {a} · With the answer shown: {b}', { a: sc.solved, b: sc.shown })
  if (!sc.cleared && sc.missing.length) {
    const where = [...new Set(sc.missing.map((id) => (mustWhere[id] ? `“${mustWhere[id]}”` : id)))].join(t(' and '))
    const note = sc.missing.length === 1
      ? t("Not cleared yet: solve the boss part in {where} too. Skip for now can't pass it.", { where })
      : t("Not cleared yet: solve the {n} boss parts in {where} too. Skip for now can't pass them.", { n: sc.missing.length, where })
    return { note, nums: `${solved}${skip}` }
  }
  let note: string
  if (sc.testedOut) note = t('Skipped with the short test: you solved its questions on your own')
  else if (sc.stars === 1) note = t(sc.unsolved.length === 1 ? 'Cleared, with {n} question still unsolved' : 'Cleared, with {n} questions still unsolved', { n: sc.unsolved.length })
  // optional questions left: "every question" would not be true
  else if (sc.stars === 3 && sc.optionalSolved < sc.optionalTotal) note = t('Every required question solved on your own')
  else note = t(STAR_NOTE[(sc.stars || 1) as 1 | 2 | 3])
  const unsolved = sc.unsolved.length ? t(' · Unsolved: {n}', { n: sc.unsolved.length }) : ''
  return { note, nums: `${solved}${unsolved}${skip}${opt}` }
}

/**
 * Mark every element with data-level="<slug>": class "done" when cleared,
 * data-stars ("★★☆") and data-grade ("3" own, "2" with answers, "1" with skips) for styling.
 */
export function markLevels(root: ParentNode = document, lang: Lang = 'en'): number {
  const t = translator(lang)
  let cleared = 0
  root.querySelectorAll<HTMLElement>('[data-level]').forEach((el) => {
    const s = scoreOf(el.dataset.level!)
    const ok = !!s?.cleared
    el.classList.toggle('done', ok)
    if (ok && s) {
      cleared++
      el.dataset.stars = starText(s.stars)
      el.dataset.grade = String(s.stars)
      el.title = t(STAR_NOTE[s.stars as 1 | 2 | 3])
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
