/**
 * A smooth gray loss map for the flat "Map" views (GD, Mini-batches).
 * The values go into a small grayscale image that the browser stretches with smoothing, and the SVG uses it as a
 * mask between two token grays: no blocky cells, and the colors still come from the theme tokens.
 *   const url = landMask((fx, fy) => …value in 0..1…)   // fx: 0 = left, 1 = right; fy: 0 = top, 1 = bottom
 *   <mask id={id}><image href={url} … /></mask>      (id from $props.id())
 * Browser only (needs a canvas); call it in onMount.
 */
export function landMask(v: (fx: number, fy: number) => number, n = 64): string {
  const c = document.createElement('canvas')
  c.width = c.height = n
  const ctx = c.getContext('2d')
  if (!ctx) return ''
  const img = ctx.createImageData(n, n)
  for (let r = 0; r < n; r++)
    for (let k = 0; k < n; k++) {
      // sample at the pixel center, so the stretched image lines up with the axes
      const g = Math.round(255 * Math.min(1, Math.max(0, v((k + 0.5) / n, (r + 0.5) / n))))
      const i = (r * n + k) * 4
      img.data[i] = img.data[i + 1] = img.data[i + 2] = g
      img.data[i + 3] = 255
    }
  ctx.putImageData(img, 0, 0)
  return c.toDataURL()
}
