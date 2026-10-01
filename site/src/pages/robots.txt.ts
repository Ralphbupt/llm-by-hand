/**
 * /robots.txt: everything may be crawled, including by AI crawlers (the course is meant to be found).
 * To keep AI crawlers out, change their groups below to "Disallow: /".
 */
import type { APIRoute } from 'astro'
import { abs } from '../config/site'

const AI = ['GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'ClaudeBot', 'Claude-User', 'Claude-SearchBot', 'anthropic-ai', 'PerplexityBot', 'Perplexity-User', 'Google-Extended', 'Applebot-Extended', 'CCBot', 'Meta-ExternalAgent', 'Amazonbot', 'DuckAssistBot', 'MistralAI-User']

export const GET: APIRoute = () => {
  const lines = [
    'User-agent: *',
    'Allow: /',
    '',
    '# AI crawlers and assistants: allowed on purpose',
    ...AI.flatMap((a) => [`User-agent: ${a}`, 'Allow: /', '']),
    `Sitemap: ${abs('/sitemap.xml')}`,
    '',
  ]
  return new Response(lines.join('\n'), { headers: { 'Content-Type': 'text/plain; charset=utf-8' } })
}
