import { createHash } from 'node:crypto'
import { describe, expect, it } from 'vitest'
import { gradeCode, hashOk } from './grade'
import type { CodeEx } from './quiz'
import { sha256Hex } from './sha256'

const node = (s: string) => createHash('sha256').update(s, 'utf8').digest('hex')

describe('sha256Hex', () => {
  it('和 Node 的 sha256 一致(含空串、多块、非 ASCII)', () => {
    for (const s of ['', 'abc', 'llm-by-hand/U5/0.980', 'x'.repeat(55), 'y'.repeat(64), 'z'.repeat(200), 'é√∂ 中'])
      expect(sha256Hex(s)).toBe(node(s))
  })
})

describe('哈希校验在主线程', () => {
  const ex: CodeEx = {
    type: 'code', prompt: '', template: 'line = "____"',
    tests: [
      { expr: 'a', sha256: node('secret').slice(0, 16) },
      { expr: 'b', sha256Pair: true },
    ],
  }
  const pair = (t: string) => [t, node(t).slice(0, 8)]

  it('原像对、校验码对 → 过', () => {
    expect(gradeCode(ex, { stdout: '', values: [{ value: 'secret' }, { value: pair('U5 0.980') }] }).ok).toBe(true)
  })
  it('原像错 → 不过,而且结果里没有期望的哈希', () => {
    const r = gradeCode(ex, { stdout: '', values: [{ value: 'guess' }, { value: pair('U5 0.980') }] })
    expect(r.ok).toBe(false)
    expect(JSON.stringify(r)).not.toContain(node('secret').slice(0, 16))
  })
  it('校验码太短、不是十六进制、或对不上 → 不过', () => {
    expect(hashOk({ sha256Pair: true }, ['t', ''])).toBe(false)
    expect(hashOk({ sha256Pair: true }, ['t', node('t').slice(0, 4)])).toBe(false)
    expect(hashOk({ sha256Pair: true }, ['t', 'zzzzzzzz'])).toBe(false)
    expect(hashOk({ sha256Pair: true }, ['t', node('u').slice(0, 8)])).toBe(false)
    expect(hashOk({ sha256: node('t').slice(0, 8) }, 5)).toBe(false)
  })
})
