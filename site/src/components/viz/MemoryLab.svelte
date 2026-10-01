<script lang="ts">
  /**
   * Plays back the "remember the first symbol" runs recorded by content/1-foundations/rnn/export.py.
   * kinds: which networks to show. Accuracy on 1000 held-out sequences, every 50 training steps.
   */
  import { onMount } from 'svelte'
  import { readable } from '@lib/readable'
  import LabFrame from './LabFrame.svelte'

  type Kind = 'rnn' | 'lstm0' | 'lstm'
  let { kinds = ['rnn'] }: { kinds?: Kind[] } = $props()
  const NAME: Record<Kind, string> = { rnn: 'RNN', lstm0: 'LSTM, every bias starts at 0', lstm: 'LSTM, forget bias starts at 2' }
  const SHORT: Record<Kind, string> = { rnn: 'RNN', lstm0: 'LSTM b=0', lstm: 'LSTM f=2' }
  const COLOR: Record<Kind, string> = { rnn: 'var(--cat-3)', lstm0: 'var(--cat-5)', lstm: 'var(--cat-1)' }

  type Data = { ks: number[]; every: number; steps: number } & Record<Kind, Record<string, number[]>>
  let data = $state<Data | null>(null)
  let error = $state('')
  let k = $state(5)
  onMount(() => {
    fetch('/data/rnn/memory.json').then((r) => r.json()).then((d) => (data = d)).catch((e) => (error = String(e)))
  })

  // accuracy never drops much below guessing (50%), so the axis runs from 40% to 100%
  const W = 400, H = 190, L = 40, R = 66, TOP = 22, B = 26, LO = 0.4
  const px = (i: number, n: number) => L + (i / (n - 1)) * (W - L - R)
  const py = (a: number) => TOP + ((1 - Math.max(LO, a)) / (1 - LO)) * (H - TOP - B)
  // drawn back to front, each a little different, so curves that coincide stay visible
  const STYLE: Record<Kind, string> = { rnn: 'stroke-width:5;opacity:0.55', lstm0: 'stroke-width:3;stroke-dasharray:6 4', lstm: 'stroke-width:2' }
  // end labels, spread apart when curves end at the same height
  function endYs(ks: Kind[], d: Data, kk: number) {
    const ys = ks.map((kind) => ({ kind, y: py(d[kind][String(kk)].at(-1)!) }))
    ys.sort((a, b) => a.y - b.y)
    for (let i = 1; i < ys.length; i++) if (ys[i].y - ys[i - 1].y < 12) ys[i].y = ys[i - 1].y + 12
    return Object.fromEntries(ys.map((e) => [e.kind, e.y + 4])) as Record<Kind, number>
  }
  const path = (c: number[]) => c.map((a, i) => `${i ? 'L' : 'M'}${px(i, c.length).toFixed(1)},${py(a).toFixed(1)}`).join(' ')
</script>

<LabFrame
  title="Remember the first symbol: real training runs"
  hint={kinds.length > 1 ? 'Pick a sequence length k. Try k = 40 and k = 80 to see where the networks start to differ.' : 'Pick a sequence length k. Try the longer ones.'}
>
  {#if error}<p class="bad">Could not load the runs: {error}</p>{/if}
  {#if data}
    {@const ys = endYs(kinds, data, k)}
    <svg use:readable viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="accuracy during training for k = {k}">
      <text x={L} y="13" class="t">accuracy on new sequences, k = {k}</text>
      {#each [0.5, 0.75, 1] as a}
        <line x1={L} x2={W - R} y1={py(a)} y2={py(a)} class="grid" class:chance={a === 0.5} />
        <text x={L - 4} y={py(a) + 4} class="t" text-anchor="end">{a * 100}%</text>
      {/each}
      <text x={L + 4} y={py(0.5) - 4} class="t">guessing</text>
      <text x={L} y={H - 6} class="t">training step 0</text>
      <text x={W - R} y={H - 5} class="t" text-anchor="end">step {data.steps}</text>
      {#each kinds as kind}
        <path d={path(data[kind][String(k)])} style="stroke:{COLOR[kind]};{kinds.length > 1 ? STYLE[kind] : 'stroke-width:2.5'}" class="line" />
        <text x={W - R + 4} y={ys[kind]} class="end" style="fill:{COLOR[kind]}">{SHORT[kind]}</text>
      {/each}
    </svg>
  {:else if !error}
    <p class="dim">Loading runs…</p>
  {/if}

  {#snippet controls()}
    {#if data}
      <div class="ks" role="group" aria-label="Sequence length k">
        <span class="dim">sequence length k</span>
        {#each data.ks as kk}<button class:on={k === kk} aria-pressed={k === kk} onclick={() => (k = kk)}>{kk}</button>{/each}
      </div>
    {/if}
  {/snippet}

  {#snippet readout()}
    {#if data}
      k = {k}: {kinds.map((kind) => `${SHORT[kind]} ${(data![kind][String(k)].at(-1)! * 100).toFixed(1)}%`).join(' · ')} after {data.steps} steps
    {:else}…{/if}
  {/snippet}

  {#snippet legend()}
    {#each kinds as kind}<span><i style="background:{COLOR[kind]}"></i>{NAME[kind]}</span>{/each}
    <span>1,500 steps of 64 sequences, a 32-number hidden state, accuracy on 1,000 new sequences</span>
  {/snippet}
</LabFrame>

<style>
  .ks { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; font-size: 0.85rem; }
  .ks button { font: inherit; font-family: var(--mono); font-size: 0.85rem; min-width: 2.4rem; min-height: 2rem; padding: 0.15rem 0.6rem; border: 1px solid var(--field); border-radius: 999px; background: var(--bg); color: var(--dim); cursor: pointer; }
  .ks button.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  .ks button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .chart { width: 100%; max-width: 36rem; display: block; background: var(--bg); border: 1px solid var(--line); border-radius: 6px; }
  .grid { stroke: var(--line); }
  .t { fill: var(--dim); font-size: 11px; font-family: var(--mono); }
  .end { font-size: 11px; font-family: var(--mono); font-weight: 600; }
  .grid.chance { stroke: var(--dim); stroke-dasharray: 3 3; }
  .line { fill: none; stroke-linejoin: round; }
  i { display: inline-block; width: 0.9rem; height: 0.25rem; border-radius: 2px; margin-right: 0.35rem; vertical-align: middle; }
  .dim { color: var(--dim); }
  .bad { color: var(--warn); }
</style>
