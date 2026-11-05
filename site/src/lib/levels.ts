/** Shared helpers for ordering and labelling levels (build time). */
import fs from 'node:fs'
import path from 'node:path'
import { load as parseYaml } from 'js-yaml'
import { getCollection, type CollectionEntry } from 'astro:content'
import { tr, type Lang } from './i18n'

export type Level = CollectionEntry<'lessons'> & {
  /** this level's page exists in the language asked for (else the page shows the English lesson) */
  translated?: boolean
  /** the translated entry, to render (only when `translated`) */
  zh?: CollectionEntry<'lessonsZh'>
  /** the English body, when `body` is a translation */
  enBody?: string
}

/** content/levels.<lang>.yaml: the title, short title, question and boss line of every level, by slug */
type LevelText = Partial<Record<'title' | 'short' | 'question' | 'boss', string>>
function levelTexts(lang: Lang): Record<string, LevelText> {
  if (lang === 'en') return {}
  const p = path.join(process.cwd(), '..', 'content', `levels.${lang}.yaml`)
  return fs.existsSync(p) ? ((parseYaml(fs.readFileSync(p, 'utf8')) ?? {}) as Record<string, LevelText>) : {}
}

/**
 * Every level, in course order. In another language, each level's text fields come from its translation
 * (content/levels.<lang>.yaml and lesson.<lang>.mdx); a level not translated yet keeps its English body.
 */
export async function allLevels(lang: Lang = 'en'): Promise<Level[]> {
  const en = (await getCollection('lessons')).sort((a, b) => a.data.order - b.data.order)
  if (lang === 'en') return en
  const texts = levelTexts(lang)
  const zh = new Map((await getCollection('lessonsZh')).map((e) => [e.id, e]))
  return en.map((e) => {
    const z = zh.get(e.id)
    const t = texts[e.id] ?? {}
    return {
      ...e,
      body: z ? z.body : e.body,
      enBody: e.body,
      translated: !!z,
      zh: z,
      data: {
        ...e.data,
        ...Object.fromEntries(Object.entries(t).filter(([, v]) => !!v)),
        // a translated title without its own short title: the English short title would not fit, so use the title
        ...(t.title && !t.short ? { short: undefined } : {}),
        ...(z?.data.recap ? { recap: z.data.recap } : {}),
        ...(z ? { glossarySkip: z.data.glossarySkip } : {}),
      },
    }
  })
}

export const PART_NAME = { foundations: 'Foundations', theory: 'Theory', engineering: 'Engineering' } as const
export const BRANCH_NAME = {
  classic: 'Classic networks',
  internals: 'Under the hood',
  diffusion: 'Diffusion',
  training: 'Training methods',
} as const

/** One line under each branch on the map: what it is and when it opens. Where each level opens: lib/nav.ts (OPENS_AFTER). */
export const BRANCH_NOTE = {
  classic: 'The networks that came before the Transformer, and the steps that led to it: convolutions, residuals, recurrent networks, LSTMs, the first attention, autoencoders, and the 2017 encoder–decoder Transformer. Opens after level 10; the 2017 Transformer (N7) opens after level 17.',
  internals: 'The machinery PyTorch hides from you: tensors in memory, numbers in a computer, your own autograd, feeding data to a model, debugging a model (boss), and the backward pass of attention. Each level opens after the main level where it becomes useful: U1–U5 during Foundations, U6 after level 17.',
  diffusion: 'Another way to generate: start from noise and clean it up. D1 and D2 open after Foundations; D3 builds on attention and Transformer blocks (levels 14–16).',
} as const
export const RUN_NAME = { browser: 'runs in your browser', local: 'runs on your computer', mixed: 'runs in your browser · last part on your computer', cloud: 'needs a cloud GPU' } as const

/** "Theory", "Theory · Diffusion" */
export function sectionName(l: Level, lang: Lang = 'en'): string {
  const p = tr(lang, PART_NAME[l.data.part])
  return l.data.branch ? `${p} · ${tr(lang, BRANCH_NAME[l.data.branch])}` : p
}

/** The fields lib/nav.ts needs, from a level entry. */
export const navItem = (l: Level) => ({
  id: l.id, level: l.data.level, title: l.data.title, short: l.data.short, order: l.data.order, branch: l.data.branch, boss: !!l.data.boss,
})
