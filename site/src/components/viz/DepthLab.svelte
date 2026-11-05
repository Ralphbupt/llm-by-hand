<script lang="ts">
  /**
   * Deep stacks, plain vs residual: how big the signal stays going up, and how big the gradient stays coming back down.
   * Computed live by stack() in lib/residuals.ts (the same numbers as demo.py).
   */
  import { stack } from '@lib/residuals'
  import { readable } from '@lib/readable'
  import LabFrame from './LabFrame.svelte'
  import { provideLang, useT } from '@lib/i18nSvelte'
  import type { Lang } from '@lib/i18n'
  let { lang = 'en' }: { lang?: Lang } = $props()
  provideLang(lang)
  const t = useT({
    'Stack {n} tanh layers: how much of the signal and the gradient is left?': '叠 {n} 个 tanh 层：信号和梯度还剩多少？',
    'Drag depth and weight scale. Compare the plain stack with the residual stack.': '拖动深度和权重尺度。比较普通堆叠和残差堆叠。',
    'Signal going up': '往上走的信号',
    'std of each layer’s output': '每一层输出的标准差',
    'Gradient coming down': '往下回来的梯度',
    'std of the gradient reaching each layer': '传到每一层的梯度的标准差',
    '{name}: plain stack vs residual stack, log scale': '{name}：普通堆叠对比残差堆叠，对数刻度',
    plain: '普通',
    residual: '残差',
    '0 (input)': '0（输入）',
    '{n} (top)': '{n}（顶部）',
    depth: '深度',
    'weight scale': '权重尺度',
    'gradient at layer 0 ÷ gradient at the top: plain': '第 0 层的梯度 ÷ 顶部的梯度：普通',
    ', residual': '，残差',
    'plain: h ← tanh(h @ W)': '普通：h ← tanh(h @ W)',
    'residual: h ← h + tanh(h @ W)': '残差：h ← h + tanh(h @ W)',
    'log scale; the dashed line is 1': '对数刻度；虚线是 1',
  })

  const D0 = 30, S0 = 0.8
  let depth = $state(D0)
  let scale = $state(S0)

  const plain = $derived(stack(depth, scale, false))
  const res = $derived(stack(depth, scale, true))
  const changed = $derived(depth !== D0 || scale !== S0)

  // log scale from 1e-6 to 1e2
  const LO = -6, HI = 2
  const W = 320, H = 170, PL = 40, PR = 52, PT = 10, PB = 26
  const xOf = (i: number) => PL + (i / Math.max(1, depth)) * (W - PL - PR)
  const yOf = (v: number) => {
    const l = Math.min(HI, Math.max(LO, Math.log10(Math.max(v, 1e-12))))
    return PT + ((HI - l) / (HI - LO)) * (H - PT - PB)
  }
  const line = (vs: number[]) => vs.map((v, i) => `${xOf(i).toFixed(1)},${yOf(v).toFixed(1)}`).join(' ')
  const ticks = [2, 0, -2, -4, -6]
  const tickLabel = (e: number) => (e === 0 ? '1' : e === 2 ? '100' : `1e${e}`)
  const fmt = (v: number) => (v >= 0.01 && v < 1000 ? v.toFixed(v < 1 ? 3 : 2) : v.toExponential(1))
  const ratio = (g: number[]) => g[0] / g[g.length - 1]
  // end labels: keep at least 13 units apart so "plain" and "residual" never overlap
  function ends(pv: number[], rv: number[]) {
    let a = yOf(pv.at(-1)!), b = yOf(rv.at(-1)!)
    const gap = 13
    if (Math.abs(a - b) < gap) {
      const mid = (a + b) / 2
      if (a <= b) { a = mid - gap / 2; b = mid + gap / 2 } else { a = mid + gap / 2; b = mid - gap / 2 }
    }
    return { plain: a + 3, res: b + 3 }
  }
</script>

<LabFrame
  title={t('Stack {n} tanh layers: how much of the signal and the gradient is left?', { n: depth })}
  hint={t('Drag depth and weight scale. Compare the plain stack with the residual stack.')}
  onreset={() => { depth = D0; scale = S0 }}
  resetDisabled={!changed}
>
  <div class="panels">
    {#each [{ key: 'act', name: t('Signal going up'), sub: t('std of each layer’s output') }, { key: 'grad', name: t('Gradient coming down'), sub: t('std of the gradient reaching each layer') }] as p}
      {@const pv = p.key === 'act' ? plain.act : plain.grad}
      {@const rv = p.key === 'act' ? res.act : res.grad}
      {@const ys = ends(pv, rv)}
      <figure>
        <figcaption><b>{p.name}</b> <span>{p.sub}</span></figcaption>
        <svg use:readable viewBox="0 0 {W} {H}" role="img" aria-label={t('{name}: plain stack vs residual stack, log scale', { name: p.name })}>
          {#each ticks as e}
            <line x1={PL} x2={W - PR} y1={yOf(10 ** e)} y2={yOf(10 ** e)} class="grid" />
            <text x={PL - 4} y={yOf(10 ** e) + 3} class="tick end">{tickLabel(e)}</text>
          {/each}
          <line x1={PL} x2={W - PR} y1={yOf(1)} y2={yOf(1)} class="one" />
          <polyline points={line(pv)} class="plain" />
          <polyline points={line(rv)} class="res" />
          <!-- label each line at its end, so no color lookup is needed -->
          <text x={W - PR + 4} y={ys.plain} class="end-lbl plain-t">{t('plain')}</text>
          <text x={W - PR + 4} y={ys.res} class="end-lbl res-t">{t('residual')}</text>
          <text x={PL} y={H - 6} class="tick">{t('0 (input)')}</text>
          <text x={W - PR} y={H - 6} class="tick end">{t('{n} (top)', { n: depth })}</text>
        </svg>
      </figure>
    {/each}
  </div>

  {#snippet controls()}
    <label class="knob">{t('depth')} <input type="range" min="1" max="50" bind:value={depth} aria-label={t('depth')} /> <b>{depth}</b></label>
    <label class="knob">{t('weight scale')} <input type="range" min="0.5" max="1.5" step="0.1" bind:value={scale} aria-label={t('weight scale')} /> <b>{scale.toFixed(1)}/√16</b></label>
  {/snippet}

  {#snippet readout()}
    {t('gradient at layer 0 ÷ gradient at the top: plain')} <b class="p">{fmt(ratio(plain.grad))}</b>{t(', residual')} <b class="r">{fmt(ratio(res.grad))}</b>
  {/snippet}

  {#snippet legend()}
    <span><i class="sw plain"></i>{t('plain: h ← tanh(h @ W)')}</span>
    <span><i class="sw res"></i>{t('residual: h ← h + tanh(h @ W)')}</span>
    <span>{t('log scale; the dashed line is 1')}</span>
  {/snippet}
</LabFrame>

<style>
  .panels { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.8rem; }
  @media (max-width: 600px) { .panels { grid-template-columns: minmax(0, 1fr); } }
  figure { margin: 0; min-width: 0; }
  figcaption { font-size: 0.85rem; margin-bottom: 0.2rem; }
  figcaption span { color: var(--dim); }
  svg { width: 100%; height: auto; display: block; background: var(--bg); border: 1px solid var(--line); border-radius: 6px; }
  .grid { stroke: var(--line); stroke-width: 0.6; }
  .one { stroke: var(--dim); stroke-dasharray: 3 3; stroke-width: 0.8; }
  .tick { font-size: 10px; fill: var(--dim); font-family: var(--mono); }
  .end { text-anchor: end; }
  .end-lbl { font-size: 10px; font-family: var(--mono); font-weight: 600; }
  polyline { fill: none; stroke-width: 2; stroke-linejoin: round; }
  .plain { stroke: var(--cat-3); }
  .res { stroke: var(--cat-1); }
  .plain-t { fill: var(--cat-3); }
  .res-t { fill: var(--cat-1); }
  .sw { display: inline-block; width: 1rem; height: 3px; vertical-align: 0.25em; margin-right: 0.35rem; }
  .sw.plain { background: var(--cat-3); }
  .sw.res { background: var(--cat-1); }
  .knob { display: inline-flex; gap: 0.4rem; align-items: center; font-size: 0.88rem; color: var(--dim); }
  .knob b { color: var(--fg); font-family: var(--mono); font-weight: 600; }
  input[type='range'] { width: 7rem; min-height: 2rem; accent-color: var(--accent); }
  .p { color: var(--cat-3); }
  .r { color: var(--cat-1); }
</style>
