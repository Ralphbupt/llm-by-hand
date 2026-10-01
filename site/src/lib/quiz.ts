/** Exercise types + loading them from YAML (build time only). */
import fs from 'node:fs'
import path from 'node:path'
import { load as parseYaml } from 'js-yaml'
import { smartExercise } from './typo'

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

const cache = new Map<string, { mtime: number; data: Record<string, Exercise> }>()
const CONTENT = path.join(process.cwd(), '..', 'content')

/** Find content/<part>/<slug>/ for a slug (folder names are unique across parts). */
function lessonDir(slug: string): string | null {
  for (const part of fs.readdirSync(CONTENT)) {
    const d = path.join(CONTENT, part, slug)
    if (fs.existsSync(d)) return d
  }
  return null
}

/** Load a level's exercises; a missing file returns {} so a page can be written before its questions. */
export function loadExercises(slug: string): Record<string, Exercise> {
  const dir = lessonDir(slug)
  const p = dir && path.join(dir, 'exercises.yaml')
  if (!p || !fs.existsSync(p)) return {}
  // re-read when the file changes, so edits show up in the dev server without a restart
  const mtime = fs.statSync(p).mtimeMs
  const hit = cache.get(slug)
  if (hit && hit.mtime === mtime) return hit.data
  const raw = (parseYaml(fs.readFileSync(p, 'utf8')) ?? {}) as Record<string, Exercise>
  // `reference:` is a boss's answer, used only by scripts/check_exercises.py: never sent to the page (no "Show answer")
  const data = Object.fromEntries(Object.entries(raw).map(([k, v]) => {
    const { reference: _, ...rest } = v as Exercise & { reference?: string }
    if (rest.hints) rest.hints = rest.hints.map((h) => ({ when: h.when, say: h.say }))
    return [k, smartExercise(rest as Exercise)]
  })) as Record<string, Exercise>
  cache.set(slug, { mtime, data })
  return data
}

/** /learn/attention/ → attention */
export function slugFromPath(pathname: string): string {
  return pathname.replace(/^\/+|\/+$/g, '').split('/').pop() ?? ''
}

export function getExercise(pathname: string, id: string): Exercise | null {
  return loadExercises(slugFromPath(pathname))[id] ?? null
}
