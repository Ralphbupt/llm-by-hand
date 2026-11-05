<script lang="ts">
  /**
   * Token lab: type text → character vocabulary → ids → embedding rows.
   * Click a token to see its one-hot row times the table. Drag a dot in the plot to change that row.
   * Starting rows come from a fixed rule (same as demo.py) so everyone sees the same numbers.
   */
  import { readable } from '@lib/readable'
  import LabFrame from './LabFrame.svelte'
  import { provideLang, useT } from '@lib/i18nSvelte'
  import type { Lang } from '@lib/i18n'
  let { lang = 'en' }: { lang?: Lang } = $props()
  provideLang(lang)
  const tx = useT({
    'From token to vector: a table lookup': '从 token 到向量：查表',
    'Pick a token to see its one-hot row times the table. Drag a point (or focus it and use the arrow keys) to change its row.': '选一个 token，看它的独热行乘以嵌入表。拖动一个点（或选中它后用方向键）可以改它那一行。',
    'Text': '文本',
    'Type something to see its vectors.': '输入一些文字，看看它们的向量。',
    'Token ids ({n} tokens). Pick one.': 'token id（共 {n} 个 token）。选一个。',
    'Embedding table E, shape ({n}, 2)': '嵌入表 E，形状 ({n}, 2)',
    'char': '字符',
    'E row': 'E 的行',
    'Embedding vectors: drag a point, or focus it and use the arrow keys': '嵌入向量：拖动一个点，或选中它后用方向键',
    'number 1 →': '第 1 个数 →',
    '↑ number 2': '↑ 第 2 个数',
    'vector for {c}: [{x}, {y}]': '{c} 的向量：[{x}, {y}]',
    'row {i}': '第 {i} 行',
    'No tokens yet.': '还没有 token。',
  })
  let text = $state('hello')
  let sel = $state(0)
  let edits = $state<Record<string, number[]>>({})
  let svg: SVGSVGElement
  let dragging = $state<string | null>(null)

  const start = (c: string) => {
    const k = c.codePointAt(0)!
    return [((k * 37) % 41 - 20) / 10, ((k * 53) % 43 - 20) / 10]
  }
  const chars = $derived([...new Set([...text])].sort())
  const stoi = $derived(Object.fromEntries(chars.map((c, i) => [c, i])) as Record<string, number>)
  const ids = $derived([...text].map((c) => stoi[c]))
  const E = $derived(chars.map((c) => edits[c] ?? start(c)))
  const pick = $derived(Math.min(sel, Math.max(0, ids.length - 1)))
  const pid = $derived(ids[pick])
  const show = (c: string) => (c === ' ' ? '␣' : c)
  const f = (v: number) => (Math.abs(v) < 1e-9 ? 0 : v).toFixed(1)

  const D = 2.5
  const sx = (x: number) => ((x + D) / (2 * D)) * 100
  const sy = (y: number) => 100 - ((y + D) / (2 * D)) * 100
  const snap = (v: number) => Math.max(-2, Math.min(2, Math.round(v * 10) / 10))
  function move(e: PointerEvent) {
    if (dragging === null) return
    const r = svg.getBoundingClientRect()
    const x = snap(-D + ((e.clientX - r.left) / r.width) * 2 * D)
    const y = snap(D - ((e.clientY - r.top) / r.height) * 2 * D)
    edits = { ...edits, [dragging]: [x, y] }
  }
  // keyboard: arrow keys move a focused point by 0.1
  function key(e: KeyboardEvent, c: string, i: number) {
    const d = { ArrowLeft: [-0.1, 0], ArrowRight: [0.1, 0], ArrowUp: [0, 0.1], ArrowDown: [0, -0.1] }[e.key]
    if (!d) return
    e.preventDefault()
    const v = E[i]
    edits = { ...edits, [c]: [snap(v[0] + d[0]), snap(v[1] + d[1])] }
    const at = [...text].indexOf(c)
    if (at >= 0) sel = at
  }
  const changed = $derived(Object.keys(edits).length > 0 || text !== 'hello' || sel !== 0)
  function reset() { text = 'hello'; edits = {}; sel = 0 }
</script>

<LabFrame
  title={tx('From token to vector: a table lookup')}
  hint={tx('Pick a token to see its one-hot row times the table. Drag a point (or focus it and use the arrow keys) to change its row.')}
  onreset={reset}
  resetDisabled={!changed}
>
  <label class="inp">{tx('Text')}
    <input bind:value={text} maxlength="40" spellcheck="false" autocomplete="off" oninput={() => (sel = 0)} />
  </label>

  {#if text.length === 0}
    <p class="empty">{tx('Type something to see its vectors.')}</p>
  {:else}
    <p class="sec">{tx('Token ids ({n} tokens). Pick one.', { n: ids.length })}</p>
    <div class="chips">
      {#each [...text] as c, i}
        <button type="button" class="chip tok" class:on={i === pick} aria-pressed={i === pick} onclick={() => (sel = i)}><b>{show(c)}</b><small>{ids[i]}</small></button>
      {/each}
    </div>

    <div class="cols">
      <div class="col">
        <p class="sec">{tx('Embedding table E, shape ({n}, 2)', { n: chars.length })}</p>
        <table>
          <thead><tr><th>id</th><th>{tx('char')}</th><th>one-hot</th><th>{tx('E row')}</th></tr></thead>
          <tbody>
            {#each chars as c, i}
              <tr class:on={i === pid}>
                <td>{i}</td><td>{show(c)}</td><td class="oh">{i === pid ? 1 : 0}</td>
                <td>[{f(E[i][0])}, {f(E[i][1])}]</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <div class="col">
        <svg bind:this={svg} viewBox="0 0 100 100" use:readable role="group" aria-label={tx('Embedding vectors: drag a point, or focus it and use the arrow keys')}
          onpointermove={move} onpointerup={() => (dragging = null)} onpointercancel={() => (dragging = null)}>
          {#each [-2, -1, 0, 1, 2] as t}
            <line x1={sx(t)} y1="0" x2={sx(t)} y2="100" class="grid" class:axis={t === 0} />
            <line x1="0" y1={sy(t)} x2="100" y2={sy(t)} class="grid" class:axis={t === 0} />
            {#if t !== 0}<text x={sx(t)} y={sy(0) + 5} class="tick" text-anchor="middle">{t}</text>
            <text x={sx(0) - 1.5} y={sy(t) + 1.5} class="tick" text-anchor="end">{t}</text>{/if}
          {/each}
          <text x="98" y={sy(0) - 2} class="ax-l" text-anchor="end">{tx('number 1 →')}</text>
          <text x={sx(0) + 2} y="5" class="ax-l">{tx('↑ number 2')}</text>
          {#if E[pid]}<line x1={sx(0)} y1={sy(0)} x2={sx(E[pid][0])} y2={sy(E[pid][1])} class="vec" />{/if}
          {#each chars as c, i}
            <g class="pt-g" role="button" tabindex="0" aria-label={tx('vector for {c}: [{x}, {y}]', { c: show(c), x: f(E[i][0]), y: f(E[i][1]) })}
              onpointerdown={(e) => { dragging = c; const at = [...text].indexOf(c); if (at >= 0) sel = at; svg.setPointerCapture(e.pointerId) }}
              onkeydown={(e) => key(e, c, i)}>
              <circle cx={sx(E[i][0])} cy={sy(E[i][1])} r="7" class="hit" />
              <circle cx={sx(E[i][0])} cy={sy(E[i][1])} r={i === pid ? 3.4 : 2.6} class="pt" class:on={i === pid} />
            </g>
            <text x={sx(E[i][0]) + 3.5} y={sy(E[i][1]) - 2.5} class="tag" class:on={i === pid}>{show(c)}</text>
          {/each}
        </svg>
      </div>
    </div>
  {/if}

  {#snippet readout()}
    {#if text.length}
      “{show(text[pick])}” → id {pid} → one-hot [{chars.map((_, i) => (i === pid ? 1 : 0)).join(', ')}] @ E = {tx('row {i}', { i: pid })} = <b>[{f(E[pid][0])}, {f(E[pid][1])}]</b>
    {:else}
      <span class="idle">{tx('No tokens yet.')}</span>
    {/if}
  {/snippet}
</LabFrame>

<style>
  .inp { display: flex; gap: 0.6rem; align-items: center; font-size: 0.88rem; color: var(--dim); }
  .inp input { flex: 1; min-width: 0; font-family: var(--mono); font-size: 1rem; padding: 0.4rem 0.55rem; border: 1px solid var(--field); border-radius: 5px; background: var(--bg); color: var(--fg); }
  .inp input:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
  .empty { margin: 0.8rem 0 0; color: var(--dim); font-size: 0.88rem; }
  .sec { margin: 0.8rem 0 0.35rem; font-size: 0.82rem; color: var(--dim); }
  .chips { display: flex; flex-wrap: wrap; gap: 0.35rem; }
  .chip { display: inline-flex; flex-direction: column; align-items: center; justify-content: center; min-width: 2.4rem; min-height: 2.4rem; padding: 0.15rem 0.3rem;
    border: 1px solid var(--line); border-radius: 5px; background: var(--bg); font-family: var(--mono); color: var(--fg); font-size: 0.95rem; line-height: 1.15; }
  .chip small { font-size: 0.74rem; color: var(--dim); }
  .chip.on { border-color: var(--accent); background: var(--highlight); }
  .tok { cursor: pointer; font: inherit; font-family: var(--mono); }
  .tok:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
  .cols { display: flex; flex-wrap: wrap; gap: 1rem; margin-top: 0.2rem; }
  .col { flex: 1 1 240px; min-width: 0; }
  table { font-family: var(--mono); font-size: 0.85rem; width: auto; }
  th, td { padding: 0.15rem 0.5rem; }
  tr.on td { background: var(--highlight); }
  tr.on .oh { color: var(--accent); font-weight: 700; }
  svg { width: 100%; max-width: 280px; aspect-ratio: 1; display: block; border: 1px solid var(--line); border-radius: 6px; background: var(--bg); touch-action: none; margin-top: 0.8rem; }
  .grid { stroke: var(--line); stroke-width: 0.3; }
  .grid.axis { stroke: var(--field); stroke-width: 0.5; }
  .hit { fill: transparent; cursor: grab; }
  .pt { fill: var(--cat-5); pointer-events: none; transition: cx 0.15s, cy 0.15s, r 0.15s; }
  .pt.on { fill: var(--accent); }
  .pt-g:focus { outline: none; }
  .pt-g:focus-visible .pt { stroke: var(--accent); stroke-width: 1.2; }
  .tag { font-size: 5px; fill: var(--fg); font-family: var(--mono); pointer-events: none; }
  .tag.on { fill: var(--accent); font-weight: 700; }
  .tick { font-size: 3.6px; fill: var(--dim); font-family: var(--mono); }
  .ax-l { font-size: 4px; fill: var(--dim); font-family: var(--mono); }
  .vec { stroke: var(--accent); stroke-width: 0.8; }
  @media (prefers-reduced-motion: reduce) { .pt { transition: none; } }
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
</style>
