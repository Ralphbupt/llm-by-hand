<script lang="ts">
  /**
   * A tensor picture inside the standard LabFrame: title, what to do, the picture, and a color key.
   * Two views of the same tensors:
   *   Flat — every tensor as plain grids of cells (one grid per batch entry), exact and readable on a phone;
   *   3D   — Tensors3D blocks you can turn.
   * Wide screens open in 3D, narrow ones (where the 3D blocks get tiny) open Flat.
   */
  import { onMount } from 'svelte'
  import LabFrame from './LabFrame.svelte'
  import Tensors3D from '../viz3d/Tensors3D.svelte'

  type Tone = 'accent' | 'ok' | 'warn' | 'cat-1' | 'cat-2' | 'cat-3' | 'cat-4' | 'cat-5' | 'ghost'
  type Key = { label: string; tone: Tone }
  type Range = { from: number[]; to: number[]; tone?: string }
  type T = { name?: string; title?: string; shape: number[]; axes?: string[]; highlight?: Range[]; ghost?: Range[] }
  let { title, hint, tensors, height = 'min(300px, 62vw)', ariaLabel, keys = [] }:
    { title: string; hint?: string; tensors: any[]; height?: string; ariaLabel: string; keys?: Key[] } = $props()

  let view = $state('3d')
  let mounted = $state(false)
  onMount(() => {
    if (window.matchMedia('(max-width: 560px)').matches) view = 'flat'
    mounted = true
  })

  const inR = (r: Range, idx: number[]) => idx.every((v, k) => v >= r.from[k] && v <= r.to[k])
  /** tone of one cell: a highlight wins over a ghost copy */
  function toneOf(t: T, idx: number[]): string | null {
    const h = t.highlight?.find((r) => inR(r, idx))
    if (h) return h.tone ?? 'accent'
    if (t.ghost?.some((r) => inR(r, idx))) return 'ghost'
    return null
  }
  const dims = (t: T) => (t.shape.length === 3 ? t.shape : [1, ...t.shape]) as [number, number, number]
  const rowAxis = (t: T) => (t.shape.length === 3 ? t.axes?.[1] : t.axes?.[0]) ?? 'rows'
  const colAxis = (t: T) => (t.shape.length === 3 ? t.axes?.[2] : t.axes?.[1]) ?? 'columns'
  const label = (t: T) => t.title ?? `${t.name} (${t.shape.join(', ')})`
  const range = (n: number) => Array.from({ length: n }, (_, i) => i)
</script>

<LabFrame {title} {hint} views={[{ id: 'flat', label: 'Flat' }, { id: '3d', label: '3D' }]} bind:view>
  {#if !mounted}
    <div style:height={height} aria-hidden="true"></div>
  {:else if view === '3d'}
    <Tensors3D {tensors} {height} {ariaLabel} />
  {:else}
    <div class="flat" role="img" aria-label={ariaLabel}>
      {#each tensors as t}
        {#if typeof t === 'string'}
          <span class="op">{t}</span>
        {:else}
          {@const [B, R, C] = dims(t)}
          <figure class="tz">
            <figcaption class="tn">{label(t)}</figcaption>
            <div class="slices">
              {#each range(B) as b}
                <div class="slice">
                  {#if B > 1}<span class="bl">{t.axes?.[0] ?? 'batch'} {b}</span>{/if}
                  <div class="grid" style:grid-template-columns="repeat({C}, var(--cell))">
                    {#each range(R) as i}
                      {#each range(C) as j}
                        {@const tone = toneOf(t, t.shape.length === 3 ? [b, i, j] : [i, j])}
                        <i class="c" class:ghost={tone === 'ghost'} style:background={tone && tone !== 'ghost' ? `var(--${tone})` : null}></i>
                      {/each}
                    {/each}
                  </div>
                </div>
              {/each}
            </div>
            <div class="ax">{rowAxis(t)} ↓ · {colAxis(t)} →</div>
          </figure>
        {/if}
      {/each}
    </div>
  {/if}
  {#snippet legend()}
    {#each keys as k}
      <span class="key"><i class:ghost={k.tone === 'ghost'} style:background={k.tone === 'ghost' ? 'transparent' : `var(--${k.tone})`}></i>{k.label}</span>
    {/each}
  {/snippet}
</LabFrame>

<style>
  .key { display: inline-flex; align-items: center; gap: 0.4rem; }
  .key i { width: 0.8rem; height: 0.8rem; border-radius: 2px; flex: none; }
  .key i.ghost { border: 1px dashed var(--field); }

  .flat { --cell: clamp(0.62rem, 2.7vw, 0.95rem); display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 0.8rem 0.7rem;
    padding: 0.8rem 0.4rem; background: var(--bg); border: 1px solid var(--line); border-radius: 6px; }
  .tz { margin: 0; display: grid; justify-items: center; gap: 0.3rem; }
  .tn { font-family: var(--mono); font-size: 0.8rem; font-weight: 650; white-space: nowrap; }
  .slices { display: grid; gap: 0.35rem; }
  .slice { display: grid; justify-items: start; gap: 0.1rem; }
  .bl { font-family: var(--mono); font-size: 0.72rem; color: var(--dim); }
  .grid { display: grid; gap: 1px; padding: 1px; background: var(--line); border-radius: 2px; }
  .c { display: block; width: var(--cell); height: var(--cell); background: var(--card); }
  .c.ghost { background: color-mix(in srgb, var(--fg) 5%, var(--card)); outline: 1px dashed var(--field); outline-offset: -2px; }
  .ax { font-family: var(--mono); font-size: 0.72rem; color: var(--dim); white-space: nowrap; }
  .op { font-family: var(--mono); font-size: 1.1rem; font-weight: 700; color: var(--dim); }
</style>
