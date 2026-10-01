<script lang="ts">
  import { onMount } from 'svelte'
  import { gradeCode, type GradeResult } from '@lib/grade'
  import { debugOn, hasReal, pass, recordMiss, subscribe, wasShown } from '@lib/progress'
  import RevealAnswer from './RevealAnswer.svelte'
  import NoWrapText from './NoWrapText.svelte'
  import { py, type PyStatus } from '@lib/pyodide/client'
  import type { CodeEx } from '@lib/quiz'

  // practice: start fresh even if already solved (the mistake book's "redo"); solving never un-solves anything
  let { id, ex, practice = false }: { id: string; ex: CodeEx; practice?: boolean } = $props()

  let code = $state(ex.template)
  let status = $state<PyStatus>('idle')
  let result = $state<GradeResult | null>(null)
  let done = $state(false)
  let failed = $state<string | null>(null)
  let misses = $state(0)
  let shown = $state(false)
  let box: HTMLTextAreaElement
  let showAnswer = $state(false)
  const solution = (ex as CodeEx & { solution?: string }).solution

  onMount(() => {
    if (!practice && hasReal(id)) done = true
    if (!practice && wasShown(id)) shown = true
    const syncDbg = () => {
      showAnswer = debugOn('answers')
      if (!practice && !done && hasReal(id)) { done = true; shown = wasShown(id) }
    }
    syncDbg()
    const unsubDbg = subscribe(syncDbg)
    // Never move focus on mount: the learner may be typing elsewhere (see firstClick).
    const unsubPy = py.onStatus((s) => {
      status = s
      if (s === 'ready') { everReady = true; slow = false; clearTimeout(slowTimer) }
    })
    return () => { unsubDbg(); unsubPy(); clearTimeout(slowTimer) }
  })

  // The first time the learner clicks into the editor (and hasn't edited yet), select ____ so typing replaces it.
  let selectedOnce = false
  function firstClick() {
    if (selectedOnce) return
    selectedOnce = true
    const at = code.indexOf('____')
    if (at < 0 || code !== ex.template) return
    // after the browser has placed the caret from the click
    requestAnimationFrame(() => {
      if (box.selectionStart === box.selectionEnd) box.setSelectionRange(at, at + 4)
    })
  }

  // Tab inserts four spaces (Python indents); Esc, then Tab, leaves the editor as usual.
  let escaped = false
  function keydown(e: KeyboardEvent) {
    if (e.key === 'Escape') { escaped = true; return }
    if (e.key === 'Tab' && !escaped && !e.shiftKey) {
      e.preventDefault()
      const { selectionStart: a, selectionEnd: b } = box
      code = code.slice(0, a) + '    ' + code.slice(b)
      requestAnimationFrame(() => box.setSelectionRange(a + 4, a + 4))
      return
    }
    if ((e.key === 'Enter') && (e.metaKey || e.ctrlKey)) { e.preventDefault(); run(); return }
    // Enter keeps the indentation of the line above, one level more after a line that ends in ':'
    if (e.key === 'Enter' && !e.shiftKey && !e.altKey && !e.isComposing) {
      e.preventDefault()
      const { selectionStart: a, selectionEnd: b } = box
      const ins = '\n' + nextIndent(code.slice(0, a))
      code = code.slice(0, a) + ins + code.slice(b)
      requestAnimationFrame(() => { box.setSelectionRange(a + ins.length, a + ins.length); measure() })
    }
    escaped = false
  }
  /** The indentation for a new line, from the text before the caret. */
  function nextIndent(before: string): string {
    const line = before.slice(before.lastIndexOf('\n') + 1)
    const lead = line.match(/^ */)![0]
    return line.trimEnd().endsWith(':') ? lead + '    ' : lead
  }

  // phones: say so when the code is wider than the box (the rest is a sideways swipe away)
  let wide = $state(false)
  function measure() { if (box) wide = box.scrollWidth > box.clientWidth + 2 }
  onMount(() => {
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(box)
    return () => ro.disconnect()
  })
  const rows = $derived(Math.max(3, code.split('\n').length + 1))

  // first load of Python: a thin progress bar, and a note if the network is slow
  let everReady = false
  let slow = $state(false)
  let slowTimer: ReturnType<typeof setTimeout> | undefined
  const firstLoad = $derived(!everReady && (status === 'loading' || status === 'running'))

  async function run() {
    failed = null
    result = null
    if (!everReady) {
      clearTimeout(slowTimer)
      slowTimer = setTimeout(() => (slow = true), 20_000)
    }
    try {
      const raw = await py.run(code, ex.tests.map((t) => ({ setup: t.setup, expr: t.expr })))
      result = gradeCode(ex, raw, misses + 1)
      if (result.ok) {
        done = true
        pass(id)
      } else {
        misses++
        if (!shown) recordMiss(id)
      }
    } catch (e: any) {
      failed = e.message ?? String(e)
      misses++
      if (!shown) recordMiss(id)
    }
  }

  // stuck: fill in the reference line, mark it as shown (unlocks what follows), and run it so the output is visible
  function reveal() {
    if (solution === undefined) return
    code = ex.template.replace('____', solution)
    shown = true
    done = true
    pass(id, { shown: true })
    run()
  }

  const label = $derived(
    status === 'loading' ? 'Loading Python (about 10 MB, only once)…'
      : status === 'running' ? 'Running…'
      : '▶ Run',
  )
</script>

<div class="code" class:done>
  <div class="prompt"><span class="tag">Code</span><NoWrapText text={ex.prompt} /></div>
  <textarea bind:this={box} bind:value={code} spellcheck="false" autocapitalize="off" autocomplete="off" wrap="off"
    rows={rows} aria-label={`Code: ${ex.prompt.replaceAll('`', '')}`} onpointerup={firstClick} onkeydown={keydown} oninput={measure}></textarea>
  {#if wide}<p class="swipe">← The code is wider than the box. Swipe sideways to see the rest. →</p>{/if}
  <p class="keys">Enter keeps the indent · Tab indents · Esc then Tab leaves the editor · ⌘/Ctrl + Enter runs</p>
  <div class="row">
    <button onclick={run} disabled={status === 'loading' || status === 'running'}>{label}</button>
    <button class="ghost" onclick={() => (code = ex.template)}>Reset</button>
    {#if done}<span class="ok">{shown ? 'Answer shown' : '✓ All tests pass'}</span>{/if}
  </div>

  {#if !done && misses > 0 && solution !== undefined}
    <RevealAnswer onreveal={reveal} />
  {/if}

  {#if showAnswer && solution !== undefined}
    <div class="dbg"><b>debug · answer for ____:</b> {solution}
      <button class="ghost fill" onclick={() => (code = ex.template.replace('____', solution))}>Insert it</button></div>
  {/if}

  {#if firstLoad}
    <div class="loadbar" role="progressbar" aria-label="Loading Python"><i></i></div>
    {#if slow}<p class="slow">The network seems slow. You can go on with the questions below and come back to run this.</p>{/if}
  {/if}

  {#if failed}
    <pre class="err">{failed}</pre>
    <button class="ghost retry" onclick={run}>Try again</button>
  {/if}

  {#if result}
    {#if result.stdout}
      <div class="label">Output</div>
      <pre class="out">{result.stdout}</pre>
    {/if}
    {#if result.error}
      <div class="label">Error</div>
      <pre class="err">{result.error}</pre>
    {/if}
    {#if result.tests}
      <div class="label">Tests</div>
      <ul class="tests">
        {#each result.tests as t, i}
          <li class:bad={!t.ok}>
            {t.ok ? '✓' : '✗'} test {i + 1}
            {#if !t.ok}
              <span class="dim">
                {#if t.error}{t.error}{:else if t.hashed}the code does not match{:else}expected {JSON.stringify(t.expect)}, got {JSON.stringify(t.got)}{/if}
              </span>
            {/if}
          </li>
        {/each}
      </ul>
    {/if}
    {#if result.hint}<p class="hint"><NoWrapText text={result.hint} /></p>{/if}
  {/if}

  {#if done && ex.after}
    <p class="after"><NoWrapText text={ex.after} /></p>
  {/if}
</div>

<style>
  .dbg { margin: 0.6rem 0 0; padding: 0.35rem 0.6rem; border: 1px dashed var(--warn); border-radius: 4px; font-size: 0.85rem; font-family: var(--mono); color: var(--warn); white-space: pre-wrap; }
  .dbg b { font-family: inherit; }
  .dbg .fill { margin-left: 0.6rem; font-size: 0.78rem; padding: 0.1rem 0.5rem; }

  .code {
    border: 1px solid var(--line);
    border-left: 3px solid var(--accent);
    border-radius: 6px;
    padding: 0.9rem 1rem;
    margin: 1.2rem 0;
    background: var(--card);
  }
  .code.done { border-left-color: var(--ok); }
  .prompt { margin-bottom: 0.6rem; }
  .tag {
    font-size: 0.72rem; padding: 0.1rem 0.4rem; border-radius: 3px;
    background: var(--accent); color: var(--on-solid); margin-right: 0.4rem; font-weight: 600;
  }
  textarea {
    width: 100%; box-sizing: border-box;
    font-family: var(--mono); font-size: 0.88rem; line-height: 1.5;
    padding: 0.7rem; border: 1px solid var(--field); border-radius: 4px;
    background: var(--bg); color: inherit; resize: vertical;
    white-space: pre; overflow-x: auto; tab-size: 4;
  }
  textarea:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
  .keys { margin: 0.25rem 0 0; font-size: 0.75rem; color: var(--dim); }
  .swipe { display: none; margin: 0.25rem 0 0; font-size: 0.78rem; color: var(--dim); }
  @media (max-width: 760px) { textarea { font-size: 16px; } .keys { display: none; } .swipe { display: block; } }
  .row { display: flex; gap: 0.5rem; align-items: center; margin-top: 0.6rem; flex-wrap: wrap; }
  @media (max-width: 760px) { .row button { min-height: 40px; } }
  button {
    font: inherit; padding: 0.3rem 0.9rem; border: 1px solid var(--line);
    border-radius: 4px; background: var(--bg); color: inherit; cursor: pointer;
  }
  button.ghost { color: var(--dim); }
  button:disabled { opacity: 0.55; cursor: default; }
  .ok { color: var(--ok); font-size: 0.9rem; }
  .label { margin-top: 0.8rem; font-size: 0.78rem; color: var(--dim); }
  pre {
    margin: 0.25rem 0 0; padding: 0.6rem; border-radius: 4px;
    background: var(--bg); border: 1px solid var(--line);
    font-family: var(--mono); font-size: 0.84rem; overflow-x: auto; white-space: pre-wrap;
  }
  pre.err { color: var(--warn); }
  .tests { margin: 0.25rem 0 0; padding-left: 1.1rem; font-size: 0.88rem; }
  .tests li.bad { color: var(--warn); }
  .dim { color: var(--dim); font-family: var(--mono); font-size: 0.8rem; }
  .hint { margin: 0.6rem 0 0; color: var(--fg); font-size: 0.9rem; }
  .after { margin: 0.8rem 0 0; padding-top: 0.6rem; border-top: 1px dashed var(--line); color: var(--fg); font-size: 0.92rem; }
  .loadbar { position: relative; height: 3px; margin-top: 0.5rem; border-radius: 2px; background: var(--line); overflow: hidden; }
  .loadbar i { position: absolute; inset: 0 auto 0 0; width: 35%; background: var(--accent); border-radius: 2px; animation: slide 1.2s ease-in-out infinite; }
  @keyframes slide { from { transform: translateX(-100%); } to { transform: translateX(290%); } }
  @media (prefers-reduced-motion: reduce) { .loadbar i { animation: none; width: 100%; opacity: 0.5; } }
  :global(html[data-motion='reduce']) .loadbar i { animation: none; width: 100%; opacity: 0.5; }
  .slow { margin: 0.4rem 0 0; font-size: 0.85rem; color: var(--dim); }
  .retry { margin-top: 0.4rem; }
</style>
