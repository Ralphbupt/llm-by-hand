/**
 * Google Analytics 4, only with consent.
 *
 * Nothing loads unless the site was built with PUBLIC_GA4_ID set (src/config/site.ts) AND the visitor pressed
 * "Allow" in the consent bar (or turned Analytics on in Settings). Consent Mode v2: every storage type starts
 * denied; "Allow" grants analytics_storage only, ads stay denied.
 *
 * track(name, params) does nothing without an ID or without consent. Never pass answer text, code or anything the
 * learner typed: only ids, level numbers, counts and ok/error.
 */
import { GA4_ID } from '../config/site'

const KEY = 'llmbh-consent'
export type Consent = 'granted' | 'denied'

type Gtag = (...args: unknown[]) => void
declare global {
  interface Window { dataLayer?: unknown[]; gtag?: Gtag }
}

export const analyticsEnabled = () => GA4_ID !== ''

/** The stored choice, or null when the visitor has not chosen yet. */
export function getConsent(): Consent | null {
  try {
    const v = localStorage.getItem(KEY)
    return v === 'granted' || v === 'denied' ? v : null
  } catch {
    return null
  }
}

/** The facts about this page that every event carries (written by SeoHead.astro as #seo-page). */
export type PageInfo = { slug?: string; level?: string; branch?: string; checkpoint?: string; boss?: boolean; kind?: string }
let page: PageInfo | null = null
export function pageInfo(): PageInfo {
  if (page) return page
  try {
    page = JSON.parse(document.getElementById('seo-page')?.textContent ?? '{}') as PageInfo
  } catch {
    page = {}
  }
  return page
}

let loaded = false
function gtag(...args: unknown[]) {
  window.dataLayer = window.dataLayer ?? []
  // gtag.js reads the arguments object, not an array
  // eslint-disable-next-line prefer-rest-params
  window.dataLayer.push(arguments)
}

/** Consent Mode v2 defaults: everything denied until the visitor allows analytics. */
function defaults() {
  if (window.gtag) return
  window.gtag = gtag as Gtag
  gtag('consent', 'default', {
    analytics_storage: 'denied',
    ad_storage: 'denied',
    ad_user_data: 'denied',
    ad_personalization: 'denied',
  })
}

/** Load gtag.js (once) after consent. */
function load() {
  if (loaded || !analyticsEnabled()) return
  loaded = true
  defaults()
  gtag('consent', 'update', { analytics_storage: 'granted' })
  gtag('js', new Date())
  gtag('config', GA4_ID, { anonymize_ip: true })
  const s = document.createElement('script')
  s.async = true
  s.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(GA4_ID)}`
  s.dataset.ga = '1'
  document.head.appendChild(s)
}

/** Remember the visitor's choice; "granted" loads analytics now, "denied" stops sending (and drops GA cookies). */
export function setConsent(v: Consent) {
  try {
    localStorage.setItem(KEY, v)
  } catch {}
  if (v === 'granted') load()
  else if (loaded) {
    window.gtag?.('consent', 'update', { analytics_storage: 'denied' })
    // GA cookies are first-party: clear them so a "No" really means no
    for (const c of document.cookie.split(';')) {
      const name = c.split('=')[0].trim()
      if (name === '_ga' || name.startsWith('_ga_')) {
        const host = location.hostname
        document.cookie = `${name}=; Max-Age=0; path=/`
        document.cookie = `${name}=; Max-Age=0; path=/; domain=.${host.split('.').slice(-2).join('.')}`
      }
    }
  }
  window.dispatchEvent(new CustomEvent('llmbh:consent', { detail: v }))
}

/** Called once per page (from SeoHead): load gtag if this visitor already allowed it. */
export function initAnalytics() {
  if (!analyticsEnabled()) return
  defaults()
  if (getConsent() === 'granted') load()
}

const ALLOWED = /^[\w./:-]{0,100}$/
/**
 * Send one event. Adds the page's level number and slug. String values must be short ids (letters, digits, . / : _ -),
 * so a free-text value can never slip through.
 */
export function track(name: string, params: Record<string, string | number | boolean | undefined> = {}) {
  if (!analyticsEnabled() || getConsent() !== 'granted' || typeof window === 'undefined') return
  load()
  const p = pageInfo()
  const out: Record<string, string | number | boolean> = {}
  if (p.slug) out.page_slug = p.slug
  if (p.level) out.level = p.level
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined) continue
    if (typeof v === 'string' && !ALLOWED.test(v)) continue
    out[k] = v
  }
  window.gtag?.('event', name, out)
}

/** The current page's checkpoint as stored in progress ("slug/id"), or '' off a level page. */
export function pageCheckpoint(): string {
  const p = pageInfo()
  return p.slug && p.checkpoint ? `${p.slug}/${p.checkpoint}` : ''
}
