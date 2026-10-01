<script lang="ts">
  /**
   * Site search. The index (/search.json) is fetched the first time the dialog opens.
   * "/" opens it from anywhere (except while typing in a field). ↑ ↓ move, Enter opens, Esc closes.
   */
  import { onMount, tick } from 'svelte'
  import { search, type Doc, type Result } from '@lib/search'

  let open = $state(false)
  let q = $state('')
  let docs: Doc[] | null = null
  let loading = $state(false)
  let results = $state<Result[]>([])
  let active = $state(0)
  let input: HTMLInputElement
  let listEl: HTMLDivElement

  // flat list of links in display order, for arrow-key navigation
  const flat = $derived(
    results.flatMap((r) => r.hits.map((h) => ({ r, h, href: r.doc.url + (h.section.anchor ? `#${h.section.anchor}` : '') }))),
  )

  let opener: HTMLElement | null = null
  let dialogEl: HTMLDialogElement
  async function show() {
    opener = document.activeElement as HTMLElement | null
    open = true
    // showModal puts the dialog in the browser's top layer, so nothing on the page
    // (formulas, sticky sidebars, 3D canvases) can paint over it
    if (!dialogEl.open) dialogEl.showModal()
    await tick()
    input?.focus()
    input?.select()
    if (!docs && !loading) {
      loading = true
      try {
        docs = await (await fetch('/search.json')).json()
      } catch {
        docs = []
      }
      loading = false
      run()
    }
  }
  function hide() {
    open = false
    if (dialogEl?.open) dialogEl.close()
    // give focus back to whatever opened the dialog (the search button, or the page for "/")
    tick().then(() => opener?.focus?.())
  }
  // keep Tab inside the dialog while it is open
  function trap(e: KeyboardEvent) {
    if (e.key !== 'Tab' || !dialogEl) return
    const f = [...dialogEl.querySelectorAll<HTMLElement>('input, button, a[href], [tabindex]:not([tabindex="-1"])')].filter((x) => !x.hasAttribute('disabled'))
    if (!f.length) return
    const first = f[0], last = f[f.length - 1]
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
  }
  function run() {
    results = docs ? search(docs, q) : []
    active = 0
  }
  async function move(d: number) {
    if (!flat.length) return
    active = (active + d + flat.length) % flat.length
    await tick()
    listEl?.querySelector<HTMLElement>(`[data-i="${active}"]`)?.scrollIntoView({ block: 'nearest' })
  }
  function key(e: KeyboardEvent) {
    if (e.key === 'ArrowDown') { e.preventDefault(); move(1) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1) }
    else if (e.key === 'Enter' && flat[active]) { e.preventDefault(); go(flat[active].href) }
    else if (e.key === 'Escape') { e.preventDefault(); hide() }
  }
  function go(href: string) {
    hide()
    const here = location.pathname
    location.href = href
    // same page, different anchor: the browser only scrolls; make sure the hash change is applied
    if (href.split('#')[0] === here) location.hash = href.split('#')[1] ?? ''
  }

  onMount(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== '/' || open || e.metaKey || e.ctrlKey || e.altKey) return
      const t = e.target
      if (t instanceof Element && t.closest('input, textarea, select, [contenteditable="true"]')) return
      e.preventDefault()
      show()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  })

  const kindLabel = (r: Result) => (r.doc.kind === 'term' ? 'Glossary' : `Level ${r.doc.level}`)
</script>

<button class="search-btn" aria-label="Search (press /)" title="Search (/)" onclick={show}>
  <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
    <circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="currentColor" stroke-width="2" />
    <path d="M15.5 15.5 21 21" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
  </svg>
</button>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
<dialog
  class="dialog" aria-label="Search the course" bind:this={dialogEl}
  onkeydown={trap}
  oncancel={(e) => { e.preventDefault(); hide() }}
  onclick={(e) => { if (e.target === dialogEl) hide() }}
>
  {#if open}
  <div class="inner">
    <div class="bar">
      <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
        <circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="currentColor" stroke-width="2" />
        <path d="M15.5 15.5 21 21" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
      </svg>
      <input
        bind:this={input}
        bind:value={q}
        oninput={run}
        onkeydown={key}
        placeholder="Search levels and terms, e.g. softmax, mask, LayerNorm"
        aria-label="Search"
        aria-controls="search-results"
        autocomplete="off"
        spellcheck="false"
      />
      <button class="close" onclick={hide} aria-label="Close search">Esc</button>
    </div>

    <div class="results" id="search-results" bind:this={listEl} role="listbox">
      {#if loading}
        <p class="empty">Loading the index…</p>
      {:else if !q.trim()}
        <p class="empty">Type a word or two. Every word must appear. ↑ ↓ to move, Enter to open.</p>
      {:else if !results.length}
        <p class="empty">Nothing matches “{q}”. Try fewer or shorter words.</p>
      {:else}
        {#each results as r}
          {@const solo = r.hits.length === 1}
          <!-- a page with one hit is one result: its title sits inside the link, so the highlight covers all of it -->
          <div class="group">
            {#if !solo}<div class="ghead"><span class="lv">{kindLabel(r)}</span> {r.doc.title}</div>{/if}
            {#each r.hits as h}
              {@const i = flat.findIndex((f) => f.h === h)}
              <a
                href={r.doc.url + (h.section.anchor ? `#${h.section.anchor}` : '')}
                class="hit" class:on={i === active} data-i={i} role="option" aria-selected={i === active}
                onmouseenter={() => (active = i)}
                onclick={(e) => { e.preventDefault(); go(r.doc.url + (h.section.anchor ? `#${h.section.anchor}` : '')) }}
              >
                {#if solo}<span class="ghead in"><span class="lv">{kindLabel(r)}</span> {r.doc.title}</span>{/if}
                {#if h.section.heading || r.doc.kind === 'level'}<span class="sec">{h.section.heading || 'Intro'}</span>{/if}
                <span class="snip">{@html h.snippet}</span>
              </a>
            {/each}
          </div>
        {/each}
      {/if}
    </div>
  </div>
  {/if}
</dialog>

<style>
  .search-btn {
    display: grid; place-items: center; width: 2rem; height: 2rem; border-radius: 999px;
    border: 1px solid var(--line); background: var(--card); color: var(--dim); cursor: pointer;
  }
  .search-btn:hover { color: var(--accent); border-color: var(--accent); }
  .dialog {
    margin: 8vh auto auto; padding: 0;
    width: min(40rem, calc(100vw - 2rem)); max-width: none; max-height: 80vh;
    background: var(--card); color: var(--fg); border: 1px solid var(--line); border-radius: 12px; box-shadow: 0 16px 48px rgb(0 0 0 / 0.35);
    overflow: hidden;
  }
  .dialog::backdrop { background: rgb(0 0 0 / 0.45); }
  .inner { display: flex; flex-direction: column; max-height: 80vh; }
  .bar { display: flex; align-items: center; gap: 0.6rem; padding: 0.7rem 0.9rem; border-bottom: 1px solid var(--line); color: var(--dim); }
  .bar input { flex: 1; min-width: 0; font: inherit; font-size: 1rem; border: 0; outline: 0; background: transparent; color: var(--fg); }
  .close { font: inherit; font-size: 0.72rem; font-family: var(--mono); padding: 0.1rem 0.45rem; border: 1px solid var(--line); border-radius: 4px; background: var(--bg); color: var(--dim); cursor: pointer; }
  .results { overflow-y: auto; padding: 0.4rem 0.4rem 0.8rem; }
  .empty { margin: 0.6rem 0.6rem; color: var(--dim); font-size: 0.9rem; }
  .group { margin-top: 0.5rem; }
  .ghead { padding: 0.2rem 0.6rem; font-weight: 600; font-size: 0.88rem; }
  .ghead.in { display: block; padding: 0 0 0.15rem; }
  .lv { font-family: var(--mono); font-size: 0.72rem; color: var(--dim); font-weight: 400; margin-right: 0.3rem; }
  .hit { display: block; padding: 0.45rem 0.6rem; border-radius: 6px; color: var(--fg); text-decoration: none; }
  .hit.on { background: color-mix(in srgb, var(--accent) 14%, transparent); }
  .sec { display: block; color: var(--accent); font-size: 0.85rem; }
  .snip { display: block; color: var(--dim); font-size: 0.82rem; line-height: 1.5; }
  .snip :global(mark) { background: var(--highlight); color: var(--fg); border-radius: 2px; padding: 0 1px; box-shadow: inset 0 -2px 0 var(--accent); }
  @media (max-width: 560px) {
    .dialog { margin: 0; width: 100vw; max-height: 100dvh; height: 100dvh; border-radius: 0; border: 0; }
    .inner { max-height: 100dvh; height: 100%; }
  }
</style>
