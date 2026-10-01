<script lang="ts">
  /**
   * The gear menu: theme, text size, motion, the "Show answer" reminder, reading mode, analytics consent (when the site
   * has an analytics ID), and progress (export, import, reset).
   * Everything is stored in this browser only.
   */
  import { onMount } from 'svelte'
  import { getSettings, setSettings, type Motion, type Scale, type Theme } from '@lib/settings'
  import { exportAll, importAll, reset, revealNeedsConfirm, setReadingMode, setRevealNeedsConfirm } from '@lib/progress'
  import { analyticsEnabled, getConsent, setConsent } from '@lib/analytics'

  let open = $state(false)
  let theme = $state<Theme>('auto')
  let scale = $state<Scale>('m')
  let motion = $state<Motion>('full')
  let askReveal = $state(true)
  let reading = $state(false)
  // analytics consent (only when the site is built with a GA4 ID): change your mind any time
  const hasAnalytics = analyticsEnabled()
  let counting = $state(false)
  let panel: HTMLDivElement
  let btn: HTMLButtonElement

  // progress tools
  let mode = $state<'none' | 'export' | 'import' | 'reset'>('none')
  let text = $state('')
  let note = $state('')

  onMount(() => {
    const s = getSettings()
    theme = s.theme
    scale = s.scale
    motion = s.motion
    askReveal = revealNeedsConfirm()
    reading = s.reading
    counting = getConsent() === 'granted'
    // the lesson page's "Turn off" button changes it too
    const onChange = () => (reading = getSettings().reading)
    window.addEventListener('quiz:progress', onChange)
    const onConsent = () => (counting = getConsent() === 'granted')
    window.addEventListener('llmbh:consent', onConsent)
    const outside = (e: PointerEvent) => {
      if (open && !panel?.contains(e.target as Node) && !btn.contains(e.target as Node)) open = false
    }
    const esc = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) { open = false; btn.focus() }
    }
    document.addEventListener('pointerdown', outside)
    document.addEventListener('keydown', esc)
    return () => {
      document.removeEventListener('pointerdown', outside)
      document.removeEventListener('keydown', esc)
      window.removeEventListener('quiz:progress', onChange)
      window.removeEventListener('llmbh:consent', onConsent)
    }
  })

  function startExport() {
    mode = 'export'
    text = exportAll()
    note = ''
    // the main way: a small file the learner can keep or move to another computer
    const url = URL.createObjectURL(new Blob([text], { type: 'application/json' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `llm-by-hand-progress-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
    note = 'Saved a progress file. Open it with Import on another browser or computer.'
  }
  async function importFile(e: Event) {
    const f = (e.currentTarget as HTMLInputElement).files?.[0]
    if (!f) return
    text = await f.text()
    doImport()
  }
  // focus the first control when the panel opens, so keyboard users land inside it
  $effect(() => {
    if (open) queueMicrotask(() => panel?.querySelector<HTMLElement>('button, input')?.focus())
  })
  async function copy() {
    try {
      await navigator.clipboard.writeText(text)
      note = 'Copied. Paste it into Import on another browser or computer.'
    } catch {
      note = 'Select the text and copy it.'
    }
  }
  function doImport() {
    try {
      const parsed = JSON.parse(text)
      if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) throw new Error()
      importAll(text)
      note = `Imported ${Object.keys(parsed).filter((k) => !k.startsWith('~')).length} answers.`
      mode = 'none'
    } catch {
      note = 'That doesn’t look like exported progress. Paste the whole text from Export.'
    }
  }
  function doReset() {
    reset()
    note = 'Progress cleared.'
    mode = 'none'
  }

  const themes: [Theme, string][] = [['auto', 'Auto'], ['light', 'Light'], ['dark', 'Dark']]
  const scales: [Scale, string][] = [['s', 'Small'], ['m', 'Medium'], ['l', 'Large']]
</script>

<div class="settings">
  <button bind:this={btn} class="gear" class:reading aria-label={reading ? 'Settings (reading mode is on)' : 'Settings'} aria-expanded={open} aria-haspopup="dialog" onclick={() => (open = !open)}>
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path fill="currentColor" d="M19.4 13a7.6 7.6 0 0 0 0-2l2-1.6-2-3.4-2.4 1a7.4 7.4 0 0 0-1.7-1L15 3.5h-4l-.4 2.5a7.4 7.4 0 0 0-1.7 1l-2.4-1-2 3.4L6.6 11a7.6 7.6 0 0 0 0 2l-2 1.6 2 3.4 2.4-1a7.4 7.4 0 0 0 1.7 1l.4 2.5h4l.4-2.5a7.4 7.4 0 0 0 1.7-1l2.4 1 2-3.4zM13 15.5a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7z" transform="translate(-1 0)" />
    </svg>
  </button>

  {#if open}
    <div class="panel" role="dialog" aria-label="Settings" bind:this={panel}>
      <div class="row">
        <span class="k">Theme</span>
        <div class="seg">
          {#each themes as [v, l]}
            <button class:on={theme === v} aria-pressed={theme === v} onclick={() => { theme = v; setSettings({ theme: v }) }}>{l}</button>
          {/each}
        </div>
      </div>
      <p class="sub">Auto follows your system.</p>

      <div class="row">
        <span class="k">Text size</span>
        <div class="seg">
          {#each scales as [v, l]}
            <button class:on={scale === v} aria-pressed={scale === v} onclick={() => { scale = v; setSettings({ scale: v }) }}>{l}</button>
          {/each}
        </div>
      </div>

      <label class="check">
        <input type="checkbox" checked={motion === 'reduce'} onchange={(e) => { motion = e.currentTarget.checked ? 'reduce' : 'full'; setSettings({ motion }) }} />
        Reduce motion
      </label>
      <label class="check">
        <input type="checkbox" checked={askReveal} onchange={(e) => { askReveal = e.currentTarget.checked; setRevealNeedsConfirm(askReveal) }} />
        Ask before showing an answer
      </label>
      <label class="check">
        <input type="checkbox" checked={reading} onchange={(e) => { reading = e.currentTarget.checked; setReadingMode(reading) }} />
        Reading mode: open every part, no stars
      </label>
      <p class="sub">Your answers and stars stay as they are. Nothing new is saved while it is on.</p>
      {#if hasAnalytics}
        <label class="check">
          <input type="checkbox" checked={counting} onchange={(e) => { counting = e.currentTarget.checked; setConsent(counting ? 'granted' : 'denied') }} />
          Share anonymous usage stats
        </label>
        <p class="sub">Google Analytics, no ads. Nothing you type is sent.</p>
      {/if}

      <div class="hr"></div>
      <div class="row">
        <span class="k">Progress</span>
        <div class="acts">
          <button class="act" onclick={startExport}>Export</button>
          <button class="act" onclick={() => { mode = 'import'; text = ''; note = '' }}>Import</button>
          <button class="act danger" onclick={() => { mode = 'reset'; note = '' }}>Reset…</button>
        </div>
      </div>
      <p class="sub">Saved in this browser only.</p>

      {#if mode === 'export'}
        <button class="link" onclick={copy}>Or copy it as text</button>
      {:else if mode === 'import'}
        <label class="file">Choose a progress file <input type="file" accept="application/json,.json" onchange={importFile} /></label>
        <textarea rows="3" bind:value={text} placeholder="…or paste exported progress here"></textarea>
        <button class="act" onclick={doImport} disabled={!text.trim()}>Import the pasted text</button>
      {:else if mode === 'reset'}
        <p class="warn">This clears every answer on every level in this browser. It can’t be undone.</p>
        <div class="seg">
          <button class="danger" onclick={doReset}>Clear all progress</button>
          <button onclick={() => (mode = 'none')}>Cancel</button>
        </div>
      {/if}
      {#if note}<p class="note">{note}</p>{/if}
    </div>
  {/if}
</div>

<style>
  .settings { position: relative; }
  .gear {
    display: grid; place-items: center; width: 2rem; height: 2rem; border-radius: 999px;
    border: 1px solid var(--line); background: var(--card); color: var(--dim); cursor: pointer;
  }
  .gear:hover, .gear[aria-expanded='true'] { color: var(--accent); border-color: var(--accent); }
  .gear { position: relative; }
  /* reading mode is on: a small dot on the gear */
  .gear.reading::after {
    content: ''; position: absolute; top: -2px; right: -2px; width: 0.55rem; height: 0.55rem; border-radius: 999px;
    background: var(--accent); border: 2px solid var(--bg);
  }
  .panel {
    position: absolute; right: 0; top: calc(100% + 0.4rem); z-index: 60; width: min(20rem, calc(100vw - 2rem));
    padding: 0.8rem 0.9rem; border: 1px solid var(--line); border-radius: 10px; background: var(--card);
    box-shadow: 0 8px 28px rgb(0 0 0 / 0.25); font-size: 0.88rem; display: grid; gap: 0.45rem;
  }
  .row { display: flex; align-items: center; justify-content: space-between; gap: 0.6rem; }
  .k { font-weight: 600; }
  .sub { margin: -0.3rem 0 0; color: var(--dim); font-size: 0.75rem; }
  .seg { display: inline-flex; border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
  .seg button { font: inherit; font-size: 0.8rem; padding: 0.2rem 0.55rem; border: 0; border-left: 1px solid var(--line); background: var(--bg); color: var(--fg); cursor: pointer; }
  .seg button:first-child { border-left: 0; }
  .seg button.on { color: var(--accent); background: var(--highlight); }
  .acts { display: inline-flex; gap: 0.35rem; flex-wrap: wrap; }
  .link { font: inherit; font-size: 0.8rem; background: none; border: 0; padding: 0; color: var(--accent); text-decoration: underline; cursor: pointer; justify-self: start; }
  .file { font-size: 0.82rem; display: grid; gap: 0.2rem; }
  @media (max-width: 760px) { .seg button, .act { min-height: 2.5rem; } }
  .check { display: flex; gap: 0.45rem; align-items: center; cursor: pointer; }
  .hr { height: 1px; background: var(--line); margin: 0.2rem 0; }
  textarea { width: 100%; font-family: var(--mono); font-size: 0.75rem; padding: 0.4rem; border: 1px solid var(--line); border-radius: 4px; background: var(--bg); color: var(--fg); resize: vertical; }
  .act { justify-self: start; font: inherit; font-size: 0.82rem; padding: 0.2rem 0.8rem; border: 1px solid var(--accent); border-radius: 4px; background: transparent; color: var(--accent); cursor: pointer; }
  .act:disabled { opacity: 0.5; cursor: default; }
  .warn { margin: 0; color: var(--warn); font-size: 0.82rem; }
  .danger { color: var(--warn) !important; }
  .note { margin: 0; color: var(--ok); font-size: 0.8rem; }
</style>
