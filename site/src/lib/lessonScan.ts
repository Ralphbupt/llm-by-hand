/** Small scans of a lesson's MDX source (build time; no Astro imports, so they can be unit-tested). */

/** Exercise ids placed inside a <Stuck> or <Deeper> box in a lesson's MDX. */
export function idsInSideBoxes(mdx: string): string[] {
  const out: string[] = []
  let depth = 0
  for (const line of mdx.split('\n')) {
    if (/<(Stuck|Deeper)[\s>]/.test(line)) depth++
    if (depth > 0) for (const m of line.matchAll(/<(?:Predict|Blank|CodeBlank)\s+id="([^"]+)"/g)) out.push(m[1])
    if (/<\/(Stuck|Deeper)>/.test(line)) depth = Math.max(0, depth - 1)
  }
  return out
}

/** The "## " heading above an exercise in a lesson's MDX, or null. */
export function sectionOf(mdx: string, id: string): string | null {
  let head: string | null = null
  for (const line of mdx.split('\n')) {
    const h = /^##\s+(.+)$/.exec(line)
    if (h) head = h[1].trim()
    if (line.includes(`id="${id}"`)) return head
  }
  return null
}
