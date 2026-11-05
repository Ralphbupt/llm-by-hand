<script lang="ts">
  /**
   * Convolution lab: a 3×3 filter slides over a picture.
   * Toy mode: a 5×5 picture of 0s and 1s (click to flip a pixel); hover an output cell to see its window.
   * Digit mode: real 28×28 handwritten digits; the whole feature map is computed live.
   */
  import { onMount } from 'svelte'
  import { conv2d, convOut, pad } from '@lib/classic'
  import { has, subscribe } from '@lib/progress'
  import { onThemeChange } from '@lib/settings'
  import MatrixGrid from './MatrixGrid.svelte'
  import Tensors3D from '../viz3d/Tensors3D.svelte'
  import LabFrame from './LabFrame.svelte'
  import { provideLang, useT } from '@lib/i18nSvelte'
  import type { Lang } from '@lib/i18n'

  // hide: the toy output stays "?" until that question is answered (one cell would be enough,
  // but the stroke makes several cells equal, so every cell is hidden)
  let { hide, lang = 'en' }: { hide?: { id: string; i: number; j: number }; lang?: Lang } = $props()
  provideLang(lang)
  const t = useT({
    'vertical edge': '竖直边缘',
    'horizontal edge': '水平边缘',
    blur: '模糊',
    'do nothing': '不变',
    channel: '通道',
    row: '行',
    col: '列',
    'picture ({c}, {h}, {w})': '图片 ({c}, {h}, {w})',
    'filter {k} of 4 ({c}, 3, 3)': '卷积核 {k}/4 ({c}, 3, 3)',
    'feature maps (4, {h}, {w})': '特征图 (4, {h}, {w})',
    'A 3×3 filter sliding over a picture': '一个 3×3 卷积核在图片上滑动',
    'Select a pixel to flip it. Point at, tap or focus an output cell to see the window it reads.': '选中一个像素可以翻转它。把鼠标指向、点一下或聚焦一个输出格，就能看到它读的窗口。',
    'Pick a digit and a filter: the whole feature map is computed live.': '选一个数字和一个卷积核：整张特征图会实时算出来。',
    '5×5 picture': '5×5 图片',
    'Real digits': '手写数字',
    picture: '图片',
    ' (with padding)': '（含边缘填充）',
    padding: '边缘填充',
    'pixel row {r}, column {c}: {v}': '像素第 {r} 行、第 {c} 列：{v}',
    'filter (editable)': '卷积核（可编辑）',
    'output {h}×{w}': '输出 {h}×{w}',
    'output feature map': '输出特征图',
    'output row {i}, column {j}': '输出第 {i} 行、第 {j} 列',
    'Could not load the digits: {e}': '无法加载数字：{e}',
    'picture: a handwritten {d}': '图片：一个手写的 {d}',
    'input digit': '输入的数字',
    Digit: '数字',
    'feature map': '特征图',
    'Loading digits…': '正在加载数字…',
    'Input channels': '输入通道',
    'input channels:': '输入通道：',
    '1 (a picture)': '1（一张图片）',
    '3 (a later layer)': '3（后面的某一层）',
    'A convolution layer in 3D: the picture, one filter, and four stacked feature maps': '3D 视图中的一个卷积层：图片、一个卷积核，以及叠起来的四张特征图',
    'one channel deep': '深一个通道',
    'all 3 channels deep, so one filter is a 3×3×3 block': '深全部 3 个通道，所以一个卷积核是一个 3×3×3 的方块',
    'The window and the filter that reads it ({depth}) are highlighted, and so is the one output number it makes, in channel {k}. Four filters make four feature maps, stacked as channels{pad}. Point at an output cell above to move the window; pick a filter to change the channel.':
      '窗口和读它的卷积核（{depth}）被高亮了，它生成的那一个输出数也被高亮了，在通道 {k} 里。四个卷积核生成四张特征图，作为通道叠在一起{pad}。指向上面的一个输出格可以移动窗口；选一个卷积核可以换通道。',
    '; pale cells are padding': '；浅色的格是边缘填充',
    Filter: '卷积核',
    stride: '步幅',
    'Hide the layer in 3D': '隐藏 3D 层',
    'Show the layer in 3D': '在 3D 中显示这一层',
    '? (answer the question below)': '?（先回答下面的问题）',
    '(pixels that are 0 add nothing)': '（为 0 的像素不贡献任何东西）',
    'output side': '输出边长',
    'positive output': '正的输出',
    'negative output': '负的输出',
    'background = 0': '背景 = 0',
    'the 3×3 window': '3×3 窗口',
  })
  let solved = $state(false)
  onMount(() => {
    if (hide) {
      const sync = () => (solved = has(hide.id))
      sync()
      const off = subscribe(sync)
      return off
    }
  })

  const PRESETS: Record<string, number[][]> = {
    'vertical edge': [[-1, 0, 1], [-1, 0, 1], [-1, 0, 1]],
    'horizontal edge': [[-1, -1, -1], [0, 0, 0], [1, 1, 1]],
    blur: [[1 / 9, 1 / 9, 1 / 9], [1 / 9, 1 / 9, 1 / 9], [1 / 9, 1 / 9, 1 / 9]],
    'do nothing': [[0, 0, 0], [0, 1, 0], [0, 0, 0]],
  }
  const IMG0 = [0, 0, 0, 0, 0].map(() => [0, 0, 1, 0, 0])
  const copy = (m: number[][]) => m.map((r) => [...r])

  let mode = $state<'toy' | 'digit'>('toy')
  let img = $state(copy(IMG0))
  let kernel = $state(copy(PRESETS['vertical edge']))
  let stride = $state(1)
  let padding = $state(0)
  let cell = $state<{ i: number; j: number } | null>(null)

  let digits = $state<{ labels: number[]; digits: number[][][] } | null>(null)
  let pick = $state(0)
  let error = $state('')
  $effect(() => {
    if (mode === 'digit' && !digits && !error)
      fetch('/data/convolutions/digits.json').then((r) => r.json()).then((d) => (digits = d)).catch((e) => (error = String(e)))
  })

  const changed = $derived(
    JSON.stringify(img) !== JSON.stringify(IMG0) ||
      JSON.stringify(kernel) !== JSON.stringify(PRESETS['vertical edge']) || stride !== 1 || padding !== 0,
  )
  function resetAll() {
    img = copy(IMG0)
    kernel = copy(PRESETS['vertical edge'])
    stride = 1
    padding = 0
    cell = null
  }

  // switching between the toy and real digits forgets the pointed-at cell
  $effect(() => {
    void mode
    cell = null
  })

  const src = $derived(mode === 'toy' ? img : digits ? digits.digits[pick].map((r) => r.map((v) => v / 255)) : null)
  const out = $derived(src ? conv2d(src, kernel, stride, padding) : null)
  const padded = $derived(mode === 'toy' ? pad(img, padding) : null)
  const isMasked = (_i: number, _j: number) => mode === 'toy' && !!hide && !solved

  const inWindow = (r: number, c: number) =>
    !!cell && r >= cell.i * stride && r < cell.i * stride + 3 && c >= cell.j * stride && c < cell.j * stride + 3
  const terms = $derived(
    cell && padded
      ? kernel.flatMap((row, a) => row.map((k, b) => [padded[cell!.i * stride + a][cell!.j * stride + b], k]))
      : [],
  )
  const fmt = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(2))
  const shade = (v: number, max: number) => {
    const a = Math.min(1, Math.abs(v) / (max || 1))
    return v >= 0
      ? `color-mix(in srgb, var(--pos) ${Math.round(a * 55)}%, transparent)`
      : `color-mix(in srgb, var(--neg) ${Math.round(a * 55)}%, transparent)`
  }
  const outMax = $derived(out ? Math.max(...out.flat().map(Math.abs)) : 1)

  // --- the whole layer in 3D: picture (C_in, H, W) ∗ one filter (C_in, 3, 3) = feature maps (4, H', W') ---
  // Four filters (the four presets) make four output channels; the window and the output cell follow the hover.
  let show3d = $state(false)
  let cin = $state(1)
  const NAMES = Object.keys(PRESETS)
  const filterIdx = $derived(Math.max(0, NAMES.findIndex((n) => JSON.stringify(kernel) === JSON.stringify(PRESETS[n]))))
  const layer = $derived.by(() => {
    if (!padded || !out) return []
    const H = padded.length, W = padded[0].length, h = out.length, w = out[0].length
    const c = cell ?? { i: 0, j: 0 }
    const r0 = c.i * stride, c0 = c.j * stride
    const border = padding
      ? [
          { from: [0, 0, 0], to: [cin - 1, padding - 1, W - 1] },
          { from: [0, H - padding, 0], to: [cin - 1, H - 1, W - 1] },
          { from: [0, 0, 0], to: [cin - 1, H - 1, padding - 1] },
          { from: [0, 0, W - padding], to: [cin - 1, H - 1, W - 1] },
        ]
      : []
    return [
      {
        shape: [cin, H, W], axes: ['channel', 'row', 'col'].map((s) => t(s)),
        title: t('picture ({c}, {h}, {w})', { c: cin, h: H, w: W }),
        highlight: [{ from: [0, r0, c0], to: [cin - 1, r0 + 2, c0 + 2], tone: 'accent' }],
        ghost: border,
      },
      '∗',
      {
        shape: [cin, 3, 3], title: t('filter {k} of 4 ({c}, 3, 3)', { k: filterIdx + 1, c: cin }),
        highlight: [{ from: [0, 0, 0], to: [cin - 1, 2, 2], tone: 'accent' }],
      },
      '=',
      {
        shape: [4, h, w], axes: ['channel', 'row', 'col'].map((s) => t(s)), title: t('feature maps (4, {h}, {w})', { h, w }),
        highlight: [
          { from: [filterIdx, c.i, c.j], to: [filterIdx, c.i, c.j], tone: 'ok' },
          { from: [filterIdx, 0, 0], to: [filterIdx, h - 1, w - 1], tone: 'dim' },
        ],
      },
    ] as any[]
  })

  // digit mode: draw the picture and the feature map on canvases
  let cvIn = $state<HTMLCanvasElement>()
  let cvOut = $state<HTMLCanvasElement>()
  // theme colors as [r, g, b], read from the page's tokens so the canvases follow light/dark
  function rgbOf(el: Element, name: string): [number, number, number] {
    const ctx = document.createElement('canvas').getContext('2d')!
    ctx.fillStyle = getComputedStyle(el).getPropertyValue(name).trim() || '#888'
    const hex = ctx.fillStyle as string // normalized to #rrggbb
    return [1, 3, 5].map((k) => parseInt(hex.slice(k, k + 2), 16)) as [number, number, number]
  }
  const mixRgb = (a: number[], b: number[], t: number) => a.map((x, k) => x + (b[k] - x) * t)
  let themeTick = $state(0)

  function paint(cv: HTMLCanvasElement, m: number[][], signed: boolean) {
    const h = m.length, w = m[0].length
    const bg = rgbOf(cv, '--bg'), fg = rgbOf(cv, '--fg'), pos = rgbOf(cv, '--pos'), neg = rgbOf(cv, '--neg')
    cv.width = w
    cv.height = h
    const ctx = cv.getContext('2d')!
    const data = ctx.createImageData(w, h)
    const max = Math.max(...m.flat().map(Math.abs)) || 1
    for (let i = 0; i < h; i++)
      for (let j = 0; j < w; j++) {
        const v = m[i][j] / max
        const k = (i * w + j) * 4
        // signed: positive toward --pos, negative toward --neg, 0 is the background
        // picture: ink toward the text color on the page background
        const c = signed ? mixRgb(bg, v >= 0 ? pos : neg, Math.abs(v)) : mixRgb(bg, fg, v)
        data.data[k] = c[0]; data.data[k + 1] = c[1]; data.data[k + 2] = c[2]
        data.data[k + 3] = 255
      }
    ctx.putImageData(data, 0, 0)
  }
  onMount(() => onThemeChange(() => themeTick++))
  $effect(() => {
    void themeTick
    if (mode === 'digit' && src && out && cvIn && cvOut) {
      paint(cvIn, src, false)
      paint(cvOut, out, true)
    }
  })
</script>

<LabFrame
  title={t('A 3×3 filter sliding over a picture')}
  hint={mode === 'toy' ? t('Select a pixel to flip it. Point at, tap or focus an output cell to see the window it reads.') : t('Pick a digit and a filter: the whole feature map is computed live.')}
  views={[{ id: 'toy', label: t('5×5 picture') }, { id: 'digit', label: t('Real digits') }]}
  bind:view={mode}
  onreset={resetAll}
  resetDisabled={!changed}
>
  <div class="row">
    {#if mode === 'toy' && padded && out}
      <div>
        <div class="label">{t('picture')}{padding ? t(' (with padding)') : ''}</div>
        <div class="cells" style="grid-template-columns: repeat({padded[0].length}, 1.9rem)">
          {#each padded as row, r}
            {#each row as v, c}
              {@const isPad = r < padding || c < padding || r >= padded.length - padding || c >= padded[0].length - padding}
              <button
                class="px" class:ink={v === 1} class:pad={isPad} class:win={inWindow(r, c)}
                disabled={isPad}
                onclick={() => { const n = copy(img); n[r - padding][c - padding] = v ? 0 : 1; img = n }}
                aria-label={isPad ? t('padding') : t('pixel row {r}, column {c}: {v}', { r: r - padding, c: c - padding, v })}
              >{v}</button>
            {/each}
          {/each}
        </div>
      </div>
      <span class="op">∗</span>
      <MatrixGrid value={kernel} label={t('filter (editable)')} editable decimals={2} onchange={(v) => (kernel = v)} />
      <span class="op">=</span>
      <div>
        <div class="label">{t('output {h}×{w}', { h: out.length, w: out[0].length })}</div>
        <div class="cells" style="grid-template-columns: repeat({out[0].length}, 2.4rem)" role="group" aria-label={t('output feature map')} onpointerleave={() => (cell = null)}>
          {#each out as row, i}
            {#each row as v, j}
              <div
                class="oc" class:hi={cell?.i === i && cell?.j === j} class:q={isMasked(i, j)}
                style={isMasked(i, j) ? '' : `background:${shade(v, outMax)}`}
                onpointerenter={() => (cell = { i, j })}
                onfocus={() => (cell = { i, j })}
                onclick={() => (cell = { i, j })}
                onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), (cell = { i, j }))}
                role="button" tabindex="0" aria-label={t('output row {i}, column {j}', { i, j })}
              >{isMasked(i, j) ? '?' : fmt(v)}</div>
            {/each}
          {/each}
        </div>
      </div>
    {:else if mode === 'digit'}
      {#if error}<p class="bad">{t('Could not load the digits: {e}', { e: error })}</p>{/if}
      {#if digits}
        <div class="digits">
          <div>
            <div class="label">{t('picture: a handwritten {d}', { d: digits.labels[pick] })}</div>
            <canvas bind:this={cvIn} class="px28" aria-label={t('input digit')}></canvas>
            <div class="chips pick" role="group" aria-label={t('Digit')}>
              {#each digits.labels as d, k}<button class:on={pick === k} aria-pressed={pick === k} onclick={() => (pick = k)}>{d}</button>{/each}
            </div>
          </div>
          <MatrixGrid value={kernel} label={t('filter (editable)')} editable decimals={2} onchange={(v) => (kernel = v)} />
          <div>
            <div class="label">{t('output {h}×{w}', { h: out?.length ?? '', w: out?.[0].length ?? '' })}</div>
            <canvas bind:this={cvOut} class="px28" aria-label={t('feature map')}></canvas>
          </div>
        </div>
      {:else if !error}
        <p class="dim">{t('Loading digits…')}</p>
      {/if}
    {/if}
  </div>

  {#if mode === 'toy' && padded && out && show3d}
    <div class="layer">
      <div class="chips cin" role="group" aria-label={t('Input channels')}>
        <span class="dim">{t('input channels:')}</span>
        <button class:on={cin === 1} aria-pressed={cin === 1} onclick={() => (cin = 1)}>{t('1 (a picture)')}</button>
        <button class:on={cin === 3} aria-pressed={cin === 3} onclick={() => (cin = 3)}>{t('3 (a later layer)')}</button>
      </div>
      <Tensors3D tensors={layer} keepView height="300px" ariaLabel={t('A convolution layer in 3D: the picture, one filter, and four stacked feature maps')} />
      <p class="cap">
        {t('The window and the filter that reads it ({depth}) are highlighted, and so is the one output number it makes, in channel {k}. Four filters make four feature maps, stacked as channels{pad}. Point at an output cell above to move the window; pick a filter to change the channel.', { depth: cin === 1 ? t('one channel deep') : t('all 3 channels deep, so one filter is a 3×3×3 block'), k: filterIdx + 1, pad: padding ? t('; pale cells are padding') : '' })}
      </p>
    </div>
  {/if}

  {#snippet controls()}
    <div class="chips" role="group" aria-label={t('Filter')}>
      <span class="dim">{t('Filter')}</span>
      {#each Object.keys(PRESETS) as name}
        <button class:on={JSON.stringify(kernel) === JSON.stringify(PRESETS[name])} aria-pressed={JSON.stringify(kernel) === JSON.stringify(PRESETS[name])} onclick={() => (kernel = copy(PRESETS[name]))}>{t(name)}</button>
      {/each}
    </div>
    <label class="sel">{t('stride')}
      <select bind:value={stride}><option value={1}>1</option><option value={2}>2</option></select>
    </label>
    <label class="sel">{t('padding')}
      <select bind:value={padding}><option value={0}>0</option><option value={1}>1</option></select>
    </label>
    {#if mode === 'toy'}
      <button class="lab-btn" aria-pressed={show3d} onclick={() => (show3d = !show3d)}>{show3d ? t('Hide the layer in 3D') : t('Show the layer in 3D')}</button>
    {/if}
  {/snippet}

  {#snippet readout()}
    {#if mode === 'toy' && cell && out}
      out[{cell.i}][{cell.j}] = {terms.filter(([p]) => p !== 0).map(([p, k]) => `${fmt(p)}×${fmt(k)}`).join(' + ') || '0'}
      = <b>{isMasked(cell.i, cell.j) ? t('? (answer the question below)') : fmt(out[cell.i][cell.j])}</b>
      <span class="dim">{t('(pixels that are 0 add nothing)')}</span>
    {:else}
      {t('output side')} = ⌊({src?.length ?? 5} − 3 + 2×{padding}) / {stride}⌋ + 1 = <b>{convOut(src?.length ?? 5, 3, stride, padding)}</b>
    {/if}
  {/snippet}

  {#snippet legend()}
    <span><i class="sw pos"></i>{t('positive output')}</span>
    <span><i class="sw neg"></i>{t('negative output')}</span>
    <span>{t('background = 0')}</span>
    {#if mode === 'toy'}<span><i class="sw win"></i>{t('the 3×3 window')}</span>{/if}
  {/snippet}
</LabFrame>

<style>
  .chips { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; }
  .chips button {
    font: inherit; font-size: 0.82rem; padding: 0.25rem 0.7rem; min-height: 2rem; border: 1px solid var(--field); border-radius: 999px;
    background: var(--bg); color: var(--dim); cursor: pointer;
  }
  .chips button.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  .chips .dim { font-size: 0.85rem; }
  .chips button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .pick { margin-top: 0.4rem; }
  .row { display: flex; flex-wrap: wrap; gap: 0.7rem; align-items: center; }
  .op { color: var(--dim); font-family: var(--mono); padding-top: 1rem; }
  .label { font-size: 0.78rem; color: var(--dim); margin-bottom: 0.2rem; font-family: var(--mono); }
  .cells { display: grid; gap: 2px; }
  .px {
    font: inherit; font-family: var(--mono); font-size: 0.78rem; height: 1.9rem; padding: 0;
    border: 1px solid var(--field); border-radius: 3px; background: var(--bg); color: var(--dim); cursor: pointer;
  }
  .px.ink { background: var(--fg); color: var(--bg); }
  .px.pad { opacity: 0.45; border-style: dashed; cursor: default; }
  .px.win { outline: 2px solid var(--accent); outline-offset: -2px; }
  .px:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
  .oc {
    font-family: var(--mono); font-size: 0.78rem; height: 1.9rem; display: grid; place-items: center;
    border: 1px solid var(--line); border-radius: 3px; cursor: pointer; transition: background 0.2s;
  }
  .oc.q { color: var(--warn); font-weight: 700; }
  .oc.hi, .oc:focus-visible { outline: 2px solid var(--fg); outline-offset: -2px; }
  .digits { display: flex; flex-wrap: wrap; gap: 0.8rem; align-items: flex-start; }
  .px28 { width: 9.5rem; max-width: 100%; aspect-ratio: 1; image-rendering: pixelated; border: 1px solid var(--line); border-radius: 4px; display: block; }
  .sw { width: 0.8rem; height: 0.8rem; border-radius: 2px; display: inline-block; vertical-align: -0.1em; margin-right: 0.3rem; }
  .sw.pos { background: var(--pos); }
  .sw.neg { background: var(--neg); }
  .sw.win { border: 2px solid var(--accent); }
  .sel { display: inline-flex; align-items: center; gap: 0.35rem; font-size: 0.85rem; color: var(--dim); }
  .sel select { font: inherit; min-height: 2rem; background: var(--bg); color: var(--fg); border: 1px solid var(--field); border-radius: 4px; }
  .layer { margin-top: 0.4rem; display: grid; gap: 0.5rem; }
  .cap { margin: 0; font-size: 0.8rem; color: var(--dim); max-width: 70ch; }
  .dim { color: var(--dim); }
  .bad { color: var(--warn); }
  @media (prefers-reduced-motion: reduce) { .oc { transition: none; } }
</style>
