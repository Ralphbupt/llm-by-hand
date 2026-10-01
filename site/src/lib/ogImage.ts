/**
 * Build time: Open Graph cards (1200 × 630 PNG) in the home page's look: dark graph paper, the display font,
 * one line of hand-checkable math. satori lays the card out as SVG; sharp turns it into a PNG.
 */
import fs from 'node:fs'
import { createRequire } from 'node:module'
import satori from 'satori'
import sharp from 'sharp'
import { SITE_URL } from '../config/site'

const require = createRequire(import.meta.url)
const font = (pkg: string, file: string) => fs.readFileSync(require.resolve(`${pkg}/files/${file}`))
let fonts: { name: string; data: Buffer; weight: 400 | 700; style: 'normal' }[] | null = null
function loadFonts() {
  fonts ??= [
    { name: 'Bricolage', data: font('@fontsource/bricolage-grotesque', 'bricolage-grotesque-latin-400-normal.woff'), weight: 400, style: 'normal' },
    { name: 'Bricolage', data: font('@fontsource/bricolage-grotesque', 'bricolage-grotesque-latin-700-normal.woff'), weight: 700, style: 'normal' },
    { name: 'Mono', data: font('@fontsource/jetbrains-mono', 'jetbrains-mono-latin-400-normal.woff'), weight: 400, style: 'normal' },
    { name: 'Mono', data: font('@fontsource/jetbrains-mono', 'jetbrains-mono-latin-700-normal.woff'), weight: 700, style: 'normal' },
  ]
  return fonts
}

// the dark theme tokens (global.css)
const C = { bg: '#16161a', card: '#1e1e23', fg: '#e6e6e3', dim: '#9a9aa3', line: '#33333b', accent: '#7aa2f7', warn: '#f0845c' }

type El = { type: string; props: Record<string, unknown> & { children?: unknown } }
const h = (type: string, style: Record<string, unknown>, ...children: unknown[]): El => ({
  type,
  props: { style, children: children.length === 1 ? children[0] : children },
})

function frame(...content: El[]): El {
  const host = new URL(SITE_URL).host
  return h('div', {
    width: 1200, height: 630, display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
    padding: '64px 80px', background: C.bg, color: C.fg, fontFamily: 'Bricolage',
    backgroundImage: `linear-gradient(${C.line}55 1px, transparent 1px), linear-gradient(90deg, ${C.line}55 1px, transparent 1px)`,
    backgroundSize: '30px 30px',
  },
    h('div', { display: 'flex', fontSize: 30, fontWeight: 700 }, 'LLM by Hand'),
    h('div', { display: 'flex', flexDirection: 'column', gap: 28 }, ...content),
    h('div', { display: 'flex', fontFamily: 'Mono', fontSize: 24, color: C.dim }, host),
  )
}

async function render(el: El): Promise<Buffer> {
  const svg = await satori(el as never, { width: 1200, height: 630, fonts: loadFonts() })
  return sharp(Buffer.from(svg)).png({ compressionLevel: 9 }).toBuffer()
}

/** The site-wide card: the headline and the first question from the home page. */
export function siteCard(): Promise<Buffer> {
  const mono = { fontFamily: 'Mono', fontSize: 46, display: 'flex', alignItems: 'center', gap: 18 }
  return render(frame(
    h('div', { display: 'flex', flexDirection: 'column', fontSize: 92, fontWeight: 700, letterSpacing: -2, lineHeight: 1.05 },
      h('div', { display: 'flex' }, 'Build your own GPT,'), h('div', { display: 'flex' }, 'by hand.')),
    h('div', { ...mono, padding: '22px 30px', background: C.card, border: `1px solid ${C.line}`, borderRadius: 12, alignSelf: 'flex-start' },
      h('span', { color: C.fg }, 'cat · dog ='),
      h('span', { color: C.accent }, '2×1 + 0×1'),
      h('span', { color: C.fg }, '='),
      h('span', { color: C.warn, border: `3px dashed ${C.warn}`, borderRadius: 8, padding: '0 18px', fontWeight: 700 }, '?'),
    ),
  ))
}

/** A level's card: its number (or side trip), title and question. */
export function levelCard(label: string, title: string, question: string): Promise<Buffer> {
  const size = title.length > 34 ? 64 : title.length > 22 ? 76 : 88
  return render(frame(
    h('div', { display: 'flex', fontFamily: 'Mono', fontSize: 30, color: C.accent }, label),
    h('div', { display: 'flex', fontSize: size, fontWeight: 700, letterSpacing: -1.5, lineHeight: 1.05 }, title),
    h('div', { display: 'flex', fontSize: 36, color: C.dim, lineHeight: 1.3, maxWidth: 1000 }, question),
  ))
}
