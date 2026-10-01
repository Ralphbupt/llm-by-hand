/** /og/site.png: the site-wide Open Graph card (lib/ogImage.ts), made at build time. */
import type { APIRoute } from 'astro'
import { siteCard } from '@lib/ogImage'

export const GET: APIRoute = async () => new Response(new Uint8Array(await siteCard()), { headers: { 'Content-Type': 'image/png' } })
