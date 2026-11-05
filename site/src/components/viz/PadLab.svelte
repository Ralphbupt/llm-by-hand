<script lang="ts">
  /**
   * Pad lab: sequences of different lengths become one rectangle (B, L_max) plus a padding mask.
   * PAD = 0 goes at the end of each row. In the mask, True = PAD = blocked.
   */
  import { onMount } from 'svelte'
  import { has, subscribe } from '@lib/progress'
  import LabFrame from './LabFrame.svelte'
  import { provideLang, useT } from '@lib/i18nSvelte'
  import type { Lang } from '@lib/i18n'

  let { hide = {}, lang = 'en' }: { hide?: Record<string, string | undefined>; lang?: Lang } = $props()
  provideLang(lang)
  const tx = useT({
    'Padding: three sequences, one rectangle': '填充：三个序列，一个矩形',
    'Make a sequence longer or shorter and watch the batch and its mask change.': '把某个序列变长或变短，看批和它的掩码怎样变化。',
    'Sequences': '序列',
    'Make sequence {i} shorter': '把序列 {i} 变短',
    'Make sequence {i} longer': '把序列 {i} 变长',
    'Answer the shape question below to see the padded batch.': '回答下面关于形状的问题，就能看到填充后的批。',
    'Batch': '批',
    'shape': '形状',
    '(True = PAD, blocked)': '（True = PAD，挡住）',
    'Show the padding mask': '显示填充掩码',
    'Batch shape': '批的形状',
    'PAD cells:': 'PAD 格：',
    '{p} of {n}': '{n} 格里有 {p} 格',
    '({pct}% of the batch is padding)': '（批的 {pct}% 是填充）',
    'real token': '真正的 token',
    'PAD = 0 (mask T)': 'PAD = 0（掩码为 T）',
  })
  let solved = $state<Record<string, boolean>>({})
  onMount(() => {
    const sync = () => {
      const next: Record<string, boolean> = {}
      for (const id of Object.values(hide)) if (id) next[id] = has(id)
      solved = next
    }
    sync()
    return subscribe(sync)
  })
  const locked = (k: string) => !!hide[k] && !solved[hide[k]!]

  const START = [[5, 3, 8], [2, 9], [7]]
  const POOL = [4, 1, 6, 2]            // tokens added when a row gets longer
  const MAX = 6
  let seqs = $state(START.map((s) => [...s]))
  let showMask = $state(true)

  let L = $derived(Math.max(...seqs.map((s) => s.length)))
  let pads = $derived(seqs.reduce((n, s) => n + L - s.length, 0))
  let isStart = $derived(JSON.stringify(seqs) === JSON.stringify(START))
  let hideShape = $derived(isStart && locked('shape'))
  let hideCount = $derived(isStart && locked('count'))

  function grow(i: number) {
    if (seqs[i].length < MAX) seqs[i] = [...seqs[i], POOL[seqs[i].length % POOL.length]]
  }
  function shrink(i: number) {
    if (seqs[i].length > 1) seqs[i] = seqs[i].slice(0, -1)
  }
  function reset() { seqs = START.map((s) => [...s]) }
</script>

<LabFrame
  title={tx('Padding: three sequences, one rectangle')}
  hint={tx('Make a sequence longer or shorter and watch the batch and its mask change.')}
  onreset={reset}
  resetDisabled={isStart}
>
  <div class="panes">
    <div class="pane">
      <p class="cap">{tx('Sequences')}</p>
      {#each seqs as s, i}
        <div class="seqrow">
          <span class="toks">[{s.join(', ')}]</span>
          <span class="btns">
            <button class="lab-btn step" aria-label={tx('Make sequence {i} shorter', { i })} disabled={s.length <= 1} onclick={() => shrink(i)}>−</button>
            <button class="lab-btn step" aria-label={tx('Make sequence {i} longer', { i })} disabled={s.length >= MAX} onclick={() => grow(i)}>+</button>
          </span>
        </div>
      {/each}
    </div>

    {#if hideShape}
      <div class="pane hidden"><p class="q"><b>?</b> {tx('Answer the shape question below to see the padded batch.')}</p></div>
    {:else}
      <div class="pane">
        <p class="cap">{tx('Batch')} <code>X</code>, {tx('shape')} ({seqs.length}, {L})</p>
        <table class="grid">
          <tbody>
            {#each seqs as s, i}
              <tr>{#each Array.from({ length: L }, (_, t) => t) as t}
                <td class:pad={t >= s.length}>{t < s.length ? s[t] : 0}</td>
              {/each}</tr>
            {/each}
          </tbody>
        </table>
      </div>
      {#if showMask}
        <div class="pane">
          <p class="cap"><code>mask</code> {tx('(True = PAD, blocked)')}</p>
          <table class="grid mask">
            <tbody>
              {#each seqs as s}
                <tr>{#each Array.from({ length: L }, (_, t) => t) as t}
                  <td class:pad={t >= s.length}>{t >= s.length ? 'T' : 'F'}</td>
                {/each}</tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    {/if}
  </div>

  {#snippet controls()}
    <label class="tog"><input type="checkbox" bind:checked={showMask} /> {tx('Show the padding mask')}</label>
  {/snippet}

  {#snippet readout()}
    {tx('Batch shape')} {hideShape ? '?' : `(${seqs.length}, ${L})`} · {tx('PAD cells:')} {hideShape || hideCount ? '?' : tx('{p} of {n}', { p: pads, n: seqs.length * L })}
    {#if !hideShape && !hideCount} {tx('({pct}% of the batch is padding)', { pct: Math.round((100 * pads) / (seqs.length * L)) })}{/if}
  {/snippet}

  {#snippet legend()}
    <span class="lg"><span class="sw"></span>{tx('real token')}</span>
    <span class="lg"><span class="sw pad"></span>{tx('PAD = 0 (mask T)')}</span>
  {/snippet}
</LabFrame>

<style>
  .panes { display: flex; flex-wrap: wrap; gap: 1.2rem; align-items: flex-start; }
  .pane { min-width: 0; }
  .pane.hidden { flex: 1 1 14rem; border: 1px dashed var(--line); border-radius: 0.4rem; padding: 0.8rem; }
  .cap { margin: 0 0 0.35rem; font-size: 0.82rem; color: var(--dim); }
  .seqrow { display: flex; align-items: center; gap: 0.6rem; min-height: 2.6rem; }
  .toks { font-family: var(--mono); font-size: 0.9rem; min-width: 8.5rem; }
  .btns { display: inline-flex; gap: 0.3rem; }
  .step { min-width: 2.5rem; }
  .grid { border-collapse: collapse; font-family: var(--mono); font-size: 0.9rem; font-variant-numeric: tabular-nums; }
  .grid td {
    width: 2rem; height: 2rem; text-align: center; border: 1px solid var(--line);
    background: color-mix(in srgb, var(--accent) 12%, var(--bg)); transition: background 0.2s;
  }
  .grid td.pad { background: var(--card); color: var(--dim); border-style: dashed; }
  .mask td { font-size: 0.8rem; }
  @media (prefers-reduced-motion: reduce) { .grid td { transition: none; } }
  .q { margin: 0; font-size: 0.9rem; }
  .q b { color: var(--warn); }
  .tog { display: inline-flex; gap: 0.5rem; align-items: center; font-size: 0.9rem; cursor: pointer; min-height: 2.5rem; }
  .tog input { width: 1.1rem; height: 1.1rem; accent-color: var(--accent); }
  .lg { display: inline-flex; align-items: center; gap: 0.35rem; margin-right: 1rem; font-size: 0.82rem; }
  .sw { display: inline-block; width: 0.9rem; height: 0.9rem; border: 1px solid var(--line); background: color-mix(in srgb, var(--accent) 12%, var(--bg)); }
  .sw.pad { background: var(--card); border-style: dashed; }
</style>
