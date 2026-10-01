import { describe, expect, it } from 'vitest'
import { gradeCode, gradeNumber, gradeShape, parseShape } from './grade'
import type { CodeEx, NumberEx, ShapeEx } from './quiz'

const numEx: NumberEx = {
  type: 'number', prompt: 'scores[2][0]?', answer: 1, tol: 0,
  hints: [
    { when: { equals: 2 }, say: '那是 scores[2][2]。' },
    { when: { any: true }, say: 'scores[i][j] = X[i]·X[j]。' },
  ],
}

describe('数字填空', () => {
  it('对了就是对了', () => expect(gradeNumber(numEx, ' 1 ').ok).toBe(true))
  it('按错值给对应提示', () => expect(gradeNumber(numEx, '2').hint).toBe('那是 scores[2][2]。'))
  it('别的错值走兜底提示', () => expect(gradeNumber(numEx, '7').hint).toBe('scores[i][j] = X[i]·X[j]。'))
  it('空着不算错值', () => expect(gradeNumber(numEx, '').hint).toMatch(/number/))
  it('容差生效', () =>
    expect(gradeNumber({ ...numEx, answer: 0.2483, tol: 0.001 }, '0.248').ok).toBe(true))
})

describe('形状填空', () => {
  const ex: ShapeEx = {
    type: 'shape', prompt: '形状?', answer: [3, 3],
    hints: [{ when: { shape: [2, 2] }, say: '写反了。' }],
  }
  it('三种写法都认', () => {
    for (const s of ['3,3', '(3, 3)', '3 3']) expect(gradeShape(ex, s).ok).toBe(true)
  })
  it('按错形状给提示', () => expect(gradeShape(ex, '(2,2)').hint).toBe('写反了。'))
  it('解析', () => expect(parseShape('(3, 4)')).toEqual([3, 4]))
})

describe('代码填空', () => {
  const ex: CodeEx = {
    type: 'code', prompt: '补全', template: 'x = ____',
    tests: [
      { expr: 'list(attention(X,2).shape)', expect: [3, 3] },
      { expr: 'attention(X,2)[2].tolist()', expect: [0.2483, 0.2483, 0.5035], tol: 0.001 },
    ],
    hints: [
      { when: { error: 'not aligned' }, say: '忘了转置。' },
      { when: { testFailed: 1 }, say: '形状对了,值不对。' },
    ],
  }

  it('全过', () => {
    const r = gradeCode(ex, { stdout: 'scores', values: [{ value: [3, 3] }, { value: [0.2483, 0.2483, 0.5035] }] })
    expect(r.ok).toBe(true)
    expect(r.stdout).toBe('scores')
  })

  it('整段报错 → 按报错给提示', () => {
    const r = gradeCode(ex, { stdout: '', error: 'ValueError: shapes not aligned', values: [] })
    expect(r.ok).toBe(false)
    expect(r.hint).toBe('忘了转置。')
  })

  it('第二条测试不过 → 按序号给提示', () => {
    const r = gradeCode(ex, { stdout: '', values: [{ value: [3, 3] }, { value: [0.3, 0.3, 0.4] }] })
    expect(r.ok).toBe(false)
    expect(r.tests![0].ok).toBe(true)
    expect(r.hint).toBe('形状对了,值不对。')
  })

  it('容差:0.248 应该算对', () => {
    const r = gradeCode(ex, { stdout: '', values: [{ value: [3, 3] }, { value: [0.248, 0.248, 0.5035] }] })
    expect(r.ok).toBe(true)
  })
})
