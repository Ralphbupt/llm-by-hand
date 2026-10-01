<script lang="ts">
  import LabFrame from './LabFrame.svelte'
  import { readable } from '@lib/readable'
  /**
   * Norm path lab (level 19): where the LayerNorm sits in each layer.
   * Post-norm: x ← LN(x + f(x)).  Pre-norm: x ← x + f(LN(x)), plus one LN at the very end.
   * Count the normalizations a signal crosses on the straight residual path from input to output.
   * The slider stops at 6 layers; the question on the page asks about 12.
   */
  let mode = $state<'post' | 'pre'>('post')
  let layers = $state(3)
  const onPath = $derived(mode === 'post' ? layers : 1)
  const ROW = 62, HX = 46, BX = 96, FX = 150
  const H = $derived(60 + layers * ROW + (mode === 'pre' ? 24 : 0))
</script>

<LabFrame
  title="Where the LayerNorm sits: on the residual path, or only in front of the sublayer"
  hint="Switch between the 2017 design and today’s, and add layers. Count the LayerNorms the input must pass through on the residual path."
  onreset={() => { mode = 'post'; layers = 3 }}
  resetDisabled={mode === 'post' && layers === 3}
>
  <!-- the residual path runs straight up the left; each layer's sublayer side sits to its right -->
  <svg class="diagram" use:readable viewBox="0 0 360 {H}" role="img"
    aria-label={`${layers} layers, ${mode === 'post' ? 'post-norm' : 'pre-norm'}: ${onPath} LayerNorm${onPath === 1 ? '' : 's'} on the residual path`}>
    <text x={HX} y={H - 6} class="io mid">input x</text>
    <text x={HX} y="12" class="io mid">output</text>
    <line x1={HX} y1={H - 18} x2={HX} y2="20" class="hw" />
    {#each Array(layers) as _, l}
      {@const yb = H - 30 - l * ROW}
      {@const yp = yb - ROW + 22}
      <text x={FX + 136} y={yb - 4} class="lbl">layer {l + 1}</text>
      <!-- the sublayer side: leave the path, (LN), function, come back to + -->
      <path d={`M${HX},${yb - 8} H${mode === 'pre' ? BX - 4 : FX}`} class="br" />
      {#if mode === 'pre'}
        <rect x={BX - 4} y={yb - 18} width="34" height="20" rx="4" class="box ln" /><text x={BX + 13} y={yb - 4} class="t mid">LN</text>
        <path d={`M${BX + 30},${yb - 8} H${FX}`} class="br" />
      {/if}
      <rect x={FX} y={yb - 18} width="128" height="20" rx="4" class="box f" /><text x={FX + 64} y={yb - 4} class="t mid">attention / FFN</text>
      <path d={`M${FX + 64},${yb - 18} V${yp + 2} H${HX + 9}`} class="br" />
      <circle cx={HX} cy={yp + 2} r="8" class="add" /><text x={HX} y={yp + 6} class="t mid">+</text>
      {#if mode === 'post'}
        <rect x={HX - 17} y={yp - 26} width="34" height="18" rx="4" class="box ln hot" /><text x={HX} y={yp - 13} class="t mid hot-t">LN</text>
      {/if}
    {/each}
    {#if mode === 'pre'}
      <rect x={HX - 30} y="26" width="60" height="18" rx="4" class="box ln hot" /><text x={HX} y="39" class="t mid hot-t">final LN</text>
    {/if}
  </svg>

  {#snippet controls()}
    <div class="seg" role="group" aria-label="Where the norm sits">
      <button type="button" class:on={mode === 'post'} aria-pressed={mode === 'post'} onclick={() => (mode = 'post')}>post-norm (2017)</button>
      <button type="button" class:on={mode === 'pre'} aria-pressed={mode === 'pre'} onclick={() => (mode = 'pre')}>pre-norm (today)</button>
    </div>
    <label class="knob">layers <b>{layers}</b><input type="range" min="1" max="6" step="1" value={layers} oninput={(e) => (layers = +e.currentTarget.value)} /></label>
  {/snippet}

  {#snippet readout()}
    LayerNorms on the residual path from input to output:
    <b>{onPath}</b>.
    {mode === 'post'
      ? 'Every layer rescales the whole sum x, so the input reaches the top only through all of them.'
      : 'Sublayers only add to x; nothing rescales it. The input reaches the top unchanged, then one final LN.'}
  {/snippet}

  {#snippet legend()}
    <span class="lg"><span class="hwk"></span>the residual path</span>
    <span class="lg"><span class="lnk">LN</span>a LayerNorm on that path</span>
  {/snippet}
</LabFrame>

<style>
  .seg { display: inline-flex; border: 1px solid var(--field); border-radius: 999px; overflow: hidden; }
  .seg button { font: inherit; font-size: 0.82rem; padding: 0.25rem 0.8rem; min-height: 2.1rem; border: 0; background: var(--bg); color: var(--fg); cursor: pointer; }
  .seg button + button { border-left: 1px solid var(--field); }
  .seg button.on { color: var(--accent); background: var(--highlight); }
  .seg button:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
  .knob { display: inline-flex; gap: 0.5rem; align-items: center; font-family: var(--mono); font-size: 0.85rem; }
  .knob b { color: var(--accent); }
  .knob input { accent-color: var(--accent); }
  .diagram { width: 100%; max-width: 440px; height: auto; display: block; }
  .io { font-size: 10px; fill: var(--dim); font-family: var(--mono); }
  .mid { text-anchor: middle; }
  .lbl { font-size: 10px; fill: var(--dim); font-family: var(--mono); }
  .hw { stroke: var(--accent); stroke-width: 4; stroke-linecap: round; opacity: 0.85; }
  .br { fill: none; stroke: var(--dim); stroke-width: 1.4; }
  .box { fill: var(--bg); stroke: var(--field); stroke-width: 1.2; }
  .box.ln.hot { stroke: var(--fg); stroke-width: 2.2; fill: color-mix(in srgb, var(--dim) 22%, var(--bg)); }
  .t { font-size: 11px; fill: var(--fg); font-family: var(--mono); }
  .hot-t { fill: var(--fg); font-weight: 700; }
  .add { fill: var(--bg); stroke: var(--accent); stroke-width: 1.6; }
  .lg { display: inline-flex; align-items: center; gap: 0.4rem; }
  .hwk { display: inline-block; width: 18px; height: 0; border-top: 4px solid var(--accent); }
  .lnk { font-family: var(--mono); border: 2px solid var(--fg); background: color-mix(in srgb, var(--dim) 22%, var(--bg)); color: var(--fg); border-radius: 4px; padding: 0 0.3rem; font-size: 0.75rem; }
  /* phones: touch targets at least 40px tall; 16px fields so iOS does not zoom */
  @media (max-width: 760px) { .seg button { min-height: 2.5rem; } .knob input { min-height: 2.5rem; } }
</style>
