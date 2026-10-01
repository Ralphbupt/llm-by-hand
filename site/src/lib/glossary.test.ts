import { describe, expect, it } from 'vitest'
import { firstUses, termId, type Term } from './glossary'

const terms: Term[] = [
  { term: 'attention', def: '', level: 'attention' },
  { term: 'multi-head attention', aliases: ['heads'], def: '', level: 'attention' },
  { term: 'entropy', def: '', level: 'probability' },
  { term: 'cross-entropy', def: '', level: 'probability' },
  { term: 'matrix', aliases: ['matrices'], def: '', level: 'matrices' },
  { term: 'value', def: '', level: 'attention', mark: false },
  { term: 'ReLU', def: '', level: 'activations' },
]

describe('firstUses', () => {
  it('marks only the first use of each term, across chunks', () => {
    const hits = firstUses(['Attention is all.', 'More attention here.'], terms)
    expect(hits).toEqual([{ chunk: 0, start: 0, end: 9, term: 0 }])
  })
  it('prefers the longer term, and the shorter one still gets its own first standalone use', () => {
    const hits = firstUses(['Use multi-head attention. Then attention again.'], terms)
    expect(hits.map((h) => terms[h.term].term)).toEqual(['multi-head attention', 'attention'])
    expect(hits[1].start).toBe('Use multi-head attention. Then '.length)
  })
  it('does not find a term inside a hyphenated word', () => {
    const hits = firstUses(['The cross-entropy loss, then entropy.'], terms)
    expect(hits.map((h) => terms[h.term].term)).toEqual(['cross-entropy', 'entropy'])
  })
  it('matches aliases and plurals, case-insensitively, whole words only', () => {
    expect(firstUses(['two matrices'], terms).map((h) => terms[h.term].term)).toEqual(['matrix'])
    expect(firstUses(['relus and ReLU'], terms)[0].start).toBe(0)
    expect(firstUses(['matrixes? no: amatrix'], terms).length).toBe(1)
  })
  it('skips terms marked mark: false', () => {
    expect(firstUses(['the value is 3'], terms)).toEqual([])
  })
  it('ids are stable', () => {
    expect(termId('Multi-head attention')).toBe('term-multi-head-attention')
  })
})
