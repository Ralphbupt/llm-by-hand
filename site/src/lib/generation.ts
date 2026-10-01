/**
 * Level 18 helpers: turning one row of scores into a choice.
 * Every function matches content/2-theory/generation/demo.py.
 */

export function softmax(scores: number[], T = 1): number[] {
  const z = scores.map((s) => s / T)
  const m = Math.max(...z)
  const e = z.map((v) => Math.exp(v - m))
  const sum = e.reduce((a, b) => a + b, 0)
  return e.map((v) => v / sum)
}

/** Indices sorted by probability, largest first (ties keep their original order). */
export function order(probs: number[]): number[] {
  return probs.map((_, i) => i).sort((a, b) => probs[b] - probs[a] || a - b)
}

function renorm(probs: number[], keep: boolean[]): number[] {
  const kept = probs.map((p, i) => (keep[i] ? p : 0))
  const sum = kept.reduce((a, b) => a + b, 0)
  return kept.map((p) => p / sum)
}

export function topKKeep(probs: number[], k: number): boolean[] {
  const keep = probs.map(() => false)
  order(probs).slice(0, k).forEach((i) => (keep[i] = true))
  return keep
}

/** Keep a word while the words ranked above it add up to less than p. */
export function topPKeep(probs: number[], p: number): boolean[] {
  const keep = probs.map(() => false)
  let before = 0
  for (const i of order(probs)) {
    if (before < p) keep[i] = true
    before += probs[i]
  }
  return keep
}

export const topK = (probs: number[], k: number) => renorm(probs, topKKeep(probs, k))
export const topP = (probs: number[], p: number) => renorm(probs, topPKeep(probs, p))

/** Cumulative sums in sorted order, returned per original index. */
export function cumulative(probs: number[]): number[] {
  const out = probs.map(() => 0)
  let acc = 0
  for (const i of order(probs)) { acc += probs[i]; out[i] = acc }
  return out
}

export function sampleIndex(probs: number[], rand = Math.random): number {
  let r = rand()
  for (let i = 0; i < probs.length; i++) {
    r -= probs[i]
    if (r < 0) return i
  }
  return probs.length - 1
}

/** The counting model exported by demo.py --export: p(next | previous two words). */
export type Trigram = { vocab: string[]; mix: number; probs: number[][][]; n_words: number }

export const SLOTS = [['the'], ['cat', 'dog', 'bird'], ['sat', 'ran', 'slept'], ['on', 'in'], ['the'],
  ['mat', 'rug', 'roof', 'park'], ['.']]

/** Does every word sit in a slot our sentence rules allow? (text starts at slot 0) */
export const followsRules = (seq: string[]) => seq.every((w, i) => SLOTS[i % 7].includes(w))

export type Step = { context: [string, string]; scores: { word: string; logp: number; seen: number; score: number }[]; pick: string }

/** Greedy decoding with a repetition penalty: score = log p − penalty × (times already written). */
export function greedyWithPenalty(m: Trigram, start: string[], n: number, penalty: number) {
  const ix = new Map(m.vocab.map((w, i) => [w, i]))
  const out = [...start]
  const seen = m.vocab.map(() => 0)
  for (const w of out) seen[ix.get(w)!]++
  const steps: Step[] = []
  for (let t = 0; t < n; t++) {
    const row = m.probs[ix.get(out[out.length - 2])!][ix.get(out[out.length - 1])!]
    const scores = m.vocab.map((word, k) => ({ word, logp: Math.log(row[k]), seen: seen[k], score: Math.log(row[k]) - penalty * seen[k] }))
    let best = 0
    for (let k = 1; k < scores.length; k++) if (scores[k].score > scores[best].score) best = k
    steps.push({ context: [out[out.length - 2], out[out.length - 1]], scores, pick: m.vocab[best] })
    out.push(m.vocab[best])
    seen[best]++
  }
  return { words: out, steps }
}

/** Length of the shortest block that repeats from the start, or 0. */
export function repeatLength(words: string[]): number {
  for (let L = 1; 2 * L <= words.length; L++) {
    let ok = true
    for (let i = 0; i < L; i++) if (words[i] !== words[i + L]) { ok = false; break }
    if (ok) return L
  }
  return 0
}
