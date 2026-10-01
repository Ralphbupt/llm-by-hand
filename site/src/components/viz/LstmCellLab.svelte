<script lang="ts">
  /**
   * One LSTM cell whose cell state c is one number. The gates are sliders between 0 and 1.
   *   c = f·c_prev + i·g        (the conveyor belt: keep some, add some)
   *   h = o·tanh(c)             (what the cell shows to the next layer)
   * Below: what is left of c after many steps with no new input (i = 0), next to a plain RNN's factor.
   * hide: values that stay "?" until a question is answered ({ c, h, keep } → exercise id).
   */
  import { onMount } from 'svelte'
  import { lstmCell } from '@lib/classic'
  import { has, subscribe } from '@lib/progress'
  import { readable } from '@lib/readable'
  import LabFrame from './LabFrame.svelte'

  let { hide = {} }: { hide?: { c?: string; h?: string; keep?: string } } = $props()
  let solved = $state<Record<string, boolean>>({})
  onMount(() => {
    const sync = () => (solved = Object.fromEntries(Object.values(hide).map((id) => [id!, has(id!)])))
    sync()
    return subscribe(sync)
  })
  const hidden = (key: 'c' | 'h' | 'keep') => !!hide[key] && !solved[hide[key]!]

  const S0 = { cPrev: 1, f: 0.9, i: 0.5, g: 0.8, o: 0.6 }
  let cPrev = $state(S0.cPrev)
  let f = $state(S0.f)
  let i = $state(S0.i)
  let g = $state(S0.g)
  let o = $state(S0.o)
  const r = $derived(lstmCell(cPrev, f, i, g, o))
  const changed = $derived(cPrev !== S0.cPrev || f !== S0.f || i !== S0.i || g !== S0.g || o !== S0.o)
  function resetAll() {
    ;({ cPrev, f, i, g, o } = S0)
  }
  const f4 = (v: number) => v.toFixed(4)
  // belt thickness for a cell-state value (|c| up to 2 → up to 26 units), and its sign
  const thick = (v: number) => Math.max(2, Math.min(26, 2 + 12 * Math.abs(v)))
  const sign = (v: number) => (v < 0 ? 'neg' : 'pos')

  // what is left over time with no input: c_t = f^t; a plain RNN multiplies by about 0.5 per step
  const T = 50
  const W = 360, H = 156, L = 36, R = 12, TOP = 10, B = 32
  const px = (t: number) => L + (t / T) * (W - L - R)
  const py = (v: number) => TOP + (1 - v) * (H - TOP - B)
  // phones: the belt runs top to bottom instead of left to right
  let boxW = $state(600)
  const narrow = $derived(boxW < 520)
  const curve = (k: number) => Array.from({ length: T + 1 }, (_, t) => `${t ? 'L' : 'M'}${px(t).toFixed(1)},${py(k ** t).toFixed(1)}`).join(' ')
</script>

<LabFrame
  title="One LSTM cell: c moves along a belt from step to step"
  hint="Move the gates. The belt’s thickness is the size of the cell state c."
  onreset={resetAll}
  resetDisabled={!changed}
>
  <div class="pic" bind:clientWidth={boxW}>
    {#if !narrow}
      <svg use:readable viewBox="0 0 540 182" class="belt" role="img"
        aria-label="The cell state flows left to right: multiplied by the forget gate, then the input is added, then the output gate reads it">
        <text x="10" y="16" class="cap">cell state c, left to right</text>
        <rect x="10" y={58 - thick(cPrev) / 2} width="150" height={thick(cPrev)} rx="3" class="band {sign(cPrev)}" />
        <text x="14" y="40" class="num">c_prev = {f4(cPrev)}</text>
        <circle cx="172" cy="58" r="14" class="gate" />
        <text x="172" y="63" class="op" text-anchor="middle">× f</text>
        <text x="172" y="94" class="small" text-anchor="middle">keep {Math.round(f * 100)}%</text>
        <rect x="186" y={58 - thick(f * cPrev) / 2} width="104" height={thick(f * cPrev)} rx="3" class="band {sign(f * cPrev)}" />
        <text x="190" y="40" class="num">{f4(f * cPrev)}</text>
        <circle cx="302" cy="58" r="14" class="gate" />
        <text x="302" y="63" class="op" text-anchor="middle">+</text>
        <line x1="302" y1="150" x2="302" y2="74" class="feed {sign(i * g)}" style="stroke-width:{hidden('c') ? 2 : Math.max(1.5, thick(i * g))}" />
        <path d="M296,80 L302,72 L308,80" class="feed-head" />
        <rect x="217" y="150" width="170" height="24" rx="5" class="box" />
        <text x="302" y="166" class="num" text-anchor="middle">i·g = {i.toFixed(2)} × {g.toFixed(2)}{hidden('c') ? '' : ` = ${(i * g).toFixed(3)}`}</text>
        {#if hidden('c')}
          <rect x="316" y="49" width="214" height="18" rx="3" class="band unknown" />
          <text x="320" y="40" class="num strong q">c = ?</text>
        {:else}
          <rect x="316" y={58 - thick(r.c) / 2} width="214" height={thick(r.c)} rx="3" class="band {sign(r.c)}" />
          <text x="320" y="40" class="num strong">c = {f4(r.c)}</text>
        {/if}
        <text x="530" y="40" class="small" text-anchor="end">→ next step</text>
        <!-- output tap, drawn to the right of everything else so no label crosses it -->
        <line x1="470" y1="70" x2="470" y2="140" class="tap" />
        <circle cx="470" cy="104" r="14" class="gate" />
        <text x="470" y="109" class="op" text-anchor="middle">× o</text>
        <text x="450" y="98" class="small" text-anchor="end">h = o · tanh(c)</text>
        <text x="450" y="112" class="small" text-anchor="end">shows {Math.round(o * 100)}%</text>
        <rect x="414" y="146" width="112" height="26" rx="5" class="box out" />
        <text x="470" y="164" class="num strong" class:q={hidden('h')} text-anchor="middle">h = {hidden('h') ? '?' : f4(r.h)}</text>
      </svg>
    {:else}
      <!-- phone: the same cell, top to bottom -->
      <svg use:readable viewBox="0 0 300 500" class="belt tall" role="img"
        aria-label="The cell state flows top to bottom: multiplied by the forget gate, then the input is added, then the output gate reads it">
        <text x="10" y="16" class="cap">cell state c, top to bottom</text>
        <rect x={80 - thick(cPrev) / 2} y="30" width={thick(cPrev)} height="90" rx="3" class="band {sign(cPrev)}" />
        <text x="110" y="62" class="num">c_prev = {f4(cPrev)}</text>
        <circle cx="80" cy="136" r="14" class="gate" />
        <text x="80" y="141" class="op" text-anchor="middle">× f</text>
        <text x="110" y="140" class="small">keep {Math.round(f * 100)}%</text>
        <rect x={80 - thick(f * cPrev) / 2} y="150" width={thick(f * cPrev)} height="70" rx="3" class="band {sign(f * cPrev)}" />
        <text x="110" y="190" class="num">{f4(f * cPrev)}</text>
        <circle cx="80" cy="236" r="14" class="gate" />
        <text x="80" y="241" class="op" text-anchor="middle">+</text>
        <line x1="150" y1="236" x2="96" y2="236" class="feed {sign(i * g)}" style="stroke-width:{hidden('c') ? 2 : Math.max(1.5, thick(i * g))}" />
        <path d="M102,230 L94,236 L102,242" class="feed-head" />
        <rect x="150" y="222" width="142" height="28" rx="5" class="box" />
        <text x="221" y="240" class="num" text-anchor="middle">i·g = {i.toFixed(2)}×{g.toFixed(2)}</text>
        {#if !hidden('c')}<text x="221" y="266" class="small" text-anchor="middle">= {(i * g).toFixed(3)}</text>{/if}
        {#if hidden('c')}
          <rect x="71" y="250" width="18" height="200" rx="3" class="band unknown" />
          <text x="110" y="300" class="num strong q">c = ?</text>
        {:else}
          <rect x={80 - thick(r.c) / 2} y="250" width={thick(r.c)} height="200" rx="3" class="band {sign(r.c)}" />
          <text x="110" y="300" class="num strong">c = {f4(r.c)}</text>
        {/if}
        <text x="80" y="470" class="small" text-anchor="middle">↓ next step</text>
        <line x1="96" y1="360" x2="196" y2="360" class="tap" />
        <circle cx="210" cy="360" r="14" class="gate" />
        <text x="210" y="365" class="op" text-anchor="middle">× o</text>
        <text x="210" y="392" class="small" text-anchor="middle">h = o · tanh(c), shows {Math.round(o * 100)}%</text>
        <rect x="150" y="404" width="120" height="28" rx="5" class="box out" />
        <text x="210" y="423" class="num strong" class:q={hidden('h')} text-anchor="middle">h = {hidden('h') ? '?' : f4(r.h)}</text>
      </svg>
    {/if}

    <div class="mem">
      <div class="label">what is left after t steps with nothing new added (i = 0)</div>
      <svg use:readable viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="what is left of c after t steps">
        {#each [0, 0.5, 1] as v}
          <line x1={L} x2={W - R} y1={py(v)} y2={py(v)} class="grid" />
          <text x={L - 4} y={py(v) + 3} class="t" text-anchor="end">{v}</text>
        {/each}
        {#each [0, 10, 25, 50] as t}<text x={px(t)} y={H - B + 13} class="t" text-anchor={t === 50 ? 'end' : 'middle'}>{t}</text>{/each}
        <text x={(L + W - R) / 2} y={H - 3} class="t" text-anchor="middle">steps t</text>
        <path d={curve(0.5)} class="line rnn" />
        <path d={curve(f)} class="line lstm" />
      </svg>
    </div>
  </div>

  {#snippet controls()}
    <fieldset class="group">
      <legend>Gates (0 to 1)</legend>
      <label><span>f, keep</span> <b>{f.toFixed(2)}</b> <input type="range" min="0" max="1" step="0.01" bind:value={f} aria-label="forget gate f" /></label>
      <label><span>i, add</span> <b>{i.toFixed(2)}</b> <input type="range" min="0" max="1" step="0.01" bind:value={i} aria-label="input gate i" /></label>
      <label><span>o, show</span> <b>{o.toFixed(2)}</b> <input type="range" min="0" max="1" step="0.01" bind:value={o} aria-label="output gate o" /></label>
    </fieldset>
    <fieldset class="group">
      <legend>Inputs</legend>
      <label><span>c_prev</span> <b>{cPrev.toFixed(2)}</b> <input type="range" min="-2" max="2" step="0.05" bind:value={cPrev} aria-label="c_prev, what the cell holds" /></label>
      <label><span>g, new candidate</span> <b>{g.toFixed(2)}</b> <input type="range" min="-1" max="1" step="0.05" bind:value={g} aria-label="g, the new candidate" /></label>
    </fieldset>
  {/snippet}

  {#snippet readout()}
    × f per step: after 10 steps <b>{hidden('keep') ? '?' : f4(f ** 10)}</b> is left, after 50 steps <b>{hidden('keep') ? '?' : f4(f ** 50)}</b> (a plain RNN, about × 0.5: {f4(0.5 ** 10)} and {(0.5 ** 50).toExponential(1)})
  {/snippet}

  {#snippet legend()}
    <span><i class="sw pos"></i>c above 0</span>
    <span><i class="sw neg"></i>c below 0</span>
    <span><i class="ln lstm"></i>LSTM cell, × f per step</span>
    <span><i class="ln rnn"></i>plain RNN, about × 0.5 per step</span>
  {/snippet}
</LabFrame>

<style>
  .pic { display: grid; gap: 0.8rem; min-width: 0; }
  .belt { width: 100%; max-width: 42rem; display: block; background: var(--bg); border: 1px solid var(--line); border-radius: 6px; }
  .belt.tall { max-width: 22rem; }
  .band { transition: y 0.2s, height 0.2s, x 0.2s, width 0.2s; }
  .band.pos { fill: var(--pos); }
  .band.neg { fill: var(--neg); }
  .band.unknown { fill: none; stroke: var(--warn); stroke-dasharray: 4 3; }
  .gate { fill: var(--card); stroke: var(--fg); stroke-width: 1.5; }
  .op { font-family: var(--mono); font-size: 13px; fill: var(--fg); }
  .num { font-family: var(--mono); font-size: 12px; fill: var(--fg); }
  .num.strong { font-weight: 700; }
  .q { fill: var(--warn); }
  .small { font-size: 11px; fill: var(--dim); }
  .cap { font-size: 12px; fill: var(--dim); }
  .feed { stroke-linecap: round; }
  .feed.pos { stroke: var(--pos); }
  .feed.neg { stroke: var(--neg); }
  .feed-head { fill: none; stroke: var(--fg); stroke-width: 2; }
  .tap { stroke: var(--dim); stroke-width: 2; stroke-dasharray: 3 3; }
  .box { fill: var(--card); stroke: var(--line); }
  .box.out { stroke: var(--fg); }
  @media (prefers-reduced-motion: reduce) { .band { transition: none; } }
  .label { font-size: 0.82rem; color: var(--dim); }
  .chart { width: 100%; max-width: 28rem; display: block; margin-top: 0.3rem; background: var(--bg); border: 1px solid var(--line); border-radius: 6px; }
  .grid { stroke: var(--line); }
  .t { fill: var(--dim); font-size: 10px; font-family: var(--mono); }
  .line { fill: none; stroke-width: 2; }
  .line.rnn { stroke: var(--cat-3); }
  .line.lstm { stroke: var(--cat-1); }
  .group { border: 1px solid var(--line); border-radius: 6px; padding: 0.4rem 0.7rem 0.6rem; margin: 0; display: grid; gap: 0.25rem; min-width: min(100%, 15rem); flex: 1 1 15rem; }
  .group legend { font-size: 0.78rem; color: var(--dim); padding: 0 0.3rem; }
  .group label { display: grid; grid-template-columns: 7.5rem 3rem minmax(0, 1fr); align-items: center; gap: 0.4rem; font-size: 0.85rem; }
  .group span { color: var(--dim); }
  .group b { font-family: var(--mono); font-weight: 600; }
  .group input { width: 100%; min-height: 2rem; accent-color: var(--accent); }
  .sw { display: inline-block; width: 0.8rem; height: 0.8rem; border-radius: 2px; vertical-align: -0.1em; margin-right: 0.3rem; }
  .sw.pos { background: var(--pos); }
  .sw.neg { background: var(--neg); }
  .ln { display: inline-block; width: 0.9rem; height: 0.25rem; border-radius: 2px; margin-right: 0.35rem; vertical-align: middle; }
  .ln.lstm { background: var(--cat-1); }
  .ln.rnn { background: var(--cat-3); }
</style>
