<script lang="ts">
  /** Attention-weight heatmap: shade = weight; point at, tap or focus a cell to see who looks at whom */
  type Props = {
    value: number[][]
    label?: string
    rowLabels?: string[]
    colLabels?: string[]
    hiRows?: number[]
    hiCols?: number[]
    masked?: { i: number; j: number }[]   // cells shown as "?" with no shading
    onhover?: (cell: { i: number; j: number } | null) => void
  }
  let { value, label, rowLabels, colLabels, hiRows = [], hiCols = [], masked = [], onhover }: Props = $props()
  const isMasked = (i: number, j: number) => masked.some((c) => c.i === i && c.j === j)
</script>

<div class="hm">
  {#if label}<div class="label">{label}</div>{/if}
  <table onpointerleave={() => onhover?.(null)}>
    {#if colLabels}
      <thead>
        <tr><th></th>{#each colLabels as c, j}<th class:hi={hiCols.includes(j)}>{c}</th>{/each}</tr>
      </thead>
    {/if}
    <tbody>
      {#each value as row, i}
        <tr>
          {#if rowLabels}<th class:hi={hiRows.includes(i)}>{rowLabels[i]}</th>{/if}
          {#each row as v, j}
            <td
              style="--w: {isMasked(i, j) ? 0 : v}"
              class:ring={hiRows.includes(i) && hiCols.includes(j)}
              class:dim={hiRows.length > 0 && !hiRows.includes(i)}
              onpointerenter={() => onhover?.({ i, j })}
              onclick={() => onhover?.({ i, j })}
              onfocus={() => onhover?.({ i, j })}
              tabindex={onhover ? 0 : undefined}
            >
              {#if isMasked(i, j)}<span class="masked">?</span>{:else}{v.toFixed(2)}{/if}
            </td>
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .hm { display: inline-block; }
  .label { font-size: 0.78rem; color: var(--dim); margin-bottom: 0.2rem; font-family: var(--mono); }
  table { border-collapse: collapse; font-family: var(--mono); font-size: 0.85rem; }
  th { color: var(--dim); font-weight: 400; font-size: 0.78rem; padding: 0.2rem 0.4rem; }
  th.hi { color: var(--accent); }
  td {
    border: 1px solid var(--line); padding: 0.3rem 0.55rem; text-align: right; min-width: 3.2rem;
    background: color-mix(in srgb, var(--accent) calc(var(--w) * 75%), transparent);
    transition: opacity 0.1s;
  }
  td.dim { opacity: 0.3; }
  .masked { color: var(--warn); font-weight: 700; }
  td.ring { outline: 2px solid var(--fg); outline-offset: -2px; }
  td[tabindex] { cursor: pointer; }
  td[tabindex]:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
</style>
