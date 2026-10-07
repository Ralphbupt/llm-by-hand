// IndexNow ping: tells Bing/Yandex/Seznam/Naver about every URL in the sitemap so they recrawl fast
// (Google does not support IndexNow). Runs after `astro build`, only on Cloudflare Pages (CF_PAGES set),
// so local builds don't ping. Never fails the build. The key file lives at public/18fa2841b08103325f6deeec42b0750b.txt.
import fs from 'node:fs'

const KEY = '18fa2841b08103325f6deeec42b0750b'
const HOST = 'llm.liko.page'

if (!process.env.CF_PAGES) {
  console.log('IndexNow: not a Cloudflare Pages build, skipping ping.')
  process.exit(0)
}

let urlList = []
try {
  const sitemap = fs.readFileSync('dist/sitemap.xml', 'utf-8')
  urlList = [...sitemap.matchAll(/<loc>(.*?)<\/loc>/g)].map((m) => m[1])
} catch {}
if (urlList.length === 0) {
  console.log('IndexNow: no URLs in dist/sitemap.xml, skipping.')
  process.exit(0)
}

try {
  const res = await fetch('https://api.indexnow.org/indexnow', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
    body: JSON.stringify({ host: HOST, key: KEY, keyLocation: `https://${HOST}/${KEY}.txt`, urlList }),
  })
  // 200 = accepted, 202 = accepted, key validation pending
  console.log(`IndexNow: submitted ${urlList.length} URLs → HTTP ${res.status}`)
} catch (err) {
  console.log(`IndexNow: ping failed (non-fatal): ${err.message}`)
}
