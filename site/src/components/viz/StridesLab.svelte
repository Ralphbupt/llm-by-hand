<script lang="ts">
  /**
   * Strides lab: one row of 12 numbers in memory, and several arrays that read it.
   * Each array is (memory, shape, strides, start). Point at, tap or focus a cell of the array to see
   * which memory cell it reads, and the address rule start + i·s0 + j·s1.
   * A copy (x.T.reshape) gets its own new memory row.
   */
  import { onMount } from 'svelte'
  import { has, subscribe } from '@lib/progress'
  import LabFrame from './LabFrame.svelte'
  import { provideLang, useT } from '@lib/i18nSvelte'
  import type { Lang } from '@lib/i18n'

  let { hide = {}, lang = 'en' }: { hide?: Record<string, string>; lang?: Lang } = $props()
  provideLang(lang)
  const t = useT({
    'Row order and memory order are the same: x is contiguous.': '行顺序和内存顺序一样：x 是内存连续的。',
    'The same memory. Only the shape and the strides swapped.': '同一块内存。只是形状和步长交换了。',
    'Every second column: the column stride doubles. Cells in odd-numbered columns (1, 3) are skipped.': '每隔一列取一列：列步长翻倍。奇数列（1、3）的格子被跳过。',
    'A slice moves the start. The strides stay (4, 1).': '切片移动了起点。步长仍然是 (4, 1)。',
    'A new shape on the same row of memory: a view.': '同一排内存上的新形状：一个视图。',
    'x.T in row order reads memory out of order, so no strides fit. NumPy copies into new memory.': '按行顺序读 x.T，内存的顺序是乱的，找不到合适的步长。NumPy 把数复制到新内存里。',
    'Stride 0: moving down a row does not move in memory. Every row reads x[0].': '步长 0：往下走一行，在内存里不动。每一行读的都是 x[0]。',
    'One row of memory, many arrays': '一排内存，多个数组',
    'Pick an array, then point at or tap one of its cells.': '选一个数组，然后指向或点一下它的某一格。',
    'new memory (a copy)': '新内存（副本）',
    'memory of x': 'x 的内存',
    '{m}: 12 numbers in one row': '{m}：12 个数排成一排',
    'memory of x is still 0, 1, 2, …, 11; this array does not share it': 'x 的内存仍然是 0, 1, 2, …, 11；这个数组不和它共用',
    'shape': '形状',
    'strides': '步长',
    'start': '起点',
    '{name} row {i}, column {j}': '{name} 第 {i} 行第 {j} 列',
    'reading {name} in row order visits {what}:': '按行顺序读 {name}，访问的{what}：',
    'positions of x': 'x 的位置',
    'memory positions': '内存位置',
    'memory': '内存',
    'value': '值',
    'Answer the question below the lab to see this address.': '先回答实验台下面的问题，才能看到这个地址。',
    'the cell you picked and the memory cell it reads': '你选的那一格，和它读的内存格',
    'memory this array never reads': '这个数组从来不读的内存',
    'read by 3 cells of the array': '被数组的 3 个格子读到',
  })
  let solved = $state<Record<string, boolean>>({})
  onMount(() => {
    const sync = () => {
      const next: Record<string, boolean> = {}
      for (const id of Object.values(hide)) next[id] = has(id)
      solved = next
    }
    sync()
    return subscribe(sync)
  })
  const masked = (key: string) => !!hide[key] && !solved[hide[key]]

  const BASE = Array.from({ length: 12 }, (_, i) => i)
  type Case = {
    key: string; name: string; shape: [number, number]; strides: [number, number]; start: number
    copy?: number[]; note: string
  }
  const T_COPY = [0, 4, 8, 1, 5, 9, 2, 6, 10, 3, 7, 11]
  const CASES: Case[] = [
    { key: 'x', name: 'x', shape: [3, 4], strides: [4, 1], start: 0, note: t('Row order and memory order are the same: x is contiguous.') },
    { key: 'T', name: 'x.T', shape: [4, 3], strides: [1, 4], start: 0, note: t('The same memory. Only the shape and the strides swapped.') },
    { key: 'step', name: 'x[:, ::2]', shape: [3, 2], strides: [4, 2], start: 0, note: t('Every second column: the column stride doubles. Cells in odd-numbered columns (1, 3) are skipped.') },
    { key: 'corner', name: 'x[1:, 1:]', shape: [2, 3], strides: [4, 1], start: 5, note: t('A slice moves the start. The strides stay (4, 1).') },
    { key: 'r26', name: 'x.reshape(2, 6)', shape: [2, 6], strides: [6, 1], start: 0, note: t('A new shape on the same row of memory: a view.') },
    { key: 'copy', name: 'x.T.reshape(2, 6)', shape: [2, 6], strides: [6, 1], start: 0, copy: T_COPY, note: t('x.T in row order reads memory out of order, so no strides fit. NumPy copies into new memory.') },
    { key: 'bc', name: 'broadcast_to(x[0], (3, 4))', shape: [3, 4], strides: [0, 1], start: 0, note: t('Stride 0: moving down a row does not move in memory. Every row reads x[0].') },
  ]

  let k = $state(0)
  let cell = $state<{ i: number; j: number } | null>(null)
  const c = $derived(CASES[k])
  const buf = $derived(c.copy ?? BASE)
  const addr = (i: number, j: number) => c.start + i * c.strides[0] + j * c.strides[1]
  const hideStrides = $derived(c.key === 'T' && masked('T'))
  const hideCopy = $derived(c.key === 'copy' && masked('copy'))
  // how many array cells read each memory cell (0 = not used by this array)
  const uses = $derived.by(() => {
    const u = Array(12).fill(0)
    for (let i = 0; i < c.shape[0]; i++) for (let j = 0; j < c.shape[1]; j++) u[addr(i, j)]++
    return u
  })
  const visits = $derived.by(() => {
    const v: number[] = []
    for (let i = 0; i < c.shape[0]; i++) for (let j = 0; j < c.shape[1]; j++) v.push(c.copy ? T_COPY[addr(i, j)] : addr(i, j))
    return v
  })
  const showVal = (m: number) => (hideCopy ? '?' : String(buf[m]))
  const pick = (i: number, j: number) => (cell = { i, j })
  const fmtS = (s: [number, number]) => (hideStrides ? '(?, ?)' : `(${s[0]}, ${s[1]})`)
</script>

<LabFrame title={t('One row of memory, many arrays')} hint={t('Pick an array, then point at or tap one of its cells.')}>
  <div class="wrap">
    <div class="lbl">{t('{m}: 12 numbers in one row', { m: c.copy ? t('new memory (a copy)') : t('memory of x') })}</div>
    <div class="mem" role="list">
      {#each buf as _, m}
        <div class="mc" role="listitem" class:unused={uses[m] === 0} class:hi={cell && addr(cell.i, cell.j) === m}>
          <span class="pos">{m}</span>
          <span class="v" class:q={hideCopy}>{showVal(m)}</span>
          <span class="n">{uses[m] > 1 ? `×${uses[m]}` : ''}</span>
        </div>
      {/each}
    </div>
    {#if c.copy}
      <div class="lbl">{t('memory of x is still 0, 1, 2, …, 11; this array does not share it')}</div>
    {/if}

    <div class="arr">
      <div class="lbl">{c.name} · {t('shape')} ({c.shape[0]}, {c.shape[1]}) · {t('strides')} {fmtS(c.strides)} · {t('start')} {c.start}</div>
      <table onpointerleave={() => (cell = null)}>
        <tbody>
          {#each Array(c.shape[0]) as _, i}
            <tr>
              {#each Array(c.shape[1]) as _, j}
                <td tabindex="0" class:hi={cell && cell.i === i && cell.j === j}
                  aria-label={t('{name} row {i}, column {j}', { name: c.name, i, j })}
                  onpointerenter={() => pick(i, j)} onclick={() => pick(i, j)} onfocus={() => pick(i, j)}
                  class:q={hideCopy}>{showVal(addr(i, j))}</td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    <div class="walk">
      <span class="lbl">{t('reading {name} in row order visits {what}:', { name: c.name, what: c.copy ? t('positions of x') : t('memory positions') })}</span>
      <span class="seq">{hideStrides || hideCopy ? '? ? ? …' : visits.join(' ')}</span>
    </div>
  </div>

  {#snippet controls()}
    {#each CASES as cs, i}
      <button class="lab-btn case" class:on={k === i} aria-pressed={k === i} onclick={() => { k = i; cell = null }}>{cs.name}</button>
    {/each}
  {/snippet}

  {#snippet readout()}
    {#if cell && !hideStrides && !hideCopy}
      {c.name}[{cell.i}, {cell.j}] → {t('memory')} {c.start} + {cell.i}·{c.strides[0]} + {cell.j}·{c.strides[1]} = {addr(cell.i, cell.j)} → {t('value')} <b>{buf[addr(cell.i, cell.j)]}</b>
    {:else if cell}
      <span class="idle">{t('Answer the question below the lab to see this address.')}</span>
    {:else}
      <span class="idle">{c.note}</span>
    {/if}
  {/snippet}

  {#snippet legend()}
    <span class="key"><i class="k-hi"></i>{t('the cell you picked and the memory cell it reads')}</span>
    <span class="key"><i class="k-un"></i>{t('memory this array never reads')}</span>
    <span class="key"><b class="k-n">×3</b>{t('read by 3 cells of the array')}</span>
  {/snippet}
</LabFrame>

<style>
  .wrap { display: flex; flex-direction: column; gap: 0.6rem; }
  .lbl { font-family: var(--mono); font-size: 0.78rem; color: var(--dim); }
  .mem { display: grid; grid-template-columns: repeat(12, minmax(1.55rem, 1fr)); gap: 2px; max-width: 34rem; }
  .mc { display: flex; flex-direction: column; align-items: center; border: 1px solid var(--line); border-radius: 3px; padding: 0.1rem 0; font-family: var(--mono); }
  .mc .pos { font-size: 0.72rem; color: var(--dim); }
  .mc .v { font-size: 0.85rem; font-variant-numeric: tabular-nums; }
  .mc .n { font-size: 0.72rem; color: var(--accent); min-height: 1em; }
  .mc.unused { border-style: dashed; }
  .mc.unused .v { color: var(--dim); }
  .mc.hi { background: var(--highlight); outline: 1.5px solid var(--accent); outline-offset: -1.5px; }
  .q { color: var(--warn) !important; }
  table { border-collapse: collapse; font-family: var(--mono); font-size: 0.85rem; width: auto; margin-top: 0.2rem; }
  td { border: 1px solid var(--line); padding: 0.25rem 0.5rem; text-align: right; min-width: 2.2rem; cursor: pointer; font-variant-numeric: tabular-nums; }
  td.hi { background: var(--highlight); outline: 1.5px solid var(--accent); outline-offset: -1.5px; }
  td:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
  .walk { display: flex; flex-wrap: wrap; gap: 0.2rem 0.5rem; align-items: baseline; }
  .seq { font-family: var(--mono); font-size: 0.85rem; }
  .case { font-family: var(--mono); font-size: 0.8rem; }
  .case.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
  .key { display: inline-flex; align-items: center; gap: 0.4rem; }
  .key i { width: 0.9rem; height: 0.9rem; border-radius: 2px; flex: none; }
  .k-hi { background: var(--highlight); outline: 1.5px solid var(--accent); outline-offset: -1.5px; }
  .k-un { border: 1px dashed var(--line); }
  .k-n { font-family: var(--mono); font-size: 0.75rem; color: var(--accent); font-weight: 400; }
</style>
