import { describe, expect, it } from 'vitest'
import { mdxToText, search, snippet, splitSections, type Doc } from './search'

const body = `import Blank from '@quiz/Blank.astro'

Intro about **attention** and $d_k$.

## 1. A weighted average

<AttentionLab />
Every word mixes the others. Uses \`softmax\`.

<Stuck q="Why is it symmetric?">
Because the dot product is symmetric.
</Stuck>

## 5. Why divide by √d_k

Large scores make softmax too sharp.

\`\`\`python
x = 1
\`\`\`
`

describe('splitSections', () => {
  const s = splitSections(body)
  it('splits at ## headings, with Astro-style anchors', () => {
    expect(s.map((x) => x.anchor)).toEqual(['', '1-a-weighted-average', '5-why-divide-by-d_k'])
  })
  it('keeps prose and the text of Stuck boxes, drops components and code', () => {
    expect(s[1].text).toContain('Every word mixes the others. Uses softmax.')
    expect(s[1].text).toContain('Why is it symmetric?')
    expect(s[1].text).not.toContain('AttentionLab')
    expect(s[2].text).not.toContain('x = 1')
    expect(s[0].text).toContain('d_k')
  })
  it('mdxToText drops imports and tags', () => {
    expect(mdxToText(`import X from 'y'\n<Gate requires="a">hi</Gate>`).trim()).toBe('hi')
  })
})

const docs: Doc[] = [
  { kind: 'level', slug: 'attention', level: '12', title: 'Attention', question: 'How does one word look at others?', url: '/learn/attention/',
    sections: [{ heading: '5. Why divide by √d_k', anchor: '5-why', text: 'Large scores make softmax too sharp.' }] },
  { kind: 'level', slug: 'probability', level: '8', title: 'Probability and sampling', question: 'How does a model roll the dice?', url: '/learn/probability/',
    sections: [{ heading: '2. How softmax works', anchor: '2-how', text: 'Softmax turns scores into probabilities. softmax again.' }] },
]

describe('search', () => {
  it('needs every word, ranks heading matches above text matches', () => {
    const r = search(docs, 'softmax')
    expect(r.map((x) => x.doc.slug)).toEqual(['probability', 'attention'])
    expect(search(docs, 'softmax sharp').map((x) => x.doc.slug)).toEqual(['attention'])
  })
  it('a title match wins', () => {
    expect(search(docs, 'attention')[0].doc.slug).toBe('attention')
  })
  it('ignores case and empty queries', () => {
    expect(search(docs, 'SOFTMAX').length).toBe(2)
    expect(search(docs, '   ')).toEqual([])
  })
  it('snippets highlight and escape', () => {
    expect(snippet('a <b> softmax c', ['softmax'])).toBe('a &lt;b&gt; <mark>softmax</mark> c')
  })
  it('ranks main levels above side trips, and the level a glossary card names first', () => {
    const lv = (slug: string, level: string, text: string): Doc => ({ kind: 'level', slug, level, title: slug, question: '', url: `/${slug}/`, sections: [{ heading: '', anchor: '', text }] })
    const side = lv('bits', 'U2', 'softmax softmax softmax')
    const main = lv('prob', '10', 'softmax softmax softmax')
    expect(search([side, main], 'softmax').map((r) => r.doc.slug)).toEqual(['prob', 'bits'])
    const other = lv('attn', '14', 'softmax softmax softmax softmax softmax')
    const term: Doc = { kind: 'term', slug: 'softmax', level: '10', title: 'softmax', question: '', url: '/g/', sections: [{ heading: '', anchor: '', text: 'turns scores into probabilities' }] }
    expect(search([other, main, term], 'softmax').map((r) => r.doc.slug).indexOf('prob')).toBeLessThan(search([other, main, term], 'softmax').map((r) => r.doc.slug).indexOf('attn'))
  })
})

describe('search snippets have no LaTeX source', async () => {
  const { texToText, mdxToText } = await import('./search')
  it('turns inline math into plain symbols', () => {
    expect(texToText('e^{\\text{score}}')).toBe('e^score')
    expect(texToText('-\\ln p_t')).toBe('-ln p_t')
    expect(texToText('x \\approx 2.72')).toBe('x ≈ 2.72')
    expect(texToText('\\frac{1}{\\sqrt{d_k}}')).toBe('1/√d_k')
    expect(mdxToText('take $e^{\\text{score}}$ of every score')).not.toMatch(/\\|\{/)
  })
})
