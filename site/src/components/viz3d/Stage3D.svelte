<script lang="ts">
  /**
   * The frame every 3D view sits in: the WebGL view (focusable, with HTML labels), and one line under it with the
   * input hint and the Reset view button (and Done on touch while the view holds one-finger drags).
   * Without WebGL it renders `fallback` (or a short note saying what the view would show) instead.
   * Surface3D, Points3D and Tensors3D use it; `onready` receives the stage once and may return a cleanup.
   */
  import { onMount, type Snippet } from 'svelte'
  import { createStage, webglAvailable, type Stage, type StageOpts, type StageState } from '@lib/three/stage'

  type Props = {
    opts: StageOpts
    ariaLabel: string
    /** CSS height of the view (e.g. '300px', 'min(260px, 62vw)'); or use `aspect` */
    height?: string
    aspect?: string
    maxHeight?: string
    fallback?: Snippet
    onready: (stage: Stage) => (() => void) | void
  }
  let { opts, ariaLabel, height, aspect, maxHeight, fallback, onready }: Props = $props()

  let ok = $state(true)
  let view = $state<HTMLDivElement>()
  let stage: Stage | null = null
  let st = $state<StageState>({ active: false, focused: false, coarse: false, paused: false })
  const hintId = `h3d-${Math.random().toString(36).slice(2, 9)}`

  onMount(() => {
    if (!webglAvailable()) { ok = false; return }
    const s = createStage(view!, { ...opts, onState: (x) => (st = x) })
    stage = s
    const off = onready(s)
    return () => {
      off?.()
      s.dispose()
      stage = null
    }
  })

  const hint = $derived(
    st.focused ? 'Arrow keys turn · + − zoom · 0 resets'
    : st.coarse ? (st.active ? 'One finger turns · Done to scroll' : 'Tap, then drag to turn · two fingers zoom')
    : st.active ? 'Scroll to zoom · Esc to release' : 'Drag to turn · click, then scroll to zoom',
  )
</script>

{#if ok}
  <div class="stage3d">
    <!-- focusable so the arrow keys can turn it (keys handled in lib/three/stage.ts) -->
    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <div class="stage3d-view" bind:this={view} role="application" aria-roledescription="3D view" aria-label={ariaLabel} aria-describedby={hintId} tabindex="0"
      style:height style:aspect-ratio={aspect} style:max-height={maxHeight}></div>
    <div class="stage3d-bar">
      <span class="stage3d-hint" id={hintId} class:on={st.active}>{hint}</span>
      {#if st.active && st.coarse}
        <button type="button" class="stage3d-btn" onclick={() => stage?.setActive(false)}>Done</button>
      {/if}
      <button type="button" class="stage3d-btn" onclick={() => stage?.resetView()}>Reset view</button>
    </div>
  </div>
{:else}
  <div class="stage3d-fallback" role="note">
    {#if fallback}
      {@render fallback()}
    {:else}
      <p><b>3D view not available.</b> This browser can't draw WebGL (it may be disabled). The view shows: {ariaLabel}.</p>
    {/if}
  </div>
{/if}
