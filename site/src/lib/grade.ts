/** 判卷 + 提示匹配。三种题走三条路,提示按 YAML 里的顺序第一条命中的生效。 */
import { allClose } from './num'
import { sha256Hex } from './sha256'
import type { CodeEx, Exercise, Hint, HintWhen, NumberEx, ShapeEx } from './quiz'

export type TestResult = { ok: boolean; expect: unknown; got: unknown; error?: string; say?: string; hashed?: boolean }
export type GradeResult = {
  ok: boolean
  hint?: string
  stdout?: string
  error?: string
  tests?: TestResult[]
}

function matchOne(w: HintWhen, ctx: MatchCtx): boolean {
  if (w.any) return true
  if (w.equals !== undefined) return typeof ctx.value === 'number' && Math.abs(ctx.value - w.equals) < 1e-9
  if (w.shape !== undefined) return Array.isArray(ctx.value) && allClose(ctx.value, w.shape, 0)
  if (w.error !== undefined) return !!ctx.error && new RegExp(w.error).test(ctx.error)
  if (w.testFailed !== undefined) return ctx.failedIndex === w.testFailed
  return false
}

type MatchCtx = { value?: unknown; error?: string; failedIndex?: number }

export function pickHint(hints: Hint[] | undefined, ctx: MatchCtx, miss = 1): string | undefined {
  const say = hints?.find((h) => matchOne(h.when, ctx))?.say
  if (Array.isArray(say)) return say[Math.min(Math.max(miss, 1), say.length) - 1]
  return say
}

export function gradeNumber(ex: NumberEx, raw: string, miss = 1): GradeResult {
  const v = Number(raw.trim())
  if (raw.trim() === '' || Number.isNaN(v)) return { ok: false, hint: 'Enter a number.' }
  const ok = Math.abs(v - ex.answer) <= (ex.tol ?? 0)
  return ok ? { ok } : { ok, hint: pickHint(ex.hints, { value: v }, miss) }
}

/** 接受 "3,4" / "(3, 4)" / "3 4" 三种写法 */
export function parseShape(raw: string): number[] | null {
  const nums = raw.match(/-?\d+/g)
  return nums && nums.length ? nums.map(Number) : null
}

export function gradeShape(ex: ShapeEx, raw: string, miss = 1): GradeResult {
  const v = parseShape(raw)
  if (!v) return { ok: false, hint: 'Enter a shape like (3, 4).' }
  const ok = allClose(v, ex.answer, 0)
  return ok ? { ok } : { ok, hint: pickHint(ex.hints, { value: v }, miss) }
}

/** 粘贴校验:哈希在主线程算,读者的 Python 改不了它 */
export function hashOk(t: { sha256?: string; sha256Pair?: boolean }, v: unknown): boolean {
  if (t.sha256 !== undefined) return typeof v === 'string' && t.sha256.length >= 8 && sha256Hex(v).startsWith(t.sha256)
  if (!Array.isArray(v) || v.length !== 2) return false
  const [text, code] = v
  return typeof text === 'string' && typeof code === 'string' && /^[0-9a-f]{8,}$/.test(code) && sha256Hex(text).startsWith(code)
}

/** 代码题:Python 那边只负责跑出值,比较和提示都在这里做,好写单元测试 */
export function gradeCode(
  ex: CodeEx,
  run: { stdout: string; error?: string; values: { value?: unknown; error?: string }[] },
  miss = 1,
): GradeResult {
  if (run.error) {
    return { ok: false, stdout: run.stdout, error: run.error, hint: pickHint(ex.hints, { error: run.error }, miss) }
  }
  const tests: TestResult[] = ex.tests.map((t, i) => {
    const r = run.values[i] ?? { error: 'This test did not run.' }
    if (t.sha256 !== undefined || t.sha256Pair) {
      // the expected hash never goes into the result, so the page can't show it
      return { ok: !r.error && hashOk(t, r.value), expect: undefined, got: undefined, error: r.error, say: t.say, hashed: true }
    }
    const ok = !r.error && allClose(r.value, t.expect, t.tol ?? 1e-6)
    return { ok, expect: t.expect, got: r.value, error: r.error, say: t.say }
  })
  const failedIndex = tests.findIndex((t) => !t.ok)
  const ok = failedIndex === -1
  return {
    ok,
    stdout: run.stdout,
    tests,
    hint: ok
      ? undefined
      : pickHint(ex.hints, { error: tests[failedIndex].error, failedIndex, value: tests[failedIndex].got }, miss),
  }
}

export function grade(ex: Exercise, raw: string, miss = 1): GradeResult {
  if (ex.type === 'number') return gradeNumber(ex, raw, miss)
  if (ex.type === 'shape') return gradeShape(ex, raw, miss)
  return { ok: false, hint: 'This exercise type is graded elsewhere.' }
}
