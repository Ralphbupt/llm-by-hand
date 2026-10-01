<script lang="ts">
  /**
   * Batch lab: 10 examples (0–4 class 0, 5–9 class 1) cut into batches, epoch after epoch.
   * Shuffling uses a small seeded generator, so the same seed always gives the same orders.
   */
  import { onMount } from 'svelte'
  import { has, subscribe } from '@lib/progress'
  import LabFrame from './LabFrame.svelte'

  let { hide = {} }: { hide?: Record<string, string | undefined> } = $props()
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
  title="10 examples, cut into batches"
  hint="Change the batch size, check Shuffle each epoch, and press Next epoch."
  onreset={reset}
  resetDisabled={!changed}
>
  <p class="cap">Epoch {epoch}{shuffle ? `, seed ${seed}` : ', no shuffle'}</p>
  {#if hidden}
    <div class="row">
      <span class="lbl">all</span>
      <span class="chips">{#each Array.from({ length: N }, (_, i) => i) as i}<span class="chip c{cls(i)}">{i}</span>{/each}</span>
    </div>
    <p class="q">Batches: <b>?</b> Answer the question below to see how the examples are cut.</p>
  {:else}
    {#each batches as b, k (k + '-' + b.join(','))}
      <div class="row">
        <span class="lbl">batch {k}</span>
        <span class="chips">{#each b as i}<span class="chip c{cls(i)}">{i}</span>{/each}</span>
        <span class="n">{b.length}</span>
      </div>
    {/each}
  {/if}

  {#snippet controls()}
    <button class="lab-btn primary" onclick={() => epoch++}>Next epoch</button>
    <label class="ctl">Batch size
      <select bind:value={bs}>{#each [2, 3, 4, 5] as v}<option value={v}>{v}</option>{/each}</select>
    </label>
    <label class="ctl tog"><input type="checkbox" bind:checked={shuffle} /> Shuffle each epoch</label>
    <span class="ctl">Seed
      <button class="lab-btn step" aria-label="Seed minus one" disabled={!shuffle || seed === 0} onclick={() => { seed--; epoch = 0 }}>−</button>
      <span class="num">{seed}</span>
      <button class="lab-btn step" aria-label="Seed plus one" disabled={!shuffle} onclick={() => { seed++; epoch = 0 }}>+</button>
    </span>
  {/snippet}

  {#snippet readout()}
    {#if hidden}
      Batches per epoch: ?
    {:else}
      {batches.length} batches ({batches.map((b) => b.length).join(', ')}); every example appears once.
      {pure} of {batches.length} batches hold only one class.
    {/if}
  {/snippet}

  {#snippet legend()}
    <span class="lg"><span class="chip c0">0</span> class 0 (examples 0–4)</span>
    <span class="lg"><span class="chip c1">5</span> class 1 (examples 5–9)</span>
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
