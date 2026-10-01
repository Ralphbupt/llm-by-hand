<script lang="ts">
  /**
   * LabFrame: the one standard chrome for every lab, so labs written by different people read the same way.
   *
   *   title · (what to do) · [view switch]
   *   ┌ picture ──────────────────────────┐   wide content scrolls inside, with a "swipe" cue on phones
   *   └───────────────────────────────────┘
   *   controls: primary · secondary …            Reset to the starting numbers
   *   readout: one live line
   *   legend
   *
   * `after` (optional) sits between the readout and the legend: a list or panel that must not push the controls
   * away from the picture.
   *
   * Buttons inside `controls` use the global classes `lab-btn`, `lab-btn primary`, `lab-btn ghost`.
   */
  import { onMount, type Snippet } from 'svelte'
  import { webglAvailable } from '@lib/three/webgl'

  /** `webgl: true` marks a view that needs WebGL; the id '3d' implies it */
  type View = { id: string; label: string; webgl?: boolean }
  type Props = {
    title: string
    /** one line: what to do with this lab ("Drag the arrows…") */
    hint?: string
    /** optional view switch, e.g. [{id:'map',label:'Map'},{id:'3d',label:'3D'}]; the exact-reading view goes first */
    views?: View[]
    view?: string
    /** show "Reset to the starting numbers" at the end of the controls row */
    onreset?: () => void
    /** gray it out when nothing has changed (it still never does harm when pressed) */
    resetDisabled?: boolean
    children: Snippet
    controls?: Snippet
    readout?: Snippet
    legend?: Snippet
    /** optional extra block after the readout and before the legend (e.g. a layer list and its panel) */
    after?: Snippet
    /** read-only: false when the browser has no WebGL (or ?no3d), so a 3D-only lab can draw a flat picture instead */
    has3d?: boolean
  }
  let {
    title, hint, views, view = $bindable(views?.[0]?.id), onreset, resetDisabled = false,
    children, controls, readout, legend, after, has3d = $bindable(true),
  }: Props = $props()

  // without WebGL (or with ?no3d) the 3D views are hidden, and a lab that starts in 3D falls back to its flat view
  const needsGl = (v: View) => v.webgl ?? v.id === '3d'
  const shown = $derived(has3d || !views ? views : views.filter((v) => !needsGl(v)))
  onMount(() => {
    has3d = webglAvailable()
    if (!has3d && views) {
      const cur = views.find((v) => v.id === view)
      const flat = views.find((v) => !needsGl(v))
      if (cur && needsGl(cur) && flat) view = flat.id
    }
  })

  // scroll boxes inside a lab (a wide table, a long row of cells): the same right-edge fade while there is more to see
  let frame: HTMLElement
  onMount(() => {
    const boxes = new Set<HTMLElement>()
    const mark = (el: HTMLElement) => {
      const more = el.scrollWidth > el.clientWidth + 2
      el.classList.toggle('lf-xs', more)
      el.classList.toggle('lf-xs-end', more && el.scrollLeft + el.clientWidth >= el.scrollWidth - 2)
    }
    const scan = () => {
      for (const el of frame.querySelectorAll<HTMLElement>('div, table, figure, pre, ol, ul')) {
        if (el === pic || boxes.has(el)) continue
        const ox = getComputedStyle(el).overflowX
        if (ox !== 'auto' && ox !== 'scroll') continue
        boxes.add(el)
        el.addEventListener('scroll', () => mark(el), { passive: true })
      }
      boxes.forEach(mark)
    }
    let t: ReturnType<typeof setTimeout> | undefined
    const later = () => { clearTimeout(t); t = setTimeout(scan, 250) }
    const ro = new ResizeObserver(later)
    ro.observe(frame)
    later()
    return () => { ro.disconnect(); clearTimeout(t) }
  })

  // a "swipe" cue when the picture is wider than the frame
  let pic: HTMLDivElement
  let scrolls = $state(false)
  let atEnd = $state(false)
  onMount(() => {
    const check = () => {
      scrolls = pic.scrollWidth > pic.clientWidth + 2
      atEnd = pic.scrollLeft + pic.clientWidth >= pic.scrollWidth - 2
    }
    const ro = new ResizeObserver(check)
    ro.observe(pic)
    if (pic.firstElementChild) ro.observe(pic.firstElementChild)
    pic.addEventListener('scroll', check, { passive: true })
    check()
    return () => { ro.disconnect(); pic.removeEventListener('scroll', check) }
  })
</script>

<section class="labframe" aria-label={title} bind:this={frame}>
  <header class="lf-head">
    <div class="lf-titles">
      <h4 class="lf-title">{title}</h4>
      {#if hint}<p class="lf-hint">{hint}</p>{/if}
    </div>
    {#if shown && shown.length > 1}
      <div class="lf-views" role="group" aria-label="View">
        {#each shown as v}
          <button type="button" class:on={view === v.id} aria-pressed={view === v.id} onclick={() => (view = v.id)}>{v.label}</button>
        {/each}
      </div>
    {/if}
  </header>

  <div class="lf-pic" class:scrolls class:at-end={atEnd} bind:this={pic} tabindex={scrolls ? 0 : undefined}>
    <div class="lf-pic-in">{@render children()}</div>
  </div>
  {#if scrolls}<p class="lf-swipe" aria-hidden="true">← swipe to see the rest →</p>{/if}

  {#if controls || onreset}
    <div class="lf-controls">
      {#if controls}<div class="lf-actions">{@render controls()}</div>{/if}
      {#if onreset}
        <button type="button" class="lab-btn ghost lf-reset" class:quiet={resetDisabled} onclick={onreset}>Reset to the starting numbers</button>
      {/if}
    </div>
  {/if}

  {#if readout}<div class="lf-readout" aria-live="polite">{@render readout()}</div>{/if}
  {#if after}<div class="lf-after">{@render after()}</div>{/if}
  {#if legend}<div class="lf-legend">{@render legend()}</div>{/if}
</section>

<style>
  .labframe { border: 1px solid var(--line); border-radius: 8px; background: var(--card); padding: 0.9rem 1rem 1rem; margin: 1.4rem 0;
    display: grid; gap: 0.7rem; min-width: 0; }
  .lf-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.8rem; flex-wrap: wrap; }
  .lf-titles { min-width: 0; }
  .lf-title { margin: 0; font-size: 0.95rem; font-weight: 650; line-height: 1.35; }
  .lf-hint { margin: 0.15rem 0 0; font-size: 0.85rem; color: var(--dim); line-height: 1.45; }
  .lf-views { display: inline-flex; border: 1px solid var(--field); border-radius: 999px; overflow: hidden; flex: none; }
  .lf-views button { font: inherit; font-size: 0.8rem; padding: 0.25rem 0.8rem; min-height: 2rem; border: 0; background: transparent; color: var(--dim); cursor: pointer; }
  .lf-views button + button { border-left: 1px solid var(--field); }
  .lf-views button.on { color: var(--accent); background: var(--highlight); }
  .lf-views button:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
  @media (pointer: coarse), (max-width: 760px) { .lf-views button { min-height: 2.5rem; padding: 0.3rem 1rem; } }
  .lf-pic { position: relative; overflow-x: auto; min-width: 0; }
  .lf-pic:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 4px; }
  .lf-pic-in { min-width: 0; }
  /* fade at the right edge while there is more to see */
  .lf-pic.scrolls:not(.at-end) { mask-image: linear-gradient(to right, #000 85%, transparent); -webkit-mask-image: linear-gradient(to right, #000 85%, transparent); }
  .labframe :global(.lf-xs:not(.lf-xs-end)) { mask-image: linear-gradient(to right, #000 88%, transparent); -webkit-mask-image: linear-gradient(to right, #000 88%, transparent); }
  .lf-swipe { margin: -0.4rem 0 0; font-size: 0.75rem; color: var(--dim); text-align: right; }
  .lf-controls { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; }
  .lf-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; flex: 1 1 auto; min-width: 0; }
  .lf-reset { margin-left: auto; }
  .lf-reset.quiet { color: var(--dim); }
  .lf-readout { font-family: var(--mono); font-size: 0.88rem; line-height: 1.5; padding: 0.45rem 0.6rem; border-radius: 6px; background: var(--bg);
    border: 1px solid var(--line); overflow-wrap: anywhere; }
  .lf-legend { font-size: 0.8rem; color: var(--dim); display: flex; flex-wrap: wrap; gap: 0.3rem 1rem; }
  @media (max-width: 760px) {
    .labframe { padding: 0.8rem 0.75rem 0.9rem; }
    /* the ghost button has no visible border, so its padding would look like an indent: line its text up with the controls */
    .lf-reset { margin-left: 0; padding-left: 0; padding-right: 0; border-left: 0; border-right: 0; }
  }
</style>
