/**
 * Helpers for levels 11–12: bigram counting, perplexity, a tiny neural bigram, and BPE.
 * Every function mirrors the Python in the levels' demo.py, so the labs and the demos print the same numbers.
 */

/** counts[i][j] = how many times token j directly follows token i */
export function bigramCounts(tokens: string[], vocab: string[]): number[][] {
  const id = new Map(vocab.map((w, i) => [w, i]))
  const C = vocab.map(() => vocab.map(() => 0))
  for (let k = 0; k + 1 < tokens.length; k++) C[id.get(tokens[k])!][id.get(tokens[k + 1])!]++
  return C
}

/** Each row divided by its total. A row with no counts stays all zero. */
export function rowProbs(C: number[][]): number[][] {
  return C.map((r) => {
    const s = r.reduce((a, b) => a + b, 0)
    return r.map((v) => (s ? v / s : 0))
  })
}

/** exp(average of −log p). Infinity if any p is 0. */
export function perplexity(ps: number[]): number {
  if (ps.some((p) => p <= 0)) return Infinity
  return Math.exp(-ps.reduce((a, p) => a + Math.log(p), 0) / ps.length)
}

/** Perplexity of a token stream under a next-token probability table P. */
export function streamPerplexity(tokens: string[], vocab: string[], P: number[][]): number {
  const id = new Map(vocab.map((w, i) => [w, i]))
  const ps: number[] = []
  for (let k = 0; k + 1 < tokens.length; k++) ps.push(P[id.get(tokens[k])!][id.get(tokens[k + 1])!])
  return perplexity(ps)
}

export function softmaxRow(z: number[]): number[] {
  const m = Math.max(...z)
  const e = z.map((v) => Math.exp(v - m))
  const s = e.reduce((a, b) => a + b, 0)
  return e.map((v) => v / s)
}

/**
 * One full-batch gradient step for the neural bigram: P = softmax(onehot(prev) @ W), loss = mean cross-entropy.
 * With counts C (total N pairs), dLoss/dW[i] = (rowsum_i · softmax(W[i]) − C[i]) / N.
 * Returns the loss before the step.
 */
export function neuralBigramStep(W: number[][], C: number[][], lr: number): number {
  const N = C.flat().reduce((a, b) => a + b, 0)
  let loss = 0
  for (let i = 0; i < W.length; i++) {
    const n = C[i].reduce((a, b) => a + b, 0)
    if (!n) continue
    const p = softmaxRow(W[i])
    for (let j = 0; j < W.length; j++) {
      if (C[i][j]) loss -= (C[i][j] * Math.log(p[j])) / N
      W[i][j] -= (lr * (n * p[j] - C[i][j])) / N
    }
  }
  return loss
}

// ---- BPE ----------------------------------------------------------------------------

export type Word = { w: string; n: number }
export type Pair = { a: string; b: string; count: number }

/** Count adjacent pairs, weighted by word frequency. Order: highest count first; ties keep first-seen order. */
export function pairCounts(segs: string[][], words: Word[]): Pair[] {
  const m = new Map<string, Pair>()
  segs.forEach((s, k) => {
    for (let i = 0; i + 1 < s.length; i++) {
      const key = s[i] + '\u0000' + s[i + 1]
      const p = m.get(key) ?? { a: s[i], b: s[i + 1], count: 0 }
      p.count += words[k].n
      m.set(key, p)
    }
  })
  return [...m.values()].sort((x, y) => y.count - x.count) // stable sort keeps first-seen order on ties
}

/** Replace every adjacent (a, b) in one segmented word with a + b. */
export function mergePair(seg: string[], a: string, b: string): string[] {
  const out: string[] = []
  for (let i = 0; i < seg.length; i++) {
    if (i + 1 < seg.length && seg[i] === a && seg[i + 1] === b) {
      out.push(a + b)
      i++
    } else out.push(seg[i])
  }
  return out
}

export type BpeStep = { segs: string[][]; pairs: Pair[]; vocab: string[]; totalTokens: number }

/** Run up to `steps` merges. history[k] is the state after k merges (history[0] = characters). */
export function bpeTrain(words: Word[], steps: number): { merges: [string, string][]; history: BpeStep[] } {
  let segs = words.map((x) => [...x.w])
  const vocab = [...new Set(words.flatMap((x) => [...x.w]))].sort()
  const merges: [string, string][] = []
  const snap = (): BpeStep => ({
    segs: segs.map((s) => [...s]),
    pairs: pairCounts(segs, words),
    vocab: [...vocab],
    totalTokens: segs.reduce((a, s, k) => a + s.length * words[k].n, 0),
  })
  const history = [snap()]
  for (let t = 0; t < steps; t++) {
    const best = history[history.length - 1].pairs[0]
    if (!best || best.count < 2) break
    merges.push([best.a, best.b])
    vocab.push(best.a + best.b)
    segs = segs.map((s) => mergePair(s, best.a, best.b))
    history.push(snap())
  }
  return { merges, history }
}

/** Encode a new word: start from characters, apply the learned merges in the order they were learned. */
export function bpeEncode(word: string, merges: [string, string][]): string[] {
  let s = [...word]
  for (const [a, b] of merges) s = mergePair(s, a, b)
  return s
}

/** The "generated words" BPE corpus: stems × suffixes, counts from a fixed rule (same as tokenization/demo.py). */
export const STEMS = ['play', 'walk', 'talk', 'jump', 'look', 'cook', 'work', 'park']
export const SUFFIXES = ['', 's', 'ed', 'ing', 'er']
export function generatedWords(): Word[] {
  const out: Word[] = []
  STEMS.forEach((st, si) =>
    SUFFIXES.forEach((sf, fi) => out.push({ w: st + sf, n: 1 + ((st.length * 7 + fi * 5 + si * 3) % 9) })),
  )
  return out
}
