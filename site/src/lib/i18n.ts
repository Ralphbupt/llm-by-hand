/**
 * Languages. English is the source language and lives at the root (/learn/x/); Chinese lives under /zh/ (/zh/learn/x/).
 * UI text is written in English in the code and looked up in a table for other languages: `t('Check')`.
 * A string missing from the table shows in English, so a half-translated component still works.
 * Placeholders: t('Level {n}', { n: 3 }).
 */
import { ZH } from '../i18n/zh'

export type Lang = 'en' | 'zh'
export const LANGS: Lang[] = ['en', 'zh']
/** The value of <html lang> */
export const HTML_LANG: Record<Lang, string> = { en: 'en', zh: 'zh-CN' }

/** /zh/learn/x/ → zh; anything else → en */
export const langOf = (pathname: string): Lang => (/^\/zh(\/|$)/.test(pathname) ? 'zh' : 'en')

/** In the browser: the page's language, from <html lang> */
export const pageLang = (): Lang =>
  typeof document !== 'undefined' && document.documentElement.lang.startsWith('zh') ? 'zh' : 'en'

/** Pages that have no Chinese version yet: Chinese pages link to the English one. */
const NOT_IN_ZH: string[] = []

/** A site path for a language: href('zh', '/learn/x/') → /zh/learn/x/ (hashes and the root work too) */
export const href = (lang: Lang, p: string): string => {
  if (lang === 'en' || NOT_IN_ZH.some((x) => p.startsWith(x))) return p
  return p === '/' ? '/zh/' : p.startsWith('/#') ? '/zh/' + p.slice(1) : '/zh' + p
}

/** The same page in the other language's path: /zh/learn/x/ ↔ /learn/x/ */
export const stripLang = (pathname: string): string => pathname.replace(/^\/zh(?=\/|$)/, '') || '/'

const TABLES: Record<Lang, Record<string, string>> = { en: {}, zh: ZH }

const fill = (s: string, vars?: Record<string, string | number>) =>
  vars ? s.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m)) : s

/** Look up one English UI string; `local` is a component's own table, checked first. */
export function tr(lang: Lang, s: string, vars?: Record<string, string | number>, local?: Record<string, string>): string {
  if (lang === 'en') return fill(s, vars)
  return fill(local?.[s] ?? TABLES[lang][s] ?? s, vars)
}

/** A `t` bound to one language (and a component's own table). */
export const translator = (lang: Lang, local?: Record<string, string>) =>
  (s: string, vars?: Record<string, string | number>) => tr(lang, s, vars, local)

/** English plural, or the one form for languages without plurals: plural('zh', 3, 'question', 'questions') */
export const plural = (lang: Lang, n: number, one: string, many: string) => tr(lang, n === 1 ? one : many, { n })
