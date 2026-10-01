<script lang="ts">
  /** Matrix grid: editable cells, hover highlights the row and column, recomputes live from upstream data */
  type Props = {
    value: number[][]
    label?: string
    editable?: boolean
    decimals?: number
    rowLabels?: string[]
    colLabels?: string[]
    hiRows?: number[]
    hiCols?: number[]
    masked?: { i: number; j: number }[]   // cells shown as "?" (e.g. the answer to a question not yet solved)
    onhover?: (cell: { i: number; j: number } | null) => void
    onchange?: (v: number[][]) => void
  }
  let {
    value, label, editable = false, decimals = 2,
    rowLabels, colLabels, hiRows = [], hiCols = [], masked = [], onhover, onchange,
  }: Props = $props()

  const fmt = (v: number) =>
    Number.isInteger(v) && decimals <= 2 ? String(v) : v.toFixed(decimals)

  function edit(i: number, j: number, raw: string) {
    const n = Number(raw)
    if (Number.isNaN(n)) return
    const next = value.map((r) => [...r])
    next[i][j] = n
    onchange?.(next)
  }
</script>

<div class="grid">
  {#if label}<div class="label">{label}</div>{/if}
  <table onpointerleave={() => onhover?.(null)}>
    {#if colLabels}
      <thead>
        <tr>
          <th></th>
          {#each colLabels as c, j}<th class:hi={hiCols.includes(j)}>{c}</th>{/each}
        </tr>
      </thead>
    {/if}
    <tbody>
      {#each value as row, i}
        <tr>
          {#if rowLabels}<th class:hi={hiRows.includes(i)}>{rowLabels[i]}</th>{/if}
          {#each row as v, j}
            <td
              class:hi={hiRows.includes(i) || hiCols.includes(j)}
              class:both={hiRows.includes(i) && hiCols.includes(j)}
              onpointerenter={() => onhover?.({ i, j })}
              onclick={() => onhover?.({ i, j })}
              onfocus={() => onhover?.({ i, j })}
              tabindex={onhover && !editable ? 0 : undefined}
              class:linked={!!onhover && !editable}
            >
              {#if masked.some((c) => c.i === i && c.j === j)}
                <span class="masked">?</span>
              {:else if editable}
                <input value={fmt(v)} inputmode="decimal" aria-label={`${label ?? 'matrix'} row ${i} column ${j}`} onchange={(e) => edit(i, j, e.currentTarget.value)} />
              {:else}
                {fmt(v)}
              {/if}
            </td>
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .grid { display: inline-block; }
  .label { font-size: 0.78rem; color: var(--dim); margin-bottom: 0.2rem; font-family: var(--mono); }
  table { border-collapse: collapse; font-family: var(--mono); font-size: 0.85rem; width: auto; }
  th, td {
    border: 1px solid var(--line); padding: 0.25rem 0.5rem;
    text-align: right; min-width: 3.1rem; transition: background 0.1s;
  }
  th { color: var(--dim); font-weight: 400; font-size: 0.78rem; border: none; text-align: center; min-width: 0; }
  th.hi { color: var(--accent); }
  td.hi { background: var(--highlight); }
  td.linked { cursor: pointer; }
  td.linked:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
  td.both { background: color-mix(in srgb, var(--accent) 28%, transparent); }
  .masked { color: var(--warn); font-weight: 700; }
  /* editable numbers look editable: the learner's color and a dashed underline */
  input {
    width: 2.6rem; font: inherit; text-align: right; padding: 0 0 1px;
    border: none; border-bottom: 1px dashed var(--field); background: none; color: var(--accent); cursor: text;
  }
  input:hover { border-bottom-color: var(--accent); }
  input:focus { outline: 2px solid var(--accent); outline-offset: 1px; border-radius: 2px; border-bottom-color: transparent; }
  @media (max-width: 760px) { input { font-size: 16px; width: 2.8rem; } td { padding: 0.35rem 0.4rem; min-height: 2.5rem; height: 2.5rem; } }
</style>
