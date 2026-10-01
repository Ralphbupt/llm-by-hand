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

  let { hide = {} }: { hide?: Record<string, string> } = $props()
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
    { key: 'x', name: 'x', shape: [3, 4], strides: [4, 1], start: 0, note: 'Row order and memory order are the same: x is contiguous.' },
    { key: 'T', name: 'x.T', shape: [4, 3], strides: [1, 4], start: 0, note: 'The same memory. Only the shape and the strides swapped.' },
    { key: 'step', name: 'x[:, ::2]', shape: [3, 2], strides: [4, 2], start: 0, note: 'Every second column: the column stride doubles. Cells in odd-numbered columns (1, 3) are skipped.' },
    { key: 'corner', name: 'x[1:, 1:]', shape: [2, 3], strides: [4, 1], start: 5, note: 'A slice moves the start. The strides stay (4, 1).' },
    { key: 'r26', name: 'x.reshape(2, 6)', shape: [2, 6], strides: [6, 1], start: 0, note: 'A new shape on the same row of memory: a view.' },
    { key: 'copy', name: 'x.T.reshape(2, 6)', shape: [2, 6], strides: [6, 1], start: 0, copy: T_COPY, note: 'x.T in row order reads memory out of order, so no strides fit. NumPy copies into new memory.' },
    { key: 'bc', name: 'broadcast_to(x[0], (3, 4))', shape: [3, 4], strides: [0, 1], start: 0, note: 'Stride 0: moving down a row does not move in memory. Every row reads x[0].' },
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

<LabFrame title="One row of memory, many arrays" hint="Pick an array, then point at or tap one of its cells.">
  <div class="wrap">
    <div class="lbl">{c.copy ? 'new memory (a copy)' : 'memory of x'}: 12 numbers in one row</div>
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
      <div class="lbl">memory of x is still 0, 1, 2, …, 11; this array does not share it</div>
    {/if}

    <div class="arr">
      <div class="lbl">{c.name} · shape ({c.shape[0]}, {c.shape[1]}) · strides {fmtS(c.strides)} · start {c.start}</div>
      <table onpointerleave={() => (cell = null)}>
        <tbody>
          {#each Array(c.shape[0]) as _, i}
            <tr>
              {#each Array(c.shape[1]) as _, j}
                <td tabindex="0" class:hi={cell && cell.i === i && cell.j === j}
                  aria-label={`${c.name} row ${i}, column ${j}`}
                  onpointerenter={() => pick(i, j)} onclick={() => pick(i, j)} onfocus={() => pick(i, j)}
                  class:q={hideCopy}>{showVal(addr(i, j))}</td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    <div class="walk">
      <span class="lbl">reading {c.name} in row order visits {c.copy ? 'positions of x' : 'memory positions'}:</span>
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
      {c.name}[{cell.i}, {cell.j}] → memory {c.start} + {cell.i}·{c.strides[0]} + {cell.j}·{c.strides[1]} = {addr(cell.i, cell.j)} → value <b>{buf[addr(cell.i, cell.j)]}</b>
    {:else if cell}
      <span class="idle">Answer the question below the lab to see this address.</span>
    {:else}
      <span class="idle">{c.note}</span>
    {/if}
  {/snippet}

  {#snippet legend()}
    <span class="key"><i class="k-hi"></i>the cell you picked and the memory cell it reads</span>
    <span class="key"><i class="k-un"></i>memory this array never reads</span>
    <span class="key"><b class="k-n">×3</b>read by 3 cells of the array</span>
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
