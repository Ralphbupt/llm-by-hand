/**
 * Typographic quotes for text that doesn't go through the Markdown pipeline
 * (component props, frontmatter, exercise YAML). Text inside `backticks` is left alone.
 */
export function smart(s: string): string {
  return s
    .split(/(`[^`]*`)/)
    .map((part) =>
      part.startsWith('`')
        ? part
        : part
            .replace(/(^|[\s([{—–-])"/g, '$1“')
            .replace(/"/g, '”')
            .replace(/(\w)'(\w)/g, '$1’$2')
            .replace(/(^|[\s([{—–-])'/g, '$1‘')
            .replace(/'/g, '’'),
    )
    .join('')
}

/** Apply smart() to every reader-facing string of an exercise (never to code, answers or tests). */
export function smartExercise<T extends Record<string, any>>(ex: T): T {
  const out: any = { ...ex }
  for (const k of ['prompt', 'promptShort', 'after', 'reveal']) if (typeof out[k] === 'string') out[k] = smart(out[k])
  if (Array.isArray(out.options)) out.options = out.options.map((o: unknown) => (typeof o === 'string' ? smart(o) : o))
  if (Array.isArray(out.hints)) out.hints = out.hints.map((h: any) => ({ ...h, say: typeof h.say === 'string' ? smart(h.say) : h.say }))
  if (Array.isArray(out.tests)) out.tests = out.tests.map((t: any) => ({ ...t, say: typeof t.say === 'string' ? smart(t.say) : t.say }))
  return out
}
