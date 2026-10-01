import { describe, expect, it } from 'vitest'
import { defaultTestOut, exercisesBySection, testOutStatus } from './testout'

const body = `
intro <Predict id="p0" />
## 1. One
<Blank id="a1" />
<Blank id="a2" />
<Predict id="p1" />
## 2. Two
<Gate requires="a2">
<Blank id="b1" />
<CodeBlank id="code" />
</Gate>
## 3. Three
<Predict id="p3" />
## 4. Four
<Blank id="d1" /> <Blank id="d2" />
## 5. Five
<CodeBlank id="check" />
`
const types: Record<string, string> = { p0: 'predict', a1: 'number', a2: 'shape', p1: 'predict', b1: 'number', code: 'code', p3: 'predict', d1: 'number', d2: 'number', check: 'code' }

describe('test-out', () => {
  it('groups quiz ids by section', () => {
    expect(exercisesBySection(body)).toEqual([['p0'], ['a1', 'a2', 'p1'], ['b1', 'code'], ['p3'], ['d1', 'd2'], ['check']])
  })
  it('defaults to the checkpoint plus two section-ending questions, spread out, no predicts', () => {
    // last non-predict per section: a2, code, d2 → spread over three → a2 and d2
    expect(defaultTestOut(body, types, 'check')).toEqual(['a2', 'd2', 'check'])
  })
  it('takes what there is on a short level, and skips a missing checkpoint', () => {
    expect(defaultTestOut('<Blank id="x" />\n## 1. A\n<Blank id="y" />', { x: 'number', y: 'number' }, 'y')).toEqual(['x', 'y'])
    expect(defaultTestOut('<Blank id="x" />', { x: 'number' }, 'gone')).toEqual(['x'])
  })
  it('is complete only when every question is solved without the answer shown', () => {
    const ids = ['a', 'b']
    expect(testOutStatus('m', ids, { 'm/a': {} })).toMatchObject({ solved: 1, complete: false })
    expect(testOutStatus('m', ids, { 'm/a': {}, 'm/b': { shown: true } })).toMatchObject({ solved: 1, shown: 1, complete: false })
    expect(testOutStatus('m', ids, { 'm/a': {}, 'm/b': {}, 'x/a': {} })).toMatchObject({ solved: 2, complete: true })
    expect(testOutStatus('m', [], {}).complete).toBe(false)
  })
})
