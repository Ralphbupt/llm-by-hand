/**
 * Build time: page descriptions and structured data (JSON-LD) for search engines.
 * The origin and the provider come from src/config/site.ts.
 */
import { SITE_NAME, SITE_URL, SITE_DESCRIPTION, AUTHOR, LICENSE_URL, abs } from '../config/site'
import { BRANCH_NAME, PART_NAME, type Level } from './levels'

/** Inline Markdown and math to plain text, for meta descriptions and JSON-LD ("`(n, k)`" → "(n, k)"). */
export function plain(s: string): string {
  return s
    .replace(/\$\$?([^$]+)\$\$?/g, (_, m: string) => m.replace(/\\(text|mathrm|operatorname)\{([^}]*)\}/g, '$2').replace(/\\[a-zA-Z]+/g, '').replace(/[{}_^]/g, ''))
    .replace(/`([^`]*)`/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/<[^>]+>/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

/** "Level 14", "Side trip U3 (Under the hood)" */
export function levelLabel(l: Level): string {
  return l.data.branch ? `Side trip ${l.data.level} (${BRANCH_NAME[l.data.branch]})` : `Level ${l.data.level}`
}

/** The meta description of a level: its question, then what it covers. Kept near 160 characters. */
export function levelDescription(l: Level): string {
  const q = plain(l.data.question)
  const tail = ` ${levelLabel(l)} of ${SITE_NAME}: work it out by hand with small numbers, in an interactive lesson.`
  const s = q + tail
  return s.length <= 200 ? s : q
}

const provider = { '@type': 'Person', '@id': 'https://liko.page/#person', name: AUTHOR.name, alternateName: AUTHOR.alternateName, url: AUTHOR.url }
const courseId = `${SITE_URL}/#course`

export function websiteLd() {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    '@id': `${SITE_URL}/#website`,
    name: SITE_NAME,
    url: `${SITE_URL}/`,
    description: SITE_DESCRIPTION,
    inLanguage: 'en',
  }
}

export function courseLd(levels: Level[]) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Course',
    '@id': courseId,
    name: SITE_NAME,
    url: `${SITE_URL}/`,
    description: SITE_DESCRIPTION,
    provider,
    inLanguage: 'en',
    isAccessibleForFree: true,
    license: LICENSE_URL,
    educationalLevel: 'Beginner to intermediate',
    teaches: 'How large language models and Transformers work, computed by hand',
    offers: { '@type': 'Offer', price: 0, priceCurrency: 'USD', category: 'Free' },
    hasCourseInstance: {
      '@type': 'CourseInstance',
      courseMode: 'online',
      inLanguage: 'en',
    },
    hasPart: levels.map((l) => ({ '@type': 'LearningResource', name: `${l.data.level}. ${l.data.title}`, url: abs(`/learn/${l.id}/`) })),
  }
}

/** One level: a LearningResource that is part of the course, at its place in reading order. */
export function levelLd(l: Level, position: number) {
  const part = PART_NAME[l.data.part]
  return {
    '@context': 'https://schema.org',
    '@type': 'LearningResource',
    name: `${l.data.level}. ${l.data.title}`,
    url: abs(`/learn/${l.id}/`),
    description: plain(l.data.question),
    learningResourceType: 'Interactive lesson',
    interactivityType: 'active',
    educationalLevel: l.data.part === 'foundations' ? 'Beginner' : 'Intermediate',
    inLanguage: 'en',
    isAccessibleForFree: true,
    license: LICENSE_URL,
    position,
    about: l.data.branch ? `${part}: ${BRANCH_NAME[l.data.branch]}` : part,
    ...(l.data.recap?.can?.length ? { teaches: l.data.recap.can.map(plain) } : {}),
    isPartOf: { '@type': 'Course', '@id': courseId, name: SITE_NAME, url: `${SITE_URL}/` },
    provider,
  }
}

/** [["LLM by Hand", "/"], ["Glossary", "/glossary/"]] → BreadcrumbList */
export function breadcrumbLd(items: [string, string][]) {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map(([name, path], i) => ({ '@type': 'ListItem', position: i + 1, name, item: abs(path) })),
  }
}

export function glossaryLd(terms: { id: string; term: string; def: string; aliases?: string[] }[]) {
  const url = abs('/glossary/')
  return {
    '@context': 'https://schema.org',
    '@type': 'DefinedTermSet',
    '@id': `${url}#terms`,
    name: `${SITE_NAME} glossary`,
    url,
    hasDefinedTerm: terms.map((t) => ({
      '@type': 'DefinedTerm',
      '@id': `${url}#${t.id}`,
      name: t.term,
      ...(t.aliases?.length ? { alternateName: t.aliases } : {}),
      description: plain(t.def),
      url: `${url}#${t.id}`,
      inDefinedTermSet: `${url}#terms`,
    })),
  }
}
