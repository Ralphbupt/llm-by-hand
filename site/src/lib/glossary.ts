/**
 * Glossary terms and the logic that finds the first use of each term in a page's prose.
 * The matching is pure (strings in, positions out) so it can be unit tested; the layout's client script
 * applies the positions to the page's text nodes.
 */

export type Term = {
  term: string
  aliases?: string[]
  def: string
  level: string // slug of the level that teaches it
  mark?: boolean // false: glossary page and search only, never underlined in lessons
  only?: string[] // underline it only on these pages (a word that means something else elsewhere, like “code”)
}

/** A term ready for the client: where it is taught, and an id for the glossary page. */
export type TermInfo = Term & { id: string; levelNum: string; levelTitle: string }

export const termId = (t: string) =>
  'term-' + t.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')

const escapeRe = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

/** Forms that count as a use of the term: the term, its aliases, and a plain plural (s / es). */
function forms(t: Term): string[] {
  const out = new Set<string>()
  for (const f of [t.term, ...(t.aliases ?? [])]) {
    out.add(f)
    if (/[a-z]$/i.test(f) && !/s$/i.test(f)) out.add(f + 's')
    if (/(x|ch|sh)$/i.test(f)) out.add(f + 'es')
  }
  return [...out]
}

/**
 * One regex for all markable terms. Longer forms come first, so “multi-head attention” wins over “attention”
 * and “gradient descent” over “gradient”. Terms are matched as whole words (a hyphen counts as part of a word,
 * so “entropy” is not found inside “cross-entropy”).
 */
export function buildMatcher(terms: Term[]): { re: RegExp; owner: Map<string, number> } {
  const owner = new Map<string, number>()
  const all: string[] = []
  terms.forEach((t, i) => {
    if (t.mark === false) return
    for (const f of forms(t)) {
      const k = f.toLowerCase()
      if (!owner.has(k)) {
        owner.set(k, i)
        all.push(f)
      }
    }
  })
  all.sort((a, b) => b.length - a.length)
  const re = new RegExp(`(?<![\\w-])(${all.map(escapeRe).join('|')})(?![\\w-])`, 'gi')
  return { re, owner }
}

export type Hit = { chunk: number; start: number; end: number; term: number }

/**
 * Walk the chunks of text in reading order and return the first use of each term (at most one hit per term).
 * A shorter term inside a longer match (“attention” inside “multi-head attention”) does not count there.
 */
export function firstUses(chunks: string[], terms: Term[]): Hit[] {
  const { re, owner } = buildMatcher(terms)
  const seen = new Set<number>()
  const hits: Hit[] = []
  chunks.forEach((text, chunk) => {
    re.lastIndex = 0
    let m: RegExpExecArray | null
    while ((m = re.exec(text))) {
      const term = owner.get(m[1].toLowerCase())
      if (term === undefined || seen.has(term)) continue
      seen.add(term)
      hits.push({ chunk, start: m.index, end: m.index + m[1].length, term })
    }
  })
  return hits
}
