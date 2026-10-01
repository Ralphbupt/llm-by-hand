import { defineConfig } from 'astro/config'
import mdx from '@astrojs/mdx'
import svelte from '@astrojs/svelte'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import { SITE_URL } from './src/config/site.ts'

const here = (p) => new URL(p, import.meta.url).pathname

// a short vector in running text ("car = [0, 2]") never breaks across lines: wrap it in <span class="vec-nw">
const VEC = /\[[−-]?\d[\d.,\s−-]*,[\d.,\s−-]*\]/g
const SKIP = new Set(['code', 'pre', 'script', 'style', 'svg', 'math'])
function rehypeNoWrapVectors() {
  const walk = (node) => {
    if (!node.children) return
    if (node.type === 'element' && (SKIP.has(node.tagName) || String(node.properties?.className ?? '').includes('katex'))) return
    node.children = node.children.flatMap((c) => {
      if (c.type !== 'text' || !VEC.test(c.value)) { walk(c); return [c] }
      VEC.lastIndex = 0
      const out = []
      let at = 0
      for (const m of c.value.matchAll(VEC)) {
        if (m.index > at) out.push({ type: 'text', value: c.value.slice(at, m.index) })
        out.push({ type: 'element', tagName: 'span', properties: { className: ['vec-nw'] }, children: [{ type: 'text', value: m[0] }] })
        at = m.index + m[0].length
      }
      if (at < c.value.length) out.push({ type: 'text', value: c.value.slice(at) })
      return out
    })
  }
  return (tree) => walk(tree)
}

// short inline code ("(n, 1) @ (1, n)") never breaks across lines either; long inline code may wrap, or it would not fit a phone
function rehypeNoWrapShortCode() {
  const text = (n) => (n.type === 'text' ? n.value : (n.children ?? []).map(text).join(''))
  const walk = (node) => {
    for (const c of node.children ?? []) {
      if (c.type !== 'element' || c.tagName === 'pre') continue
      if (c.tagName === 'code') {
        if (text(c).length <= 24) c.properties = { ...c.properties, className: [...[c.properties?.className ?? []].flat(), 'code-nw'] }
      } else walk(c)
    }
  }
  return (tree) => walk(tree)
}

// a long trailing comment in a code block wraps under itself instead of running off the box ("# the next 64 ids …"):
// each comment token (the theme's comment color, text starting with #) gets class "cmt" and --c, the column it starts
// at; global.css turns it into an inline block as wide as the room left on its line, so its wrapped lines stay in the
// comment's column
const wrapCodeComments = {
  name: 'wrap-code-comments',
  line(lineEl) {
    const text = (n) => (n.type === 'text' ? n.value : (n.children ?? []).map(text).join(''))
    const out = []
    let col = 0
    for (const c of lineEl.children) {
      const t = text(c)
      const color = String(c.properties?.style ?? '').match(/color:\s*(#[0-9a-f]+)/i)?.[1] ?? ''
      if (c.type === 'element' && /^#6a737d$/i.test(color) && t.trimStart().startsWith('#')) {
        // an indented comment line comes as one token "    # …": its indent goes in front, so it wraps under the "#"
        const lead = t.length - t.trimStart().length
        if (lead) { out.push({ type: 'text', value: t.slice(0, lead) }); col += lead; c.children = [{ type: 'text', value: t.slice(lead) }] }
        c.properties.className = ['cmt']
        c.properties.style = `${c.properties.style};--c:${col}`
        col += t.length - lead
      } else col += t.length
      out.push(c)
    }
    lineEl.children = out
  },
}

export default defineConfig({
  // the public origin (one place: src/config/site.ts); canonical URLs, the sitemap and llms.txt use it
  site: SITE_URL,
  // every page is a folder with index.html (/learn/x/), the way Cloudflare Pages serves it; links always end in /
  trailingSlash: 'always',
  build: { format: 'directory' },
  integrations: [mdx(), svelte()],
  markdown: {
    remarkPlugins: [remarkMath],
    rehypePlugins: [rehypeKatex, rehypeNoWrapVectors, rehypeNoWrapShortCode],
    shikiConfig: { transformers: [wrapCodeComments] },
  },
  vite: {
    resolve: {
      alias: {
        '@lib': here('./src/lib'),
        '@quiz': here('./src/components/quiz'),
        '@viz': here('./src/components/viz'),
        '@text': here('./src/components/text'),
      },
    },
    // lessons live in ../content, outside the site folder: allow reading it and watch it,
    // so new level folders show up in the dev server without a restart
    server: { fs: { allow: [here('..')] } },
    plugins: [{ name: 'watch-content', configureServer(server) { server.watcher.add(here('../content')) } }],
  },
})
