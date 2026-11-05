/**
 * Language inside a Svelte island. The island's top component gets `lang` from its Astro wrapper and calls
 * provideLang(lang); every component inside it (LabFrame, MatrixGrid, …) calls useT() to get a `t` for that language.
 * A component's own Chinese strings go in a local table: useT({ 'Reset': '重置' }).
 */
import { getContext, setContext } from 'svelte'
import { translator, type Lang } from './i18n'

const KEY = 'llmbh-lang'

export function provideLang(lang: Lang = 'en'): Lang {
  setContext(KEY, lang)
  return lang
}

export const langCtx = (): Lang => getContext<Lang>(KEY) ?? 'en'

export const useT = (local?: Record<string, string>) => translator(langCtx(), local)
