<script lang="ts">
  /**
   * Serve lab (level 20): one decode step for B users.
   * The read line is the time to read the weights once plus every user's KV cache; the arithmetic line is
   * B × 2N FLOPs. The step takes the longer one. The numbers match demo.py: 7 billion weights of 2 bytes,
   * 10¹² bytes/s, 10¹⁴ FLOPs/s, 8 K/V heads × d_k 128 × 32 layers = 128 KiB of cache per token.
   * The GPU holds 80 GB: past the B where the weights and the caches no longer fit, the chart is grayed out.
   */
  import { readable } from '@lib/readable'
  import LabFrame from './LabFrame.svelte'

  const N = 7e9, BW = 1e12, FL = 1e14
  const T_W = ((N * 2) / BW) * 1000          // 14 ms: read the weights once
  const T_M = ((2 * N) / FL) * 1000          // 0.14 ms: arithmetic for one user's token
  const KV_TOK = 2 * 8 * 128 * 32 * 2        // 131,072 bytes per token
  const CTXS = [0, 500, 4000]
  const B0 = 8, C0 = 0, BMAX = 256, YMAX = 60

  let B = $state(B0)
  let ctx = $state(C0)
  const tCache = $derived(((ctx * KV_TOK) / BW) * 1000)   // ms to read one user's cache
  const read = $derived(T_W + B * tCache)
  const math = $derived(B * T_M)
  const step = $derived(Math.max(read, math))
  const gap = $derived(T_M - tCache)
  const meet = $derived(gap > 0 ? T_W / gap : Infinity)
  const meets = $derived(Number.isFinite(meet) && meet <= BMAX)
  const memW = (N * 2) / 1e9                                  // 14 GB of weights
  const memC = $derived((B * ctx * KV_TOK) / 1e9)            // GB of cache for B users
  const MEM = 80                                              // GB on the GPU
  const bFit = $derived(ctx > 0 ? Math.floor((MEM - memW) / ((ctx * KV_TOK) / 1e9)) : Infinity)  // 125 at 4,000 tokens
  const fitsAll = $derived(bFit >= BMAX)
  const over = $derived(B > bFit)

  // the chart, in viewBox units
  const W = 400, H = 230, L = 44, R = 12, T = 10, BOT = 34
  const px = (b: number) => L + (b / BMAX) * (W - L - R)
  const py = (ms: number) => T + (1 - ms / YMAX) * (H - T - BOT)
  const readPath = $derived(`M${px(0)},${py(T_W)} L${px(BMAX)},${py(T_W + BMAX * tCache)}`)
  const mathPath = `M${px(0)},${py(0)} L${px(BMAX)},${py(BMAX * T_M)}`

  // the read label follows its line, placed along its visible part
  const READ_TAG_W = 165                                       // rough width of "read: weights + every cache"
  type Tag = { x: number; y: number; anchor: string; x2?: number; y2?: number }
  const readTag: Tag = $derived.by((): Tag => {
    if (tCache <= 0) return { x: px(4), y: py(T_W) - 6, anchor: 'start' }
    const top = Math.min(BMAX, (YMAX - T_W) / tCache)       // where the line leaves the chart
    const b = top * 0.6, x = px(b), y = py(T_W + b * tCache)
    // gentle line: end the label above the point
    if (x - READ_TAG_W >= L + 2) return { x: x - 2, y: y - 6, anchor: 'end' }
    // steep line: two short lines just left of the line, each ending where the line is at its height
    // (14 units apart and 8 clear of the line, so the labels still fit when a phone enlarges them)
    const at = (ms: number) => px((ms - T_W) / tCache) - 8
    const ms1 = T_W + top * 0.87 * tCache, ms2 = ms1 - (14 / (H - T - BOT)) * YMAX
    return { x: at(ms1), y: py(ms1), anchor: 'end', x2: at(ms2), y2: py(ms2) }
  })
  // the "equal" label is hidden while the cursor is close to the crossing point (the legend still gives B)
  const nearMeet = $derived(Math.abs(B - meet) < 20)

  const f2 = (v: number) => v.toFixed(2)
  const changed = $derived(B !== B0 || ctx !== C0)
  function reset() { B = B0; ctx = C0 }
</script>

<!-- shown only when the lines cross: a legend with "your B" alone looks left over -->
{#snippet legend()}
  <span class="lg"><i class="k cur"></i>your B</span>
  <span class="lg"><i class="k ok"></i>crossover: the two times are equal at B = {Math.round(meet)}</span>
{/snippet}

<LabFrame
  title="One decode step for B users: reading time and arithmetic time"
  hint="Move the slider to add users. Then give each user a longer conversation."
  onreset={reset} resetDisabled={!changed} legend={meets ? legend : undefined}
>
  <svg use:readable class="serve-chart" viewBox={`0 0 ${W} ${H}`} role="img"
    aria-label={`Time of one step against the number of users. Read line from ${f2(T_W)} ms, arithmetic line from 0 ms. ${meets ? `They meet at B = ${Math.round(meet)}.` : 'They do not meet.'}${fitsAll ? '' : ` Above B = ${bFit} the caches no longer fit in 80 GB.`}`}>
    <defs><clipPath id="serve-clip"><rect x={L} y={T} width={W - L - R} height={H - T - BOT} /></clipPath></defs>
    {#each [0, 20, 40, 60] as v}
      <line x1={L} x2={W - R} y1={py(v)} y2={py(v)} class="grid" />
      <text x={L - 4} y={py(v) + 3.5} text-anchor="end" class="tick">{v}</text>
    {/each}
    {#each [50, 100, 150, 200, 250] as v}
      <text x={px(v)} y={H - BOT + 13} text-anchor="middle" class="tick">{v}</text>
    {/each}
    <line x1={L} x2={W - R} y1={py(0)} y2={py(0)} class="axis" />
    <line x1={L} x2={L} y1={T} y2={py(0)} class="axis" />
    <text x={(L + W - R) / 2} y={H - 4} text-anchor="middle" class="albl">users in one step, B</text>
    <text x="10" y={(T + H - BOT) / 2} text-anchor="middle" class="albl" transform={`rotate(-90 10 ${(T + H - BOT) / 2})`}>time per step (ms)</text>

    <g clip-path="url(#serve-clip)">
      <path d={readPath} class="ln read" />
      <path d={mathPath} class="ln math" />
      {#if !fitsAll}<rect x={px(bFit)} y={T} width={W - R - px(bFit)} height={H - T - BOT} class="full" />{/if}
    </g>
    {#if !fitsAll}
      <line x1={px(bFit)} x2={px(bFit)} y1={T} y2={py(0)} class="memline" />
      <text x={px(bFit) + 4} y={py(0) - 5} class="tag full-t">over 80 GB</text>
    {/if}
    <line x1={px(B)} x2={px(B)} y1={T} y2={py(0)} class="cur" />
    {#if readTag.x2 !== undefined}
      <text text-anchor="end" class="tag read"><tspan x={readTag.x} y={readTag.y}>read: weights</tspan><tspan x={readTag.x2} y={readTag.y2}>+ every cache</tspan></text>
    {:else}
      <text x={readTag.x} y={readTag.y} text-anchor={readTag.anchor} class="tag read">read: weights{ctx ? ' + every cache' : ''}</text>
    {/if}
    <text x={px(BMAX) - 2} y={py(BMAX * T_M) - 6} text-anchor="end" class="tag math">arithmetic: B × 2N</text>

    {#if meets}
      <circle cx={px(meet)} cy={py(meet * T_M)} r="6" class="meet" />
      {#if !nearMeet}<text x={meet > 150 ? W - R : px(meet) + 9} y={py(meet * T_M) + (meet > 150 ? 24 : 16)} text-anchor={meet > 150 ? 'end' : 'start'} class="tag ok">equal at B = {Math.round(meet)}</text>{/if}
    {/if}

    {#if read <= YMAX}<circle cx={px(B)} cy={py(read)} r="3.5" class="dot read" />{/if}
    {#if math <= YMAX}<circle cx={px(B)} cy={py(math)} r="3.5" class="dot math" />{/if}
    {#if step > YMAX}<text x={px(B) + (B > 200 ? -4 : 4)} y={T + 10} text-anchor={B > 200 ? 'end' : 'start'} class="tag cur-t">step {f2(step)} ms ↑</text>{/if}
  </svg>

  {#snippet controls()}
    <label class="knob">users B <input type="range" min="1" max={BMAX} step="1" bind:value={B} aria-label="number of users in one step" /> <b>{B}</b></label>
    <span class="seg" role="group" aria-label="Tokens of conversation per user">
      <span class="seglbl">tokens per user</span>
      {#each CTXS as c}
        <button type="button" class="lab-btn" aria-pressed={ctx === c} onclick={() => (ctx = c)}>{c.toLocaleString('en-US')}</button>
      {/each}
    </span>
  {/snippet}

  {#snippet readout()}
    B = {B}: read {f2(read)} ms, arithmetic {f2(math)} ms, so a step takes <b>{f2(step)} ms</b>.
    <span class="nw">{(1000 / step).toFixed(1)} tokens/s per user,</span>
    <span class="nw">{Math.round((B * 1000) / step).toLocaleString('en-US')} in total.</span>
    <br />Memory: <span class="nw">{memW.toFixed(0)} GB of weights</span> + <span class="nw">{memC.toFixed(1)} GB of cache</span>
    <span class="nw">= {(memW + memC).toFixed(1)} GB of {MEM}.</span>
    {#if over}<br /><b>This does not fit on an 80 GB GPU:</b> at most {bFit} users fit.{/if}
    {#if !meets}<br />The lines don’t cross: reading is the limit for every B.{/if}
  {/snippet}

</LabFrame>

<style>
  svg { width: 100%; height: auto; display: block; max-width: 560px; }
  /* the readout and legend end where the chart ends */
  :global(.labframe:has(svg.serve-chart) > :is(.lf-readout, .lf-legend)) { max-width: 560px; box-sizing: border-box; }
  .full { fill: var(--card); opacity: 0.7; }
  .memline { stroke: var(--dim); stroke-width: 1.2; stroke-dasharray: 5 3; }
  .tag.full-t { fill: var(--dim); }
  .grid { stroke: var(--line); stroke-width: 0.8; stroke-dasharray: 2 3; }
  .axis { stroke: var(--dim); stroke-width: 0.8; }
  .tick { fill: var(--dim); font-size: 9px; font-family: var(--mono); }
  .albl { fill: var(--dim); font-size: 10px; }
  .ln { fill: none; stroke-width: 2.2; transition: d 0.2s ease-out; }
  .ln.read { stroke: var(--cat-1); }
  .ln.math { stroke: var(--cat-3); }
  .tag { font-size: 10px; font-family: var(--mono); paint-order: stroke; stroke: var(--card); stroke-width: 3px; stroke-linejoin: round; }
  .tag.read { fill: var(--cat-1); }
  .tag.math { fill: var(--cat-3); }
  .tag.ok { fill: var(--ok); }
  .tag.cur-t { fill: var(--accent); }
  .meet { fill: none; stroke: var(--ok); stroke-width: 2; }
  .cur { stroke: var(--accent); stroke-width: 1.2; stroke-dasharray: 3 3; }
  .dot.read { fill: var(--cat-1); }
  .dot.math { fill: var(--cat-3); }
  .knob { display: inline-flex; align-items: center; gap: 0.45rem; font-size: 0.88rem; color: var(--dim); margin-right: 0.8rem; }
  .knob input { width: min(12rem, 45vw); accent-color: var(--accent); }
  .knob b { color: var(--fg); font-family: var(--mono); min-width: 2.2em; }
  .seg { display: inline-flex; align-items: center; gap: 0.35rem; flex-wrap: wrap; }
  .seglbl { font-size: 0.85rem; color: var(--dim); margin-right: 0.2rem; }
  .seg .lab-btn { min-width: 3rem; font-family: var(--mono); }
  .nw { white-space: nowrap; }
  .lg { display: inline-flex; align-items: center; gap: 0.4rem; }
  .k { flex: none; display: inline-block; width: 1rem; }
  .k.read { border-top: 2.2px solid var(--cat-1); }
  .k.math { border-top: 2.2px solid var(--cat-3); }
  .k.cur { border-top: 1.5px dashed var(--accent); }
  .k.ok { width: 0.75rem; height: 0.75rem; border: 2px solid var(--ok); border-radius: 50%; }
  @media (prefers-reduced-motion: reduce) { .ln { transition: none; } }
</style>
