// Every page at phone width (390 px) must not scroll sideways: document scrollWidth <= clientWidth.
// Also: no short inline vector ("[0, 2]") in prose or question text may break across two lines.
// Then, at desktop width (1280 px): no code block, code box or recap line may cut its text off at the right edge
// (scrollWidth > clientWidth on a <pre>, a code <textarea> or a line of the recap card, which is opened for the
// check): move a long comment to its own line above, or shorten the recap line. Skip the desktop pass with NO_WIDE=1.
// Needs the dev server (cd site && npx astro dev --port 4322) and Google Chrome.
//   node scripts/check_overflow.mjs [baseUrl] [width] [/learn/slug/ ...]
// With page paths, only those pages are checked; without, every level plus the home, glossary, math, setup and
// review pages. One browser, PAGES_AT_ONCE tabs in parallel (default 4). Each page loads once: it is checked at the
// phone width, then the same tab is widened to 1280 px for the code check.
// Opens every page with all gates open (the local debug switch), scrolls through so labs load, and lists the pages
// that overflow with the widest element that sticks out. Exit code 1 when any page has a problem.
import { spawn } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

const args = process.argv.slice(2)
const base = (args.find((a) => /^https?:/.test(a)) ?? 'http://localhost:4322').replace(/\/$/, '')
const W = +(args.find((a) => /^\d+$/.test(a)) ?? 390)
const only = args.filter((a) => a.startsWith('/'))
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..')
const slugs = []
for (const part of fs.readdirSync(path.join(root, 'content'))) {
  const dir = path.join(root, 'content', part)
  if (!fs.statSync(dir).isDirectory()) continue
  for (const s of fs.readdirSync(dir)) if (fs.existsSync(path.join(dir, s, 'lesson.en.mdx'))) slugs.push(s)
}
const urls = only.length
  ? only.map((p) => base + p)
  : [...new Set(slugs)].map((s) => `${base}/learn/${s}/`).concat(['', 'glossary/', 'math/', 'setup/', 'review/'].map((p) => `${base}/${p}`))
const AT_ONCE = Math.max(1, +(process.env.PAGES_AT_ONCE ?? 4))

const chromeBin = process.env.CHROME ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'overflow-'))
const chrome = spawn(chromeBin, ['--headless=new', '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--no-first-run', 'about:blank'], { stdio: 'ignore' })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
let port
for (let i = 0; i < 100 && !port; i++) { try { port = fs.readFileSync(path.join(profile, 'DevToolsActivePort'), 'utf8').split('\n')[0] } catch { await sleep(100) } }
for (let i = 0; i < 40; i++) { try { await (await fetch(`http://127.0.0.1:${port}/json/version`)).json(); break } catch { await sleep(200) } }

/** A tab with its own DevTools connection. */
async function openTab() {
  const t = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })).json()
  const ws = new WebSocket(t.webSocketDebuggerUrl)
  let id = 0
  const pending = new Map()
  ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id && pending.has(d.id)) { pending.get(d.id)(d.result); pending.delete(d.id) } }
  await new Promise((r) => (ws.onopen = r))
  const send = (method, params = {}) => new Promise((res) => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })) })
  const ev = async (expression) => (await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }))?.result?.value
  return { send, ev, close: () => ws.close() }
}

const phone = { width: W, height: 844, deviceScaleFactor: 2, mobile: true }
const desk = { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false }
const scroll = (step, pause) => `(async()=>{for(let y=0;y<document.documentElement.scrollHeight;y+=${step}){scrollTo(0,y);await new Promise(r=>setTimeout(r,${pause}))}})()`

async function checkPage(tab, u) {
  const out = []
  const name = u.replace(base, '') || '/'
  await tab.send('Emulation.setDeviceMetricsOverride', phone)
  await tab.send('Page.navigate', { url: u })
  await sleep(2000)
  await tab.ev(scroll(700, 100))
  await sleep(1200)
  const r = JSON.parse(await tab.ev(`(()=>{const cw=document.documentElement.clientWidth, sw=document.documentElement.scrollWidth; let worst=null;
    if (sw>cw) for (const e of document.querySelectorAll('body *')) { const b=e.getBoundingClientRect(); if (b.right<=cw+1||!b.width) continue;
      let q=e.parentElement, clipped=false; while(q&&q!==document.body){ if(getComputedStyle(q).overflowX!=='visible'){clipped=true;break} q=q.parentElement }
      if(!clipped&&(!worst||b.right>worst.right)) worst={right:Math.round(b.right), el:e.tagName.toLowerCase()+'.'+[...e.classList].join('.')} }
    return JSON.stringify({sw,cw,worst})})()`))
  if (r.sw > r.cw) out.push(['bad', `OVERFLOW ${name}  ${r.sw} > ${r.cw}  ${r.worst ? r.worst.el + ' (right edge ' + r.worst.right + ')' : ''}`])
  // a short vector in text ("car = [0, 2]") must stay on one line: the learner copies those numbers
  // (a long one, over 40 characters, may wrap: it would not fit a phone line anyway)
  const split = JSON.parse(await tab.ev(`(()=>{const VEC=/\\[[−-]?\\d[\\d.,\\s−-]*,[\\d.,\\s−-]*\\]/g, out=[];
    const w=document.createTreeWalker(document.querySelector('main')??document.body, NodeFilter.SHOW_TEXT);
    for(let n=w.nextNode(); n; n=w.nextNode()){ if(n.parentElement.closest('pre,code,textarea,script,style,svg,.katex')) continue;
      for(const m of n.data.matchAll(VEC)){ const rg=document.createRange(); rg.setStart(n,m.index); rg.setEnd(n,m.index+m[0].length);
        const tops=new Set([...rg.getClientRects()].filter(x=>x.width>0).map(x=>Math.round(x.top))); if(tops.size>1&&m[0].length<=40) out.push(m[0]) } }
    return JSON.stringify(out)})()`))
  if (split.length) out.push(['bad', `SPLIT ${name}  ${split.join('  ')}`])
  if (!process.env.NO_WIDE) {
    // desktop: code that is cut off at the right edge of its box. Same tab, widened: the labs are already loaded.
    await tab.send('Emulation.setDeviceMetricsOverride', desk)
    await tab.ev(`document.querySelectorAll('details.recap').forEach(d=>d.open=true)`)
    await sleep(600)
    const cut = JSON.parse(await tab.ev(`(()=>{const out=[]; for(const e of document.querySelectorAll('main pre, main textarea, details.recap li')){
        if(!e.clientWidth||e.scrollWidth<=e.clientWidth+1) continue
        const text=e.tagName==='TEXTAREA'?e.value:e.innerText; const lines=text.split('\\n'); let longest=lines.reduce((a,b)=>b.length>a.length?b:a,'')
        out.push((e.closest('details.recap')?'recap ':'')+e.tagName.toLowerCase()+' '+e.scrollWidth+'/'+e.clientWidth+': '+longest.trim().slice(0,90)) }
      return JSON.stringify(out)})()`))
    for (const c of cut) out.push(['clipped', `CLIPPED ${name}  ${c}`])
  }
  return out
}

// the debug switch lives in localStorage, shared by every tab of this profile
const first = await openTab()
await first.send('Page.navigate', { url: base + '/' })
await sleep(1200)
await first.ev(`localStorage.setItem('llmbh-debug-open','1')`)
const tabs = [first]
for (let i = 1; i < Math.min(AT_ONCE, urls.length); i++) tabs.push(await openTab())

let bad = 0, clipped = 0, next = 0
await Promise.all(tabs.map(async (tab) => {
  while (next < urls.length) {
    const u = urls[next++]
    for (const [kind, line] of await checkPage(tab, u)) {
      if (kind === 'bad') bad++; else clipped++
      console.log(line)
    }
  }
}))
console.log(bad ? `${bad} page problem(s) at ${W}px` : `ok: ${urls.length} pages, none scroll sideways or split a vector at ${W}px`)
if (!process.env.NO_WIDE) console.log(clipped ? `${clipped} code block(s) or recap line(s) cut off at 1280px` : `ok: no code block or recap line cut off at 1280px`)
tabs.forEach((t) => t.close()); chrome.kill()
setTimeout(() => { try { fs.rmSync(profile, { recursive: true, force: true }) } catch {} process.exit(bad || clipped ? 1 : 0) }, 300)
