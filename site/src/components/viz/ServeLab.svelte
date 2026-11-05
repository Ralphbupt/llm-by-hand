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
  import { provideLang, useT } from '@lib/i18nSvelte'
  import type { Lang } from '@lib/i18n'

  let { lang = 'en' }: { lang?: Lang } = $props()
  provideLang(lang)
  const t = useT({
    'your B': '你的 B',
    'crossover: the two times are equal at B = {b}': '交叉点：B = {b} 时两个时间相等',
    'One decode step for B users: reading time and arithmetic time': 'B 个用户的一步解码：读取时间和算术时间',
    'Move the slider to add users. Then give each user a longer conversation.': '拖动滑块增加用户。再给每个用户更长的对话。',
    'Time of one step against the number of users. Read line from {r} ms, arithmetic line from 0 ms.': '一步的时间随用户数的变化。读取线从 {r} ms 开始，算术线从 0 ms 开始。',
    'They meet at B = {b}.': '两条线在 B = {b} 处相交。',
    'They do not meet.': '两条线不相交。',
    'Above B = {b} the caches no longer fit in 80 GB.': 'B 超过 {b} 后，缓存放不进 80 GB 了。',
    'users in one step, B': '一步里的用户数 B',
    'time per step (ms)': '每步时间（ms）',
    'over 80 GB': '超过 80 GB',
    'read: weights': '读取：权重',
    '+ every cache': '+ 每份缓存',
    ' + every cache': ' + 每份缓存',
    'arithmetic: B × 2N': '算术：B × 2N',
    'equal at B = {b}': 'B = {b} 时相等',
    'step {s} ms ↑': '一步 {s} ms ↑',
    'users B': '用户数 B',
    'number of users in one step': '一步里的用户数',
    'Tokens of conversation per user': '每个用户的对话 token 数',
    'tokens per user': '每个用户的 token 数',
    'B = {b}: read {r} ms, arithmetic {m} ms, so a step takes': 'B = {b}：读取 {r} ms，算术 {m} ms，所以一步要花',
    '.': '。',
    '{n} tokens/s per user,': '每个用户每秒 {n} 个 token，',
    '{n} in total.': '总共每秒 {n} 个。',
    'Memory:': '显存：',
    '{n} GB of weights': '{n} GB 权重',
    '{n} GB of cache': '{n} GB 缓存',
    '= {n} GB of {m}.': '= {n} GB，共 {m} GB。',
    'This does not fit on an 80 GB GPU:': '一块 80 GB 的 GPU 放不下：',
    'at most {n} users fit.': '最多放得下 {n} 个用户。',
    'The lines don’t cross: reading is the limit for every B.': '两条线不相交：不管 B 是多少，瓶颈都是读取。',
  })

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
  <span class="lg"><i class="k cur"></i>{t('your B')}</span>
  <span class="lg"><i class="k ok"></i>{t('crossover: the two times are equal at B = {b}', { b: Math.round(meet) })}</span>
{/snippet}

<LabFrame
  title={t('One decode step for B users: reading time and arithmetic time')}
  hint={t('Move the slider to add users. Then give each user a longer conversation.')}
  onreset={reset} resetDisabled={!changed} legend={meets ? legend : undefined}
>
  <svg use:readable class="serve-chart" viewBox={`0 0 ${W} ${H}`} role="img"
    aria-label={`${t('Time of one step against the number of users. Read line from {r} ms, arithmetic line from 0 ms.', { r: f2(T_W) })} ${meets ? t('They meet at B = {b}.', { b: Math.round(meet) }) : t('They do not meet.')}${fitsAll ? '' : ` ${t('Above B = {b} the caches no longer fit in 80 GB.', { b: bFit })}`}`}>
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
    <text x={(L + W - R) / 2} y={H - 4} text-anchor="middle" class="albl">{t('users in one step, B')}</text>
    <text x="10" y={(T + H - BOT) / 2} text-anchor="middle" class="albl" transform={`rotate(-90 10 ${(T + H - BOT) / 2})`}>{t('time per step (ms)')}</text>

    <g clip-path="url(#serve-clip)">
      <path d={readPath} class="ln read" />
      <path d={mathPath} class="ln math" />
      {#if !fitsAll}<rect x={px(bFit)} y={T} width={W - R - px(bFit)} height={H - T - BOT} class="full" />{/if}
    </g>
    {#if !fitsAll}
      <line x1={px(bFit)} x2={px(bFit)} y1={T} y2={py(0)} class="memline" />
      <text x={px(bFit) + 4} y={py(0) - 5} class="tag full-t">{t('over 80 GB')}</text>
    {/if}
    <line x1={px(B)} x2={px(B)} y1={T} y2={py(0)} class="cur" />
    {#if readTag.x2 !== undefined}
      <text text-anchor="end" class="tag read"><tspan x={readTag.x} y={readTag.y}>{t('read: weights')}</tspan><tspan x={readTag.x2} y={readTag.y2}>{t('+ every cache')}</tspan></text>
    {:else}
      <text x={readTag.x} y={readTag.y} text-anchor={readTag.anchor} class="tag read">{t('read: weights')}{ctx ? t(' + every cache') : ''}</text>
    {/if}
    <text x={px(BMAX) - 2} y={py(BMAX * T_M) - 6} text-anchor="end" class="tag math">{t('arithmetic: B × 2N')}</text>

    {#if meets}
      <circle cx={px(meet)} cy={py(meet * T_M)} r="6" class="meet" />
      {#if !nearMeet}<text x={meet > 150 ? W - R : px(meet) + 9} y={py(meet * T_M) + (meet > 150 ? 24 : 16)} text-anchor={meet > 150 ? 'end' : 'start'} class="tag ok">{t('equal at B = {b}', { b: Math.round(meet) })}</text>{/if}
    {/if}

    {#if read <= YMAX}<circle cx={px(B)} cy={py(read)} r="3.5" class="dot read" />{/if}
    {#if math <= YMAX}<circle cx={px(B)} cy={py(math)} r="3.5" class="dot math" />{/if}
    {#if step > YMAX}<text x={px(B) + (B > 200 ? -4 : 4)} y={T + 10} text-anchor={B > 200 ? 'end' : 'start'} class="tag cur-t">{t('step {s} ms ↑', { s: f2(step) })}</text>{/if}
  </svg>

  {#snippet controls()}
    <label class="knob">{t('users B')} <input type="range" min="1" max={BMAX} step="1" bind:value={B} aria-label={t('number of users in one step')} /> <b>{B}</b></label>
    <span class="seg" role="group" aria-label={t('Tokens of conversation per user')}>
      <span class="seglbl">{t('tokens per user')}</span>
      {#each CTXS as c}
        <button type="button" class="lab-btn" aria-pressed={ctx === c} onclick={() => (ctx = c)}>{c.toLocaleString('en-US')}</button>
      {/each}
    </span>
  {/snippet}

  {#snippet readout()}
    {t('B = {b}: read {r} ms, arithmetic {m} ms, so a step takes', { b: B, r: f2(read), m: f2(math) })} <b>{f2(step)} ms</b>{t('.')}
    <span class="nw">{t('{n} tokens/s per user,', { n: (1000 / step).toFixed(1) })}</span>
    <span class="nw">{t('{n} in total.', { n: Math.round((B * 1000) / step).toLocaleString('en-US') })}</span>
    <br />{t('Memory:')} <span class="nw">{t('{n} GB of weights', { n: memW.toFixed(0) })}</span> + <span class="nw">{t('{n} GB of cache', { n: memC.toFixed(1) })}</span>
    <span class="nw">{t('= {n} GB of {m}.', { n: (memW + memC).toFixed(1), m: MEM })}</span>
    {#if over}<br /><b>{t('This does not fit on an 80 GB GPU:')}</b> {t('at most {n} users fit.', { n: bFit })}{/if}
    {#if !meets}<br />{t('The lines don’t cross: reading is the limit for every B.')}{/if}
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
