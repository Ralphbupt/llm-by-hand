/** /llms-full.txt: every level's prose and question prompts in reading order, as Markdown (never answers or hints). */
import type { APIRoute } from 'astro'
import { allLevels } from '@lib/levels'
import { levelToMarkdown } from '@lib/mdExport'
import { SITE_NAME, SITE_DESCRIPTION, abs } from '../config/site'

export const GET: APIRoute = async () => {
  const all = await allLevels()
  const head = [`# ${SITE_NAME}: all lessons`, '', `> ${SITE_DESCRIPTION}`, '', `Source: ${abs('/')} · lessons CC BY-SA 4.0`, '']
  const body = all.map((l) => levelToMarkdown(l).replace(/^# /, '## ').replace(/\n(#{2,5}) /g, '\n#$1 '))
  return new Response(head.join('\n') + '\n' + body.join('\n---\n\n'), { headers: { 'Content-Type': 'text/plain; charset=utf-8' } })
}
