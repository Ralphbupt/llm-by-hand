/**
 * Browser side for the home prototypes: which levels are cleared (and with how many stars),
 * which main-line level is next, and the mistakes count. Reads the embedded level index like the real home page.
 */
import { scoreOf, starText, mistakeCount } from '@lib/marks'
import { subscribe } from '@lib/progress'

export type HomeState = {
  cleared: Map<string, number> // slug → stars (1..3)
  next: string | null // first main-line slug not cleared (null when nothing is cleared yet, or all are)
  started: boolean
  mistakes: number
}

export function readState(mainOrder: string[], allSlugs: string[]): HomeState {
  const cleared = new Map<string, number>()
  for (const s of allSlugs) {
    const sc = scoreOf(s)
    if (sc?.cleared) cleared.set(s, sc.stars)
  }
  const started = cleared.size > 0
  const next = started ? (mainOrder.find((s) => !cleared.has(s)) ?? null) : null
  return { cleared, next, started, mistakes: mistakeCount() }
}

export function onProgress(fn: () => void) {
  fn()
  return subscribe(fn)
}

export { starText }
