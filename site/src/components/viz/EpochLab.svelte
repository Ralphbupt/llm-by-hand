<script lang="ts">
  /**
   * Batch lab: 10 examples (0–4 class 0, 5–9 class 1) cut into batches, epoch after epoch.
   * Shuffling uses a small seeded generator, so the same seed always gives the same orders.
   */
  import { onMount } from 'svelte'
  import { has, subscribe } from '@lib/progress'
  import LabFrame from './LabFrame.svelte'
  import { provideLang, useT } from '@lib/i18nSvelte'
  import type { Lang } from '@lib/i18n'

  let { hide = {}, lang = 'en' }: { hide?: Record<string, string | undefined>; lang?: Lang } = $props()
  provideLang(lang)
  const tx = useT({
    '10 examples, cut into batches': '10 个样本，切成批',
    'Change the batch size, check Shuffle each epoch, and press Next epoch.': '改变批大小，勾选“每轮打乱”，然后按“下一轮”。',
    'Epoch {e}, seed {s}': '第 {e} 轮，随机种子 {s}',
    'Epoch {e}, no shuffle': '第 {e} 轮，不打乱',
    'all': '全部',
    'Batches:': '批：',
    'Answer the question below to see how the examples are cut.': '回答下面的问题，就能看到样本是怎样切分的。',
    'batch {k}': '第 {k} 批',
    'Next epoch': '下一轮',
    'Batch size': '批大小',
    'Shuffle each epoch': '每轮打乱',
    'Seed': '随机种子',
    'Seed minus one': '随机种子减一',
    'Seed plus one': '随机种子加一',
    'Batches per epoch: ?': '每轮的批数：?',
    '{n} batches ({sizes}); every example appears once.': '{n} 批（{sizes}）；每个样本出现一次。',
    '{p} of {n} batches hold only one class.': '{n} 批里有 {p} 批只有一个类别。',
    'class 0 (examples 0–4)': '类别 0（样本 0–4）',
    'class 1 (examples 5–9)': '类别 1（样本 5–9）',
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

  const N = 10
  const cls = (i: number) => (i < 5 ? 0 : 1)
  let bs = $state(4)
  let shuffle = $state(false)
  let seed = $state(0)
  let epoch = $state(0)

  // mulberry32: a tiny seeded random generator
  function rng(s: number) {
    let a = s >>> 0
    return () => {
      a = (a + 0x6d2b79f5) >>> 0
      let t = a
      t = Math.imul(t ^ (t >>> 15), t | 1)
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296
    }
  }
  function order(e: number): number[] {
    const idx = Array.from({ length: N }, (_, i) => i)
    if (!shuffle) return idx
    const r = rng(seed * 1000 + e + 1)
    for (let i = N - 1; i > 0; i--) {
      const j = Math.floor(r() * (i + 1))
      ;[idx[i], idx[j]] = [idx[j], idx[i]]
    }
    return idx
  }
  const cut = (idx: number[]) => {
    const out: number[][] = []
    for (let i = 0; i < N; i += bs) out.push(idx.slice(i, i + bs))
    return out
  }
  let batches = $derived(cut(order(epoch)))
  let pure = $derived(batches.filter((b) => b.every((i) => cls(i) === cls(b[0]))).length)
  let hidden = $derived(locked('batches') && bs === 4 && !shuffle)
  let changed = $derived(bs !== 4 || shuffle || seed !== 0 || epoch !== 0)

  function reset() { bs = 4; shuffle = false; seed = 0; epoch = 0 }
</script>

<LabFrame
  title={tx('10 examples, cut into batches')}
  hint={tx('Change the batch size, check Shuffle each epoch, and press Next epoch.')}
  onreset={reset}
  resetDisabled={!changed}
>
  <p class="cap">{shuffle ? tx('Epoch {e}, seed {s}', { e: epoch, s: seed }) : tx('Epoch {e}, no shuffle', { e: epoch })}</p>
  {#if hidden}
    <div class="row">
      <span class="lbl">{tx('all')}</span>
      <span class="chips">{#each Array.from({ length: N }, (_, i) => i) as i}<span class="chip c{cls(i)}">{i}</span>{/each}</span>
    </div>
    <p class="q">{tx('Batches:')} <b>?</b> {tx('Answer the question below to see how the examples are cut.')}</p>
  {:else}
    {#each batches as b, k (k + '-' + b.join(','))}
      <div class="row">
        <span class="lbl">{tx('batch {k}', { k })}</span>
        <span class="chips">{#each b as i}<span class="chip c{cls(i)}">{i}</span>{/each}</span>
        <span class="n">{b.length}</span>
      </div>
    {/each}
  {/if}

  {#snippet controls()}
    <button class="lab-btn primary" onclick={() => epoch++}>{tx('Next epoch')}</button>
    <label class="ctl">{tx('Batch size')}
      <select bind:value={bs}>{#each [2, 3, 4, 5] as v}<option value={v}>{v}</option>{/each}</select>
    </label>
    <label class="ctl tog"><input type="checkbox" bind:checked={shuffle} /> {tx('Shuffle each epoch')}</label>
    <span class="ctl">{tx('Seed')}
      <button class="lab-btn step" aria-label={tx('Seed minus one')} disabled={!shuffle || seed === 0} onclick={() => { seed--; epoch = 0 }}>−</button>
      <span class="num">{seed}</span>
      <button class="lab-btn step" aria-label={tx('Seed plus one')} disabled={!shuffle} onclick={() => { seed++; epoch = 0 }}>+</button>
    </span>
  {/snippet}

  {#snippet readout()}
    {#if hidden}
      {tx('Batches per epoch: ?')}
    {:else}
      {tx('{n} batches ({sizes}); every example appears once.', { n: batches.length, sizes: batches.map((b) => b.length).join(', ') })}
      {tx('{p} of {n} batches hold only one class.', { p: pure, n: batches.length })}
    {/if}
  {/snippet}

  {#snippet legend()}
    <span class="lg"><span class="chip c0">0</span> {tx('class 0 (examples 0–4)')}</span>
    <span class="lg"><span class="chip c1">5</span> {tx('class 1 (examples 5–9)')}</span>
  {/snippet}
</LabFrame>

<style>
  .cap { margin: 0 0 0.4rem; color: var(--dim); font-size: 0.85rem; }
  .row { display: flex; align-items: center; gap: 0.5rem; margin: 0.3rem 0; }
  .lbl { width: 4.2rem; flex: none; font-family: var(--mono); font-size: 0.8rem; color: var(--dim); }
  .chips { display: flex; flex-wrap: wrap; gap: 0.25rem; }
  .chip {
    display: inline-flex; align-items: center; justify-content: center; width: 1.9rem; height: 1.9rem;
    border-radius: 0.3rem; font-family: var(--mono); font-size: 0.85rem; font-weight: 600; color: var(--on-solid);
    animation: pop 0.2s ease-out;
  }
  .chip.c0 { background: var(--cat-1); }
  .chip.c1 { background: var(--cat-2); }
  @keyframes pop { from { transform: scale(0.85); opacity: 0.4; } to { transform: none; opacity: 1; } }
  @media (prefers-reduced-motion: reduce) { .chip { animation: none; } }
  .n { font-family: var(--mono); font-size: 0.8rem; color: var(--dim); margin-left: auto; }
  .q { margin: 0.5rem 0 0; font-size: 0.9rem; }
  .q b { color: var(--warn); }
  .ctl { display: inline-flex; align-items: center; gap: 0.35rem; font-size: 0.88rem; min-height: 2.5rem; }
  .ctl select { font: inherit; min-height: 2.3rem; padding: 0 0.3rem; border: 1px solid var(--field); border-radius: 0.3rem; background: var(--bg); color: var(--fg); }
  .tog input { width: 1.1rem; height: 1.1rem; accent-color: var(--accent); }
  .step { min-width: 2.5rem; }
  .num { font-family: var(--mono); min-width: 1.4rem; text-align: center; }
  .lg { display: inline-flex; align-items: center; gap: 0.35rem; margin-right: 1rem; font-size: 0.82rem; }
  .lg .chip { width: 1.3rem; height: 1.3rem; font-size: 0.72rem; animation: none; }
</style>
