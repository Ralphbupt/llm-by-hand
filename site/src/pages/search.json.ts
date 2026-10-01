/** The search index: every level split into sections, plus every glossary term. Built from the lesson files. */
import type { APIRoute } from 'astro'
import { allLevels } from '@lib/levels'
import { loadGlossary } from '@lib/glossaryData'
import { splitSections, type Doc } from '@lib/search'
import { smart } from '@lib/typo'

export const GET: APIRoute = async () => {
  const docs: Doc[] = []
  for (const l of await allLevels()) {
    docs.push({
      kind: 'level',
      slug: l.id,
      level: l.data.level,
      title: smart(l.data.title),
      question: smart(l.data.question),
      url: `/learn/${l.id}/`,
      sections: splitSections(l.body ?? '').map((s) => ({ ...s, heading: smart(s.heading), text: smart(s.text) })),
    })
  }
  for (const t of await loadGlossary()) {
    docs.push({
      kind: 'term',
      slug: t.id,
      level: t.levelNum,
      title: t.term,
      question: (t.aliases ?? []).join(', '),
      url: `/glossary/#${t.id}`,
      sections: [{ heading: '', anchor: '', text: t.def }],
    })
  }
  return new Response(JSON.stringify(docs), { headers: { 'Content-Type': 'application/json' } })
}
