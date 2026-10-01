/** /learn/<slug>.md: one level as Markdown (lesson prose and question prompts, never answers). See lib/mdExport.ts. */
import type { APIRoute } from 'astro'
import { allLevels, type Level } from '@lib/levels'
import { levelToMarkdown } from '@lib/mdExport'

export async function getStaticPaths() {
  return (await allLevels()).map((entry) => ({ params: { slug: entry.id }, props: { entry } }))
}

export const GET: APIRoute = ({ props }) =>
  new Response(levelToMarkdown((props as { entry: Level }).entry), { headers: { 'Content-Type': 'text/markdown; charset=utf-8' } })
