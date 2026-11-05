import { defineConfig } from 'astro/config'
import mdx from '@astrojs/mdx'
import svelte from '@astrojs/svelte'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import fs from 'node:fs'
import GithubSlugger from 'github-slugger'
import { SITE_URL } from './src/config/site.ts'
import { headingIds } from './src/lib/search.ts'

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

// a Chinese lesson (lesson.zh.mdx) links to the Chinese pages: /learn/x/ → /zh/learn/x/ (pages with a Chinese version only)
const ZH_PAGES = /^\/(learn|glossary|review|start|math|setup)\//
function rehypeZhLinks() {
  const walk = (node) => {
    if (node.type === 'element' && node.tagName === 'a' && typeof node.properties?.href === 'string' && ZH_PAGES.test(node.properties.href))
      node.properties.href = '/zh' + node.properties.href
    for (const c of node.children ?? []) walk(c)
  }
  return (tree, file) => { if (/\.zh\.mdx$/.test(file.path ?? '')) walk(tree) }
}

// a translated lesson keeps the English heading ids, so /learn/x/#4-learning-rate-schedules finds its section in
// every language: the n-th heading of lesson.zh.mdx gets the id of the n-th heading of lesson.en.mdx. Links inside the
// page written with the translated heading's own slug (#2-整台机器) are pointed at the English id too.
function rehypeEnglishHeadingIds() {
  const text = (n) => (n.type === 'text' ? n.value : (n.children ?? []).map(text).join(''))
  return (tree, file) => {
    const p = file.path ?? ''
    if (!/lesson\.zh\.mdx$/.test(p)) return
    const en = headingIds(fs.readFileSync(p.replace(/lesson\.zh\.mdx$/, 'lesson.en.mdx'), 'utf8').replace(/^---\n[\s\S]*?\n---\n/, ''))
    const heads = []
    const walk = (n) => { if (n.type === 'element' && /^h[2-6]$/.test(n.tagName)) heads.push(n); for (const c of n.children ?? []) walk(c) }
    walk(tree)
    // same headings at every depth: map one to one; otherwise only the ## sections (check_zh.py keeps those equal)
    const same = heads.length === en.length && heads.every((h, i) => Number(h.tagName[1]) === en[i].depth)
    const pairs = same ? heads.map((h, i) => [h, en[i].id])
      : heads.filter((h) => h.tagName === 'h2').map((h, i) => [h, en.filter((e) => e.depth === 2)[i]?.id])
    const slugger = new GithubSlugger()
    const own = new Map()
    for (const h of heads) own.set(h, slugger.slug(text(h)))
    const moved = new Map()
    for (const [h, id] of pairs) if (id) { moved.set('#' + own.get(h), '#' + id); h.properties = { ...h.properties, id } }
    const fix = (n) => {
      const h = n.type === 'element' && n.tagName === 'a' && typeof n.properties?.href === 'string' ? decodeURIComponent(n.properties.href) : ''
      if (moved.has(h)) n.properties.href = moved.get(h)
      for (const c of n.children ?? []) fix(c)
    }
    fix(tree)
  }
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
    rehypePlugins: [rehypeKatex, rehypeNoWrapVectors, rehypeNoWrapShortCode, rehypeZhLinks, rehypeEnglishHeadingIds],
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
