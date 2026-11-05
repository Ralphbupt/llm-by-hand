<script lang="ts">
  /**
   * One GRU step next to the LSTM it simplifies (level N4).
   *   candidate  h̃ = tanh(a + r · u · h_prev)     a = the input's part (x @ W), u = the weight on the old h (fixed at 1 here)
   *   new state  h = (1 − z) · h_prev + z · h̃
   * Move the update gate z and the reset gate r and watch what the new h keeps and what it takes.
   * The new h always lands between h_prev and h̃: z says how far along the way it goes.
   */
  import { readable } from '@lib/readable'
  import LabFrame from './LabFrame.svelte'
  import { provideLang, useT } from '@lib/i18nSvelte'
  import type { Lang } from '@lib/i18n'

  let { lang = 'en' }: { lang?: Lang } = $props()
  provideLang(lang)
  const t = useT({
    'One GRU step: keep the old state, or take the new candidate': 'GRU 的一步：保留旧状态，还是取新的候选值',
    'Move the gates. The new h always lands between h_prev and the candidate h̃; z says how close h is to h̃.': '拖动各个门。新的 h 总是落在 h_prev 和候选值 h̃ 之间；z 决定 h 离 h̃ 有多近。',
    'The old state, the candidate and the new state as bars from −1 to 1': '旧状态、候选值和新状态，画成 −1 到 1 之间的条',
    'old state h_prev': '旧状态 h_prev',
    'candidate h̃': '候选值 h̃',
    'new h': '新的 h',
    'Gates (0 to 1)': '门（0 到 1）',
    'r, reset': 'r，重置',
    'z, update': 'z，更新',
    'reset gate r': '重置门 r',
    'update gate z': '更新门 z',
    'Inputs': '输入',
    'h_prev, old state': 'h_prev，旧状态',
    'a, input part': 'a，输入部分',
    'input part a': '输入部分 a',
    ', and h =': '，h =',
    'With z near 0, the old state passes through almost unchanged: the GRU’s “keep” path.': 'z 接近 0 时，旧状态几乎原样通过：这就是 GRU 的“保留”通路。',
    'With r near 0, the candidate ignores the old state and uses only the input.': 'r 接近 0 时，候选值忽略旧状态，只用输入。',
    'the way from h_prev to h̃': '从 h_prev 到 h̃ 的这段路',
    'The LSTM and the GRU side by side': 'LSTM 和 GRU 对比',
    'state carried between steps': '在步与步之间传递的状态',
    'h and c': 'h 和 c',
    'h only': '只有 h',
    'gates': '门',
    'forget, input, output': '遗忘门、输入门、输出门',
    'update z, reset r': '更新门 z、重置门 r',
    'weight blocks': '权重块',
    '“keep” path': '“保留”通路',
  })

  const START = { hPrev: 0.8, a: -0.6, z: 0.3, r: 1 }
  let hPrev = $state(START.hPrev)
  let a = $state(START.a)
  let z = $state(START.z)
  let r = $state(START.r)
  const cand = $derived(Math.tanh(a + r * hPrev))
  const h = $derived((1 - z) * hPrev + z * cand)
  const changed = $derived(hPrev !== START.hPrev || a !== START.a || z !== START.z || r !== START.r)
  function reset() {
    hPrev = START.hPrev; a = START.a; z = START.z; r = START.r
  }
  const f = (v: number) => (Math.abs(v) < 0.005 ? '0.00' : v.toFixed(2))

  // picture: three bars from −1 to 1 around a zero line
  const W = 360, X0 = 150, X1 = 346
  const bx = (v: number) => (X0 + X1) / 2 + (v * (X1 - X0)) / 2
  const ROWS = [34, 76, 118] // bar centers: h_prev, candidate, new h
  const BH = 14
</script>

<LabFrame
  title={t('One GRU step: keep the old state, or take the new candidate')}
  hint={t('Move the gates. The new h always lands between h_prev and the candidate h̃; z says how close h is to h̃.')}
  onreset={reset}
  resetDisabled={!changed}
>
  <svg use:readable viewBox="0 0 {W} 168" class="bars" role="img"
    aria-label={t('The old state, the candidate and the new state as bars from −1 to 1')}>
    {#each [-1, -0.5, 0.5, 1] as g}<line x1={bx(g)} x2={bx(g)} y1="16" y2="136" class="grid" />{/each}
    <line x1={bx(0)} x2={bx(0)} y1="14" y2="138" class="zero" />
    {#each [-1, 0, 1] as v}<text x={bx(v)} y="154" class="tick" text-anchor={v === -1 ? 'start' : v === 1 ? 'end' : 'middle'}>{v}</text>{/each}

    <text x="10" y={ROWS[0] - 2} class="name">{t('old state h_prev')}</text>
    <text x="10" y={ROWS[0] + 12} class="val">{f(hPrev)}</text>
    <rect x={Math.min(bx(0), bx(hPrev))} y={ROWS[0] - BH / 2} width={Math.abs(bx(hPrev) - bx(0))} height={BH} rx="2" class="bar old" />

    <text x="10" y={ROWS[1] - 2} class="name">{t('candidate h̃')}</text>
    <text x="10" y={ROWS[1] + 12} class="val">{f(cand)}</text>
    <rect x={Math.min(bx(0), bx(cand))} y={ROWS[1] - BH / 2} width={Math.abs(bx(cand) - bx(0))} height={BH} rx="2" class="bar cand" />

    <text x="10" y={ROWS[2] - 2} class="name strong">{t('new h')}</text>
    <text x="10" y={ROWS[2] + 12} class="val strong">{f(h)}</text>
    <!-- the way from h_prev to h̃; the new h sits z of the way along it -->
    <line x1={bx(hPrev)} x2={bx(cand)} y1={ROWS[2]} y2={ROWS[2]} class="way" />
    <line x1={bx(hPrev)} x2={bx(hPrev)} y1={ROWS[2] - 11} y2={ROWS[2] + 11} class="end" />
    <line x1={bx(cand)} x2={bx(cand)} y1={ROWS[2] - 11} y2={ROWS[2] + 11} class="end" />
    <rect x={Math.min(bx(0), bx(h))} y={ROWS[2] - BH / 2} width={Math.abs(bx(h) - bx(0))} height={BH} rx="2" class="bar new" />
    <line x1={bx(h)} x2={bx(h)} y1={ROWS[2] - 10} y2={ROWS[2] + 10} class="mark" />
  </svg>

  {#snippet controls()}
    <fieldset class="group">
      <legend>{t('Gates (0 to 1)')}</legend>
      <label><span>{t('r, reset')}</span> <b>{f(r)}</b> <input type="range" min="0" max="1" step="0.05" bind:value={r} aria-label={t('reset gate r')} /></label>
      <label><span>{t('z, update')}</span> <b>{f(z)}</b> <input type="range" min="0" max="1" step="0.05" bind:value={z} aria-label={t('update gate z')} /></label>
    </fieldset>
    <fieldset class="group">
      <legend>{t('Inputs')}</legend>
      <label><span>{t('h_prev, old state')}</span> <b>{f(hPrev)}</b> <input type="range" min="-1" max="1" step="0.05" bind:value={hPrev} aria-label={t('old state h_prev')} /></label>
      <label><span>{t('a, input part')}</span> <b>{f(a)}</b> <input type="range" min="-2" max="2" step="0.1" bind:value={a} aria-label={t('input part a')} /></label>
    </fieldset>
  {/snippet}

  {#snippet readout()}
    h̃ = tanh({f(a)} + {f(r)} × {f(hPrev)}) = {f(cand)}{t(', and h =')} {f(1 - z)} × {f(hPrev)} + {f(z)} × {f(cand)} = <b>{f(h)}</b>.
    {#if z < 0.1}<span class="note">{t('With z near 0, the old state passes through almost unchanged: the GRU’s “keep” path.')}</span>{:else if r < 0.1}<span class="note">{t('With r near 0, the candidate ignores the old state and uses only the input.')}</span>{/if}
  {/snippet}

  {#snippet legend()}
    <span><i class="sw old"></i>{t('old state h_prev')}</span>
    <span><i class="sw cand"></i>{t('candidate h̃')}</span>
    <span><i class="sw new"></i>{t('new h')}</span>
    <span><i class="sw way"></i>{t('the way from h_prev to h̃')}</span>
  {/snippet}
</LabFrame>

<figure class="cmp">
  <table>
    <caption>{t('The LSTM and the GRU side by side')}</caption>
    <thead><tr><th scope="col"></th><th scope="col">LSTM</th><th scope="col">GRU</th></tr></thead>
    <tbody>
      <tr><th scope="row">{t('state carried between steps')}</th><td>{t('h and c')}</td><td>{t('h only')}</td></tr>
      <tr><th scope="row">{t('gates')}</th><td>{t('forget, input, output')}</td><td>{t('update z, reset r')}</td></tr>
      <tr><th scope="row">{t('weight blocks')}</th><td>4 (f, i, g, o)</td><td>3 (z, r, h̃)</td></tr>
      <tr><th scope="row">{t('“keep” path')}</th><td>c = f · c + i · g</td><td>h = (1 − z) · h + z · h̃</td></tr>
    </tbody>
  </table>
</figure>

<style>
  .bars { width: 100%; max-width: 32rem; display: block; background: var(--bg); border: 1px solid var(--line); border-radius: 6px; }
  .grid { stroke: var(--line); stroke-dasharray: 2 3; }
  .zero { stroke: var(--dim); stroke-width: 1.2; }
  .tick { font-size: 10px; fill: var(--dim); font-family: var(--mono); }
  .name { font-size: 10.5px; fill: var(--dim); }
  .name.strong { fill: var(--fg); font-weight: 650; }
  .val { font-size: 11px; fill: var(--fg); font-family: var(--mono); }
  .val.strong { font-weight: 700; fill: var(--accent); }
  .bar { transition: x 0.2s, width 0.2s; }
  .bar.old { fill: var(--dim); }
  .bar.cand { fill: color-mix(in srgb, var(--fg) 12%, transparent); stroke: var(--fg); stroke-width: 1.5; stroke-dasharray: 4 2; }
  .bar.new { fill: var(--accent); }
  .way { stroke: var(--fg); stroke-width: 1.2; opacity: 0.7; }
  .end { stroke: var(--fg); stroke-width: 1.2; opacity: 0.7; }
  .mark { stroke: var(--accent); stroke-width: 2.5; }
  @media (prefers-reduced-motion: reduce) { .bar { transition: none; } }

  .group { border: 1px solid var(--line); border-radius: 6px; padding: 0.4rem 0.7rem 0.6rem; margin: 0; display: grid; gap: 0.25rem; min-width: min(100%, 15rem); flex: 1 1 15rem; }
  .group legend { font-size: 0.78rem; color: var(--dim); padding: 0 0.3rem; }
  .group label { display: grid; grid-template-columns: 7.5rem 3rem minmax(0, 1fr); align-items: center; gap: 0.4rem; font-size: 0.85rem; }
  .group span { color: var(--dim); }
  .group b { font-family: var(--mono); font-weight: 600; }
  .group input { width: 100%; min-height: 2rem; accent-color: var(--accent); }
  @media (max-width: 760px) { .group input { min-height: 2.5rem; } }
  .note { display: block; margin-top: 0.25rem; font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }

  .sw { display: inline-block; width: 0.9rem; height: 0.6rem; border-radius: 2px; vertical-align: -0.05em; margin-right: 0.35rem; }
  .sw.old { background: var(--dim); }
  .sw.cand { background: color-mix(in srgb, var(--fg) 12%, transparent); border: 1.5px dashed var(--fg); box-sizing: border-box; }
  .sw.new { background: var(--accent); }
  .sw.way { height: 0.6rem; border-left: 1.5px solid var(--fg); border-right: 1.5px solid var(--fg); background: linear-gradient(var(--fg), var(--fg)) center / 100% 1.5px no-repeat; border-radius: 0; opacity: 0.8; }

  .cmp { margin: -0.6rem 0 1.4rem; }
  .cmp table { border-collapse: collapse; width: 100%; max-width: 40rem; font-size: 0.82rem; }
  .cmp caption { text-align: left; font-size: 0.8rem; color: var(--dim); padding-bottom: 0.3rem; }
  .cmp th, .cmp td { border: 1px solid var(--line); padding: 0.3rem 0.5rem; text-align: left; vertical-align: top; }
  .cmp thead th { font-weight: 650; color: var(--fg); }
  .cmp tbody th { color: var(--dim); font-weight: 400; width: 34%; }
  .cmp td { font-family: var(--mono); }
</style>
