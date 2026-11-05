<script lang="ts">
  /**
   * Where does the decoder look? Attention weights recorded from the trained models of level N5:
   *   numbers → words (demo.py --export): rows are the words it wrote, columns the digits it read;
   *   reversal (export.py): the anti-diagonal pattern of reading a string backwards.
   */
  import { onMount } from 'svelte'
  import Heatmap from './Heatmap.svelte'
  import LabFrame from './LabFrame.svelte'
  import { provideLang, useT } from '@lib/i18nSvelte'
  import type { Lang } from '@lib/i18n'

  let { lang = 'en' }: { lang?: Lang } = $props()
  provideLang(lang)
  const t = useT({
    'Where the decoder looks': '解码器在看哪里',
    'Point at or tap a cell. Rows: what the decoder wrote. Columns: what it read. Darker = more weight.': '指向或点一下某一格。行：解码器写出的东西。列：它读入的东西。颜色越深，权重越大。',
    'Numbers → words': '数字 → 英文单词',
    'Reversing digits': '倒转数字',
    'Could not load the recorded weights: {e}': '无法加载录下的权重：{e}',
    '✓ correct': '✓ 正确',
    '✗ wrong': '✗ 错误',
    'a digit string, read backwards': '一个数字串，倒着读',
    'Loading the recorded weights…': '正在加载录下的权重……',
    'number': '数字',
    'previous number': '上一个数字',
    'pick a number': '选一个数字',
    'next number': '下一个数字',
    'Writing “{w}”, the decoder gives digit {j} (“{c}”) weight': '写 “{w}” 时，解码器给第 {j} 位数字（“{c}”）的权重是',
    'Writing “{w}”, the decoder gives input {j} (“{c}”) weight': '写 “{w}” 时，解码器给第 {j} 个输入（“{c}”）的权重是',
    '.': '。',
    'Rows: the words it wrote. Columns: the digits it read. Point at or tap a cell.': '行：它写出的词。列：它读入的数字。指向或点一下某一格。',
    'Each output digit looks almost only at one input digit: the last one first, then backwards. Point at or tap a cell.': '每个输出数字几乎只看一个输入数字：先看最后一个，然后往前倒着看。指向或点一下某一格。',
    'Waiting for the recorded weights…': '正在等待录下的权重……',
    'attention weight, 0 → 1': '注意力权重，0 → 1',
    'Strongest look for each word: {list}': '每个词看得最重的数字：{list}',
    ', ': '，',
  })

  type Ex = { n: number; src: string[]; pad: number; out: string[]; right: boolean; weights: number[][] }
  let nums = $state<Ex[]>([])
  let rev = $state<{ src: number[]; pred: number[]; weights: number[][] } | null>(null)
  let error = $state('')
  let tab = $state('words')
  let pick = $state(0)
  let cell = $state<{ i: number; j: number } | null>(null)

  onMount(() => {
    Promise.all([
      fetch('/data/seq2seq-attention/alignments.json').then((r) => r.json()),
      fetch('/data/seq2seq-attention/bottleneck.json').then((r) => r.json()),
    ]).then(([a, b]) => { nums = a.examples; rev = b.example }).catch((e) => (error = String(e)))
  })

  const ex = $derived(nums[pick])
  // padding columns get weight 0 (they are masked), so leave them out of the picture
  const words = $derived(ex ? { value: ex.weights.map((row) => row.slice(ex.pad)), rows: [...ex.out, '<eos>'], cols: ex.src } : null)
  const tok = (t: number) => (t === 12 ? '<eos>' : t < 10 ? String(t) : '·')
  const reverse = $derived(rev ? { value: rev.weights, rows: rev.pred.map(tok), cols: rev.src.map(String) } : null)
  const view = $derived(tab === 'words' ? words : reverse)
  const strongest = (row: number[]) => row.reduce((b, v, j) => (v > row[b] ? j : b), 0)
  // a new tab or example starts with nothing picked
  $effect(() => { void tab; void pick; cell = null })
  const fmtN = (n: number) => n.toLocaleString('en-US')
</script>

<LabFrame
  title={t('Where the decoder looks')}
  hint={t('Point at or tap a cell. Rows: what the decoder wrote. Columns: what it read. Darker = more weight.')}
  views={[{ id: 'words', label: t('Numbers → words') }, { id: 'reverse', label: t('Reversing digits') }]}
  bind:view={tab}
  onreset={() => { tab = 'words'; pick = 0; cell = null }}
  resetDisabled={tab === 'words' && pick === 0 && cell === null}
>
  {#if error}
    <p class="bad">{t('Could not load the recorded weights: {e}', { e: error })}</p>
  {:else if view}
    {#if tab === 'words' && ex}
      <div class="cap"><b>{fmtN(ex.n)}</b> → {ex.out.join(' ')} <span class:ok={ex.right} class:bad={!ex.right}>{ex.right ? t('✓ correct') : t('✗ wrong')}</span></div>
    {:else}
      <div class="cap">{t('a digit string, read backwards')}</div>
    {/if}
    <Heatmap value={view.value} rowLabels={view.rows} colLabels={view.cols} hiRows={cell ? [cell.i] : []} hiCols={cell ? [cell.j] : []} onhover={(c) => (cell = c)} />
  {:else}
    <div class="loading">{t('Loading the recorded weights…')}</div>
  {/if}

  {#snippet controls()}
    {#if tab === 'words' && nums.length}
      <span class="lbl">{t('number')}</span>
      <button type="button" class="lab-btn step" aria-label={t('previous number')} disabled={pick === 0} onclick={() => (pick = pick - 1)}>‹</button>
      <select bind:value={pick} aria-label={t('pick a number')}>
        {#each nums as e, k}<option value={k}>{fmtN(e.n)}</option>{/each}
      </select>
      <button type="button" class="lab-btn step" aria-label={t('next number')} disabled={pick === nums.length - 1} onclick={() => (pick = pick + 1)}>›</button>
    {/if}
  {/snippet}

  {#snippet readout()}
    {#if view && cell}
      {t(tab === 'words' ? 'Writing “{w}”, the decoder gives digit {j} (“{c}”) weight' : 'Writing “{w}”, the decoder gives input {j} (“{c}”) weight', { w: view.rows[cell.i], j: cell.j, c: view.cols[cell.j] })} <b>{view.value[cell.i][cell.j].toFixed(2)}</b>{t('.')}
    {:else if tab === 'words' && ex}
      {t('Rows: the words it wrote. Columns: the digits it read. Point at or tap a cell.')}
    {:else if view}
      {t('Each output digit looks almost only at one input digit: the last one first, then backwards. Point at or tap a cell.')}
    {:else}
      <span class="idle">{t('Waiting for the recorded weights…')}</span>
    {/if}
  {/snippet}

  {#snippet legend()}
    <span><i class="ramp"></i>{t('attention weight, 0 → 1')}</span>
    {#if tab === 'words' && !cell && words}
      <span class="tip">{t('Strongest look for each word: {list}', { list: words.rows.map((w, i) => `${w} → ${words.cols[strongest(words.value[i])]}`).join(t(', ')) })}</span>
    {/if}
  {/snippet}
</LabFrame>

<style>
  .loading { min-height: 16rem; display: grid; place-items: center; color: var(--dim); font-size: 0.85rem; border: 1px dashed var(--line); border-radius: 6px; }
  .cap { font-size: 0.85rem; color: var(--dim); margin-bottom: 0.35rem; font-family: var(--mono); }
  .cap b { color: var(--fg); }
  .cap .ok { color: var(--ok); font-family: system-ui, -apple-system, sans-serif; margin-left: 0.4rem; }
  .cap .bad { margin-left: 0.4rem; font-family: system-ui, -apple-system, sans-serif; }
  .lbl { font-size: 0.85rem; color: var(--dim); }
  .step { min-width: 2.5rem; font-family: var(--mono); padding: 0.3rem 0.6rem; }
  select { font: inherit; font-family: var(--mono); font-size: 0.88rem; min-height: 2.1rem; padding: 0.2rem 0.5rem; border: 1px solid var(--field); border-radius: 6px; background: var(--bg); color: var(--fg); }
  @media (max-width: 760px) { select { min-height: 2.5rem; } }
  .ramp { display: inline-block; width: 3rem; height: 0.7rem; border: 1px solid var(--line); border-radius: 2px; vertical-align: -0.1em; margin-right: 0.35rem;
    background: linear-gradient(to right, transparent, color-mix(in srgb, var(--accent) 75%, transparent)); }
  .tip { flex-basis: 100%; font-family: var(--mono); }
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
  .bad { color: var(--warn); }
  p.bad { margin: 0; }
</style>
