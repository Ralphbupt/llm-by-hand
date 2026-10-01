<script lang="ts">
  /**
   * The boss run, played back: lines written by a character-level LSTM (and a plain RNN) at points during training.
   * Recorded by content/1-foundations/lstm/demo.py --export. Every line is checked against the rules here, live.
   */
  import { onMount } from 'svelte'
  import { RULES } from '@lib/classic'
  import { readable } from '@lib/readable'
  import LabFrame from './LabFrame.svelte'

  type Snap = { step: number; lines: string[]; ok: number; color: number; broken: number }
  let data = $state<{ temp: number; runs: { lstm: Snap[]; rnn: Snap[] } } | null>(null)
  let error = $state('')
  let kind = $state<'lstm' | 'rnn'>('lstm')
  let at = $state(0)
  onMount(() => {
    fetch('/data/lstm/samples.json').then((r) => r.json()).then((d) => (data = d)).catch((e) => (error = String(e)))
  })

  const LINE = /^the (\w+) (\w+) (\w+) the (\w+) (\w+)\.$/
  function check(line: string): 'ok' | 'color' | 'broken' {
    const m = LINE.exec(line)
    if (!m) return 'broken'
    const [, c1, a, v, c2, t] = m
    const ok = RULES.colors.includes(c1) && RULES.animals.includes(a) && RULES.verbs.includes(v) && RULES.colors.includes(c2) && RULES.things.includes(t)
    if (!ok) return 'broken'
    return c1 === c2 ? 'ok' : 'color'
  }
  const snaps = $derived(data ? data.runs[kind] : [])
  const snap = $derived(snaps[Math.min(at, snaps.length - 1)])
  const LABEL = { ok: '✓ follows every rule', color: '✗ the two colors differ', broken: '✗ broken' }
  const NAME = { lstm: 'LSTM', rnn: 'plain RNN' }

  const W = 360, H = 172, L = 40, R = 12, TOP = 12, B = 38
  const maxStep = $derived(data ? data.runs.lstm.at(-1)!.step : 1)
  const xticks = $derived([0, 1, 2, 3].map((k) => Math.round((k * maxStep) / 3)))
  const px = (s: number) => L + (s / maxStep) * (W - L - R)
  const py = (v: number) => TOP + (1 - v) * (H - TOP - B)
  const path = (ss: Snap[]) => ss.map((s, k) => `${k ? 'L' : 'M'}${px(s.step).toFixed(1)},${py(s.ok).toFixed(1)}`).join(' ')
  const okAt = (k: 'lstm' | 'rnn') => (data ? data.runs[k][Math.min(at, data.runs[k].length - 1)].ok : 0)
</script>

<LabFrame
  title="The boss run, played back: what each model writes as it trains"
  hint="Drag through training. Each line is checked against the rules as you watch."
  onreset={() => { at = 0; kind = 'lstm' }}
  resetDisabled={at === 0 && kind === 'lstm'}
>
  {#if error}
    <p class="bad">Could not load the samples: {error}</p>
  {:else if !data || !snap}
    <div class="loading">Loading the recorded samples…</div>
  {:else}
    <div class="cap">fraction of 200 sampled lines that follow every rule</div>
    <svg use:readable viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Fraction of lines that follow every rule during training, LSTM and plain RNN">
      {#each [0, 0.5, 1] as v}
        <line x1={L} x2={W - R} y1={py(v)} y2={py(v)} class="grid" />
        <text x={L - 5} y={py(v) + 3.5} class="t" text-anchor="end">{v * 100}%</text>
      {/each}
      {#each xticks as s, k}<text x={px(s)} y={H - B + 14} class="t" text-anchor={k === 0 ? 'start' : k === xticks.length - 1 ? 'end' : 'middle'}>{s.toLocaleString('en-US')}</text>{/each}
      <text x={(L + W - R) / 2} y={H - 5} class="t" text-anchor="middle">training step</text>
      <line x1={L} x2={W - R} y1={py(1 / 6)} y2={py(1 / 6)} class="chance" />
      <text x={W - R - 4} y={py(1 / 6) - 5} class="t" text-anchor="end">chance for the colors: 1 in 6</text>
      <line x1={px(snap.step)} x2={px(snap.step)} y1={TOP} y2={H - B} class="now" />
      <path d={path(data.runs.rnn)} class="line rnn" class:faint={kind !== 'rnn'} />
      <path d={path(data.runs.lstm)} class="line lstm" class:faint={kind !== 'lstm'} />
      <circle cx={px(snap.step)} cy={py(okAt('rnn'))} r="3.5" class="pt rnn" />
      <circle cx={px(snap.step)} cy={py(okAt('lstm'))} r="3.5" class="pt lstm" />
    </svg>

    <div class="cap">{snap.lines.length} lines from the <b>{NAME[kind]}</b> at step {snap.step.toLocaleString('en-US')}</div>
    <ul class="lines">
      {#each snap.lines as line}
        {@const k = check(line)}
        <li class={k}><code>{line || '(empty line)'}</code><span>{LABEL[k]}</span></li>
      {/each}
    </ul>
  {/if}

  {#snippet controls()}
    {#if data}
      <label class="slider"><span>training step <b>{snap?.step.toLocaleString('en-US')}</b></span>
        <input type="range" min="0" max={snaps.length - 1} bind:value={at} aria-label="training step" />
      </label>
      <div class="seg" role="group" aria-label="Show lines from">
        <button type="button" class:on={kind === 'lstm'} aria-pressed={kind === 'lstm'} onclick={() => (kind = 'lstm')}>LSTM</button>
        <button type="button" class:on={kind === 'rnn'} aria-pressed={kind === 'rnn'} onclick={() => (kind = 'rnn')}>plain RNN</button>
      </div>
    {/if}
  {/snippet}

  {#snippet readout()}
    {#if data && snap}
      Of 200 lines sampled at temperature {data.temp}: <b>{(snap.ok * 100).toFixed(0)}%</b> follow every rule,
      {(snap.color * 100).toFixed(0)}% have the right shape but two different colors, {(snap.broken * 100).toFixed(0)}% are broken.
    {:else}
      <span class="idle">Waiting for the recorded run…</span>
    {/if}
  {/snippet}

  {#snippet legend()}
    <span><i class="ln lstm"></i>LSTM</span>
    <span><i class="ln rnn"></i>plain RNN</span>
    <span><i class="ln chance-sw"></i>chance level for the color rule</span>
    <span><i class="ln now-sw"></i>the step you picked</span>
  {/snippet}
</LabFrame>

<style>
  .loading { min-height: 26rem; display: grid; place-items: center; color: var(--dim); font-size: 0.85rem; border: 1px dashed var(--line); border-radius: 6px; }
  .cap { font-size: 0.8rem; color: var(--dim); }
  .cap b { color: var(--fg); }
  .chart { width: 100%; max-width: 34rem; display: block; background: var(--bg); border: 1px solid var(--line); border-radius: 6px; }
  .grid { stroke: var(--line); }
  .chance { stroke: var(--dim); stroke-dasharray: 3 3; }
  .now { stroke: var(--fg); stroke-width: 1; stroke-dasharray: 2 2; }
  .t { fill: var(--dim); font-size: 10px; font-family: var(--mono); }
  .line { fill: none; stroke-width: 2.5; transition: opacity 0.2s; }
  .line.faint { stroke-width: 1.5; opacity: 0.55; }
  .line.lstm, .pt.lstm { stroke: var(--cat-1); }
  .line.rnn, .pt.rnn { stroke: var(--cat-3); }
  .pt { fill: var(--bg); stroke-width: 2; }
  .lines { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.2rem; }
  .lines li { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 0.1rem 0.8rem; font-size: 0.82rem; border-left: 3px solid var(--line); padding: 0.15rem 0.5rem; }
  .lines li code { background: none; padding: 0; overflow-wrap: anywhere; min-width: 0; }
  .lines li span { font-size: 0.78rem; }
  .lines li.ok { border-color: var(--ok); }
  .lines li.ok span { color: var(--ok); }
  .lines li.color, .lines li.broken { border-color: var(--warn); }
  .lines li.color span, .lines li.broken span { color: var(--warn); }
  .slider { display: grid; gap: 0.1rem; flex: 1 1 16rem; font-size: 0.85rem; color: var(--dim); }
  .slider b { font-family: var(--mono); color: var(--fg); }
  .slider input { width: 100%; min-height: 2rem; accent-color: var(--accent); }
  .seg { display: inline-flex; border: 1px solid var(--field); border-radius: 6px; overflow: hidden; }
  .seg button { font: inherit; font-size: 0.85rem; min-height: 2.1rem; padding: 0.2rem 0.8rem; border: 0; background: var(--bg); color: var(--fg); cursor: pointer; }
  .seg button + button { border-left: 1px solid var(--field); }
  .seg button.on { color: var(--accent); background: var(--highlight); }
  .seg button:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
  @media (max-width: 760px) { .slider input, .seg button { min-height: 2.5rem; } }
  .ln { display: inline-block; width: 1rem; height: 0; border-top: 2.5px solid; vertical-align: middle; margin-right: 0.35rem; }
  .ln.lstm { border-color: var(--cat-1); }
  .ln.rnn { border-color: var(--cat-3); }
  .ln.chance-sw { border-top: 1.5px dashed var(--dim); }
  .ln.now-sw { border-top: 1.5px dotted var(--fg); }
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
  .bad { color: var(--warn); margin: 0; }
  @media (prefers-reduced-motion: reduce) { .line { transition: none; } }
</style>
