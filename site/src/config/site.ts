/**
 * The site's public identity, in one place. The origin is also read by astro.config.mjs (`site:`),
 * so changing SITE_URL here moves canonical URLs, the sitemap, llms.txt and Open Graph tags together.
 */
export const SITE_URL = 'https://llm.liko.page'
export const SITE_NAME = 'LLM by Hand'
export const SITE_TAGLINE = 'Build your own GPT, by hand.'
export const SITE_DESCRIPTION =
  'Learn how large language models work by computing every number yourself, in small interactive levels: from one dot product to a GPT you write and train.'
/** The course author, shown as the provider in structured data. alternateName links the liko.page domain to the same person. */
export const AUTHOR = { name: 'Link', alternateName: 'Liko', url: 'https://blog.liko.page' }
export const LICENSE_URL = 'https://creativecommons.org/licenses/by-sa/4.0/'
/** theme-color for the browser chrome, matching --bg in global.css (light, dark). */
export const THEME_COLOR = { light: '#fdfdfc', dark: '#16161a' }
/** Google Analytics 4 measurement ID; unset (dev, previews, forks) → no analytics code and no consent bar. */
export const GA4_ID: string = (import.meta.env?.PUBLIC_GA4_ID ?? '').trim()

/** An absolute URL on this site: abs('/learn/x/') → https://llm.liko.page/learn/x/ */
export const abs = (path: string) => new URL(path, SITE_URL).href
