/**
 * Site search: turning lesson MDX into searchable sections (build time), and matching a query (in the browser).
 * Everything here is pure so it can be unit tested.
 */
import GithubSlugger from 'github-slugger'

export type Section = { heading: string; anchor: string; text: string }
export type Doc = {
  kind: 'level' | 'term'
  slug: string // level slug, or the glossary term id
  level: string // "12", "D1"; for terms, the level that teaches it
  title: string
  question: string
  url: string
  sections: Section[]
}

/** Strip MDX down to readable text. Keeps the text inside Stuck / Deeper / TryIt, and their titles. */
const TEX_SYM: Record<string, string> = {
  approx: '≈', times: '×', cdot: '·', ln: 'ln', log: 'log', exp: 'exp', sum: 'Σ', prod: 'Π', to: '→', rightarrow: '→',
  leftarrow: '←', le: '≤', leq: '≤', ge: '≥', geq: '≥', neq: '≠', ne: '≠', in: '∈', infty: '∞', pm: '±', sqrt: '√',
  alpha: 'α', beta: 'β', gamma: 'γ', delta: 'δ', Delta: 'Δ', epsilon: 'ε', varepsilon: 'ε', theta: 'θ', lambda: 'λ',
  mu: 'μ', sigma: 'σ', Sigma: 'Σ', pi: 'π', tau: 'τ', partial: '∂', nabla: '∇', top: 'T', odot: '⊙', ldots: '…', dots: '…', cdots: '…',
  max: 'max', min: 'min', mid: '|',
}
/** Inline LaTeX → plain text for search snippets: "e^{\text{score}} \approx 2" → "e^score ≈ 2". */
export function texToText(tex: string): string {
  const wrap = (x: string) => (/^[\w.√]+$/.test(x) ? x : `(${x})`)
  let t = tex
  // inside out: the innermost {…} first, so nested macros come apart
  for (let i = 0; i < 4; i++) {
    t = t
      .replace(/\\(?:text|mathrm|mathbf|mathit|operatorname|textbf|boldsymbol|mathcal|hat|bar|tilde|vec)\s*\{([^{}]*)\}/g, '$1')
      .replace(/\\sqrt\s*\{([^{}]*)\}/g, (_, x: string) => '√' + wrap(x))
      .replace(/\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}/g, (_, a: string, b: string) => `${wrap(a)}/${wrap(b)}`)
  }
  return t
    .replace(/\\(?:left|right|big|Big|bigg|Bigg)\b\s*/g, '')
    .replace(/\\[,;:! ]|\\quad|\\qquad|~/g, ' ')
    .replace(/\\([{}_%#&$])/g, '$1')
    .replace(/\\([A-Za-z]+)/g, (_, w: string) => TEX_SYM[w] ?? w)
    .replace(/([_^])\{([^{}]*)\}/g, '$1$2')
    .replace(/[{}]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

export function mdxToText(src: string): string {
  return src
    .replace(/```[\s\S]*?```/g, ' ')                          // code blocks
    .replace(/^import .*$/gm, '')                             // imports
    .replace(/\{\/\*[\s\S]*?\*\/\}/g, ' ')                     // MDX comments
    .replace(/<Stuck\s+q="([^"]*)"\s*>/g, ' $1 ')             // keep the question of a Stuck box
    .replace(/<(?:Deeper|TryIt)\s+title="([^"]*)"\s*>/g, ' $1 ')
    .replace(/<[A-Za-z][^<>]*?\/>/g, ' ')                     // self-closing components (labs, quiz)
    .replace(/<\/?[A-Za-z][^<>]*>/g, ' ')                     // any other tag
    .replace(/\$\$[\s\S]*?\$\$/g, ' ')                        // display math
    .replace(/\$([^$\n]+)\$/g, (_, m: string) => texToText(m))   // inline math: plain symbols, no LaTeX source
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1')                // links and images → text
    .replace(/(^|\s)_([^_\n]+)_(?=[\s.,;:!?]|$)/gm, '$1$2')     // _emphasis_ (keeps d_k intact)
    .replace(/[*`]+/g, '')                                    // bold and code marks
    .replace(/^\s*(?:[-*+]|\d+\.)\s+/gm, '')                 // list markers
    .replace(/^\s*>\s?/gm, '')                                // blockquote marks
    .replace(/^\s*\|?[\s:|-]+\|[\s:|-]*$/gm, ' ')                   // table separator rows (|---|---|)
    .replace(/\s*\|\s*/g, ' · ')                               // table cell pipes
    .replace(/[ \t]+/g, ' ')
}

/** The text of a heading as the page renders it (enough to reproduce Astro's heading ids). */
function headingText(raw: string): string {
  return raw.replace(/`([^`]*)`/g, '$1').replace(/\$([^$]*)\$/g, (_, m: string) => texToText(m)).replace(/\*/g, '').trim()
}

/**
 * Split a lesson body into sections at its `##` headings. Anchors use the same slugger as Astro
 * (every heading level counts toward de-duplication, in page order).
 */
export function splitSections(body: string): Section[] {
  const slugger = new GithubSlugger()
  const sections: Section[] = [{ heading: '', anchor: '', text: '' }]
  const lines = body.replace(/```[\s\S]*?```/g, '').split('\n')
  for (const line of lines) {
    const m = line.match(/^(#{2,6})\s+(.*)$/)
    if (m) {
      const text = headingText(m[2])
      const anchor = slugger.slug(text)
      if (m[1].length === 2) {
        sections.push({ heading: text, anchor, text: '' })
        continue
      }
    }
    sections[sections.length - 1].text += line + '\n'
  }
  return sections
    .map((s) => ({ ...s, text: mdxToText(s.text).replace(/\s+/g, ' ').trim() }))
    .filter((s) => s.heading || s.text)
}

// ---------- matching (browser) ----------

export const norm = (s: string) =>
  s.toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '').replace(/[’‘]/g, "'").replace(/[“”]/g, '"')

export type Result = {
  doc: Doc
  hits: { section: Section; score: number; snippet: string }[]
  score: number
}

function count(hay: string, word: string): number {
  let n = 0
  for (let i = hay.indexOf(word); i >= 0; i = hay.indexOf(word, i + word.length)) n++
  return n
}

const escapeHtml = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

/** About 150 characters around the first match, with every query word wrapped in <mark>. */
export function snippet(text: string, words: string[], width = 150): string {
  const low = norm(text)
  let at = -1
  for (const w of words) {
    const i = low.indexOf(w)
    if (i >= 0 && (at < 0 || i < at)) at = i
  }
  if (at < 0) at = 0
  let start = Math.max(0, at - Math.floor(width / 3))
  if (start > 0) {
    const sp = text.indexOf(' ', start)
    if (sp >= 0 && sp < at) start = sp + 1
  }
  const end = Math.min(text.length, start + width)
  let out = escapeHtml(text.slice(start, end))
  for (const w of [...words].sort((a, b) => b.length - a.length)) {
    if (!w) continue
    out = out.replace(new RegExp(w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi'), (m) => `<mark>${m}</mark>`)
  }
  return (start > 0 ? '…' : '') + out + (end < text.length ? '…' : '')
}

/**
 * Every query word must appear somewhere in the level (title, question or the section).
 * Ranking: title > heading > text. Results are grouped by level, best first; main levels rank above side trips,
 * and the level a matching glossary card names as its teacher ranks higher still.
 */
export function search(docs: Doc[], query: string, limit = 12): Result[] {
  const words = norm(query).split(/\s+/).filter(Boolean)
  if (!words.length) return []
  const results: Result[] = []
  for (const doc of docs) {
    const title = norm(doc.title)
    const top = title + ' ' + norm(doc.question)
    const hits: Result['hits'] = []
    for (const section of doc.sections) {
      const head = norm(section.heading)
      const text = norm(section.text)
      let score = 0
      let all = true
      for (const w of words) {
        const inTitle = title.includes(w) ? 1 : 0
        const inTop = top.includes(w) ? 1 : 0
        const inHead = head.includes(w) ? 1 : 0
        const inText = count(text, w)
        if (!inTop && !inHead && !inText) { all = false; break }
        score += inTitle * 30 + inTop * 8 + inHead * 12 + Math.min(inText, 5)
      }
      if (all) hits.push({ section, score, snippet: snippet(section.text || section.heading, words) })
    }
    if (!hits.length) continue
    hits.sort((a, b) => b.score - a.score)
    const kept = hits.slice(0, 3)
    results.push({ doc, hits: kept, score: kept[0].score + (doc.kind === 'term' ? 4 : 0) })
  }
  // main levels before side trips, and first the level that a matching glossary card says teaches the term
  const taught = new Set(results.filter((r) => r.doc.kind === 'term').map((r) => r.doc.level))
  const isMainLevel = (d: Doc) => d.kind === 'level' && /^\d+$/.test(d.level)
  for (const r of results) {
    if (isMainLevel(r.doc)) r.score += 6
    if (r.doc.kind === 'level' && taught.has(r.doc.level)) r.score += 10
  }
  results.sort((a, b) => b.score - a.score || Number(isMainLevel(b.doc)) - Number(isMainLevel(a.doc)))
  return results.slice(0, limit)
}
