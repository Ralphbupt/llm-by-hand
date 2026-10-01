/**
 * "Already know this? Test out": a few of the level's own questions. Solving all of them on your own
 * clears the level (three stars) and opens every Gate on the page. Pure helpers, used at build time and in the browser.
 */

/** Ids of quiz components in an MDX body, grouped by `## ` section (text before the first `##` is section 0). */
export function exercisesBySection(body: string): string[][] {
  const sections: string[][] = [[]]
  const re = /<(?:Blank|CodeBlank|Predict)\b[^>]*?\bid=["']([^"']+)["']/g
  for (const line of body.split('\n')) {
    if (/^##\s/.test(line)) sections.push([])
    for (const m of line.matchAll(re)) sections[sections.length - 1].push(m[1])
  }
  return sections.filter((s) => s.length > 0)
}

/**
 * Default test-out when the frontmatter has none: the checkpoint plus up to two other questions
 * (no Predicts), each the last question of its section, spread over the level (not two neighbors).
 */
export function defaultTestOut(body: string, types: Record<string, string>, checkpoint: string, extra = 2): string[] {
  const lastOfEach: string[] = []
  for (const sec of exercisesBySection(body)) {
    const ok = sec.filter((id) => id !== checkpoint && types[id] && types[id] !== 'predict')
    const last = ok.at(-1)
    if (last && !lastOfEach.includes(last)) lastOfEach.push(last)
  }
  const n = lastOfEach.length
  let picks: string[]
  if (n <= extra) picks = lastOfEach
  else {
    // evenly spread: for 3 → first and last; for 5 → 2nd and 4th
    const idx = new Set<number>()
    for (let k = 1; k <= extra; k++) idx.add(Math.min(n - 1, Math.max(0, Math.round((k * (n + 1)) / (extra + 1)) - 1)))
    picks = [...idx].sort((a, b) => a - b).map((i) => lastOfEach[i])
  }
  return types[checkpoint] ? [...picks, checkpoint] : picks
}

/** Where a test-out stands, from the stored progress ("<slug>/<id>" → entry). */
export function testOutStatus(slug: string, ids: string[], progress: Record<string, { shown?: boolean }>) {
  let solved = 0
  let shown = 0
  for (const id of ids) {
    const e = progress[`${slug}/${id}`]
    if (!e) continue
    if (e.shown) shown++
    else solved++
  }
  // complete = every question solved without "Show answer"
  return { total: ids.length, solved, shown, complete: ids.length > 0 && solved === ids.length }
}
