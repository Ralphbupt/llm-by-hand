<script lang="ts">
  /**
   * The bottleneck, measured: two LSTM encoder–decoders reverse digit strings of growing length.
   * plain = the decoder only gets the encoder's final (h, c); attn = the same plus attention.
   * Real runs recorded by content/1-foundations/seq2seq-attention/export.py (300 new strings per length).
   */
  import { onMount } from 'svelte'
  import { readable } from '@lib/readable'
  import LabFrame from './LabFrame.svelte'

  type Kind = 'plain' | 'attn'
  let { models = ['plain', 'attn'] }: { models?: Kind[] } = $props()
  type Data = { lengths: number[]; steps: number } & Record<Kind, Record<string, number[]>>
  let data = $state<Data | null>(null)
  let error = $state('')
  let H = $state('32')
  let sel = $state<number | null>(null) // index of the picked length; null = the longest
  onMount(() => {
    fetch('/data/seq2seq-attention/bottleneck.json').then((r) => r.json()).then((d) => (data = d)).catch((e) => (error = String(e)))
  })

  const NAME: Record<Kind, string> = { plain: 'without attention', attn: 'with attention' }
  const W = 360, Hh = 200, L = 40, R = 14, TOP = 16, B = 36
  const px = (i: number, n: number) => L + (i / (n - 1)) * (W - L - R)
  const py = (a: number) => TOP + (1 - a) * (Hh - TOP - B)
  const path = (c: number[]) => c.map((a, i) => `${i ? 'L' : 'M'}${px(i, c.length).toFixed(1)},${py(a).toFixed(1)}`).join(' ')
  const pct = (a: number) => `${Math.round(a * 100)}%`
  const n = $derived(data ? data.lengths.length : 1)
  const at = $derived(sel ?? n - 1)
  const colW = $derived((W - L - R) / Math.max(1, n - 1))
</script>

<LabFrame
  title="Reversing digit strings: exact answers on new strings"
  hint="Tap a length to read its numbers. Switch the state size H to give the model a bigger state."
  onreset={() => { H = '32'; sel = null }}
  resetDisabled={H === '32' && sel === null}
>
  {#if error}
    <p class="bad">Could not load the runs: {error}</p>
  {:else if !data}
    <div class="loading">Loading the recorded runs…</div>
  {:else}
    <div class="cap">fraction of strings reversed with every digit right</div>
    <svg use:readable viewBox="0 0 {W} {Hh}" class="chart" role="group" aria-label="Accuracy against input length">
      {#each [0, 0.5, 1] as a}
        <line x1={L} x2={W - R} y1={py(a)} y2={py(a)} class="grid" />
        <text x={L - 5} y={py(a) + 3.5} class="t" text-anchor="end">{a * 100}%</text>
      {/each}
      <rect x={Math.max(L - 12, px(at, n) - colW / 2)} y={TOP - 6} width={Math.min(W - 2, px(at, n) + colW / 2) - Math.max(L - 12, px(at, n) - colW / 2)} height={Hh - TOP - B + 12} rx="3" class="col" />
      {#each data.lengths as len, i}
        <text x={px(i, n)} y={Hh - B + 15} class="t" class:on={i === at} text-anchor="middle">{len}</text>
      {/each}
      <text x={(W + L) / 2} y={Hh - 4} class="t" text-anchor="middle">input length (digits)</text>
      {#each models as k}
        <path d={path(data[k][H])} class="line {k}" />
        {#each data[k][H] as a, i}<circle cx={px(i, n)} cy={py(a)} r={i === at ? 3.6 : 2.6} class="pt {k}" />{/each}
        <text x={W - R - 2} y={py(data[k][H][n - 1]) + (k === 'plain' && models.length > 1 && data.attn[H][n - 1] - data.plain[H][n - 1] < 0.15 ? 14 : -7)}
          class="end {k}" text-anchor="end">{NAME[k]}</text>
      {/each}
      <!-- tap targets: one per length (the keyboard uses the table's column buttons) -->
      {#each data.lengths as _, i}
        <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
        <rect x={px(i, n) - colW / 2} y={TOP - 6} width={colW} height={Hh - TOP - B + 26} class="hit" aria-hidden="true"
          onpointerenter={(e) => e.pointerType === 'mouse' && (sel = i)} onclick={() => (sel = i)} />
      {/each}
    </svg>

    <table>
      <thead>
        <tr><th scope="col">length</th>
          {#each data.lengths as len, i}
            <th scope="col" class:on={i === at}><button type="button" aria-pressed={i === at} onclick={() => (sel = i)}>{len}</button></th>
          {/each}
        </tr>
      </thead>
      <tbody>
        {#each models as k}
          <tr><th scope="row"><i class="sw {k}"></i>{NAME[k]}</th>{#each data[k][H] as a, i}<td class:on={i === at}>{pct(a)}</td>{/each}</tr>
        {/each}
      </tbody>
    </table>
  {/if}

  {#snippet controls()}
    <span class="lbl">state size H</span>
    <div class="seg" role="group" aria-label="state size H">
      {#each ['32', '128'] as h}<button type="button" class:on={H === h} aria-pressed={H === h} onclick={() => (H = h)}>{h}</button>{/each}
    </div>
  {/snippet}

  {#snippet readout()}
    {#if data}
      H = {H}, strings of {data.lengths[at]} digits:
      {#each models as k, j}{j ? ', ' : ''}{NAME[k]} <b>{pct(data[k][H][at])}</b>{/each} exactly right.
    {:else}
      <span class="idle">Waiting for the recorded runs…</span>
    {/if}
  {/snippet}

  {#snippet legend()}
    {#each models as k}<span><i class="sw {k}"></i>{NAME[k]}</span>{/each}
    {#if data}<span class="tip">Same LSTM size, {data.steps.toLocaleString('en-US')} training steps on lengths 2–24, then 300 new strings per length. An answer counts only if every digit is right.</span>{/if}
  {/snippet}
</LabFrame>

<style>
  .loading { min-height: 20rem; display: grid; place-items: center; color: var(--dim); font-size: 0.85rem; border: 1px dashed var(--line); border-radius: 6px; }
  .cap { font-size: 0.8rem; color: var(--dim); }
  .chart { width: 100%; max-width: 34rem; display: block; background: var(--bg); border: 1px solid var(--line); border-radius: 6px; margin: 0.2rem 0 0.7rem; }
  .grid { stroke: var(--line); }
  .col { fill: var(--highlight); }
  .hit { fill: transparent; cursor: pointer; outline: none; }
  .t { fill: var(--dim); font-size: 10px; font-family: var(--mono); }
  .t.on { fill: var(--accent); font-weight: 700; }
  .line { fill: none; stroke-width: 2.2; stroke-linejoin: round; }
  .line.plain { stroke: var(--cat-3); }
  .line.attn { stroke: var(--cat-1); }
  .pt { stroke: var(--bg); stroke-width: 1; }
  .pt.plain { fill: var(--cat-3); }
  .pt.attn { fill: var(--cat-1); }
  .end { font-size: 10px; font-weight: 650; paint-order: stroke; stroke: var(--bg); stroke-width: 3px; }
  .end.plain { fill: var(--cat-3); }
  .end.attn { fill: var(--cat-1); }

  table { border-collapse: collapse; font-size: 0.8rem; font-family: var(--mono); width: 100%; max-width: 34rem; table-layout: fixed; }
  th, td { border: 1px solid var(--line); padding: 0.25rem 0.35rem; text-align: right; }
  thead th:first-child, tbody th { width: 30%; }
  th { color: var(--dim); font-weight: 400; }
  tbody th { text-align: left; font-family: system-ui, -apple-system, sans-serif; line-height: 1.25; }
  thead th { padding: 0; }
  thead th:first-child { padding: 0.25rem 0.35rem; text-align: left; font-family: system-ui, -apple-system, sans-serif; }
  thead th button { font: inherit; width: 100%; min-height: 2.1rem; padding: 0.2rem 0.35rem; border: 0; background: transparent; color: var(--dim); text-align: right; cursor: pointer; }
  thead th.on button { color: var(--accent); font-weight: 700; }
  td.on, thead th.on { background: var(--highlight); }
  td.on { color: var(--fg); font-weight: 650; }

  .lbl { font-size: 0.85rem; color: var(--dim); }
  .seg { display: inline-flex; border: 1px solid var(--field); border-radius: 6px; overflow: hidden; }
  .seg button { font: inherit; font-family: var(--mono); font-size: 0.85rem; min-height: 2.1rem; padding: 0.2rem 0.9rem; border: 0; background: var(--bg); color: var(--fg); cursor: pointer; }
  .seg button + button { border-left: 1px solid var(--field); }
  .seg button.on { color: var(--accent); background: var(--highlight); }
  .seg button:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
  @media (max-width: 760px) { .seg button, thead th button { min-height: 2.5rem; } }
  .sw { display: inline-block; width: 0.9rem; height: 0; border-top: 2.5px solid; vertical-align: middle; margin-right: 0.35rem; }
  .sw.plain { border-color: var(--cat-3); }
  .sw.attn { border-color: var(--cat-1); }
  tbody th .sw { width: 0.6rem; margin-right: 0.3rem; }
  .tip { flex-basis: 100%; }
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
  .bad { color: var(--warn); margin: 0; }
</style>
