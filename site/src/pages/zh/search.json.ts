import type { APIRoute } from 'astro'
import { searchDocs } from '@lib/searchIndex'

export const GET: APIRoute = async () =>
  new Response(JSON.stringify(await searchDocs('zh')), { headers: { 'Content-Type': 'application/json' } })
