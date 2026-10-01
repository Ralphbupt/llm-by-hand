<script lang="ts">
  /**
   * A recurrent network whose hidden state h is one number, unrolled step by step:
   * h_t = act(w_x·x_t + w_h·h_(t−1) + b). The same three weights at every step.
   * hide: steps whose h stays "?" until a question is answered.
   */
  import { onMount } from 'svelte'
  import { rnnScalar } from '@lib/classic'
  import { has, subscribe } from '@lib/progress'
  import { readable } from '@lib/readable'
  import LabFrame from './LabFrame.svelte'

  let { hide = [] }: { hide?: { id: string; t: number }[] } = $props()
  let solved = $state<Record<string, boolean>>({})
  onMount(() => {
    const sync = () => (solved = Object.fromEntries(hide.map((h) => [h.id, has(h.id)])))
    sync()
    return subscribe(sync)
  })
  const masked = (t: number) => hide.some((h) => h.t === t && !solved[h.id])

  const X0 = [1, 0, 0, 0]
  let xs = $state([...X0])
  let wx = $state(1)
  let wh = $state(0.5)
  let b = $state(0)
  let shown = $state(1)

  const hs = $derived(rnnScalar(xs, wx, wh, b))
  const zs = $derived(xs.map((x, t) => wx * x + wh * (t ? hs[t - 1] : 0) + b))
  const changed = $derived(JSON.stringify(xs) !== JSON.stringify(X0) || wx !== 1 || wh !== 0.5 || b !== 0)
  function resetAll() {
    xs = [...X0]
    wx = 1
    wh = 0.5
    b = 0
    shown = 1
  }
  const f4 = (v: number) => v.toFixed(4)
  const bar = (v: number) => `${Math.min(100, Math.abs(v) * 100)}%`
</script>

<LabFrame
  title="A recurrent network, one step at a time"
  hint="Press Next step. Change the weights or the inputs x and watch h change at every step."
  onreset={resetAll}
  resetDisabled={!changed && shown === 1}
>
  <!-- the unrolled chain: one node per step, the same w_x and w_h on every arrow -->
  <svg use:readable viewBox="0 0 {40 + 110 * xs.length} 150" class="chain" role="img" aria-label="The network unrolled over time: each step reads x and the previous h">
    <text x="4" y="64" class="lbl">h₀=0</text>
    {#each xs as x, t}
      {@const cx = 90 + 110 * t}
      {@const on = t < shown}
      {@const hid = masked(t + 1)}
      <!-- arrow from the previous hidden state -->
      <line x1={t === 0 ? 44 : cx - 88} y1="60" x2={cx - 25} y2="60" class="arrow" class:off={!on} />
      <path d="M{cx - 31},55 L{cx - 24},60 L{cx - 31},65" class="head" class:off={!on} />
      {#if t > 0}<text x={cx - 56} y="52" class="w" text-anchor="middle">× w_h</text>{/if}
      <!-- arrow from the input -->
      <line x1={cx} y1="110" x2={cx} y2="85" class="arrow" class:off={!on} />
      <path d="M{cx - 5},91 L{cx},84 L{cx + 5},91" class="head" class:off={!on} />
      <text x={cx + 8} y="102" class="w">× w_x</text>
      <rect x={cx - 22} y="112" width="44" height="24" rx="5" class="xbox" />
      <text x={cx} y="128" class="v" text-anchor="middle">x={x}</text>
      <!-- the hidden-state node, shaded by its value and sign -->
      <circle {cx} cy="60" r="24" class="node" class:off={!on}
        style={on && !hid ? `fill: color-mix(in srgb, var(${hs[t] < 0 ? '--neg' : '--pos'}) ${Math.round(Math.min(1, Math.abs(hs[t])) * 70)}%, var(--card))` : ''} />
      <text x={cx} y="56" class="lbl" text-anchor="middle">h{t + 1}</text>
      <text x={cx} y="71" class="v" class:q={on && hid} text-anchor="middle">{!on ? '…' : hid ? '?' : hs[t].toFixed(2)}</text>
    {/each}
  </svg>

  <p class="cap mono">z = w_x·x_t + w_h·h_(t−1) + b, then h_t = tanh(z)</p>
  <div class="scroll">
    <table>
      <thead><tr><th>t</th><th>x_t</th><th>z</th><th>h_t</th><th>size of h</th></tr></thead>
      <tbody>
        {#each xs as x, t}
          <tr class:off={t >= shown}>
            <td>{t + 1}</td>
            <td>
              <input class="num" type="number" step="0.5" value={x} aria-label={`input x at step ${t + 1}`}
                onchange={(e) => { const n = [...xs]; n[t] = Number(e.currentTarget.value) || 0; xs = n }} />
            </td>
            {#if t < shown}
              <td class="mono z">{wx.toFixed(2)}×{x} + {wh.toFixed(2)}×{masked(t) ? '?' : f4(t ? hs[t - 1] : 0)} + {b.toFixed(2)} = {masked(t) ? '?' : f4(zs[t])}</td>
              <td class="mono strong" class:q={masked(t + 1)}>{masked(t + 1) ? '?' : f4(hs[t])}</td>
              <td><span class="bar" class:neg={hs[t] < 0} style="width:{masked(t + 1) ? '0%' : bar(hs[t])}"></span></td>
            {:else}
              <td class="dim">…</td><td class="dim">…</td><td></td>
            {/if}
          </tr>
        {/each}
      </tbody>
    </table>
  </div>

  {#snippet controls()}
    <button class="lab-btn primary" onclick={() => (shown = Math.min(xs.length, shown + 1))} disabled={shown >= xs.length}>Next step</button>
    <button class="lab-btn" onclick={() => (shown = xs.length)} disabled={shown >= xs.length}>All steps</button>
    <span class="knobs">
      <label>w_x <b>{wx.toFixed(2)}</b> <input type="range" min="-2" max="2" step="0.05" bind:value={wx} aria-label="w_x" /></label>
      <label>w_h <b>{wh.toFixed(2)}</b> <input type="range" min="-2" max="2" step="0.05" bind:value={wh} aria-label="w_h" /></label>
      <label>b <b>{b.toFixed(2)}</b> <input type="range" min="-1" max="1" step="0.05" bind:value={b} aria-label="b" /></label>
    </span>
  {/snippet}

  {#snippet readout()}
    step {shown} of {xs.length}: h{shown} = {masked(shown) ? '?' : f4(hs[shown - 1])}. The same w_x, w_h and b are used at every step; only h carries anything forward.
  {/snippet}

  {#snippet legend()}
    <span><i class="sw pos"></i>h above 0</span>
    <span><i class="sw neg"></i>h below 0</span>
    <span>deeper color: bigger |h|</span>
  {/snippet}
</LabFrame>

<style>
  .chain { width: 100%; max-width: 36rem; display: block; background: var(--bg); border: 1px solid var(--line); border-radius: 6px; }
  .chain .arrow { stroke: var(--fg); stroke-width: 1.5; }
  .chain .head { fill: none; stroke: var(--fg); stroke-width: 1.5; }
  .chain .off { opacity: 0.25; }
  .chain .node { fill: var(--card); stroke: var(--fg); stroke-width: 1.5; transition: fill 0.2s; }
  .chain .node.off { stroke-dasharray: 3 3; }
  .chain .xbox { fill: var(--card); stroke: var(--line); }
  .chain .lbl { font-size: 11px; fill: var(--dim); font-family: var(--mono); }
  .chain .v { font-size: 12px; fill: var(--fg); font-family: var(--mono); font-weight: 700; }
  .chain .v.q { fill: var(--warn); }
  .chain .w { font-size: 11px; fill: var(--dim); font-family: var(--mono); }
  @media (prefers-reduced-motion: reduce) { .chain .node { transition: none; } }
  .knobs { display: inline-flex; flex-wrap: wrap; gap: 0.4rem 1rem; font-size: 0.85rem; font-family: var(--mono); color: var(--dim); }
  .knobs label { display: grid; grid-template-columns: 2.2rem 2.9rem 6.5rem; align-items: center; gap: 0.35rem; }
  .knobs b { color: var(--fg); font-weight: 600; min-width: 2.6rem; }
  .knobs input { width: 6.5rem; min-height: 2rem; accent-color: var(--accent); }
  .scroll { overflow-x: auto; margin-top: 0.4rem; }
  .cap { margin: 0.7rem 0 0; font-size: 0.8rem; color: var(--dim); }
  td.z { font-size: 0.74rem; white-space: normal; word-break: break-word; }
  table { border-collapse: collapse; font-size: 0.82rem; width: 100%; }
  th, td { border: 1px solid var(--line); padding: 0.3rem 0.45rem; text-align: left; }
  th { color: var(--dim); font-weight: 400; font-size: 0.76rem; }
  tr.off td { opacity: 0.6; }
  .mono { font-family: var(--mono); }
  .strong { font-weight: 700; }
  .q { color: var(--warn); }
  .num { width: 2.8rem; min-height: 2rem; font: inherit; font-family: var(--mono); background: var(--bg); color: var(--fg); border: 1px solid var(--field); border-radius: 3px; }
  .bar { display: block; height: 0.6rem; background: var(--pos); border-radius: 2px; }
  .bar.neg { background: var(--neg); }
  .sw { display: inline-block; width: 0.8rem; height: 0.8rem; border-radius: 2px; vertical-align: -0.1em; margin-right: 0.3rem; }
  .sw.pos { background: var(--pos); }
  .sw.neg { background: var(--neg); }
  .dim { color: var(--dim); }
</style>
