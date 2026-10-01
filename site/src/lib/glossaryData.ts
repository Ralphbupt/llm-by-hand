/** Build-time: load content/glossary.yaml and attach the level number and title that teach each term. */
import fs from 'node:fs'
import path from 'node:path'
import { load as parseYaml } from 'js-yaml'
import { allLevels } from './levels'
import { termId, type Term, type TermInfo } from './glossary'
import { smart } from './typo'

export async function loadGlossary(): Promise<TermInfo[]> {
  const file = path.join(process.cwd(), '..', 'content', 'glossary.yaml')
  const terms = (parseYaml(fs.readFileSync(file, 'utf8')) ?? []) as Term[]
  const levels = new Map((await allLevels()).map((l) => [l.id, l]))
  return terms
    .map((t) => {
      const l = levels.get(t.level)
      return {
        ...t,
        def: smart(t.def),
        id: termId(t.term),
        levelNum: l?.data.level ?? '',
        levelTitle: l ? (l.data.short ?? l.data.title) : '',
      }
    })
    .sort((a, b) => a.term.localeCompare(b.term, 'en', { sensitivity: 'base' }))
}
