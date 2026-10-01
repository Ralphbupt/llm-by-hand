/**
 * The path through the course: the main line, and where each side-trip level opens.
 * Pure (no astro:content), so it is shared by the lesson layout, the sidebar and the home map, and tested.
 *
 * Rules (AUTHORING.md, "The path"):
 * - Prev/Next on a main level walk the main line only.
 * - Each side-trip level opens after one main level, its real prerequisite (OPENS_AFTER). The sidebar lists it
 *   under that level, the map draws it next to that level, and that level ends with "Side trips now open".
 * - Inside a branch, Next walks the branch. Prev is the reverse of Next:
 *   - when the level before opens after the same main level, Prev is that level;
 *   - otherwise (U1 to U4 each open after a different level, and U6 opens after 17 while U5 opens after 10) the page is
 *     built with Prev leading back to the main level the learner came from (the opening level if we don't know), and
 *     `branchPrev` names the level before. The browser turns Prev back into `branchPrev` when the learner walked to
 *     this level through it in the same trip (LessonLayout keeps the trip in sessionStorage). So 10 → U1 → U2 → U3 and
 *     then Prev goes U2, U1, 10; but 17 → U6 and then Prev goes back to 17, not to U5.
 * - The last side-trip level's Next continues the main line with the main level after the one the learner came from, so
 *   Prev and Next never point at the same page. After the last main level there is nothing to continue: Next is the
 *   course map.
 * - A level in RECOMMENDED is listed first after its main level, with a half-line note.
 */

/** Side-trip level slug → the main level after which it opens. Every side-trip level needs an entry. */
export const OPENS_AFTER: Record<string, string> = {
  // Under the hood
  'tensors-in-memory': 'matrices',
  'numbers-in-a-computer': 'neurons-and-loss',
  autograd: 'backprop',
  'data-pipeline': 'numpy-to-pytorch',
  debugging: 'numpy-to-pytorch',
  'attention-backward': 'full-model',
  // Classic networks
  convolutions: 'probability',
  'residuals-and-norms': 'probability',
  rnn: 'probability',
  lstm: 'probability',
  'seq2seq-attention': 'probability',
  autoencoders: 'probability',
  'encoder-decoder': 'full-model',
  // Diffusion
  'noise-and-denoise': 'probability',
  'sampling-and-guidance': 'probability',
  'latents-and-dit': 'transformer-parts',
}

/** Side trips to point out after their main level: listed first in "Side trips after this level", with this note. */
export const RECOMMENDED: Record<string, string> = {
  'encoder-decoder': 'the original design, with an encoder and a decoder',
}

/** The last main level's end card: the course map, and then the first of these side trips not yet cleared. */
export const AFTER_COURSE = ['encoder-decoder', 'attention-backward']

export type NavItem = { id: string; level: string; title: string; short?: string; order: number; branch?: string; boss?: boolean }

export const isMain = (l: Pick<NavItem, 'branch'>) => !l.branch

/** The main levels, in course order. */
export const mainLine = <T extends NavItem>(all: T[]): T[] => [...all].sort((a, b) => a.order - b.order).filter(isMain)

/** The main level a side-trip level opens after (throws if the table misses it, so a new side-trip level can't slip through). */
export function opensAfter<T extends NavItem>(all: T[], l: T, table = OPENS_AFTER): T {
  const id = table[l.id]
  const m = id ? all.find((x) => x.id === id && isMain(x)) : undefined
  if (!m) throw new Error(`lib/nav.ts: OPENS_AFTER has no main level for the side-trip level "${l.id}"`)
  return m
}

/** Side-trip levels that open after this main level, in course order. */
export const tripsAfter = <T extends NavItem>(all: T[], mainId: string, table = OPENS_AFTER, rec = RECOMMENDED): T[] =>
  [...all].sort((a, b) => Number(!!rec[b.id]) - Number(!!rec[a.id]) || a.order - b.order).filter((l) => !isMain(l) && table[l.id] === mainId)

/** The same, grouped by branch (keeps the order of first appearance). */
export function tripGroups<T extends NavItem>(all: T[], mainId: string, table = OPENS_AFTER, rec = RECOMMENDED): { branch: string; levels: T[] }[] {
  const out: { branch: string; levels: T[] }[] = []
  for (const l of tripsAfter(all, mainId, table, rec)) {
    const g = out.find((x) => x.branch === l.branch)
    if (g) g.levels.push(l)
    else out.push({ branch: l.branch!, levels: [l] })
  }
  return out
}

export type Neighbors<T> = {
  prev?: T
  next?: T
  /** side-trip levels: prev/next leave the branch and go back to the main line */
  prevIsBack?: boolean
  nextIsBack?: boolean
  /** the last side-trip level: Next continues the main line (the main level after the one the learner came from) */
  nextIsContinue?: boolean
  /** side-trip levels: the main level the next side-trip level opens after (the browser may send the learner back first) */
  nextOpensAfter?: T
  /** side-trip levels whose Prev leads back to the main line: the side-trip level before, for the browser to restore */
  branchPrev?: T
  /** side-trip levels: the main level this one opens after */
  home?: T
}

export function neighbors<T extends NavItem>(all: T[], id: string, table = OPENS_AFTER): Neighbors<T> {
  const sorted = [...all].sort((a, b) => a.order - b.order)
  const here = sorted.find((l) => l.id === id)
  if (!here) return {}
  if (isMain(here)) {
    const main = sorted.filter(isMain)
    const i = main.indexOf(here)
    return { prev: main[i - 1], next: main[i + 1] }
  }
  const branch = sorted.filter((l) => l.branch === here.branch)
  const i = branch.indexOf(here)
  const home = opensAfter(sorted, here, table)
  const out: Neighbors<T> = { home }
  // Prev stays in the branch while the level before opens after the same main level. Otherwise it leads back to the
  // main line, and branchPrev lets the browser restore the side-trip level when the learner came through it
  if (i > 0 && table[branch[i - 1].id] === table[here.id]) out.prev = branch[i - 1]
  else { out.prev = home; out.prevIsBack = true; if (i > 0) out.branchPrev = branch[i - 1] }
  if (i < branch.length - 1) { out.next = branch[i + 1]; out.nextOpensAfter = opensAfter(sorted, branch[i + 1], table) }
  else {
    const main = sorted.filter(isMain)
    const after = main[main.indexOf(home) + 1]
    if (after) { out.next = after; out.nextIsContinue = true }
    else { out.next = home; out.nextIsBack = true }
  }
  return out
}

/** Sidebar / map placement: each main level followed by the side trips that open after it. */
export function placement<T extends NavItem>(all: T[], table = OPENS_AFTER): { main: T; trips: { branch: string; levels: T[] }[] }[] {
  return mainLine(all).map((m) => ({ main: m, trips: tripGroups(all, m.id, table) }))
}

/**
 * The trip: the side-trip levels walked since the last main level, kept per browser tab (sessionStorage), together
 * with the main level it started from. `from` is fixed when the trip starts. The last main level is also kept in
 * localStorage, which all tabs share, so a main level opened in another tab must not change where this trip leads back.
 */
export type Trip = { from?: string; levels: string[] }

/** Read a stored trip. Accepts the older form (a plain list of levels); anything else is an empty trip. */
export function readTrip(raw: string | null): Trip {
  try {
    const v = JSON.parse(raw ?? 'null')
    if (Array.isArray(v)) return { levels: v.filter((x) => typeof x === 'string') }
    if (v && typeof v === 'object' && Array.isArray(v.levels))
      return { from: typeof v.from === 'string' ? v.from : undefined, levels: v.levels.filter((x: unknown) => typeof x === 'string') }
  } catch { /* not JSON */ }
  return { levels: [] }
}

/**
 * The trip after arriving on a level. A main level ends the trip (null). A side-trip level joins it; a new trip
 * (or one that came from a page outside the levels, `fresh`) starts at the last main level, or at `home`, the main
 * level this side trip opens after, when no main level was visited yet.
 */
export function stepTrip(raw: string | null, here: string, isBranch: boolean, lastMain: string | null, home?: string, fresh = false): Trip | null {
  if (!isBranch) return null
  const t = fresh ? { levels: [] } : readTrip(raw)
  const from = t.levels.length && t.from ? t.from : (lastMain ?? home)
  return { from, levels: t.levels.includes(here) ? t.levels : [...t.levels, here] }
}

/** True when the page came from this site but not from a level page (home, glossary, review, ...): the trip starts over. */
export function cameFromOutsideLevels(referrer: string, origin: string): boolean {
  if (!referrer) return false
  try {
    const u = new URL(referrer)
    return u.origin === origin && !/^\/learn\/[^/]+\/?$/.test(u.pathname)
  } catch { return false }
}
