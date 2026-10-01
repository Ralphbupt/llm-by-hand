import { describe, expect, it } from 'vitest'
import { idsInSideBoxes, sectionOf } from './lessonScan'

const mdx = `## 1. Start
<Blank id="a" />
<Stuck q="Why?">
Text.
<Predict id="in-stuck" />
</Stuck>
## Step 2: the forward shape
<Deeper title="More">
<Blank id="in-deeper" />
</Deeper>
<CodeBlank id="boss" />
`

describe('lesson scans', () => {
  it('finds exercises inside Stuck and Deeper boxes only', () => {
    expect(idsInSideBoxes(mdx)).toEqual(['in-stuck', 'in-deeper'])
  })
  it('names the section an exercise sits in', () => {
    expect(sectionOf(mdx, 'boss')).toBe('Step 2: the forward shape')
    expect(sectionOf(mdx, 'a')).toBe('1. Start')
    expect(sectionOf(mdx, 'nope')).toBeNull()
  })
})
