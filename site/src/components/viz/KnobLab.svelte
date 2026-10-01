<script lang="ts">
  /**
   * Attention is learned. Two words, apple = [1, 0] and sweet = [0, 1].
   * Only one number in W_Q can change: c. Sweet's query is [c, 0], so c is the volume of "sweet → apple".
   * The target: sweet's output should be apple's content, [1, 0]. Gradient descent turns the knob.
   */
  import Heatmap from './Heatmap.svelte'
  import LabFrame from './LabFrame.svelte'
  import { readable } from '@lib/readable'
  import { onMount } from 'svelte'
  import { has, subscribe } from '@lib/progress'

  // A value that a question on the page asks for stays "?" until that question is solved.
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


  const LR = 1
  const s2 = Math.SQRT2
  let c = $state(0)
  let step = $state(0)
  let history = $state<number[]>([0.5])
  let cs = $state<number[]>([0]) // where c has been, for the trail on the loss curve

  // softmax of [c/√2, 0] is a sigmoid; output = [p, 1 - p]; loss = (p - 1)² + (1 - p)² = 2(1 - p)²
  const P = (c: number) => 1 / (1 + Math.exp(-c / s2))
  const lossAt = (c: number) => 2 * (1 - P(c)) ** 2
  const gradAt = (c: number) => { const p = P(c); return (-4 * (1 - p) * p * (1 - p)) / s2 }

  const p = $derived(P(c))
  const loss = $derived(lossAt(c))
  const grad = $derived(gradAt(c))
  const weights = $derived([[0.5, 0.5], [p, 1 - p]])

  function train(n: number) {
    let x = c
    const h = [...history]
    for (let k = 0; k < n; k++) { x -= LR * gradAt(x); h.push(lossAt(x)) }
    const t = [...cs]
    let y = c
    for (let k = 0; k < n; k++) { y -= LR * gradAt(y); if (n <= 10 || k % Math.ceil(n / 20) === 0) t.push(y) }
    t.push(x)
    c = x; step += n; history = h.slice(-400); cs = t.slice(-60)
  }
  function reset() { c = 0; step = 0; history = [0.5]; cs = [0]; farthest = 0 }
  function setC(v: number) { c = v; history = [...history, lossAt(v)].slice(-400); cs = [v] }

  // the loss as a function of the knob: a slope that flattens out but never reaches 0
  const W = 300, H = 150, PADL = 30, PADB = 26
  const C0 = -3, C1 = 8, L1 = 1.6
  const px = (v: number) => PADL + ((v - C0) / (C1 - C0)) * (W - PADL - 6)
  const py = (l: number) => (H - PADB) - (l / L1) * (H - PADB - 8)
  // until the "does it ever stop?" guess is made, the curve is only drawn as far as c has been
  let farthest = $state(0)
  $effect(() => { if (c > farthest) farthest = c })
  const landTo = $derived(locked('forever') ? Math.min(C1, Math.max(0.5, farthest + 0.5)) : C1)
  const land = $derived(Array.from({ length: 111 }, (_, k) => C0 + (k / 110) * (C1 - C0)).filter((v) => v <= landTo)
    .map((v, k) => `${k ? 'L' : 'M'}${px(v).toFixed(1)},${py(lossAt(v)).toFixed(1)}`).join(' '))
  // tangent at the current c: its slope is d loss / d c
  const tan = $derived.by(() => {
    const dx = 1.2
    return { x1: px(c - dx), y1: py(loss - grad * dx), x2: px(c + dx), y2: py(loss + grad * dx) }
  })
  const f = (v: number, d = 3) => v.toFixed(d)
  const sgn = (v: number, d: number) => (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(d)
</script>

<LabFrame
  title="Attention is learned: gradient descent changes one number, c, in W_Q"
  hint="Press a step button and let training change c, or set c yourself with the slider."
  onreset={reset}
  resetDisabled={step === 0 && c === 0}
>
  <div class="grid">
    <div class="col">
      <div class="pair">
        <div class="wq">
          <div class="label">W_Q</div>
          <table><tbody><tr><td>0</td><td>0</td></tr><tr><td class="knob">c = {f(c, 2)}</td><td>0</td></tr></tbody></table>
        </div>
        <Heatmap value={weights} label="weights (who looks at whom)" rowLabels={['apple', 'sweet']} colLabels={['apple', 'sweet']} hiRows={[1]} hiCols={[0]} masked={locked('start') ? [{ i: 1, j: 0 }, { i: 1, j: 1 }] : []} />
      </div>
      <dl>
        <div><dt>steps</dt><dd>{step}</dd></div>
        <div><dt>sweet’s query</dt><dd>[{f(c, 2)}, 0]</dd></div>
        <div><dt>sweet’s output</dt><dd>{locked('start') ? '[?, ?]' : `[${f(p)}, ${f(1 - p)}]`}</dd></div>
        <div><dt>target</dt><dd class="target">[1, 0]</dd></div>
        <div><dt>loss</dt><dd>{f(loss, 5)}</dd></div>
        <div><dt>d loss / d c</dt><dd class="g">{f(grad, 4)}</dd></div>
      </dl>
    </div>

    <div class="col">
      <div class="label">loss for every value of the number c</div>
      <svg viewBox="0 0 {W} {H}" use:readable role="img" aria-label="The loss as a function of c: it falls toward 0 as c grows but never reaches it. The ball is the current c.">
        <line x1={PADL} y1={py(0)} x2={W - 4} y2={py(0)} class="axis" />
        <line x1={PADL} y1={py(0)} x2={PADL} y2={4} class="axis" />
        {#each [0, 0.5, 1, 1.5] as l}<text x={PADL - 4} y={py(l) + 3} class="tk end">{l}</text>{/each}
        {#each [-2, 0, 2, 4, 6, 8] as v}<text x={px(v)} y={H - 10} class="tk mid">{v}</text>{/each}
        <text x={W - 4} y={py(0) - 6} class="tk end">c →</text>
        <text x={PADL + 4} y="10" class="tk">loss</text>
        <path d={land} class="land" />
        <line x1={px(C0)} y1={py(0)} x2={px(C1)} y2={py(0)} class="zero" />
        {#each cs.slice(0, -1) as v}<circle cx={px(v)} cy={py(lossAt(v))} r="2" class="trail" />{/each}
        {#if Math.abs(grad) > 1e-4}<line {...tan} class="tan" />{/if}
        <circle cx={px(Math.min(C1, Math.max(C0, c)))} cy={py(loss)} r="5" class="ball" />
      </svg>
      <p class="cap">{#if locked('forever')}The curve appears as far as the ball has gone.{:else}Training rolls the ball right; the curve keeps flattening, so the steps keep shrinking.{/if}</p>
      {#if !locked('forever')}<p class="cap">The gradient is negative, so each step makes c larger. It never stops: the weight only reaches 1 when c is infinite.</p>{/if}
    </div>
  </div>

  {#snippet controls()}
    <button type="button" class="lab-btn primary" onclick={() => train(1)}>1 step</button>
    <button type="button" class="lab-btn" onclick={() => train(10)}>10 steps</button>
    <button type="button" class="lab-btn" onclick={() => train(200)}>200 steps</button>
    <label class="slider">
      <span>set c yourself</span>
      <input type="range" min="-3" max="8" step="0.01" value={c} oninput={(e) => setC(Number(e.currentTarget.value))} aria-label="the number c" />
    </label>
  {/snippet}

  {#snippet readout()}
    c = {f(c, 2)} · loss {f(loss, 5)} · slope <span class="g">{f(grad, 4)}</span>, so the next step moves c by {sgn(-LR * grad, 4)}
  {/snippet}

  {#snippet legend()}
    <span class="key"><i class="dot"></i>the current c (a step moves it)</span>
    <span class="key"><i class="ln tan-sw"></i>its slope, d loss / d c (the gradient)</span>
    <span class="key"><i class="ln zero-sw"></i>loss 0: the target, never quite reached</span>
  {/snippet}
</LabFrame>

<style>
  .grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.15fr); gap: 1.4rem; align-items: start; }
  .col { display: flex; flex-direction: column; gap: 0.7rem; min-width: 0; }
  .pair { display: flex; flex-wrap: wrap; gap: 0.8rem 1.2rem; align-items: flex-start; }
  .label { font-size: 0.78rem; color: var(--dim); font-family: var(--mono); margin-bottom: 0.2rem; }
  table { border-collapse: collapse; font-family: var(--mono); font-size: 0.85rem; width: auto; }
  td { border: 1px solid var(--line); padding: 0.3rem 0.6rem; text-align: right; }
  td.knob { color: var(--accent); font-weight: 700; box-shadow: inset 0 0 0 1px var(--accent); }
  dl { margin: 0; display: grid; grid-template-columns: auto 1fr; gap: 0.2rem 0.9rem; font-size: 0.85rem; }
  dl div { display: contents; }
  dt { color: var(--dim); }
  dd { margin: 0; font-family: var(--mono); font-variant-numeric: tabular-nums; }
  dd.target { color: var(--ok); }
  .g { color: var(--grad); }
  svg { width: 100%; height: auto; display: block; border: 1px solid var(--line); border-radius: 6px; background: var(--bg); }
  .axis { stroke: var(--dim); stroke-width: 0.8; }
  .zero { stroke: var(--ok); stroke-width: 1.2; stroke-dasharray: 4 3; }
  .land { fill: none; stroke: var(--fg); stroke-width: 1.6; opacity: 0.8; }
  .trail { fill: var(--accent); opacity: 0.35; }
  .tan { stroke: var(--grad); stroke-width: 1.4; stroke-dasharray: 4 2.5; }
  .ball { fill: var(--accent); stroke: var(--bg); stroke-width: 1.5; transition: cx 0.2s ease-out, cy 0.2s ease-out; }
  .tk { font-size: 10px; fill: var(--dim); font-family: var(--mono); }
  .tk.end { text-anchor: end; }
  .tk.mid { text-anchor: middle; }
  .cap { margin: 0; font-size: 0.8rem; color: var(--dim); line-height: 1.5; }
  .slider { display: inline-flex; align-items: center; gap: 0.5rem; font-size: 0.82rem; color: var(--dim); flex: 1 1 12rem; min-height: 2.5rem; }
  .slider input { flex: 1; min-width: 6rem; accent-color: var(--accent); }
  .key { display: inline-flex; align-items: center; gap: 0.4rem; }
  .key .dot { width: 0.7rem; height: 0.7rem; border-radius: 50%; background: var(--accent); }
  .key .ln { width: 1.1rem; height: 0; border-top: 2px dashed; }
  .tan-sw { border-color: var(--grad); }
  .zero-sw { border-color: var(--ok); }
  @media (prefers-reduced-motion: reduce) { .ball { transition: none; } }
  @media (max-width: 720px) { .grid { grid-template-columns: minmax(0, 1fr); } .slider { flex-basis: 100%; } }
</style>
