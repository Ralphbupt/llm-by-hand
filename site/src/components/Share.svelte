<script lang="ts">
  /**
   * Share a level: the system share sheet where there is one (phones), otherwise a small menu with
   * "Copy link", "Copy text" and, once the level is cleared, "Save image" (a 1200×630 card drawn on a canvas).
   * Links use the page's own origin, so they become real links once the site is deployed.
   */
  import { onMount } from 'svelte'
  import { subscribe } from '@lib/progress'
  import { scoreOf } from '@lib/marks'

  let { slug, level, title, question, compact = false }: { slug: string; level: string; title: string; question: string; compact?: boolean } = $props()

  let open = $state(false)
  let note = $state('')
  let stars = $state(0)
  let menu: HTMLDivElement
  let btn: HTMLButtonElement

  onMount(() => {
    const sync = () => (stars = scoreOf(slug)?.cleared ? (scoreOf(slug)?.stars ?? 0) : 0)
    sync()
    const off = subscribe(sync)
    const outside = (e: PointerEvent) => {
      if (open && !menu?.contains(e.target as Node) && !btn.contains(e.target as Node)) open = false
    }
    document.addEventListener('pointerdown', outside)
    return () => { off(); document.removeEventListener('pointerdown', outside) }
  })

  const url = () => `${location.origin}/learn/${slug}/`
  const starText = (n: number) => '★'.repeat(n) + '☆'.repeat(3 - n)
  const text = () =>
    stars
      ? `I cleared level ${level} · ${title} on LLM by Hand ${starText(stars)}, computing every number by hand.`
      : `Level ${level} · ${title}: ${question} Learning it by computing every number by hand on LLM by Hand.`

  async function share() {
    note = ''
    // the system share sheet, where the browser has one (mostly phones)
    if (navigator.share && matchMedia('(pointer: coarse)').matches) {
      try {
        await navigator.share({ title: `${title} · LLM by Hand`, text: text(), url: url() })
        return
      } catch {
        /* cancelled or refused: fall through to the menu */
      }
    }
    open = !open
  }

  async function copy(what: 'link' | 'text') {
    const s = what === 'link' ? url() : `${text()} ${url()}`
    try {
      await navigator.clipboard.writeText(s)
      note = what === 'link' ? 'Link copied.' : 'Text copied.'
    } catch {
      note = s
    }
  }

  function css(name: string, fallback: string) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
  }

  function wrap(ctx: CanvasRenderingContext2D, s: string, x: number, y: number, max: number, lh: number) {
    const words = s.split(' ')
    let line = ''
    for (const w of words) {
      const t = line ? `${line} ${w}` : w
      if (ctx.measureText(t).width > max && line) {
        ctx.fillText(line, x, y)
        y += lh
        line = w
      } else line = t
    }
    ctx.fillText(line, x, y)
    return y
  }

  function saveImage() {
    const cv = document.createElement('canvas')
    cv.width = 1200
    cv.height = 630
    const g = cv.getContext('2d')!
    const bg = css('--bg', '#16161a'), fg = css('--fg', '#e6e6e3'), dim = css('--dim', '#8b8b93')
    const line = css('--line', '#33333b'), accent = css('--accent', '#7aa2f7'), ok = css('--ok', '#7bc97b')
    g.fillStyle = bg
    g.fillRect(0, 0, 1200, 630)
    // graph paper, like the home page
    g.strokeStyle = line
    g.globalAlpha = 0.5
    for (let x = 0; x <= 1200; x += 30) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, 630); g.stroke() }
    for (let y = 0; y <= 630; y += 30) { g.beginPath(); g.moveTo(0, y); g.lineTo(1200, y); g.stroke() }
    g.globalAlpha = 1
    const display = "'Bricolage Grotesque Variable', system-ui, sans-serif"
    g.fillStyle = accent
    g.font = `700 30px ${display}`
    g.fillText(`Level ${level}`, 80, 120)
    g.fillStyle = fg
    g.font = `750 76px ${display}`
    let y = wrap(g, title, 80, 210, 1040, 84)
    g.fillStyle = dim
    g.font = `400 34px system-ui, sans-serif`
    y = wrap(g, question, 80, y + 70, 1040, 46)
    if (stars) {
      g.fillStyle = ok
      g.font = `700 64px system-ui, sans-serif`
      g.fillText(starText(stars), 80, 540)
    }
    g.fillStyle = fg
    g.font = `700 32px ${display}`
    g.textAlign = 'right'
    g.fillText('LLM by Hand', 1120, 540)
    g.fillStyle = dim
    g.font = `400 24px system-ui, sans-serif`
    g.fillText('computing every number by hand', 1120, 578)
    const a = document.createElement('a')
    a.href = cv.toDataURL('image/png')
    a.download = `llm-by-hand-${slug}.png`
    a.click()
    note = 'Image saved.'
  }
</script>

<div class="share" class:compact>
  <button bind:this={btn} class="sbtn" aria-label="Share" aria-expanded={open} aria-haspopup="menu" onclick={share}>
    <svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M12 3v12M7 8l5-5 5 5M5 13v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6" /></svg>
    <span class="slabel">Share</span>
  </button>
  {#if open}
    <div class="menu" role="menu" bind:this={menu}>
      <button role="menuitem" onclick={() => copy('link')}>Copy link</button>
      <button role="menuitem" onclick={() => copy('text')}>Copy text with link</button>
      {#if stars}<button role="menuitem" onclick={saveImage}>Save image</button>{/if}
      {#if note}<p class="note">{note}</p>{/if}
    </div>
  {/if}
</div>

<style>
  .share { position: relative; display: inline-block; }
  .sbtn { display: inline-flex; align-items: center; gap: 0.35rem; font: inherit; font-size: 0.82rem; padding: 0.25rem 0.7rem;
    border: 1px solid var(--line); border-radius: 999px; background: var(--card); color: var(--dim); cursor: pointer; }
  .sbtn:hover, .sbtn[aria-expanded='true'] { color: var(--accent); border-color: var(--accent); }
  .menu { position: absolute; right: 0; top: calc(100% + 0.35rem); z-index: 40; min-width: 12rem; display: grid; gap: 0.2rem;
    padding: 0.4rem; border: 1px solid var(--line); border-radius: 8px; background: var(--card); box-shadow: 0 6px 20px rgb(0 0 0 / 0.25); }
  .compact .menu { left: 0; right: auto; }
  /* phones: in the page header it is just the icon, on the same line as the level info */
  @media (max-width: 560px) {
    .share:not(.compact) .slabel { display: none; }
    .share:not(.compact) .sbtn { width: 2.5rem; height: 2.5rem; justify-content: center; padding: 0; }
  }
  .menu button { font: inherit; font-size: 0.85rem; text-align: left; padding: 0.35rem 0.6rem; border: 0; border-radius: 5px; background: transparent; color: var(--fg); cursor: pointer; }
  .menu button:hover { background: var(--bg); }
  .note { margin: 0.2rem 0.6rem 0.3rem; font-size: 0.78rem; color: var(--ok); word-break: break-all; }
</style>
