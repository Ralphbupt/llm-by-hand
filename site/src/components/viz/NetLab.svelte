<script lang="ts">
  /**
   * The standard frame for a Net3D placement: LabFrame with a Flat / 3D switch, step buttons (start, back, play,
   * next), a one-line readout with the step's text, the layer list (focusable, read by screen readers, the keyboard
   * way to select a layer) and the panel of the selected layer (name, shape, parameters, current values).
   * Lesson labs (BackpropNetLab, MlpNetLab, …) build a spec and render this.
   */
  import { onMount, type Snippet } from 'svelte'
  import LabFrame from './LabFrame.svelte'
  import Net3D from '../viz3d/Net3D.svelte'
  import Net2D from '../viz3d/Net2D.svelte'
  import { flat, fmtNum, fmtShape, groupTones, paramsOf, stateAt, type Net3DSpec, type NetValues } from '@lib/three/net'

  type Props = {
    spec: Net3DSpec
    title: string
    /** what to do */
    hint?: string
    /** one line under the picture: what to look at */
    caption: string
    ariaLabel: string
    /** hide parameter counts (until a question about them is answered) */
    hideParams?: boolean
    /** what the readout says before the first step */
    idle?: string
    /** extra controls before the step buttons (e.g. width and depth) */
    extra?: Snippet
    /** start on this step (−1 = before the first) */
    start?: number
    numbers?: boolean
    height?: string
    onreset?: () => void
    changed?: boolean
    /** the view to start in: 'flat' (the exact-reading view, default) or '3d' when size and depth are the point */
    initialView?: 'flat' | '3d'
  }
  let { spec, title, hint, caption, ariaLabel, hideParams = false, idle = 'Press Next to start.', extra, start = -1, numbers, height, onreset, changed = false, initialView = 'flat' }: Props = $props()

  // svelte-ignore state_referenced_locally
  let view = $state<string>(initialView)
  let has3d = $state(true)
  // a hint about turning the view only makes sense while the 3D view is showing
  const shownHint = $derived(view === '3d' && has3d ? hint : hint?.replace(/\s*Turn the view[^.]*\./, ''))
  // svelte-ignore state_referenced_locally
  let step = $state(start)
  let selected = $state<string | null>(null)
  let playing = $state(false)
  let timer: ReturnType<typeof setInterval> | undefined
  onMount(() => {
    return () => clearInterval(timer)
  })

  const steps = $derived(spec.steps ?? [])
  const st = $derived(stateAt(spec, step))
  // a new spec (other width, other example): back to the start, keep the selection only if the layer still exists
  let lastId = ''
  $effect(() => {
    const id = spec.id
    if (id === lastId) return
    lastId = id
    step = Math.min(start, steps.length - 1)
    if (selected && !spec.nodes.some((n) => n.id === selected)) selected = null
  })

  function go(k: number) {
    step = Math.max(-1, Math.min(steps.length - 1, k))
  }
  function stop() {
    playing = false
    clearInterval(timer)
  }
  function play() {
    if (playing) return stop()
    if (step >= steps.length - 1) step = -1
    playing = true
    go(step + 1)
    timer = setInterval(() => {
      if (step >= steps.length - 1) return stop()
      go(step + 1)
    }, 1500)
  }
  function reset() {
    stop()
    step = start
    selected = null
    onreset?.()
  }

  const node = $derived(selected ? spec.nodes.find((n) => n.id === selected) ?? null : null)
  const nodeParams = $derived(node ? paramsOf(spec, node.id) : undefined)
  const totalParams = $derived(spec.nodes.reduce((a, n) => a + (paramsOf(spec, n.id) ?? 0), 0))

  /** A value tensor as at most 6 rows of at most 8 numbers (the first channel of a 3D tensor). */
  function rows(v: NetValues | undefined): string[][] {
    if (!v) return []
    const a = v as any[]
    const m: number[][] = Array.isArray(a[0]) ? (Array.isArray(a[0][0]) ? a[0] : a) : [a]
    const cut = (r: number[]) => [...r.slice(0, 8).map((x) => fmtNum(x)), ...(r.length > 8 ? ['…'] : [])]
    return [...m.slice(0, 6).map(cut), ...(m.length > 6 ? [['⋮']] : [])]
  }

  // ↑ / ↓ move through the layer list
  function listKey(e: KeyboardEvent) {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
    const btns = [...(e.currentTarget as HTMLElement).querySelectorAll('button')]
    const i = btns.indexOf(document.activeElement as HTMLButtonElement)
    const j = Math.max(0, Math.min(btns.length - 1, i + (e.key === 'ArrowDown' ? 1 : -1)))
    btns[j]?.focus()
    e.preventDefault()
  }
  const pick = (id: string | null) => (selected = id)

  // the legend lists only what this picture actually draws
  const tonesOf = $derived(groupTones(spec))
  const key = $derived({
    signed: spec.edges.some((e) => e.kind === 'dense' && e.weights && !e.shared),
    forward: steps.some((x) => x.dir === 'forward'),
    backward: steps.some((x) => x.dir === 'backward'),
    shared: Object.values(tonesOf)[0] as string | undefined,
    attention: spec.edges.some((e) => e.kind === 'attention'),
    rail: spec.edges.some((e) => e.kind === 'residual'),
    // discs filled by their value use the same two colors as the weights
    values: steps.some((x) => Object.keys(x.values ?? {}).some((id) => { const n = spec.nodes.find((m) => m.id === id); return n?.kind === 'neurons' && !n.fill })),
    // a row whose fill shows how far along it is (the words written so far)
    progress: spec.nodes.some((n) => n.fill === 'progress'),
  })
  const layers = $derived(spec.nodes.filter((n) => n.kind !== 'op'))
</script>

<LabFrame {title} hint={shownHint} bind:has3d views={[{ id: 'flat', label: 'Flat' }, { id: '3d', label: '3D' }]} bind:view onreset={reset} resetDisabled={!changed && step === start && !selected}>
  {#snippet children()}
    {#if view === '3d'}
      <Net3D {spec} {step} {selected} onselect={pick} {ariaLabel} {numbers} {height}>
        {#snippet fallback()}<Net2D {spec} {step} {selected} onselect={pick} {ariaLabel} {numbers} />{/snippet}
      </Net3D>
    {:else}
      <Net2D {spec} {step} {selected} onselect={pick} {ariaLabel} {numbers} />
    {/if}
  {/snippet}
  {#snippet controls()}
    <!-- choices (which network) on their own row, the step buttons as a group below them -->
    {#if extra}<div class="nl-extra">{@render extra()}</div>{/if}
    {#if steps.length}
      <button type="button" class="lab-btn" onclick={() => { stop(); go(-1) }} disabled={step < 0} aria-label="Back to the start">⏮</button>
      <button type="button" class="lab-btn" onclick={() => { stop(); go(step - 1) }} disabled={step < 0}>◀ Back</button>
      <button type="button" class="lab-btn" onclick={play} aria-pressed={playing}>{playing ? '⏸ Pause' : '▶ Play'}</button>
      <button type="button" class="lab-btn primary" onclick={() => { stop(); go(step + 1) }} disabled={step >= steps.length - 1}>Next ▶</button>
    {/if}
  {/snippet}
  {#snippet after()}
    <div class="nl-below">
      <!-- the layer list: the keyboard and screen-reader way into the picture. Folded, so the controls stay next to it -->
      <details class="nl-list" open={layers.length <= 5}>
      <summary>Layers ({layers.length})</summary>
      <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
      <ol class="nl-layers" aria-label="Layers, from input to output" onkeydown={listKey}>
        {#each layers as n (n.id)}
          {@const on = st.active.has(n.id)}
          <li>
            <button type="button" class="nl-layer" class:on class:back={on && st.dir === 'backward'} aria-pressed={selected === n.id}
              onclick={() => pick(selected === n.id ? null : n.id)}>
              <span class="nl-name">{n.title ?? n.label}</span> <span class="nl-shape">{fmtShape(n.shape)}</span>
            </button>
          </li>
        {/each}
      </ol>
      </details>
      {#if node}
        <div class="nl-panel" aria-live="polite">
          <p class="nl-head"><b>{node.title ?? node.label}</b> <span class="nl-shape">{fmtShape(node.shape)}</span>
            {#if node.axes}<span class="nl-dim"> · axes: {node.axes.join(', ')}</span>{/if}
            {#if nodeParams !== undefined}<span class="nl-dim"> · parameters: {hideParams ? '?' : nodeParams.toLocaleString('en')}</span>{/if}
          </p>
          {#if node.note}<p class="nl-note">{node.note}</p>{/if}
          {#if st.values[node.id]}
            <p class="nl-k">values{flat(st.values[node.id]).length > 48 ? ' (the first rows)' : ''}</p>
            <table class="nl-vals"><tbody>{#each rows(st.values[node.id]) as r}<tr>{#each r as c}<td>{c}</td>{/each}</tr>{/each}</tbody></table>
          {/if}
          {#if st.dir === 'backward' && st.grads[node.id]}
            <p class="nl-k grad">gradient ∂L/∂(value)</p>
            <table class="nl-vals grad"><tbody>{#each rows(st.grads[node.id]) as r}<tr>{#each r as c}<td>{c}</td>{/each}</tr>{/each}</tbody></table>
          {/if}
          {#if !st.values[node.id] && !(st.dir === 'backward' && st.grads[node.id])}<p class="nl-dim">No numbers yet at this step.</p>{/if}
        </div>
      {/if}
    </div>
  {/snippet}
  {#snippet readout()}
    {#if st.step}
      <span class:nl-back={st.dir === 'backward'}>Step {step + 1} of {steps.length} · {st.dir === 'backward' ? 'backward' : 'forward'} · <b>{st.step.title}</b></span>{#if st.step.text}: {st.step.text}{/if}
    {:else}
      {idle}{#if !hideParams && totalParams}<span class="nl-dim">{' · '}{totalParams.toLocaleString('en')} parameters in all</span>{/if}
    {/if}
  {/snippet}
  {#snippet legend()}
    <p class="nl-cap">{caption}</p>
    <p class="nl-key">
      {#if key.signed || key.values}
        {@const what = key.signed && key.values ? 'weight or value' : key.signed ? 'weight' : 'value'}
        <span><i class="sw pos"></i>positive {what}</span><span><i class="sw neg"></i>negative {what}</span>
      {/if}
      {#if key.values}<span class="nl-dim">A disc’s fill is its value: the stronger the color, the further from 0.</span>{/if}
      {#if key.progress}<span class="nl-dim">Gray disc = done; hollow disc = not reached yet.</span>{/if}
      {#if key.shared}<span><i class="sw" style="background: var(--{key.shared})"></i>the same weights, used again</span>{/if}
      {#if key.forward}<span><i class="sw accent"></i>forward (this step)</span>{/if}
      {#if key.backward}<span><i class="sw grad"></i>backward: gradient</span>{/if}
      {#if key.backward}<span class="nl-dim">“∂ −0.5” = the gradient ∂L/∂(that value).</span>{/if}
      {#if key.attention}<span class="nl-dim">Thicker arc = more attention weight.</span>{/if}
      <span class="nl-dim">{key.signed ? 'Thicker line = larger |w|. ' : ''}Select a layer to see its numbers.</span>
    </p>
  {/snippet}
</LabFrame>

<style>
  .nl-extra { flex: 1 0 100%; display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem 1rem; }
  .nl-below { display: grid; grid-template-columns: minmax(0, 15rem) minmax(0, 1fr); gap: 0.75rem; align-items: start; }
  .nl-list summary { cursor: pointer; font-size: 0.82rem; color: var(--dim); padding: 0.15rem 0; }
  .nl-list[open] summary { margin-bottom: 0.25rem; }
  @media (max-width: 560px) { .nl-below { grid-template-columns: 1fr; } }
  .nl-layers { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 2px; }
  .nl-layer {
    width: 100%; text-align: left; font: inherit; font-size: 0.85rem; background: none; color: var(--fg);
    border: 1px solid transparent; border-radius: 6px; padding: 0.2rem 0.45rem; cursor: pointer;
  }
  .nl-layer:hover { background: var(--highlight); }
  .nl-layer[aria-pressed='true'] { border-color: var(--accent); }
  .nl-layer.on .nl-name { color: var(--accent); font-weight: 600; }
  .nl-layer.on.back .nl-name { color: var(--grad); }
  .nl-shape { font-family: var(--mono, ui-monospace, monospace); font-size: 0.8rem; color: var(--dim); }
  .nl-panel { border: 1px solid var(--line); border-radius: 8px; padding: 0.5rem 0.65rem; font-size: 0.85rem; min-width: 0; overflow-x: auto; }
  .nl-panel p { margin: 0 0 0.3rem; }
  .nl-dim { color: var(--dim); }
  .nl-note { color: var(--fg); }
  .nl-k { font-size: 0.75rem; color: var(--dim); }
  .nl-k.grad { color: var(--grad); }
  .nl-vals { border-collapse: collapse; font-family: var(--mono, ui-monospace, monospace); font-size: 0.78rem; font-variant-numeric: tabular-nums; margin-bottom: 0.3rem; }
  .nl-vals td { padding: 0.05rem 0.4rem; text-align: right; }
  .nl-vals.grad td { color: var(--grad); }
  .nl-back { color: var(--grad); }
  .nl-cap { margin: 0 0 0.25rem; }
  .nl-key { display: flex; flex-wrap: wrap; gap: 0.25rem 0.9rem; margin: 0; font-size: 0.8rem; }
  .sw { display: inline-block; width: 0.9rem; height: 0.25rem; border-radius: 2px; margin-right: 0.3rem; vertical-align: middle; }
  .sw.pos { background: var(--pos); }
  .sw.neg { background: var(--neg); }
  .sw.accent { background: var(--accent); }
  .sw.grad { background: var(--grad); }
</style>
