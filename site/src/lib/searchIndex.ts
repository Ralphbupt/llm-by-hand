/** The search index: every level split into sections, plus every glossary term. Built from the lesson files. */
import { allLevels, type Level } from './levels'
import { loadGlossary } from './glossaryData'
import { headingIds, splitSections, type Doc, type Section } from './search'
import { smart } from './typo'
import { href, type Lang } from './i18n'

/** A translated level keeps the English heading ids (astro.config.mjs): its n-th section links to the n-th English one. */
function anchorsInEnglish(l: Level, sections: Section[]): Section[] {
  if (!l.translated) return sections
  const en = headingIds(l.enBody ?? '').filter((h) => h.depth === 2).map((h) => h.id)
  let k = 0
  return sections.map((s) => (s.heading ? { ...s, anchor: en[k++] ?? s.anchor } : s))
}

/** The index for one language (/search.json, /zh/search.json): a level not translated yet is indexed in English. */
export async function searchDocs(lang: Lang): Promise<Doc[]> {
  const docs: Doc[] = []
  for (const l of await allLevels(lang)) {
    docs.push({
      kind: 'level',
      slug: l.id,
      level: l.data.level,
      title: smart(l.data.title),
      question: smart(l.data.question),
      url: href(lang, `/learn/${l.id}/`),
      sections: anchorsInEnglish(l, splitSections(l.body ?? '')).map((s) => ({ ...s, heading: smart(s.heading), text: smart(s.text) })),
    })
  }
  for (const t of await loadGlossary(lang)) {
    docs.push({
      kind: 'term',
      slug: t.id,
      level: t.levelNum,
      title: t.term,
      question: (t.aliases ?? []).join(', '),
      url: href(lang, `/glossary/#${t.id}`),
      sections: [{ heading: '', anchor: '', text: t.def }],
    })
  }
  return docs
}
