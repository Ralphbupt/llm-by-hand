/** Build-time data shared by the home-page prototypes (preview/a, b, c). */
import { allLevels, BRANCH_NAME, BRANCH_NOTE, navItem, type Level } from '@lib/levels'
import { placement } from '@lib/nav'
import { levelIndex } from '@lib/score'
import { smart } from '@lib/typo'
import { tr, type Lang } from '@lib/i18n'

export const later = [
  { key: 'engineering', name: 'Engineering', short: 'Engineering', sub: 'Making it fast and affordable: GPUs, kernels, memory, serving.',
    items: ['The workload ledger', 'Accelerators', 'Kernels and FlashAttention', 'Talking between GPUs', 'Parallelism', 'ZeRO and memory', 'Mixed precision', 'Checkpoints and failures', 'KV cache', 'Batching and scheduling', 'Quantization', 'Speculative decoding', 'Distributed inference', 'Device, edge, cloud'] },
  { key: 'training', name: 'Training large models', short: 'Training large models', sub: 'How real models are taught: data, stability, fine-tuning, alignment, evaluation.',
    items: ['Pretraining: data and scale', 'Training stability', 'Fine-tuning and LoRA', 'Instruction tuning, alignment', 'Evaluation'] },
  { key: 'applications', name: 'Applications', short: 'Applications', sub: 'Building with a model: context, tools, retrieval, agents, the harness.',
    items: ['Prompts and in-context learning', 'Structured output and tool calls', 'Retrieval', 'RAG', 'The agent loop', 'The harness', 'Evaluating and securing an agent'] },
]

/** The planned parts, in a language */
export const laterIn = (lang: Lang) =>
  later.map((p) => ({ ...p, name: tr(lang, p.name), short: tr(lang, p.short), sub: tr(lang, p.sub), items: p.items.map((x) => tr(lang, x)) }))

export type Node = { id: string; level: string; title: string; short: string; question: string; boss: boolean; main: boolean }
const toNode = (l: Level, main: boolean): Node => ({
  id: l.id, level: l.data.level, title: l.data.title, short: l.data.short ?? l.data.title,
  question: smart(l.data.question), boss: !!l.data.boss, main,
})

export async function homeData(lang: Lang = 'en') {
  const all = await allLevels(lang)
  const t = (s: string) => tr(lang, s)
  const main = (part: Level['data']['part']) => all.filter((l) => l.data.part === part && !l.data.branch).map((l) => toNode(l, true))
  const branch = (b: keyof typeof BRANCH_NAME) => all.filter((l) => l.data.branch === b).map((l) => toNode(l, false))
  return {
    foundations: main('foundations'),
    theory: main('theory'),
    branches: {
      internals: { name: t(BRANCH_NAME.internals), note: t(BRANCH_NOTE.internals), after: 'backprop', levels: branch('internals') },
      classic: { name: t(BRANCH_NAME.classic), note: t(BRANCH_NOTE.classic), after: 'probability', levels: branch('classic') },
      diffusion: { name: t(BRANCH_NAME.diffusion), note: t(BRANCH_NOTE.diffusion), after: 'transformer-parts', levels: branch('diffusion') },
    },
    // side trips, placed where each level opens (lib/nav.ts): one group per (main level, branch)
    trips: (() => {
      const seen = new Set<string>()
      return placement(all.map((l) => ({ ...l, ...navItem(l) }))).flatMap((p) => p.trips.map((b) => {
        const key = b.branch as keyof typeof BRANCH_NOTE
        const first = !seen.has(key)
        seen.add(key)
        return {
          key, name: t(BRANCH_NAME[key]), note: first ? t(BRANCH_NOTE[key]) : undefined, first,
          after: p.main.id, afterLevel: p.main.data.level,
          levels: b.levels.map((l) => toNode(l, false)),
        }
      }))
    })(),
    index: await levelIndex(lang),
    written: all.length,
  }
}
