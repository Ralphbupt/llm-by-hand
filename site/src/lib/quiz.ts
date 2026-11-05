/** Exercise types + loading them from YAML (build time only). */
import fs from 'node:fs'
import path from 'node:path'
import { load as parseYaml } from 'js-yaml'
import { smartExercise } from './typo'
import { langOf, type Lang } from './i18n'

export type HintWhen = {
  any?: boolean
  equals?: number            // 填了这个值
  shape?: number[]           // 填了这个形状
  error?: string             // 运行报错,正则匹配异常信息
  testFailed?: number        // 第几条测试没过(从 0 数)
}
/** `say` may be a ladder: the 1st wrong try shows say[0], the 2nd say[1], … (the last repeats). Never put the full answer in a ladder; that's what Show answer is for. */
export type Hint = { when: HintWhen; say: string | string[] }
// A hint may also carry `wrong:` (a typical wrong fill that shows it), used only by scripts/hint_reach.py: stripped below.

/**
 * `warmup: false` keeps a question out of the warm-up (it needs its page or lab to make sense).
 * `run: local` marks a question answered by running code on the learner's computer (never in a warm-up).
 * `promptShort` is a shorter prompt (no formulas) shown in the test-out panel, where the page around it is not read.
 * `optional: true` marks a question the level clears without (an optional section, a Stuck or Deeper box): it never costs a star.
 */
type Base = { prompt: string; promptShort?: string; hints?: Hint[]; after?: string; warmup?: boolean; run?: 'browser' | 'local'; optional?: boolean }

export type NumberEx = Base & { type: 'number'; answer: number; tol?: number; unit?: string }
export type ShapeEx = Base & { type: 'shape'; answer: number[] }
/**
 * A code test compares the value of `expr` with `expect`. Two kinds of paste checks hash in the browser instead,
 * outside the learner's Python (which could replace hashlib): `sha256` = the value is a string whose SHA-256 hex
 * starts with this; `sha256Pair` = the value is [text, code] and the SHA-256 hex of text starts with code (8+ hex digits).
 * The page never shows the expected hash.
 */
export type CodeTest = { setup?: string; expr: string; expect?: unknown; tol?: number; say?: string; sha256?: string; sha256Pair?: boolean }
export type CodeEx = Base & { type: 'code'; template: string; tests: CodeTest[] }
/** A Predict with `answer` (index of the right option) is graded: a wrong pick counts as a miss. Without it, it's an ungraded guess. */
export type PredictEx = Base & { type: 'predict'; options: string[]; reveal: string; answer?: number }

export type Exercise = NumberEx | ShapeEx | CodeEx | PredictEx

const cache = new Map<string, { mtime: number; data: Record<string, any> }>()
const CONTENT = path.join(process.cwd(), '..', 'content')

/** Find content/<part>/<slug>/ for a slug (folder names are unique across parts). */
function lessonDir(slug: string): string | null {
  for (const part of fs.readdirSync(CONTENT)) {
    const d = path.join(CONTENT, part, slug)
    if (fs.existsSync(d)) return d
  }
  return null
}

/**
 * A translation of a level's questions: exercises.<lang>.yaml holds only the text of each question, keyed by the same
 * ids. Answers, tests and hint conditions stay in exercises.yaml, so they can never drift apart.
 *   prompt, promptShort, after, reveal, unit, template: replace the English
 *   options: the options, in the same order
 *   hints: one `say` per hint, in the same order (a string, or a ladder list)
 *   tests: one `say` per test, in the same order
 * Anything left out stays English.
 */
type Overlay = Partial<Record<'prompt' | 'promptShort' | 'after' | 'reveal' | 'unit' | 'template', string>> & {
  options?: string[]; hints?: (string | string[] | null)[]; tests?: (string | null)[]
}

function readYaml(p: string, key: string): Record<string, any> {
  if (!fs.existsSync(p)) return {}
  // re-read when the file changes, so edits show up in the dev server without a restart
  const mtime = fs.statSync(p).mtimeMs
  const hit = cache.get(key)
  if (hit && hit.mtime === mtime) return hit.data
  const data = (parseYaml(fs.readFileSync(p, 'utf8')) ?? {}) as Record<string, any>
  cache.set(key, { mtime, data })
  return data
}

function applyOverlay(ex: Exercise, o: Overlay | undefined): Exercise {
  if (!o) return ex
  const out: any = { ...ex }
  for (const k of ['prompt', 'promptShort', 'after', 'reveal', 'unit', 'template'] as const) if (typeof o[k] === 'string') out[k] = o[k]
  if (o.options && out.options) out.options = out.options.map((x: string, i: number) => o.options![i] ?? x)
  if (o.hints && out.hints) out.hints = out.hints.map((h: Hint, i: number) => (o.hints![i] != null ? { ...h, say: o.hints![i] } : h))
  if (o.tests && out.tests) out.tests = out.tests.map((t: CodeTest, i: number) => (o.tests![i] != null ? { ...t, say: o.tests![i] } : t))
  return out
}

/** Does this level have its questions in `lang`? */
export function hasExerciseText(slug: string, lang: Lang): boolean {
  const dir = lessonDir(slug)
  return lang === 'en' || (!!dir && fs.existsSync(path.join(dir, `exercises.${lang}.yaml`)))
}

/** Load a level's exercises; a missing file returns {} so a page can be written before its questions. */
export function loadExercises(slug: string, lang: Lang = 'en'): Record<string, Exercise> {
  const dir = lessonDir(slug)
  if (!dir) return {}
  const raw = readYaml(path.join(dir, 'exercises.yaml'), slug) as Record<string, Exercise>
  const tr = lang === 'en' ? {} : (readYaml(path.join(dir, `exercises.${lang}.yaml`), `${slug}.${lang}`) as Record<string, Overlay>)
  // `reference:` is a boss's answer, used only by scripts/check_exercises.py: never sent to the page (no "Show answer")
  return Object.fromEntries(Object.entries(raw).map(([k, v]) => {
    const { reference: _, ...rest } = v as Exercise & { reference?: string }
    if (rest.hints) rest.hints = rest.hints.map((h) => ({ when: h.when, say: h.say }))
    return [k, smartExercise(applyOverlay(rest as Exercise, tr[k]))]
  })) as Record<string, Exercise>
}

/** /learn/attention/ → attention */
export function slugFromPath(pathname: string): string {
  return pathname.replace(/^\/+|\/+$/g, '').split('/').pop() ?? ''
}

export function getExercise(pathname: string, id: string): Exercise | null {
  return loadExercises(slugFromPath(pathname), langOf(pathname))[id] ?? null
}
