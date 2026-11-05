<script lang="ts">
  /** Receptive field: stack 3×3 (or 5×5) layers, optionally with 2×2 pooling, and see how much of the picture one output pixel sees. */
  import LabFrame from './LabFrame.svelte'
  import { provideLang, useT } from '@lib/i18nSvelte'
  import type { Lang } from '@lib/i18n'
  let { lang = 'en' }: { lang?: Lang } = $props()
  provideLang(lang)
  const t = useT({
    'conv {l} ({k}×{k})': '卷积 {l}（{k}×{k}）',
    'pool {l} (2×2)': '池化 {l}（2×2）',
    'How much of the picture one output pixel sees': '一个输出像素能看到图片的多大一块',
    'Add layers, switch the filter size, turn pooling on, and watch the field grow.': '加层、换卷积核大小、打开池化，看感受野怎样变大。',
    "A {n}×{n} picture; the last layer's center pixel sees {r}×{r} of it": '一张 {n}×{n} 的图片；最后一层的中心像素能看到其中的 {r}×{r}',
    'What each layer sees': '每一层看到什么',
    '{name}: sees': '{name}：看到',
    ' (bigger than this grid)': '（比这张网格还大）',
    layers: '层数',
    'number of layers': '层数',
    'Filter size': '卷积核大小',
    '3×3 filters': '3×3 卷积核',
    '5×5 filters': '5×5 卷积核',
    '2×2 pooling after each layer': '每层之后做 2×2 池化',
    'one pixel after the last layer sees': '最后一层之后的一个像素能看到图片上',
    'pixels of the picture': '个像素',
    'the output pixel': '输出像素',
    'darkest ring: what the first layer sees; each lighter ring: what one more layer adds': '最深的一圈：第一层看到的；每一圈更浅的：多一层增加的部分',
  })
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
      out.push({ name: t('conv {l} ({k}×{k})', { l, k }), r })
      if (pool) {
        r += jump
        jump *= 2
        out.push({ name: t('pool {l} (2×2)', { l }), r })
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
  title={t('How much of the picture one output pixel sees')}
  hint={t('Add layers, switch the filter size, turn pooling on, and watch the field grow.')}
  onreset={() => { layers = 1; k = 3; pool = false }}
  resetDisabled={!changed}
>
  <div class="grid">
    <div class="board" style="grid-template-columns: repeat({N}, 1fr)" role="img" aria-label={t("A {n}×{n} picture; the last layer's center pixel sees {r}×{r} of it", { n: N, r: String(steps.at(-1)?.r) })}>
      {#each Array(N) as _, i}
        {#each Array(N) as _, j}
          <span class:center={i === c && j === c} style={i === c && j === c ? '' : shade(ring(i, j))}></span>
        {/each}
      {/each}
    </div>
    <ol class="trace" aria-label={t('What each layer sees')}>
      {#each steps as s, n}<li><i class="sw" style={shade(n)}></i>{t('{name}: sees', { name: s.name })} <b>{s.r}×{s.r}</b>{s.r > N ? t(' (bigger than this grid)') : ''}</li>{/each}
    </ol>
  </div>

  {#snippet controls()}
    <label class="slider">{t('layers')} <b>{layers}</b>
      <input type="range" min="1" max="4" bind:value={layers} aria-label={t('number of layers')} />
    </label>
    <span class="opts" role="radiogroup" aria-label={t('Filter size')}>
      <label><input type="radio" bind:group={k} value={3} /> {t('3×3 filters')}</label>
      <label><input type="radio" bind:group={k} value={5} /> {t('5×5 filters')}</label>
    </span>
    <label class="opts"><input type="checkbox" bind:checked={pool} /> {t('2×2 pooling after each layer')}</label>
  {/snippet}

  {#snippet readout()}
    {t('one pixel after the last layer sees')} <b>{steps.at(-1)?.r}×{steps.at(-1)?.r}</b> {t('pixels of the picture')}
  {/snippet}

  {#snippet legend()}
    <span><i class="sw center-sw"></i>{t('the output pixel')}</span>
    <span>{t('darkest ring: what the first layer sees; each lighter ring: what one more layer adds')}</span>
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
