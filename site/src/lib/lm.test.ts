import { describe, expect, it } from 'vitest'
import {
  bigramCounts, bpeEncode, bpeTrain, mergePair, neuralBigramStep, perplexity, rowProbs, streamPerplexity,
} from './lm'

// the hand example from level 11
const tiny = 'the cat sat . the dog sat . a cat ran .'.split(' ')
const V = ['the', 'a', 'cat', 'dog', 'sat', 'ran', '.']

describe('bigram (numbers from language-models/demo.py)', () => {
  it('counts and probabilities', () => {
    const C = bigramCounts(tiny, V)
    expect(C[4][6]).toBe(2) // sat → .
    expect(rowProbs(C)[2][4]).toBe(0.5) // P(sat | cat)
    expect(rowProbs(C)[1][3]).toBe(0) // P(dog | a)
  })
  it('perplexity of "the cat sat ."', () => {
    expect(perplexity([0.5, 0.5, 1])).toBeCloseTo(1.5874, 4)
    expect(perplexity([0.1, 0.1])).toBeCloseTo(10, 9)
    expect(perplexity([0.5, 0])).toBe(Infinity)
    const P = rowProbs(bigramCounts(tiny, V))
    expect(streamPerplexity('the cat sat .'.split(' '), V, P)).toBeCloseTo(1.5874, 4)
  })
  it('neural bigram moves toward the count probabilities', () => {
    const C = bigramCounts(tiny, V)
    const W = V.map(() => V.map(() => 0))
    const first = neuralBigramStep(W, C, 1)
    expect(first).toBeCloseTo(Math.log(7), 9) // all-zero W = uniform over 7 tokens
    let last = first
    for (let k = 0; k < 2000; k++) last = neuralBigramStep(W, C, 5)
    expect(last).toBeLessThan(first)
  })
})

describe('BPE (hand example from tokenization/demo.py)', () => {
  const words = [{ w: 'cat', n: 4 }, { w: 'cats', n: 2 }, { w: 'hat', n: 3 }, { w: 'hats', n: 1 }]
  it('first counts and merges', () => {
    const { merges, history } = bpeTrain(words, 4)
    expect(history[0].pairs[0]).toEqual({ a: 'a', b: 't', count: 10 })
    expect(merges.map((m) => m.join('+'))).toEqual(['a+t', 'c+at', 'h+at', 'cat+s'])
    expect(history[2].pairs.find((p) => p.a === 'c' && p.b === 'at')).toBeUndefined()
    expect(history[1].pairs[0]).toEqual({ a: 'c', b: 'at', count: 6 })
    expect(history[0].totalTokens).toBe(4 * 3 + 2 * 4 + 3 * 3 + 1 * 4)
  })
  it('encodes words it never saw', () => {
    const { merges } = bpeTrain(words, 3)
    expect(bpeEncode('cats', merges)).toEqual(['cat', 's'])
    expect(bpeEncode('that', merges)).toEqual(['t', 'hat'])
    expect(bpeEncode('chat', merges)).toEqual(['c', 'hat'])
  })
  it('mergePair', () => {
    expect(mergePair(['a', 'a', 'a'], 'a', 'a')).toEqual(['aa', 'a'])
  })
})

describe('generated BPE words', () => {
  it('first merges match the demo', async () => {
    const { generatedWords } = await import('./lm')
    const w = generatedWords()
    expect(w.length).toBe(40)
    const { merges, history } = bpeTrain(w, 40)
    // printed by tokenization/demo.py
    expect(merges.slice(0, 5).map((m) => m.join('+'))).toEqual(['k+e', 'a+l', 'o+o', 'i+n', 'in+g'])
    expect(history[0].vocab.length).toBe(19)
    expect(history[0].totalTokens).toBe(1068)
    expect(history[40].vocab.length).toBe(59)
    expect(history[40].totalTokens).toBe(263)
  })
})

describe('the generated stories (numbers printed by language-models/demo.py)', () => {
  it('counting and neural perplexity on the kept-aside stories', async () => {
    const d = (await import('../../public/data/language-models/corpus.json')).default as {
      vocab: string[]; train: string[]; heldout: string[]
    }
    const tr = d.train.join(' ').split(' ')
    const ho = d.heldout.join(' ').split(' ')
    expect(tr.length).toBe(853)
    const C = bigramCounts(tr, d.vocab)
    expect(streamPerplexity(ho, d.vocab, rowProbs(C))).toBeCloseTo(2.016, 3)
    const W = d.vocab.map(() => d.vocab.map(() => 0))
    for (let k = 0; k < 300; k++) neuralBigramStep(W, C, 5)
    const { softmaxRow } = await import('./lm')
    expect(streamPerplexity(ho, d.vocab, W.map(softmaxRow))).toBeCloseTo(2.037, 3)
  })
})
