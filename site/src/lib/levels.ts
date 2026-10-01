/** Shared helpers for ordering and labelling levels (build time). */
import { getCollection, type CollectionEntry } from 'astro:content'

export type Level = CollectionEntry<'lessons'>

export async function allLevels(): Promise<Level[]> {
  return (await getCollection('lessons')).sort((a, b) => a.data.order - b.data.order)
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
export function sectionName(l: Level): string {
  const p = PART_NAME[l.data.part]
  return l.data.branch ? `${p} · ${BRANCH_NAME[l.data.branch]}` : p
}

/** The fields lib/nav.ts needs, from a level entry. */
export const navItem = (l: Level) => ({
  id: l.id, level: l.data.level, title: l.data.title, short: l.data.short, order: l.data.order, branch: l.data.branch, boss: !!l.data.boss,
})
