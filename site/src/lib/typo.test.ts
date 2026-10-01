import { describe, expect, it } from 'vitest'
import { smart, smartExercise } from './typo'

describe('smart quotes', () => {
  it('curls double and single quotes', () => {
    expect(smart('How does one word "look at" others?')).toBe('How does one word “look at” others?')
    expect(smart("it's the model's turn")).toBe('it’s the model’s turn')
    expect(smart("'quoted'")).toBe('‘quoted’')
  })
  it('leaves code alone', () => {
    expect(smart('type `x = "a"` then "go"')).toBe('type `x = "a"` then “go”')
  })
  it('only touches reader-facing exercise text', () => {
    const ex = smartExercise({ type: 'code', prompt: 'Say "hi"', template: 'print("hi")', hints: [{ when: { any: true }, say: "don't" }] })
    expect(ex.prompt).toBe('Say “hi”')
    expect(ex.template).toBe('print("hi")')
    expect(ex.hints[0].say).toBe('don’t')
  })
})
