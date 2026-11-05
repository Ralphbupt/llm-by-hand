/** Build-time: load content/glossary.yaml and attach the level number and title that teach each term. */
import fs from 'node:fs'
import path from 'node:path'
import { load as parseYaml } from 'js-yaml'
import { allLevels } from './levels'
import { termId, type Term, type TermInfo } from './glossary'
import { smart } from './typo'
import type { Lang } from './i18n'

/**
 * A translation of the glossary: content/glossary.<lang>.yaml, keyed by the English term, with the translated `term`,
 * `aliases` (the words the lessons in that language use; English names like "softmax" can stay as aliases) and `def`.
 * The id (the #anchor on the glossary page) stays the English one, so links work in both languages.
 * A term without a translation keeps its English text.
 */
type TermText = { term?: string; aliases?: string[]; def?: string }

const read = (file: string) => (fs.existsSync(file) ? parseYaml(fs.readFileSync(file, 'utf8')) : null)

export async function loadGlossary(lang: Lang = 'en'): Promise<TermInfo[]> {
  const dir = path.join(process.cwd(), '..', 'content')
  const terms = (read(path.join(dir, 'glossary.yaml')) ?? []) as Term[]
  const tr = (lang === 'en' ? {} : read(path.join(dir, `glossary.${lang}.yaml`)) ?? {}) as Record<string, TermText>
  const levels = new Map((await allLevels(lang)).map((l) => [l.id, l]))
  return terms
    .map((t) => {
      const l = levels.get(t.level)
      const x = tr[t.term] ?? {}
      return {
        ...t,
        term: x.term ?? t.term,
        aliases: x.aliases ?? (x.term ? [t.term, ...(t.aliases ?? [])] : t.aliases),
        def: smart(x.def ?? t.def),
        id: termId(t.term),
        levelNum: l?.data.level ?? '',
        levelTitle: l ? (l.data.short ?? l.data.title) : '',
      }
    })
    .sort((a, b) => a.term.localeCompare(b.term, lang === 'zh' ? 'zh-Hans-u-co-pinyin' : 'en', { sensitivity: 'base' }))
}
