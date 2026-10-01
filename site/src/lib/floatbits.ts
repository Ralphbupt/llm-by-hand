/**
 * Floating-point formats by hand: float32, float16, bfloat16.
 * A normal number is (−1)^sign × (1 + mant / 2^M) × 2^(exp − bias). Rounding is to the nearest
 * representable number, ties to the even one, as NumPy and PyTorch do. Matches
 * content/1-foundations/numbers-in-a-computer/demo.py.
 */
export type Fmt = 'float32' | 'float16' | 'bfloat16'
export const FORMATS: Record<Fmt, { E: number; M: number }> = {
  float32: { E: 8, M: 23 },
  float16: { E: 5, M: 10 },
  bfloat16: { E: 8, M: 7 },
}
export type Bits = { sign: number; exp: number; mant: number }

const bias = (f: Fmt) => 2 ** (FORMATS[f].E - 1) - 1

function roundHalfEven(q: number): number {
  const fl = Math.floor(q)
  const d = q - fl
  if (d > 0.5) return fl + 1
  if (d < 0.5) return fl
  return fl % 2 === 0 ? fl : fl + 1
}

/** The bit fields of the format’s nearest number to v. */
export function encode(v: number, f: Fmt): Bits {
  const { E, M } = FORMATS[f]
  const maxExp = 2 ** E - 1
  if (Number.isNaN(v)) return { sign: 0, exp: maxExp, mant: 2 ** (M - 1) }
  const sign = v < 0 || Object.is(v, -0) ? 1 : 0
  const a = Math.abs(v)
  if (a === Infinity) return { sign, exp: maxExp, mant: 0 }
  if (a === 0) return { sign, exp: 0, mant: 0 }
  const b = bias(f)
  const emin = 1 - b
  let e = Math.floor(Math.log2(a))
  while (2 ** e > a) e--
  while (2 ** (e + 1) <= a) e++
  if (e < emin) {
    // subnormal: steps of 2^(emin − M)
    const n = roundHalfEven(a / 2 ** (emin - M))
    if (n >= 2 ** M) return { sign, exp: 1, mant: 0 }
    return { sign, exp: 0, mant: n }
  }
  let n = roundHalfEven(a / 2 ** (e - M))
  if (n >= 2 ** (M + 1)) { e++; n = 2 ** M }
  if (e > b) return { sign, exp: maxExp, mant: 0 }       // too big: infinity
  return { sign, exp: e + b, mant: n - 2 ** M }
}

/** The value of a bit pattern. */
export function decode(bits: Bits, f: Fmt): number {
  const { E, M } = FORMATS[f]
  const s = bits.sign ? -1 : 1
  if (bits.exp === 2 ** E - 1) return bits.mant ? NaN : s * Infinity
  if (bits.exp === 0) return s * (bits.mant / 2 ** M) * 2 ** (1 - bias(f))
  return s * (1 + bits.mant / 2 ** M) * 2 ** (bits.exp - bias(f))
}

/** v rounded to the format. */
export const roundTo = (v: number, f: Fmt) => decode(encode(v, f), f)

/** Facts about a format: the largest number, the smallest normal one, the gap after 1. */
export function facts(f: Fmt) {
  const { M } = FORMATS[f]
  const b = bias(f)
  return { largest: (2 - 2 ** -M) * 2 ** b, smallestNormal: 2 ** (1 - b), gapAfter1: 2 ** -M, bias: b, perOctave: 2 ** M }
}

/** Short display: inf, nan, or up to `digits` significant digits. */
export function show(v: number, digits = 4): string {
  if (Number.isNaN(v)) return 'nan'
  if (v === Infinity) return 'inf'
  if (v === -Infinity) return '−inf'
  if (v === 0) return '0'
  const a = Math.abs(v)
  const t = a >= 1e5 || a < 1e-4 ? v.toExponential(digits - 1) : String(Number(v.toPrecision(digits)))
  return t.replace('-', '−')
}
