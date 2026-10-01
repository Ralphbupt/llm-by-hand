/**
 * The display order of a graded Predict's options: a fixed shuffle seeded by the exercise id, so the right option
 * is not always in the same place, while the server render and the browser agree (no random numbers).
 * scripts/check_exercises.py mirrors this exactly (option_order) to check where the answers land: keep the two in step.
 */

/** FNV-1a over the id's UTF-16 code units, then a final bit mix, as an unsigned 32-bit number. */
export function seedOf(id: string): number {
  let h = 2166136261
  for (let i = 0; i < id.length; i++) {
    h ^= id.charCodeAt(i)
    h = Math.imul(h, 16777619) >>> 0
  }
  h ^= h >>> 16
  h = Math.imul(h, 0x85ebca6b) >>> 0
  h ^= h >>> 13
  h = Math.imul(h, 0xc2b2ae35) >>> 0
  h ^= h >>> 16
  return h >>> 0
}

/**
 * order[k] = the index (in exercises.yaml) of the option shown in place k. Seeded by the plain id
 * ("<page>/<id>" → "<id>"), so the same question looks the same on its page, in the warm-up and in the mistake book.
 */
export function optionOrder(id: string, n: number): number[] {
  const order = Array.from({ length: n }, (_, i) => i)
  let s = seedOf(id.split('/').pop() ?? id)
  for (let i = n - 1; i > 0; i--) {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0
    const j = (s >>> 16) % (i + 1)
    ;[order[i], order[j]] = [order[j], order[i]]
  }
  return order
}
