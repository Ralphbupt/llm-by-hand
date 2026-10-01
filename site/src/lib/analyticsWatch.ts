/**
 * Page-level analytics events that need no hook inside a component: first open of a level or side trip,
 * level cleared / boss passed (watched through the progress event), glossary opens, downloads.
 * Every event goes through track(), which sends nothing without an ID and consent.
 * The events recorded where they happen live in lib/progress.ts (checkpoint_pass, answer_reveal, hint_open,
 * test_out_pass) and lib/pyodide/client.ts (code_run).
 */
import { analyticsEnabled, getConsent, pageInfo, track } from './analytics'
import { scoreOf } from './marks'

const SEEN = 'llmbh-ga-seen'

function seenOnce(key: string): boolean {
  try {
    const all = JSON.parse(localStorage.getItem(SEEN) ?? '[]') as string[]
    if (all.includes(key)) return true
    all.push(key)
    localStorage.setItem(SEEN, JSON.stringify(all.slice(-400)))
  } catch {}
  return false
}

/** The glossary id of the n-th term in the page's #glossary-data (a lesson underlines terms by index). */
function termId(n: number): string | undefined {
  try {
    return (JSON.parse(document.getElementById('glossary-data')?.textContent ?? '[]') as { id?: string }[])[n]?.id
  } catch {
    return undefined
  }
}

export function watchAnalytics() {
  if (!analyticsEnabled()) return
  const p = pageInfo()
  const consented = () => getConsent() === 'granted'

  // first open of a level (and of a side-trip level); counted once consent exists
  const opened = () => {
    if (!consented() || p.kind !== 'level' || !p.slug) return
    if (!seenOnce(`start:${p.slug}`)) {
      track('level_start')
      if (p.branch) track('side_trip_open', { branch: p.branch })
    }
  }
  opened()
  if (p.kind === 'glossary') track('glossary_open', { source: 'page' })
  window.addEventListener('llmbh:consent', opened)

  // level cleared during this visit (false → true), and a boss level's boss passed
  if (p.kind === 'level' && p.slug) {
    let was = !!scoreOf(p.slug)?.cleared
    window.addEventListener('quiz:progress', () => {
      const now = !!scoreOf(p.slug!)?.cleared
      if (now && !was) {
        track('level_clear')
        if (p.boss) track('boss_pass')
      }
      was = now
    })
  }

  document.addEventListener('click', (e) => {
    const t = e.target as Element | null
    // a glossary term in a lesson (its card opens)
    const term = t?.closest?.('.gl-term') as HTMLElement | null
    if (term) track('glossary_open', { source: 'lesson', term: termId(Number(term.dataset.term)) })
    // a file for running a level on your computer
    const a = t?.closest?.('a[href^="/files/"]') as HTMLAnchorElement | null
    if (a) track('download', { file_path: a.getAttribute('href') ?? '' })
  })
}
