/**
 * Svelte action for SVG charts drawn in viewBox units: keeps every <text> at least `min` CSS pixels tall on
 * screen (default 11.5px), scaled by the reader's text-size setting (the root font size). Without it, an SVG that
 * shrinks to a phone's width shrinks its labels to 6–8px.
 *
 *   <svg viewBox="0 0 100 60" use:readable> … <text font-size="4">…</text> … </svg>
 *
 * Labels that are already big enough on screen are left alone. Re-runs on resize and when text changes.
 */
export function readable(svg: SVGSVGElement, opts: { min?: number } = {}) {
  let min = opts.min ?? 11.5
  let raf = 0
  const fit = () => {
    cancelAnimationFrame(raf)
    raf = requestAnimationFrame(() => {
      const ctm = svg.getScreenCTM()
      if (!ctm || !ctm.a) return
      const rootScale = parseFloat(getComputedStyle(document.documentElement).fontSize) / 16 || 1
      const want = min * rootScale
      svg.querySelectorAll<SVGTextElement>('text').forEach((t) => {
        // remember the authored size once (attribute or CSS), in user units
        if (!t.dataset.fs) {
          t.style.fontSize = ''
          t.dataset.fs = String(parseFloat(getComputedStyle(t).fontSize) || 4)
        }
        const authored = parseFloat(t.dataset.fs)
        const onScreen = authored * ctm.a
        t.style.fontSize = onScreen < want ? `${want / ctm.a}px` : ''
      })
    })
  }
  const ro = new ResizeObserver(fit)
  ro.observe(svg)
  const mo = new MutationObserver((m) => {
    if (m.some((r) => r.type === 'childList' || r.type === 'characterData')) {
      svg.querySelectorAll<SVGTextElement>('text:not([data-fs])').length && fit()
    }
  })
  mo.observe(svg, { childList: true, subtree: true, characterData: true })
  const onScale = () => fit()
  window.addEventListener('llmbh:theme', onScale)
  const html = new MutationObserver(fit)
  html.observe(document.documentElement, { attributes: true, attributeFilter: ['data-scale'] })
  fit()
  return {
    update(o: { min?: number } = {}) { min = o.min ?? 11.5; fit() },
    destroy() { ro.disconnect(); mo.disconnect(); html.disconnect(); window.removeEventListener('llmbh:theme', onScale); cancelAnimationFrame(raf) },
  }
}
