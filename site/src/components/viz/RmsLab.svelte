<script lang="ts">
  /** RMS lab (level 19): LayerNorm and RMSNorm side by side on one vector of four numbers. */
  import { onMount } from 'svelte'
  import LabFrame from './LabFrame.svelte'
  import { has, subscribe } from '@lib/progress'
  import { layerNorm, rmsNorm } from '@lib/modern'

  let { hide = {} }: { hide?: { rms?: string; out?: string } } = $props()
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
  const locked = (k: 'rms' | 'out') => !!hide[k] && !solved[hide[k]!]

  const X0 = [1, 1, 3, 5]
  let x = $state([...X0])
  const ln = $derived(layerNorm(x))
  const rm = $derived(rmsNorm(x))
  const isStart = $derived(x.every((v, i) => v === X0[i]))
  const f = (v: number) => (Number.isFinite(v) ? v.toFixed(4) : '—')
  // bars: each vector drawn around its own zero line, scaled to its largest size
  const BW = 140, BH = 64
  const bars = (v: number[]) => {
    const m = Math.max(1e-9, ...v.map((a) => Math.abs(a)))
    return v.map((a, i) => ({ x: 8 + i * 32, h: (a / m) * (BH / 2 - 6), a }))
  }
  const rmsHidden = $derived(isStart && (locked('rms') || locked('out')))
  function set(i: number, raw: string) { const n = Number(raw); if (!Number.isNaN(n)) x = x.map((v, j) => (j === i ? n : v)) }
</script>

{#snippet plot(v: number[], tone: string, label: string, hidden = false)}
  <figure class="mini">
    <svg viewBox="0 0 {BW} {BH}" role="img" aria-label={label}>
      <line x1="2" y1={BH / 2} x2={BW - 2} y2={BH / 2} class="zero" />
      {#if hidden}
        <text x={BW / 2} y={BH / 2 - 6} class="q">?</text>
      {:else}
        {#each bars(v) as b}
          <rect x={b.x} y={b.h >= 0 ? BH / 2 - b.h : BH / 2} width="22" height={Math.max(1, Math.abs(b.h))} rx="2" style:fill={tone} class="bar" />
        {/each}
      {/if}
    </svg>
    <figcaption>{label}</figcaption>
  </figure>
{/snippet}

<LabFrame
  title="LayerNorm and RMSNorm on the same four numbers"
  hint="Edit any number of x. LayerNorm shifts and scales; RMSNorm only scales."
  onreset={() => (x = [...X0])}
  resetDisabled={isStart}
>
  <div class="row">
    <span class="lbl">x =</span>
    {#each x as v, i}
      <input aria-label={`x${i}`} inputmode="decimal" value={v} onchange={(e) => set(i, e.currentTarget.value)} />
    {/each}
  </div>

  <div class="plots">
    {@render plot(x, 'var(--dim)', 'input x')}
    {@render plot(ln.out, 'var(--fg)', 'LayerNorm: shifted, then scaled')}
    {@render plot(rm.out, 'var(--accent)', 'RMSNorm: only scaled', rmsHidden)}
  </div>

  <div class="cols">
    <div class="col">
      <h4>LayerNorm</h4>
      <p>1. mean = <b>{f(ln.mean)}</b></p>
      <p>2. subtract it: <span class="nw">[{x.map((v) => (v - ln.mean).toFixed(2)).join(', ')}]</span></p>
      <p>3. std = <b>{f(ln.std)}</b></p>
      <p>4. divide: <span class="nw">[{ln.out.map((v) => v.toFixed(4)).join(', ')}]</span></p>
      <p class="dim">output mean 0, std 1</p>
    </div>
    <div class="col">
      <h4>RMSNorm</h4>
      <p>1. mean of squares = {isStart && locked('rms') ? '?' : f(rm.meanSq)}</p>
      <p>2. rms = √ that = <b>{isStart && locked('rms') ? '?' : f(rm.rms)}</b></p>
      <p>3. divide: <span class="nw">[{rm.out.map((v, i) => (isStart && (locked('rms') || (i === rm.out.length - 1 && locked('out'))) ? '?' : v.toFixed(4))).join(', ')}]</span></p>
      <p class="dim">no mean subtracted: the output keeps its sign pattern</p>
    </div>
  </div>

  {#snippet readout()}
    {#if isStart && (locked('rms') || locked('out'))}<span class="idle">Some RMSNorm numbers show “?” until you answer the questions below. Edit x to explore other vectors.</span>
    {:else}LayerNorm: mean {f(ln.mean)}, std {f(ln.std)} · RMSNorm: rms {f(rm.rms)}{/if}
  {/snippet}
</LabFrame>

<style>
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
  .row { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; font-family: var(--mono); }
  .lbl { font-size: 0.88rem; }
  input { width: 3.6rem; min-height: 2.1rem; font: inherit; font-family: var(--mono); padding: 0.2rem 0.4rem; border: 1px solid var(--field); border-radius: 6px; background: var(--bg); color: var(--accent); }
  input:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
  .cols { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.8rem; margin-top: 0.8rem; }
  @media (max-width: 560px) { .cols { grid-template-columns: minmax(0, 1fr); } }
  .col { border: 1px solid var(--line); border-radius: 6px; padding: 0.5rem 0.7rem; font-family: var(--mono); font-size: 0.82rem; min-width: 0; overflow-wrap: anywhere; background: var(--bg); }
  .col h4 { margin: 0 0 0.3rem; font-family: inherit; font-size: 0.88rem; }
  .col p { margin: 0.15rem 0; }
  .col .nw { white-space: nowrap; } /* a vector stays on one line */
  .dim { color: var(--dim); }
  .plots { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0.6rem; margin-top: 0.8rem; }
  @media (max-width: 480px) { .plots { gap: 0.3rem; } }
  .mini { margin: 0; border: 1px solid var(--line); border-radius: 6px; padding: 0.3rem; background: var(--bg); min-width: 0; }
  .mini svg { width: 100%; height: auto; display: block; }
  .mini figcaption { font-size: 0.75rem; color: var(--dim); text-align: center; line-height: 1.3; }
  .zero { stroke: var(--dim); stroke-width: 0.8; }
  .bar { transition: y 0.2s ease-out, height 0.2s ease-out; }
  .q { font-size: 18px; fill: var(--warn); text-anchor: middle; font-family: var(--mono); }
  @media (prefers-reduced-motion: reduce) { .bar { transition: none; } }
  /* phones: touch targets at least 40px tall; 16px fields so iOS does not zoom */
  @media (max-width: 760px) { input { min-height: 2.5rem; font-size: 16px; } }
</style>
