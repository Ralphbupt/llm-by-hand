/**
 * /sitemap.xml: the home page, every level and the reference pages (not the 404 or the mistakes book), in English,
 * and their Chinese versions (only levels already translated: an untranslated /zh/ level is noindex).
 */
import type { APIRoute } from 'astro'
import { allLevels } from '@lib/levels'
import { abs } from '../config/site'

export const GET: APIRoute = async () => {
  const paths = [
    '/', '/start/', ...(await allLevels()).map((l) => `/learn/${l.id}/`), '/glossary/', '/math/', '/setup/',
    '/zh/', '/zh/start/', ...(await allLevels('zh')).filter((l) => l.translated).map((l) => `/zh/learn/${l.id}/`), '/zh/glossary/', '/zh/math/', '/zh/setup/',
  ]
  const xml = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...paths.map((p) => `  <url><loc>${abs(p)}</loc></url>`),
    '</urlset>',
    '',
  ].join('\n')
  return new Response(xml, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } })
}
