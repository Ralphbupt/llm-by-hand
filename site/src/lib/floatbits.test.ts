import { describe, expect, it } from 'vitest'
import { decode, encode, facts, roundTo } from './floatbits'

// numbers printed by content/1-foundations/numbers-in-a-computer/demo.py
describe('float formats (matches demo.py)', () => {
  it('decodes float16 0 10001 1000000000 as 6', () => {
    expect(decode({ sign: 0, exp: 0b10001, mant: 0b1000000000 }, 'float16')).toBe(6)
    expect(encode(6, 'float16')).toEqual({ sign: 0, exp: 17, mant: 512 })
  })
  it('stores 0.1 in each format', () => {
    expect(roundTo(0.1, 'float32')).toBeCloseTo(0.10000000149, 11)
    expect(roundTo(0.1, 'float16')).toBeCloseTo(0.099975585938, 11)
    expect(roundTo(0.1, 'bfloat16')).toBeCloseTo(0.10009765625, 11)
    expect(encode(0.1, 'float16')).toEqual({ sign: 0, exp: 0b01011, mant: 0b1001100110 })
  })
  it('rounds to the nearest, ties to even', () => {
    expect(roundTo(256.75, 'bfloat16')).toBe(256)
    expect(roundTo(257, 'bfloat16')).toBe(256)
    expect(roundTo(257.5, 'bfloat16')).toBe(258)
    expect(roundTo(1.001, 'bfloat16')).toBe(1)
  })
  it('overflows and underflows like numpy', () => {
    expect(roundTo(90000, 'float16')).toBe(Infinity)
    expect(roundTo(Math.exp(11), 'float16')).toBe(59872)
    expect(roundTo(Math.exp(12), 'float16')).toBe(Infinity)
    expect(roundTo(Math.exp(89), 'float32')).toBe(Infinity)
    expect(roundTo(1e-8, 'float16')).toBe(0)
    expect(roundTo(2 ** -24, 'float16')).toBe(2 ** -24)
  })
  it('knows the range of each format', () => {
    expect(facts('float16').largest).toBe(65504)
    expect(facts('bfloat16').largest).toBeCloseTo(3.3895313892515355e38, -30)
    expect(facts('bfloat16').perOctave).toBe(128)
  })
})
