/** /og/<slug>.png: a level's Open Graph card (lib/ogImage.ts), made at build time. */
import type { APIRoute } from 'astro'
import { allLevels, BRANCH_NAME, type Level } from '@lib/levels'
import { levelCard } from '@lib/ogImage'
import { plain } from '@lib/seo'

export async function getStaticPaths() {
  return (await allLevels()).map((entry) => ({ params: { slug: entry.id }, props: { entry } }))
}

export const GET: APIRoute = async ({ props }) => {
  const { data } = (props as { entry: Level }).entry
  const label = data.branch ? `Side trip ${data.level} · ${BRANCH_NAME[data.branch]}` : `Level ${data.level}`
  const png = await levelCard(label, plain(data.title), plain(data.question))
  return new Response(new Uint8Array(png), { headers: { 'Content-Type': 'image/png' } })
}
