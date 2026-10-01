/**
 * Reader settings, stored in this browser: theme, text size, motion, reading mode.
 * They are applied as attributes on <html> (data-theme, data-scale, data-motion, data-reading); global.css does the rest.
 * Reading mode opens every part and records nothing (progress.ts asks readingMode()).
 * An inline script in each page's <head> applies them before the first paint (see settingsBootScript).
 */
export type Theme = 'auto' | 'light' | 'dark'
export type Scale = 's' | 'm' | 'l'
export type Motion = 'full' | 'reduce'
export type Settings = { theme: Theme; scale: Scale; motion: Motion; reading: boolean }

const KEY = 'llmbh-settings'
const DEFAULTS: Settings = { theme: 'auto', scale: 'm', motion: 'full', reading: false }
export const THEME_EVENT = 'llmbh:theme'

export function getSettings(): Settings {
  try {
    return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(KEY) ?? '{}') }
  } catch {
    return { ...DEFAULTS }
  }
}

export function setSettings(patch: Partial<Settings>) {
  const before = getSettings()
  const next = { ...before, ...patch }
  try {
    localStorage.setItem(KEY, JSON.stringify(next))
  } catch {
    /* ignore */
  }
  apply(next)
  if (next.theme !== before.theme) window.dispatchEvent(new CustomEvent(THEME_EVENT))
}

export function apply(s: Settings = getSettings()) {
  const el = document.documentElement
  if (s.theme === 'auto') el.removeAttribute('data-theme')
  else el.dataset.theme = s.theme
  if (s.scale === 'm') el.removeAttribute('data-scale')
  else el.dataset.scale = s.scale
  if (s.motion === 'full') el.removeAttribute('data-motion')
  else el.dataset.motion = s.motion
  if (s.reading) el.dataset.reading = '1'
  else el.removeAttribute('data-reading')
}

/** Reading mode: every Gate open, every masked lab value shown, nothing recorded, no stars. */
export function readingMode(): boolean {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? '{}').reading === true
  } catch {
    return false
  }
}

/** True when the page is currently dark (system or chosen). */
export function isDark(): boolean {
  const t = document.documentElement.dataset.theme
  if (t) return t === 'dark'
  return matchMedia('(prefers-color-scheme: dark)').matches
}

/** True when animations should be skipped (system setting or the reader's choice). */
export function reducedMotion(): boolean {
  return document.documentElement.dataset.motion === 'reduce' || matchMedia('(prefers-reduced-motion: reduce)').matches
}

/** Call fn whenever the page switches between light and dark, from the system or from the settings menu. */
export function onThemeChange(fn: () => void): () => void {
  const mq = matchMedia('(prefers-color-scheme: dark)')
  mq.addEventListener('change', fn)
  window.addEventListener(THEME_EVENT, fn)
  return () => {
    mq.removeEventListener('change', fn)
    window.removeEventListener(THEME_EVENT, fn)
  }
}

/** Inline <head> script: apply saved settings before the first paint (no flash of the wrong theme). */
export const settingsBootScript = `try{var s=JSON.parse(localStorage.getItem('${KEY}')||'{}'),e=document.documentElement;if(s.theme&&s.theme!=='auto')e.dataset.theme=s.theme;if(s.scale&&s.scale!=='m')e.dataset.scale=s.scale;if(s.motion==='reduce')e.dataset.motion='reduce';if(s.reading)e.dataset.reading='1'}catch(_){}`
