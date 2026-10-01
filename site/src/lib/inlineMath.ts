/** Build time: short text with `$KaTeX$` and `code` spans → safe HTML (used by the recap card). */
import katex from 'katex'

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

export function inlineMath(src: string): string {
  return src
    .split(/(\$[^$]+\$|`[^`]+`)/g)
    .map((part) => {
      if (/^\$[^$]+\$$/.test(part)) return katex.renderToString(part.slice(1, -1), { throwOnError: false, output: 'html' })
      if (/^`[^`]+`$/.test(part)) return `<code>${esc(part.slice(1, -1))}</code>`
      return esc(part)
    })
    .join('')
}
