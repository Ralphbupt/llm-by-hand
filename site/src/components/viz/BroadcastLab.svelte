<script lang="ts">
  /**
   * Broadcasting lab: add two arrays of different shapes. Dimensions of size 1 are stretched
   * (shown as faded copies) until both shapes match; then the cells are added one by one.
   * Point at, tap or focus a result cell to see which two numbers made it.
   */
  import LabFrame from './LabFrame.svelte'
  import { provideLang, useT } from '@lib/i18nSvelte'
  import type { Lang } from '@lib/i18n'

  let { lang = 'en' }: { lang?: Lang } = $props()
  provideLang(lang)
  const t = useT({
    'A is stretched to the right, B is stretched down.': 'A 向右拉伸，B 向下拉伸。',
    'The same row is added to every row of A.': '同一行加到 A 的每一行上。',
    'Each row of A gets its own number.': 'A 的每一行各加一个自己的数。',
    'mask': '掩码',
    'One mask row (the last word is padding) blocks that column for every row.': '一行掩码（最后一个词是填充）把每一行的这一列都挡住了。',
    'Neither size is 1 and they differ: 2 vs 3. Broadcasting fails.': '两个大小都不是 1，而且不相等：2 和 3。广播失败。',
    'Broadcasting: stretch, then add': '广播：先拉伸，再相加',
    'Pick a case, then point at or tap a cell of the result.': '选一个例子，然后指向或点一下结果里的某一格。',
    'result': '结果',
    'result row {i}, column {j}': '结果第 {i} 行第 {j} 列',
    'Error: {a} and {b} don’t match, and neither is 1.': '报错：{a} 和 {b} 不相等，也都不是 1。',
    'stretched copy, not stored': '拉伸出来的副本，并没有存下来',
    'the cell you picked and the two numbers that made it': '你选的那一格，和算出它的两个数',
  })
  type Case = { name: string; a: number[][]; b: number[][]; bLabel?: string; note: string }
  const col = (v: number[]) => v.map((x) => [x])
  const CASES: Case[] = [
    { name: '(4,1) + (1,5)', a: col([0, 1, 2, 3]), b: [[0, 10, 20, 30, 40]], note: t('A is stretched to the right, B is stretched down.') },
    { name: '(3,4) + (1,4)', a: [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]], b: [[100, 200, 300, 400]], note: t('The same row is added to every row of A.') },
    { name: '(3,4) + (3,1)', a: [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]], b: col([100, 200, 300]), note: t('Each row of A gets its own number.') },
    { name: `${t('mask')} (1,4) → (4,4)`, a: [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14, 15]], b: [[0, 0, 0, -99]], bLabel: t('mask'), note: t('One mask row (the last word is padding) blocks that column for every row.') },
    { name: '(3,2) + (1,3)', a: [[1, 2], [3, 4], [5, 6]], b: [[10, 20, 30]], note: t('Neither size is 1 and they differ: 2 vs 3. Broadcasting fails.') },
  ]
  let k = $state(0)
  let cell = $state<{ i: number; j: number } | null>(null)
  const c = $derived(CASES[k])
  const ra = $derived(c.a.length), ca = $derived(c.a[0].length)
  const rb = $derived(c.b.length), cb = $derived(c.b[0].length)
  const fit = (x: number, y: number) => x === y || x === 1 || y === 1
  const ok = $derived(fit(ra, rb) && fit(ca, cb))
  const R = $derived(Math.max(ra, rb)), C = $derived(Math.max(ca, cb))
  // stretched views: index a size-1 dimension with 0
  const at = (m: number[][], i: number, j: number) => m[m.length === 1 ? 0 : i][m[0].length === 1 ? 0 : j]
  const realA = (i: number, j: number) => (ra === 1 ? i === 0 : true) && (ca === 1 ? j === 0 : true)
  const realB = (i: number, j: number) => (rb === 1 ? i === 0 : true) && (cb === 1 ? j === 0 : true)
  const srcHit = (m: number[][], i: number, j: number) =>
    !!cell && (m.length === 1 || i === cell.i) && (m[0].length === 1 || j === cell.j) && (m.length === 1 ? i === 0 : true) && (m[0].length === 1 ? j === 0 : true)
</script>

<LabFrame title={t('Broadcasting: stretch, then add')} hint={t('Pick a case, then point at or tap a cell of the result.')}>
  {#if ok}
    <div class="row">
      <div class="m">
        <div class="lbl">A ({ra}, {ca}) → ({R}, {C})</div>
        <table>
          <tbody>
            {#each Array(R) as _, i}
              <tr>{#each Array(C) as _, j}<td class:ghost={!realA(i, j)} class:hi={srcHit(c.a, i, j) || (cell && cell.i === i && cell.j === j)}>{at(c.a, i, j)}</td>{/each}</tr>
            {/each}
          </tbody>
        </table>
      </div>
      <span class="op">+</span>
      <div class="m">
        <div class="lbl">{c.bLabel ?? 'B'} ({rb}, {cb}) → ({R}, {C})</div>
        <table>
          <tbody>
            {#each Array(R) as _, i}
              <tr>{#each Array(C) as _, j}<td class:ghost={!realB(i, j)} class:hi={srcHit(c.b, i, j) || (cell && cell.i === i && cell.j === j)}>{at(c.b, i, j)}</td>{/each}</tr>
            {/each}
          </tbody>
        </table>
      </div>
      <span class="op">=</span>
      <div class="m">
        <div class="lbl">{t('result')} ({R}, {C})</div>
        <table onpointerleave={() => (cell = null)}>
          <tbody>
            {#each Array(R) as _, i}
              <tr>{#each Array(C) as _, j}
                <td class="res" class:hi={cell && cell.i === i && cell.j === j} tabindex="0"
                  aria-label={t('result row {i}, column {j}', { i, j })}
                  onpointerenter={() => (cell = { i, j })} onclick={() => (cell = { i, j })} onfocus={() => (cell = { i, j })}>{at(c.a, i, j) + at(c.b, i, j)}</td>
              {/each}</tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {:else}
    <div class="row">
      <div class="m"><div class="lbl">A ({ra}, {ca})</div>
        <table><tbody>{#each c.a as r}<tr>{#each r as v}<td>{v}</td>{/each}</tr>{/each}</tbody></table></div>
      <span class="op">+</span>
      <div class="m"><div class="lbl">B ({rb}, {cb})</div>
        <table><tbody>{#each c.b as r}<tr>{#each r as v}<td>{v}</td>{/each}</tr>{/each}</tbody></table></div>
      <span class="bad">{t('Error: {a} and {b} don’t match, and neither is 1.', { a: ca, b: cb })}</span>
    </div>
  {/if}

  {#snippet controls()}
    {#each CASES as cs, i}
      <button class="lab-btn case" class:on={k === i} aria-pressed={k === i} onclick={() => { k = i; cell = null }}>{cs.name}</button>
    {/each}
  {/snippet}

  {#snippet readout()}
    {#if cell && ok}
      {t('result')}[{cell.i}][{cell.j}] = A[{ra === 1 ? 0 : cell.i}][{ca === 1 ? 0 : cell.j}] + {c.bLabel ?? 'B'}[{rb === 1 ? 0 : cell.i}][{cb === 1 ? 0 : cell.j}] = {at(c.a, cell.i, cell.j)} + {at(c.b, cell.i, cell.j)} = <b>{at(c.a, cell.i, cell.j) + at(c.b, cell.i, cell.j)}</b>
    {:else}
      <span class="idle">{c.note}</span>
    {/if}
  {/snippet}

  {#snippet legend()}
    <span class="key"><i class="k-ghost"></i>{t('stretched copy, not stored')}</span>
    <span class="key"><i class="k-hi"></i>{t('the cell you picked and the two numbers that made it')}</span>
  {/snippet}
</LabFrame>

<style>
  .row { display: flex; flex-wrap: wrap; gap: 0.6rem; align-items: center; }
  .lbl { font-family: var(--mono); font-size: 0.78rem; color: var(--dim); margin-bottom: 0.2rem; }
  table { border-collapse: collapse; font-family: var(--mono); font-size: 0.85rem; width: auto; }
  td { border: 1px solid var(--line); padding: 0.2rem 0.45rem; text-align: right; min-width: 2.3rem; }
  td.ghost { color: var(--dim); border-style: dashed; border-color: var(--field); background: transparent; }
  td.hi { background: var(--highlight); color: var(--fg); outline: 1.5px solid var(--accent); outline-offset: -1.5px; }
  td.res { cursor: pointer; }
  td.res:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
  .op { font-family: var(--mono); color: var(--dim); }
  .bad { color: var(--warn); font-size: 0.88rem; }
  .case { font-family: var(--mono); font-size: 0.8rem; }
  .case.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
  .key { display: inline-flex; align-items: center; gap: 0.4rem; }
  .key i { width: 0.9rem; height: 0.9rem; border-radius: 2px; flex: none; }
  .k-ghost { border: 1px dashed var(--field); }
  .k-hi { background: var(--highlight); outline: 1.5px solid var(--accent); outline-offset: -1.5px; }
</style>
