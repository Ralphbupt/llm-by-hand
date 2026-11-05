<script lang="ts">
  /**
   * Trade-off lab (level 18): write 200 six-word continuations with one strategy,
   * then count how many are different (diversity) and how many follow our sentence rules (quality).
   */
  import { onMount } from 'svelte'
  import LabFrame from './LabFrame.svelte'
  import { readable } from '@lib/readable'
  import { softmax, topK, topP, sampleIndex, followsRules, type Trigram } from '@lib/generation'
  import { provideLang, useT } from '@lib/i18nSvelte'
  import type { Lang } from '@lib/i18n'

  let { lang = 'en' }: { lang?: Lang } = $props()
  provideLang(lang)
  // `t` is a loop counter below, so the translator is `tx`
  const tx = useT({
    'greedy': '贪心',
    'temperature': '温度',
    'Different or correct? You can’t have both at the maximum': '不同还是正确？两者不能同时达到最大',
    'Faint curves: each strategy at every value of its setting. Pick a strategy, set it, and write 200 continuations to add your own point.': '浅色曲线：每种策略在它的设置取各个值时的结果。选一种策略，调好设置，写 200 个续写，加上你自己的点。',
    'Loading the counting model…': '正在加载计数模型…',
    'Each strategy as a curve: different continuations across, fraction that follows the rules up; your runs as labeled points': '每种策略画成一条曲线：横轴是不同续写的个数，纵轴是符合规则的比例；你的每次运行是带标签的点',
    'different continuations (of 200) →': '不同的续写（共 200 个）→',
    '↑ fraction that follows the rules': '↑ 符合规则的比例',
    'ideal': '理想',
    '{a} {b}: {d} different, {v}% follow the rules': '{a} {b}：{d} 个不同，{v}% 符合规则',
    'greedy: {d} different, {v}%': '贪心：{d} 个不同，{v}%',
    '/ 200 different': '/ 200 个不同',
    '(diversity)': '（多样性）',
    'follow the sentence rules': '符合句子规则',
    '(quality)': '（质量）',
    'Strategy': '策略',
    'Write 200 continuations': '写 200 个续写',
    '{name}: {d} of 200 different · {v}% follow the rules': '{name}：200 个里有 {d} 个不同 · {v}% 符合规则',
    'Press “Write 200 continuations” to add a point for {name}.': '按“写 200 个续写”，为 {name} 加一个点。',
    'temperature sweep': '温度扫描',
    'top-k sweep': 'top-k 扫描',
    'top-p sweep': 'top-p 扫描',
    'your runs': '你的运行',
    'underlined': '带下划线的',
    ' words break the rules · each run uses fresh random numbers': '词不符合规则 · 每次运行都用新的随机数',
  })

  let model = $state<Trigram | null>(null)
  onMount(() => { fetch('/data/generation/trigram.json').then((r) => r.json()).then((m) => { model = m; sweep(); generate() }) })

  type Strat = 'greedy' | 'temp' | 'topk' | 'topp'
  let strat = $state<Strat>('temp')
  let T = $state(1)
  let k = $state(3)
  let p = $state(0.9)
  let result = $state<{ distinct: number; valid: number; examples: { words: string[]; ok: boolean[] }[] } | null>(null)
  // every run lands on the chart, so the trade-off between the two numbers shows up as you try strategies
  let runs = $state<{ name: string; distinct: number; valid: number }[]>([])
  const nameOf = () => (strat === 'greedy' ? tx('greedy') : strat === 'temp' ? `T ${T.toFixed(1)}` : strat === 'topk' ? `top-k ${k}` : `top-p ${p.toFixed(2)}`)

  type Setting = { strat: Strat; T: number; k: number; p: number }
  const current = (): Setting => ({ strat, T, k, p })
  function pickWith(q: number[], st: Setting): number {
    if (st.strat === 'greedy') return q.indexOf(Math.max(...q))
    if (st.strat === 'temp') return sampleIndex(softmax(q.map(Math.log), st.T))
    if (st.strat === 'topk') return sampleIndex(topK(q, st.k))
    return sampleIndex(topP(q, st.p))
  }
  function runWith(st: Setting) {
    const m = model!
    const ix = new Map(m.vocab.map((w, i) => [w, i]))
    const seen = new Set<string>()
    let valid = 0
    const examples: { words: string[]; ok: boolean[] }[] = []
    for (let r = 0; r < 200; r++) {
      const seq = ['.', 'the']
      for (let t = 0; t < 6; t++) {
        const q = m.probs[ix.get(seq[seq.length - 2])!][ix.get(seq[seq.length - 1])!]
        seq.push(m.vocab[pickWith(q, st)])
      }
      const words = seq.slice(1)
      seen.add(words.join(' '))
      if (followsRules(words)) valid++
      if (examples.length < 6) examples.push({ words, ok: words.map((w, i) => followsRules(words.slice(0, i + 1))) })
    }
    return { distinct: seen.size, valid: valid / 200, examples }
  }
  // the background: each strategy swept across its setting, drawn as a faint curve, so the trade-off is visible
  // before the learner runs anything
  type Curve = { strat: Strat; label: string; pts: { distinct: number; valid: number; tag: string }[] }
  let curves = $state<Curve[]>([])
  function sweep() {
    const T_ = [0.3, 0.6, 1, 1.5, 2, 3]
    const K_ = [1, 2, 3, 5, 8, 14]
    const P_ = [0.3, 0.5, 0.7, 0.9, 1]
    const mk = (strat: Strat, label: string, list: number[], f: (v: number) => Setting, tag: (v: number) => string): Curve =>
      ({ strat, label, pts: list.map((v) => ({ ...runWith(f(v)), tag: tag(v) })) })
    curves = [
      mk('temp', tx('temperature'), T_, (v) => ({ strat: 'temp', T: v, k, p }), (v) => `T ${v}`),
      mk('topk', 'top-k', K_, (v) => ({ strat: 'topk', T, k: v, p }), (v) => `k ${v}`),
      mk('topp', 'top-p', P_, (v) => ({ strat: 'topp', T, k, p: v }), (v) => `p ${v}`),
    ]
    greedyPt = runWith({ strat: 'greedy', T, k, p })
  }
  let greedyPt = $state<{ distinct: number; valid: number } | null>(null)

  function generate() {
    if (!model) return
    const r = runWith(current())
    result = r
    const name = nameOf()
    runs = [...runs.filter((x) => x.name !== name), { name, distinct: r.distinct, valid: r.valid }].slice(-8)
  }
  function reset() { strat = 'temp'; T = 1; k = 3; p = 0.9; result = null; runs = []; generate() }
  const curveColor: Record<string, string> = { temp: 'var(--cat-1)', topk: 'var(--cat-3)', topp: 'var(--cat-2)' }
  // chart geometry
  const CW = 360, CH = 240, L = 40, B = 44, TOP = 30
  const cx = (d: number) => L + (d / 200) * (CW - L - 10)
  const cy = (v: number) => CH - B - v * (CH - B - TOP)
</script>

<LabFrame
  title={tx('Different or correct? You can’t have both at the maximum')}
  hint={tx('Faint curves: each strategy at every value of its setting. Pick a strategy, set it, and write 200 continuations to add your own point.')}
  onreset={reset}
  resetDisabled={runs.length <= 1 && strat === 'temp' && T === 1}
>
  {#if !model}
    <div class="skeleton" aria-hidden="true"></div>
    <p class="dim">{tx('Loading the counting model…')}</p>
  {:else}
    <svg class="chart" use:readable viewBox="0 0 {CW} {CH}" role="img" aria-label={tx('Each strategy as a curve: different continuations across, fraction that follows the rules up; your runs as labeled points')}>
      {#each [0, 0.25, 0.5, 0.75, 1] as v}<line x1={L} y1={cy(v)} x2={CW - 8} y2={cy(v)} class="gl" /><text x={L - 6} y={cy(v) + 3.5} class="tk end">{v * 100}%</text>{/each}
      {#each [0, 50, 100, 150, 200] as d}<line x1={cx(d)} y1={cy(0)} x2={cx(d)} y2={cy(0) + 4} class="ax" /><text x={cx(d)} y={cy(0) + 15} class="tk mid">{d}</text>{/each}
      <line x1={L} y1={cy(0)} x2={CW - 8} y2={cy(0)} class="ax" />
      <line x1={L} y1={cy(0)} x2={L} y2={TOP - 8} class="ax" />
      <text x={(L + CW - 8) / 2} y={CH - 6} class="tk mid axt">{tx('different continuations (of 200) →')}</text>
      <text x={L - 30} y="12" class="tk axt">{tx('↑ fraction that follows the rules')}</text>
      <rect x={cx(150)} y={cy(1)} width={cx(200) - cx(150)} height={cy(0.85) - cy(1)} class="goal" />
      <text x={cx(175)} y={cy(0.925) + 3.5} class="tk mid goal-t">{tx('ideal')}</text>
      {#each curves as c}
        <polyline points={c.pts.map((q) => `${cx(q.distinct)},${cy(q.valid)}`).join(' ')} class="curve" style:--c={curveColor[c.strat]} />
        {#each c.pts as q}<circle cx={cx(q.distinct)} cy={cy(q.valid)} r="2.2" class="cpt" style:--c={curveColor[c.strat]}><title>{tx('{a} {b}: {d} different, {v}% follow the rules', { a: c.label, b: q.tag, d: q.distinct, v: Math.round(q.valid * 100) })}</title></circle>{/each}
      {/each}
      {#if greedyPt}<rect x={cx(greedyPt.distinct) - 3} y={cy(greedyPt.valid) - 3} width="6" height="6" class="gpt"><title>{tx('greedy: {d} different, {v}%', { d: greedyPt.distinct, v: Math.round(greedyPt.valid * 100) })}</title></rect>{/if}
      {#each runs as r, i}
        {@const cur = i === runs.length - 1}
        <circle cx={cx(r.distinct)} cy={cy(r.valid)} r={cur ? 5.5 : 4} class="pt" class:cur />
        <text x={cx(r.distinct) + (r.distinct > 140 ? -8 : 8)} y={cy(r.valid) + 4} class="pl" class:cur class:end={r.distinct > 140}>{r.name}</text>
      {/each}
    </svg>

    {#if result}
      <div class="score">
        <div><span class="big">{result.distinct}</span> {tx('/ 200 different')} <span class="dim">{tx('(diversity)')}</span></div>
        <div><span class="big">{Math.round(result.valid * 100)}%</span> {tx('follow the sentence rules')} <span class="dim">{tx('(quality)')}</span></div>
      </div>
      <ul class="ex">
        {#each result.examples as e}
          <li>{#each e.words as w, i}<span class:bad={!e.ok[i]}>{w}</span>{' '}{/each}</li>
        {/each}
      </ul>
    {/if}
  {/if}

  {#snippet controls()}
    <div class="strats" role="group" aria-label={tx('Strategy')}>
      {#each [['greedy', 'greedy'], ['temp', 'temperature'], ['topk', 'top-k'], ['topp', 'top-p']] as [v, name]}
        <button type="button" class:on={strat === v} aria-pressed={strat === v} onclick={() => { strat = v as Strat; result = null }}>{tx(name)}</button>
      {/each}
    </div>
    {#if strat === 'temp'}
      <label class="knob">T <b>{T.toFixed(1)}</b><input type="range" min="0.2" max="3" step="0.1" value={T} oninput={(e) => { T = +e.currentTarget.value; result = null }} /></label>
    {:else if strat === 'topk'}
      <label class="knob">k <b>{k}</b><input type="range" min="1" max="14" step="1" value={k} oninput={(e) => { k = +e.currentTarget.value; result = null }} /></label>
    {:else if strat === 'topp'}
      <label class="knob">p <b>{p.toFixed(2)}</b><input type="range" min="0.05" max="1" step="0.05" value={p} oninput={(e) => { p = +e.currentTarget.value; result = null }} /></label>
    {/if}
    <button type="button" class="lab-btn primary" onclick={generate} disabled={!model}>{tx('Write 200 continuations')}</button>
  {/snippet}

  {#snippet readout()}
    {#if result}{tx('{name}: {d} of 200 different · {v}% follow the rules', { name: nameOf(), d: result.distinct, v: Math.round(result.valid * 100) })}{:else}<span class="idle">{tx('Press “Write 200 continuations” to add a point for {name}.', { name: nameOf() })}</span>{/if}
  {/snippet}

  {#snippet legend()}
    <span class="lg"><i class="ln" style="--c: var(--cat-1)"></i>{tx('temperature sweep')}</span>
    <span class="lg"><i class="ln" style="--c: var(--cat-3)"></i>{tx('top-k sweep')}</span>
    <span class="lg"><i class="ln" style="--c: var(--cat-2)"></i>{tx('top-p sweep')}</span>
    <span class="lg"><i class="sq"></i>{tx('greedy')}</span>
    <span class="lg"><i class="dt"></i>{tx('your runs')}</span>
    <span class="lg"><u>{tx('underlined')}</u>{tx(' words break the rules · each run uses fresh random numbers')}</span>
  {/snippet}
</LabFrame>

<style>
  .skeleton { height: 14rem; border-radius: 6px; background: var(--bg); border: 1px dashed var(--line); }
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
  .strats { display: inline-flex; border: 1px solid var(--field); border-radius: 999px; overflow: hidden; flex-wrap: wrap; }
  .strats button { font: inherit; font-size: 0.82rem; padding: 0.25rem 0.75rem; min-height: 2.1rem; border: 0; background: var(--bg); color: var(--fg); cursor: pointer; }
  .strats button + button { border-left: 1px solid var(--field); }
  .strats button.on { color: var(--accent); background: var(--highlight); }
  .strats button:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
  .knob { display: inline-flex; gap: 0.5rem; align-items: center; font-family: var(--mono); font-size: 0.85rem; }
  .knob b { color: var(--accent); }
  .knob input { min-width: 130px; accent-color: var(--accent); }
  .chart { width: 100%; max-width: 480px; height: auto; display: block; }
  .ax { stroke: var(--dim); stroke-width: 0.8; }
  .gl { stroke: var(--line); stroke-width: 0.5; }
  .tk { font-size: 9.5px; fill: var(--dim); font-family: var(--mono); }
  .axt { fill: var(--fg); }
  .tk.end, .pl.end { text-anchor: end; }
  .tk.mid { text-anchor: middle; }
  .goal { fill: color-mix(in srgb, var(--ok) 16%, transparent); stroke: var(--ok); stroke-width: 0.8; stroke-dasharray: 3 2; }
  .goal-t { fill: var(--ok); font-weight: 600; }
  .curve { fill: none; stroke: var(--c); stroke-width: 1.6; opacity: 0.55; }
  .cpt { fill: var(--c); opacity: 0.7; }
  .gpt { fill: var(--cat-4); }
  .pt { fill: var(--card); stroke: var(--accent); stroke-width: 2; transition: cx 0.25s ease-out, cy 0.25s ease-out; }
  .pt.cur { fill: var(--accent); }
  .pl { font-size: 10px; fill: var(--fg); font-family: var(--mono); }
  .pl.cur { font-weight: 700; }
  .score { display: flex; flex-wrap: wrap; gap: 0.5rem 2rem; }
  .big { font-family: var(--mono); font-size: 1.4rem; font-weight: 700; color: var(--accent); }
  .ex { font-family: var(--mono); font-size: 0.85rem; margin: 0.4rem 0 0; padding-left: 1.1rem; }
  .bad { color: var(--warn); font-weight: 700; text-decoration: underline; text-underline-offset: 3px; }
  .dim { color: var(--dim); font-size: 0.85rem; margin: 0; }
  .lg { display: inline-flex; align-items: center; gap: 0.35rem; }
  .ln { display: inline-block; width: 16px; height: 0; border-top: 2px solid var(--c); }
  .sq { display: inline-block; width: 7px; height: 7px; background: var(--cat-4); }
  .dt { display: inline-block; width: 9px; height: 9px; border-radius: 50%; background: var(--accent); }
  @media (prefers-reduced-motion: reduce) { .pt { transition: none; } }
  /* phones: touch targets at least 40px tall; 16px fields so iOS does not zoom */
  @media (max-width: 760px) { .strats button { min-height: 2.5rem; } .knob input { min-height: 2.5rem; } }
</style>
