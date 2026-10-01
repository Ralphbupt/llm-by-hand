<script lang="ts">
  /**
   * The model microscope: one short input goes through a whole tiny trained model, step by step.
   * Every tensor is shown with its named axes (each axis keeps one color everywhere), its numbers, and the shape of the
   * same tensor in the page's full model. Point at, tap or focus a number to read its full index.
   * Data: site/public/data/<data>/microscope.json, written by content/<part>/<data>/trace.py (any part, e.g. 1-foundations or 2-theory).
   */
  import { onMount } from 'svelte'
  import { fade } from 'svelte/transition'
  import LabFrame from './LabFrame.svelte'
  import { reducedMotion } from '@lib/settings'

  type Tensor = {
    name: string
    axes: [string, number][]
    big: string
    values: (number | null)[][]
    rows?: string[] | null
    cols?: string[] | null
    note?: string | null
  }
  type Step = { title: string; text: string; tensors: Tensor[]; top?: [string, number][]; targets?: string[]; loss?: number }
  type Data = { input: string; warning?: string; steps: Step[] }

  let { data: slug }: { data: string } = $props()
  let data = $state<Data | null>(null)
  let failed = $state(false)
  let k = $state(0)
  let pick = $state<{ t: number; r: number; c: number } | null>(null)
  let root: HTMLDivElement
  let rail = $state<HTMLOListElement>()
  // keep the current stop in view inside the rail (it scrolls sideways on phones) without moving the page
  $effect(() => {
    const i = k
    const li = rail?.children[i] as HTMLElement | undefined
    if (!rail || !li) return
    rail.scrollTo({ left: li.offsetLeft - rail.clientWidth / 2 + li.clientWidth / 2, behavior: 'smooth' })
  })

  onMount(async () => {
    try { data = await (await fetch(`/data/${slug}/microscope.json`)).json() } catch { failed = true }
  })

  const step = $derived(data ? data.steps[k] : null)
  function go(i: number) {
    if (!data) return
    k = Math.max(0, Math.min(data.steps.length - 1, i))
    pick = null
  }
  function onKey(e: KeyboardEvent) {
    const tag = (e.target as HTMLElement).tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA') return
    if (e.key === 'ArrowRight' && !(e.target as HTMLElement).closest('td')) { go(k + 1); e.preventDefault() }
    if (e.key === 'ArrowLeft' && !(e.target as HTMLElement).closest('td')) { go(k - 1); e.preventDefault() }
  }

  // One color per kind of axis, the same on every step: batch, positions, widths, heads, vocabulary.
  // Positions and widths label the heat tables, so they get the two category colors furthest from the
  // --pos / --neg cell colors (teal and magenta); heads and vocabulary never label a heat table.
  function axisColor(name: string) {
    if (name === 'B') return 'var(--cat-5)'
    if (name.startsWith('L')) return 'var(--cat-1)'
    if (name.startsWith('d_')) return 'var(--cat-4)'
    if (name === 'h') return 'var(--cat-3)'
    return 'var(--cat-2)'
  }
  // The table shows the last two axes: rows = second to last, columns = last. Leading axes are fixed at index 0.
  const colAxis = (t: Tensor) => t.axes[t.axes.length - 1]
  const rowAxis = (t: Tensor) => (t.axes.length >= 2 ? t.axes[t.axes.length - 2] : null)
  const lead = (t: Tensor) => t.axes.slice(0, Math.max(0, t.axes.length - 2))
  // two different axes with one size are easy to mix up (scores (L, L) is the same axis twice: fine)
  const clashing = (t: Tensor) => {
    const out = new Set<string>()
    t.axes.forEach(([n, v], i) => t.axes.forEach(([n2, v2], j) => { if (i !== j && v > 1 && v === v2 && n !== n2) { out.add(n); out.add(n2) } }))
    return out
  }
  const wide = (t: Tensor) => (t.values[0]?.length ?? 0) > 12

  function maxAbs(t: Tensor) {
    let m = 0
    for (const r of t.values) for (const v of r) if (v !== null) m = Math.max(m, Math.abs(v))
    return m || 1
  }
  // signed values: --pos / --neg, strength by size; a blocked score (−∞) is hatched
  function cellStyle(v: number | null, m: number) {
    if (v === null) return ''
    const p = Math.round((60 * Math.abs(v)) / m)
    return `background: color-mix(in srgb, var(${v >= 0 ? '--pos' : '--neg'}) ${p}%, var(--bg))`
  }
  const fmt = (v: number | null) => (v === null ? '−∞' : v.toFixed(2).replace('-', '−'))
  // token ids are labels, not amounts: whole numbers, shown plainly (no sign colors)
  // (a token-id tensor is (B, L): two axes, whole numbers; attention weights can also round to 0 and 1, but have three axes)
  const isIds = (t: Tensor) => t.axes.length === 2 && t.values.every((r) => r.every((v) => v !== null && Number.isInteger(v)))
  const fmtIn = (t: Tensor, v: number | null) => (v !== null && isIds(t) ? String(v) : fmt(v))
  // leading axes that are longer than 1 but not drawn (the table shows only index 0 of them)
  const sliced = (t: Tensor) => lead(t).filter(([, v]) => v > 1)
  // a table wider than its box: fade the right edge and say so, until it is scrolled to the end
  function cue(el: HTMLElement) {
    const check = () => {
      const more = el.scrollWidth > el.clientWidth + 2 && el.scrollLeft + el.clientWidth < el.scrollWidth - 2
      el.parentElement?.classList.toggle('more', more)
    }
    const ro = new ResizeObserver(check)
    ro.observe(el)
    el.addEventListener('scroll', check, { passive: true })
    check()
    return { destroy() { ro.disconnect(); el.removeEventListener('scroll', check) } }
  }
  const stepIn = () => ({ duration: reducedMotion() ? 0 : 180 })
  function topOf(row: (number | null)[], cols: string[] | null | undefined, n = 3) {
    return row
      .map((v, i) => ({ w: cols?.[i] ?? String(i), v: v ?? -Infinity }))
      .sort((a, b) => b.v - a.v)
      .slice(0, n)
  }
  function where(t: Tensor, r: number, c: number) {
    const parts = lead(t).map(([n]) => `${n}=0`)
    const ra = rowAxis(t)
    if (ra) parts.push(`${ra[0]}=${r}${t.rows?.[r] != null ? ` (${t.rows[r]})` : ''}`)
    const ca = colAxis(t)
    parts.push(`${ca[0]}=${c}${t.cols?.[c] != null ? ` (${t.cols[c]})` : ''}`)
    return `${t.name} [${parts.join(', ')}]`
  }
  const picked = $derived(step && pick ? step.tensors[pick.t] : null)
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div bind:this={root} onkeydown={onKey}>
<LabFrame
  title={data ? `The whole model under a microscope: “${data.input}”` : 'The whole model under a microscope'}
  hint="Step through one input, from token ids to the next token. Point at or tap any number to read where it sits."
>
  {#if failed}
    <p class="dim">The recorded run could not be loaded. Reload the page to try again.</p>
  {:else if !data || !step}
    <div class="skeleton" aria-hidden="true"></div>
    <p class="dim">Loading the recorded run…</p>
  {:else}
    <ol class="rail" bind:this={rail} aria-label="Steps through the model">
      {#each data.steps as s, i}
        <li class:on={i === k} class:past={i < k}>
          <button type="button" aria-current={i === k ? 'step' : undefined} aria-label={`Step ${i + 1}: ${s.title}`} title={s.title} onclick={() => go(i)}>{i + 1}</button>
        </li>
      {/each}
    </ol>

    {#key k}
    <div class="stepbody" in:fade={stepIn()}>
    <div class="stephead">
      <span class="sn">Step {k + 1} of {data.steps.length}</span>
      <h5>{step.title}</h5>
    </div>
    <p class="text">{step.text}</p>

    {#each step.tensors as t, ti}
      {@const clash = clashing(t)}
      {@const ra = rowAxis(t)}
      {@const ca = colAxis(t)}
      <div class="tensor">
        <div class="tname">
          <span class="nm">{t.name}</span>
          <span class="axes" aria-label="shape">
            (
            {#each t.axes as [n, v], ai}
              {#if ai}<span class="comma">,</span>{/if}
              <span class="ax" class:clash={clash.has(n)} style:--ax={axisColor(n)}><span class="axn">{n}</span> {v}</span>
            {/each}
            )
          </span>
        </div>
        <div class="big">In the full model: <span class="mono">{t.big}</span></div>
        {#if clash.size}
          <p class="clashnote"><b>Same size, different meaning:</b> {[...clash].join(' and ')} are both {t.axes.find(([n]) => clash.has(n))?.[1]} here. Distinguish them by position, never by size.</p>
        {/if}
        {#if t.note}<p class="note">{t.note}</p>{/if}
        {#if sliced(t).length}
          <p class="note">The table shows {sliced(t).map(([n, v]) => `${n} = 0 (of ${v})`).join(', ')}.</p>
        {/if}

        {#if wide(t)}
          <div class="tops">
            <p class="note toplbl">{t.values[0].length} {ca[0]} per row, too many to list. The three highest in each row:</p>
            {#each t.values as row, r}
              <div class="toprow">
                <span class="rl" style:--ax={ra ? axisColor(ra[0]) : 'var(--dim)'}>{t.rows?.[r] ?? r}</span>
                <span class="chips">
                  {#each topOf(row, t.cols) as e, j}
                    <span class="chip" class:first={j === 0}><span class="cw" style:--ax={axisColor(ca[0])}>{e.w}</span> <span class="cv">{fmt(e.v)}</span></span>
                  {/each}
                </span>
              </div>
            {/each}
          </div>
        {:else}
          {@const m = maxAbs(t)}
          {@const ids = isIds(t)}
          {@const showRows = !!ra && t.values.length > 1}
          <div class="tablewrap">
            <div class="axislabels">
              {#if ra && t.values.length > 1}<span class="axl" style:--ax={axisColor(ra[0])}>rows ↓ {ra[0]}</span>{/if}
              <span class="axl" style:--ax={axisColor(ca[0])}>columns → {ca[0]}</span>
            </div>
            <div class="scroll" use:cue>
              <table class:ids>
                <thead>
                  <tr>
                    {#if showRows}<th></th>{/if}
                    {#each t.values[0] as _, c}<th class="ch" style:--ax={axisColor(ca[0])}>{t.cols?.[c] ?? c}</th>{/each}
                  </tr>
                </thead>
                <tbody>
                  {#each t.values as row, r}
                    <tr>
                      {#if showRows && ra}<th class="rh" style:--ax={axisColor(ra[0])}>{t.rows?.[r] ?? r}</th>{/if}
                      {#each row as v, c}
                        <td
                          tabindex="0"
                          class:blocked={v === null}
                          class:sel={pick?.t === ti && pick.r === r && pick.c === c}
                          style={ids ? '' : cellStyle(v, m)}
                          onpointerenter={() => (pick = { t: ti, r, c })}
                          onfocus={() => (pick = { t: ti, r, c })}
                          onclick={() => (pick = { t: ti, r, c })}
                        >{ids ? v : fmt(v)}</td>
                      {/each}
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
            <p class="cue" aria-hidden="true">← swipe the table to see all {t.values[0].length} columns →</p>
          </div>
        {/if}
      </div>
    {/each}

    {#if step.top}
      <div class="next">
        <div class="lbl">Last position, as probabilities (softmax). The five highest:</div>
        {#each step.top as [w, p], i}
          <div class="bar" class:win={i === 0}><span class="w">{w}</span><span class="track"><i style="width: {Math.max(1, p * 100)}%"></i></span><span class="p">{p.toFixed(3)}</span></div>
        {/each}
        <p class="note">Next token: <b class="nt">{step.top[0][0]}</b>.
          {#if step.targets} While training, every row is compared with tgt_out = {step.targets.join(' ')}: loss {step.loss}.{/if}</p>
      </div>
    {/if}

    {#if data.warning && k === data.steps.length - 1}<p class="note caution">{data.warning}</p>{/if}
    </div>
    {/key}
  {/if}

  {#snippet controls()}
    <button type="button" class="lab-btn" onclick={() => go(k - 1)} disabled={!data || k === 0}>‹ Back</button>
    {@const end = !data || k === data.steps.length - 1}
    <button type="button" class="lab-btn" class:primary={!end} onclick={() => go(k + 1)} disabled={end}>Next step ›</button>
    {#if data && k === data.steps.length - 1}<button type="button" class="lab-btn ghost" onclick={() => go(0)}>Start again from step 1</button>{/if}
  {/snippet}

  {#snippet readout()}
    {#if picked && pick}
      {@const v = picked.values[pick.r][pick.c]}
      {where(picked, pick.r, pick.c)} = <b>{fmtIn(picked, v)}</b>{#if v === null} (blocked by the mask){/if}
    {:else}
      <span class="idle">Point at or tap a number to see its full index. ← → also move between steps.</span>
    {/if}
  {/snippet}

  {#snippet legend()}
    <span class="lg"><i class="sw" style="background: color-mix(in srgb, var(--pos) 60%, var(--bg))"></i>positive</span>
    <span class="lg"><i class="sw" style="background: color-mix(in srgb, var(--neg) 60%, var(--bg))"></i>negative</span>
    <span class="lg"><i class="sw hatch"></i>−∞ blocked by the mask</span>
    <span class="lg"><i class="dot" style="background: var(--cat-5)"></i>batch</span>
    <span class="lg"><i class="dot" style="background: var(--cat-1)"></i>positions</span>
    <span class="lg"><i class="dot" style="background: var(--cat-4)"></i>widths</span>
    <span class="lg"><i class="dot" style="background: var(--cat-3)"></i>heads</span>
    <span class="lg"><i class="dot" style="background: var(--cat-2)"></i>vocabulary</span>
  {/snippet}
</LabFrame>
</div>

<style>
  .dim { color: var(--dim); font-size: 0.88rem; margin: 0; }
  .skeleton { height: 14rem; border-radius: 6px; background: var(--bg); border: 1px dashed var(--line); }
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }

  /* the step rail: numbered stops on one line */
  .rail { list-style: none; display: flex; margin: 0; padding: 0.15rem 0; overflow-x: auto; scrollbar-width: none; position: relative; }
  .rail::-webkit-scrollbar { display: none; }
  .rail li { position: relative; flex: 1 0 auto; display: flex; justify-content: center; min-width: 2.4rem; }
  .rail li::before { content: ''; position: absolute; top: 50%; left: 0; right: 0; height: 2px; background: var(--line); }
  .rail li:first-child::before { left: 50%; }
  .rail li:last-child::before { right: 50%; }
  .rail li.past::before, .rail li.on::before { background: color-mix(in srgb, var(--accent) 45%, var(--line)); }
  .rail button { position: relative; font: inherit; font-family: var(--mono); font-size: 0.78rem; width: 2rem; height: 2rem; border-radius: 50%;
    border: 1.5px solid var(--field); background: var(--bg); color: var(--dim); cursor: pointer; }
  .rail li.past button { border-color: color-mix(in srgb, var(--accent) 55%, var(--field)); color: var(--fg); }
  .rail li.on button { background: var(--accent); border-color: var(--accent); color: var(--on-solid); font-weight: 700; }
  .rail button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

  .stephead { display: flex; align-items: baseline; gap: 0.6rem; flex-wrap: wrap; margin-top: 0.4rem; }
  .sn { font-family: var(--mono); font-size: 0.75rem; color: var(--dim); }
  h5 { margin: 0; font-size: 1rem; }
  .text { margin: 0.2rem 0 0.4rem; font-size: 0.92rem; max-width: 70ch; line-height: 1.55; }

  .tensor { margin: 0.9rem 0 0.4rem; padding-top: 0.7rem; border-top: 1px solid var(--line); }
  .tname { display: flex; flex-wrap: wrap; gap: 0.3rem 0.7rem; align-items: baseline; }
  .nm { font-weight: 650; font-size: 0.92rem; }
  .axes { font-family: var(--mono); font-size: 0.82rem; color: var(--dim); display: inline-flex; flex-wrap: wrap; align-items: baseline; gap: 0.15rem; }
  .comma { margin-right: 0.15rem; }
  .ax { color: var(--fg); padding: 0 0.3rem; border-radius: 4px; border: 1px solid color-mix(in srgb, var(--ax) 55%, transparent);
    background: color-mix(in srgb, var(--ax) 12%, transparent); }
  .axn { color: var(--ax); font-weight: 600; }
  .ax.clash { border-style: dashed; border-color: var(--fg); }
  .big { font-size: 0.8rem; color: var(--dim); margin-top: 0.2rem; }
  .mono { font-family: var(--mono); }
  .clashnote { font-size: 0.82rem; margin: 0.35rem 0 0; padding: 0.3rem 0.55rem; border-left: 2px dashed var(--fg); background: var(--bg); border-radius: 0 4px 4px 0; }
  .note { font-size: 0.82rem; color: var(--dim); margin: 0.3rem 0 0; }
  .caution { color: var(--fg); border-left: 2px solid var(--field); padding-left: 0.5rem; }

  .tablewrap { margin-top: 0.45rem; }
  .axislabels { display: flex; gap: 0.9rem; flex-wrap: wrap; font-size: 0.75rem; margin-bottom: 0.2rem; }
  .axl { color: var(--ax); font-family: var(--mono); font-weight: 600; }
  .scroll { overflow-x: auto; max-width: 100%; }
  .tablewrap:global(.more) .scroll { mask-image: linear-gradient(to right, #000 82%, transparent); -webkit-mask-image: linear-gradient(to right, #000 82%, transparent); }
  .cue { display: none; margin: 0.25rem 0 0; font-size: 0.75rem; color: var(--dim); text-align: right; }
  .tablewrap:global(.more) .cue { display: block; }
  table { border-collapse: separate; border-spacing: 2px; font-family: var(--mono); font-size: 0.78rem; width: auto; }
  th { font-weight: 500; padding: 0.15rem 0.35rem; border: 0; white-space: nowrap; }
  th.ch { color: var(--ax); text-align: right; border-bottom: 2px solid color-mix(in srgb, var(--ax) 50%, transparent); }
  th.rh { color: var(--ax); text-align: right; border-right: 2px solid color-mix(in srgb, var(--ax) 50%, transparent); }
  td { padding: 0.25rem 0.4rem; text-align: right; min-width: 2.9rem; border-radius: 3px; font-variant-numeric: tabular-nums; cursor: default; border: 1px solid transparent; }
  td:focus-visible { outline: 2px solid var(--accent); outline-offset: 0; }
  td.sel { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
  table.ids td { background: var(--bg); border-color: var(--line); }
  td.blocked { color: var(--dim); background: repeating-linear-gradient(135deg, var(--bg) 0 4px, var(--line) 4px 5px); }

  .tops { display: grid; gap: 0.3rem; margin-top: 0.45rem; }
  .toplbl { margin: 0 0 0.15rem; }
  .toprow { display: grid; grid-template-columns: 4.2rem minmax(0, 1fr); gap: 0.6rem; align-items: baseline; font-size: 0.82rem; }
  .rl { font-family: var(--mono); color: var(--ax); font-weight: 600; overflow-wrap: anywhere; border-right: 2px solid color-mix(in srgb, var(--ax) 50%, transparent); padding-right: 0.4rem; text-align: right; }
  .chips { display: flex; flex-wrap: wrap; gap: 0.3rem; }
  .chip { font-family: var(--mono); white-space: nowrap; padding: 0.1rem 0.45rem; border-radius: 4px; border: 1px solid var(--line); background: var(--bg); }
  .chip.first { border-color: var(--field); }
  .cw { color: var(--ax); font-weight: 600; }
  .cv { font-variant-numeric: tabular-nums; }

  .next { margin-top: 0.9rem; padding-top: 0.7rem; border-top: 1px solid var(--line); }
  .lbl { font-size: 0.82rem; color: var(--dim); margin-bottom: 0.35rem; }
  .bar { display: grid; grid-template-columns: 4.5rem minmax(0, 1fr) 3.4rem; gap: 0.5rem; align-items: center; font-family: var(--mono); font-size: 0.82rem; margin: 0.15rem 0; }
  .w { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .track { height: 0.75rem; background: var(--bg); border: 1px solid var(--line); border-radius: 3px; overflow: hidden; }
  .track i { display: block; height: 100%; background: color-mix(in srgb, var(--fg) 40%, var(--bg)); }
  .bar.win .track i { background: var(--accent); }
  .bar.win .w { color: var(--accent); font-weight: 700; }
  .p { text-align: right; font-variant-numeric: tabular-nums; }
  .nt { color: var(--accent); }

  .lg { display: inline-flex; align-items: center; gap: 0.35rem; }
  .sw { width: 0.9rem; height: 0.7rem; border-radius: 2px; border: 1px solid var(--line); display: inline-block; }
  .sw.hatch { background: repeating-linear-gradient(135deg, var(--bg) 0 3px, var(--field) 3px 4px); }
  .dot { width: 0.6rem; height: 0.6rem; border-radius: 50%; display: inline-block; }

  @media (max-width: 520px) {
    td { min-width: 2.6rem; padding: 0.25rem 0.3rem; }
    /* phones: the numbered stops become one segmented progress bar (each segment a 40px-tall tap target);
       the number is in "Step k of n" right below */
    .rail { overflow: visible; gap: 3px; padding: 0; }
    .rail li { flex: 1 1 0; min-width: 0; }
    .rail li::before { display: none; }
    .rail button { width: 100%; height: 2.5rem; border: 0; border-radius: 0; background: transparent; font-size: 0; color: transparent; padding: 0; }
    .rail button::after { content: ''; position: absolute; left: 0; right: 0; top: calc(50% - 3px); height: 6px; border-radius: 3px; background: var(--line); }
    .rail li.past button { border: 0; }
    .rail li.past button::after { background: color-mix(in srgb, var(--accent) 50%, var(--line)); }
    .rail li.on button { background: transparent; border: 0; }
    .rail li.on button::after { background: var(--accent); top: calc(50% - 4px); height: 8px; }
    .rail button:focus-visible { outline-offset: -2px; border-radius: 4px; }
    .bar { grid-template-columns: 3.6rem minmax(0, 1fr) 3rem; }
  }
</style>
