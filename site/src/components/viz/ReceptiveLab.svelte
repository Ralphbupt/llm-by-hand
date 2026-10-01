<script lang="ts">
  /** Receptive field: stack 3×3 (or 5×5) layers, optionally with 2×2 pooling, and see how much of the picture one output pixel sees. */
  import LabFrame from './LabFrame.svelte'
  const N = 19
  let layers = $state(1)
  let k = $state(3)
  let pool = $state(false)

  // r: side of the patch one output pixel sees; jump: how far apart neighboring pixels of the current layer sit in the picture
  const steps = $derived.by(() => {
    let r = 1, jump = 1
    const out: { name: string; r: number }[] = []
    for (let l = 1; l <= layers; l++) {
      r += (k - 1) * jump
      out.push({ name: `conv ${l} (${k}×${k})`, r })
      if (pool) {
        r += jump
        jump *= 2
        out.push({ name: `pool ${l} (2×2)`, r })
      }
    }
    return out
  })
  const c = Math.floor(N / 2)
  const changed = $derived(layers !== 1 || k !== 3 || pool)
  // which step first reaches each pixel: rings grow outward, one ring per layer (0 = the first layer's patch)
  const ring = (i: number, j: number) => {
    const d = Math.max(Math.abs(i - c), Math.abs(j - c))
    const s = steps.findIndex((st) => d <= Math.floor(st.r / 2))
    return s
  }
  const shade = (s: number) => (s < 0 ? '' : `background: color-mix(in srgb, var(--accent) ${Math.round(60 - (45 * s) / Math.max(1, steps.length - 1 || 1))}%, var(--bg))`)
</script>

<LabFrame
  title="How much of the picture one output pixel sees"
  hint="Add layers, switch the filter size, turn pooling on, and watch the field grow."
  onreset={() => { layers = 1; k = 3; pool = false }}
  resetDisabled={!changed}
>
  <div class="grid">
    <div class="board" style="grid-template-columns: repeat({N}, 1fr)" role="img" aria-label={`A ${N}×${N} picture; the last layer's center pixel sees ${steps.at(-1)?.r}×${steps.at(-1)?.r} of it`}>
      {#each Array(N) as _, i}
        {#each Array(N) as _, j}
          <span class:center={i === c && j === c} style={i === c && j === c ? '' : shade(ring(i, j))}></span>
        {/each}
      {/each}
    </div>
    <ol class="trace" aria-label="What each layer sees">
      {#each steps as s, n}<li><i class="sw" style={shade(n)}></i>{s.name}: sees <b>{s.r}×{s.r}</b>{s.r > N ? ' (bigger than this grid)' : ''}</li>{/each}
    </ol>
  </div>

  {#snippet controls()}
    <label class="slider">layers <b>{layers}</b>
      <input type="range" min="1" max="4" bind:value={layers} aria-label="number of layers" />
    </label>
    <span class="opts" role="radiogroup" aria-label="Filter size">
      <label><input type="radio" bind:group={k} value={3} /> 3×3 filters</label>
      <label><input type="radio" bind:group={k} value={5} /> 5×5 filters</label>
    </span>
    <label class="opts"><input type="checkbox" bind:checked={pool} /> 2×2 pooling after each layer</label>
  {/snippet}

  {#snippet readout()}
    one pixel after the last layer sees <b>{steps.at(-1)?.r}×{steps.at(-1)?.r}</b> pixels of the picture
  {/snippet}

  {#snippet legend()}
    <span><i class="sw center-sw"></i>the output pixel</span>
    <span>darkest ring: what the first layer sees; each lighter ring: what one more layer adds</span>
  {/snippet}
</LabFrame>

<style>
  .grid { display: grid; grid-template-columns: minmax(0, 15rem) minmax(0, 1fr); gap: 1rem; align-items: start; }
  @media (max-width: 560px) { .grid { grid-template-columns: minmax(0, 1fr); } }
  .board { display: grid; gap: 1px; width: 100%; max-width: 15rem; aspect-ratio: 1; background: var(--line); border: 1px solid var(--line); }
  .board span { background: var(--bg); transition: background 0.2s; }
  .board span.center { background: var(--fg); }
  .trace { margin: 0; padding-left: 0; list-style: none; display: grid; gap: 0.25rem; font-family: var(--mono); font-size: 0.82rem; }
  .sw { display: inline-block; width: 0.75rem; height: 0.75rem; border: 1px solid var(--line); border-radius: 2px; margin-right: 0.4rem; vertical-align: -0.1em; }
  .sw.center-sw { background: var(--fg); }
  .slider { display: inline-flex; align-items: center; gap: 0.5rem; font-size: 0.88rem; color: var(--dim); }
  .slider b { color: var(--fg); font-family: var(--mono); }
  .slider input { accent-color: var(--accent); min-height: 2rem; }
  .opts { display: inline-flex; flex-wrap: wrap; gap: 0.2rem 0.9rem; font-size: 0.88rem; color: var(--dim); }
  .opts label, label.opts { display: inline-flex; align-items: center; gap: 0.3rem; min-height: 2rem; }
  @media (prefers-reduced-motion: reduce) { .board span { transition: none; } }
</style>
