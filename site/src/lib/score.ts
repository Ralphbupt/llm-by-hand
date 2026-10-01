/**
 * Build time: every level's exercise ids and checkpoint, so the browser can score levels
 * (stars on the map and in the sidebar, the summary at the bottom of a lesson) without loading every page.
 */
import { allLevels } from './levels'
import { loadExercises } from './quiz'
import { pointsAtPage, warmEligible, type WarmData, type WarmItem } from './warmup'
import { OPENS_AFTER } from './nav'
import { idsInSideBoxes, sectionOf } from './lessonScan'

/**
 * `optional`: ids that never cost a star (see levelScore): flagged `optional: true` in exercises.yaml, or placed
 * inside a <Stuck> or <Deeper> box on the page.
 * `mustWhere`: for each mustSolve part, the section it sits in ("Step 2: the forward shape"), so the end card can name it.
 */
export type LevelIndex = Record<string, { ids: string[]; checkpoint: string; mustSolve?: string[]; optional?: string[]; mustWhere?: Record<string, string> }>

export async function levelIndex(): Promise<LevelIndex> {
  const out: LevelIndex = {}
  for (const l of await allLevels()) {
    const exs = loadExercises(l.id)
    const body = l.body ?? ''
    const boxed = new Set(idsInSideBoxes(body))
    const optional = Object.keys(exs).filter((id) => exs[id].optional || boxed.has(id))
    const mustWhere: Record<string, string> = {}
    for (const id of l.data.mustSolve ?? []) { const h = sectionOf(body, id); if (h) mustWhere[id] = h }
    out[l.id] = {
      ids: Object.keys(exs),
      checkpoint: l.data.checkpoint,
      ...(l.data.mustSolve ? { mustSolve: l.data.mustSolve } : {}),
      ...(Object.keys(mustWhere).length ? { mustWhere } : {}),
      ...(optional.length ? { optional } : {}),
    }
  }
  return out
}

/** Safe to drop inside <script type="application/json"> */
export const toJsonScript = (v: unknown) => JSON.stringify(v).replace(/</g, '\\u003c')

/**
 * Build time: the warm-up questions a level may ask: every number, shape and graded predict of the levels
 * it builds on, with only the fields the quiz components need.
 * - A main level: the main levels before it, and the side-trip levels that opened before it.
 * - A side-trip level: only its prerequisites, i.e. the main line up to the level it opens after
 *   (lib/nav.ts), and the earlier levels of its own branch.
 */
export async function warmData(slug: string): Promise<WarmData> {
  const all = await allLevels()
  const here = all.find((l) => l.id === slug)
  const orderOf = (id: string) => all.find((l) => l.id === id)?.data.order ?? Infinity
  // the main-line point a level hangs on: its own order (main) or the order of the level it opens after (branch)
  const anchor = (l: (typeof all)[number]) => (l.data.branch ? orderOf(OPENS_AFTER[l.id]) : l.data.order)
  let earlier: typeof all = []
  if (here && !here.data.branch) {
    earlier = all.filter((l) => l.data.order < here.data.order && (!l.data.branch || anchor(l) < here.data.order))
  } else if (here) {
    const top = anchor(here)
    earlier = all.filter((l) => (!l.data.branch && l.data.order <= top) || (l.data.branch === here.data.branch && l.data.order < here.data.order))
  }
  const items: WarmItem[] = []
  for (const l of earlier) {
    for (const [id, ex] of Object.entries(loadExercises(l.id))) {
      if (!warmEligible(ex) || ex.type === 'code') continue
      // away from its page, the question needs the version that stands alone (the one the test-out uses too)
      const it: WarmItem = { id, page: l.id, type: ex.type, prompt: ex.promptShort ?? ex.prompt, answer: ex.answer! }
      if (ex.type === 'number') { if (ex.tol !== undefined) it.tol = ex.tol; if (ex.unit) it.unit = ex.unit }
      if (ex.type === 'predict') { it.options = ex.options; it.reveal = ex.reveal }
      if (ex.hints?.length) it.hints = ex.hints
      if (ex.after && !pointsAtPage(ex.after)) it.after = ex.after
      items.push(it)
    }
  }
  return { levels: earlier.map((l) => ({ slug: l.id, level: l.data.level, title: l.data.short ?? l.data.title, main: !l.data.branch })), items }
}
