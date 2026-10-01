<script lang="ts">
  /**
   * Gradients pile up: one parameter w, one example x = 2, y = 6, loss = (w·x − y)².
   * Buttons mimic PyTorch: backward() ADDS to w.grad, step() moves w, zero_grad() clears w.grad.
   */
  import LabFrame from './LabFrame.svelte'
  import { readable } from '@lib/readable'

  const X = 2, Y = 6, LR = 0.05, W0 = 1
  let w = $state(W0)
  let grad = $state(0)
  let hist = $state<number[]>([W0])
  let log = $state<string[]>([])

  const loss = $derived((w * X - Y) ** 2)
  const thisGrad = $derived(2 * (w * X - Y) * X)
  const f = (v: number) => (Math.abs(v) < 1e-9 ? '0' : Number.isInteger(v) ? String(v) : v.toFixed(3))

  function say(s: string) { log = [...log.slice(-5), s] }
  function backward() {
    const g = thisGrad
    grad += g
    say(`loss.backward(): adds ${f(g)} → w.grad = ${f(grad)}`)
  }
  function step() {
    const before = w
    w = w - LR * grad
    hist = [...hist, w]
    say(`opt.step(): w = ${f(before)} − ${LR} × ${f(grad)} = ${f(w)}`)
  }
  function zero() { grad = 0; say('opt.zero_grad(): w.grad = 0') }
  function train(n: number, clear: boolean) {
    for (let i = 0; i < n; i++) {
      if (clear) grad = 0
      grad += 2 * (w * X - Y) * X
      w = w - LR * grad
      hist = [...hist, w]
    }
    say(`${n} steps ${clear ? 'with' : 'WITHOUT'} zero_grad → w = ${f(w)}`)
  }
  function reset() { w = W0; grad = 0; hist = [W0]; log = [] }

  // chart of w over steps; the best w is 3
  const GMAX = 64 // bar scale: four backward calls at the start (4 × 16)
  const Wd = 300, Hd = 120, WMAX = 6, WMIN = -1
  const sx = (i: number, n: number) => (n <= 1 ? 0 : (i / (n - 1)) * Wd)
  const sy = (v: number) => Hd - ((Math.max(WMIN, Math.min(WMAX, v)) - WMIN) / (WMAX - WMIN)) * Hd
  const path = $derived(hist.map((v, i) => `${sx(i, Math.max(hist.length, 2)).toFixed(1)},${sy(v).toFixed(1)}`).join(' '))
</script>

<LabFrame
  title="Gradients are added together until you clear them"
  hint="Press the three calls in order, then press 1 twice in a row and see w.grad grow."
  onreset={reset}
  resetDisabled={hist.length === 1 && grad === 0 && log.length === 0}
>
  <p class="setup">w = <b>{f(w)}</b> · x = 2 · y = 6 · loss = (w·x − y)² = <b>{f(loss)}</b> · lr = {LR}</p>
  <div class="cols">
    <div class="left">
      <div class="state">
        <div><span class="k">gradient of this loss</span><span class="v">{f(thisGrad)}</span></div>
        <div><span class="k">w.grad (what step() uses)</span><span class="v g">{f(grad)}</span></div>
      </div>
      <!-- the pile: w.grad as a bar, next to one backward's worth, so piling up is visible -->
      <div class="pile" aria-hidden="true">
        <div class="pr"><span class="k">one backward</span><span class="track"><i class="one" style="width:{Math.min(100, (Math.abs(thisGrad) / GMAX) * 100)}%"></i></span></div>
        <div class="pr"><span class="k">w.grad</span><span class="track"><i class="acc" style="width:{Math.min(100, (Math.abs(grad) / GMAX) * 100)}%"></i>{#if Math.abs(grad) > GMAX}<b class="over">too large to draw →</b>{/if}</span></div>
      </div>
      {#if log.length}<ol class="log">{#each log as l}<li>{l}</li>{/each}</ol>{/if}
    </div>
    <svg viewBox="-26 -12 336 156" class="plot" use:readable aria-label="w after each step">
      <line x1="0" y1={Hd} x2={Wd} y2={Hd} class="axis" />
      <line x1="0" y1="0" x2="0" y2={Hd} class="axis" />
      <line x1="0" y1={sy(3)} x2={Wd} y2={sy(3)} class="best" />
      <text x={Wd} y={sy(3) - 3} class="tick ok" text-anchor="end">best w = 3</text>
      {#each [0, 2, 4, 6] as v}
        <line x1="0" x2={Wd} y1={sy(v)} y2={sy(v)} class="grid" />
        <text x="-6" y={sy(v) + 3.5} class="tick" text-anchor="end">{v}</text>
      {/each}
      <text x="-24" y="-3" class="tick name">w</text>
      <polyline points={path} class="curve" />
      {#each hist as v, i}<circle cx={sx(i, Math.max(hist.length, 2))} cy={sy(v)} r="2.2" class="dot" />{/each}
      <text x={Wd / 2} y={Hd + 16} class="tick" text-anchor="middle">step() calls → ({hist.length - 1} so far)</text>
    </svg>
  </div>

  {#snippet controls()}
    <div class="api" role="group" aria-label="PyTorch calls">
      <button class="lab-btn code" onclick={backward}><span class="n">1</span>loss.backward()</button>
      <button class="lab-btn code" onclick={step}><span class="n">2</span>opt.step()</button>
      <button class="lab-btn code" onclick={zero}><span class="n">3</span>opt.zero_grad()</button>
    </div>
    <div class="demo" role="group" aria-label="Shortcuts">
      <span class="lbl">or run 10 steps:</span>
      <button class="lab-btn small" onclick={() => train(10, true)}>10 steps with zero_grad</button>
      <button class="lab-btn small" onclick={() => train(10, false)}>10 steps without</button>
    </div>
  {/snippet}

  {#snippet readout()}
    {#if log.length}{log.at(-1)}{:else}<span class="idle">w.grad starts at 0. Press 1, 2, 3 for one clean training step.</span>{/if}
  {/snippet}

  {#snippet legend()}
    <span><i class="sw gr"></i>w.grad, the sum step() uses</span>
    <span><i class="sw gr1"></i>the gradient of one backward</span>
    <span><i class="sw wln"></i>w after each step</span>
    <span><i class="sw okd"></i>best w = 3</span>
  {/snippet}
</LabFrame>

<style>
  .setup { font-family: var(--mono); font-size: 0.85rem; margin: 0 0 0.7rem; overflow-wrap: anywhere; }
  .cols { display: flex; flex-wrap: wrap; gap: 1rem 1.4rem; align-items: flex-start; }
  .left { flex: 1 1 260px; min-width: 0; }
  .state { display: grid; gap: 0.2rem; font-family: var(--mono); font-size: 0.85rem; }
  .state div { display: flex; justify-content: space-between; gap: 1rem; border-bottom: 1px dashed var(--line); padding: 0.1rem 0; }
  .k { color: var(--dim); }
  .v { font-variant-numeric: tabular-nums; }
  .v.g { color: var(--grad); font-weight: 700; }
  .pile { display: grid; gap: 0.3rem; margin-top: 0.7rem; font-family: var(--mono); font-size: 0.78rem; }
  .pr { display: grid; grid-template-columns: 7rem minmax(0, 1fr); gap: 0.5rem; align-items: center; }
  .track { position: relative; height: 0.8rem; background: var(--bg); border: 1px solid var(--line); border-radius: 3px; overflow: hidden; }
  .track i { position: absolute; inset: 0 auto 0 0; transition: width 0.25s; }
  .track i.one { background: var(--grad); opacity: 0.4; }
  .track i.acc { background: var(--grad); }
  .over { position: absolute; right: 0.3rem; top: 50%; transform: translateY(-50%); font-size: 0.72rem; line-height: 1; color: var(--on-solid); }
  @media (prefers-reduced-motion: reduce) { .track i { transition: none; } }
  .log { margin: 0.7rem 0 0; padding-left: 1.4rem; font-family: var(--mono); font-size: 0.76rem; color: var(--dim); display: grid; gap: 0.1rem; overflow-wrap: anywhere; }
  .plot { width: 100%; max-width: 380px; flex: 1 1 280px; margin: 0 auto; overflow: visible; }
  .axis { stroke: var(--dim); stroke-width: 0.8; }
  .best { stroke: var(--ok); stroke-dasharray: 4 3; stroke-width: 1; }
  .tick { font-size: 10px; fill: var(--dim); font-family: var(--mono); }
  .tick.ok { fill: var(--ok); }
  .tick.name { fill: var(--fg); font-style: italic; }
  .grid { stroke: var(--line); stroke-width: 0.5; }
  .curve { fill: none; stroke: var(--accent); stroke-width: 1.5; }
  .dot { fill: var(--accent); }
  .api, .demo { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }
  .demo { flex-basis: 100%; }
  .code { font-family: var(--mono); font-size: 0.85rem; display: inline-flex; align-items: center; gap: 0.45rem; }
  .n { display: inline-grid; place-items: center; width: 1.25rem; height: 1.25rem; border-radius: 50%; background: var(--accent); color: var(--on-solid);
    font-family: system-ui, -apple-system, sans-serif; font-size: 0.72rem; font-weight: 700; }
  .lbl { font-size: 0.82rem; color: var(--dim); }
  .small { font-size: 0.82rem; }
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
  .sw { display: inline-block; width: 0.9rem; height: 0.6rem; border-radius: 2px; margin-right: 0.35rem; vertical-align: -0.02rem; }
  .sw.gr { background: var(--grad); }
  .sw.gr1 { background: var(--grad); opacity: 0.4; }
  .sw.wln { height: 0; border-top: 2px solid var(--accent); border-radius: 0; vertical-align: 0.2rem; }
  .sw.okd { height: 0; border-top: 2px dashed var(--ok); border-radius: 0; vertical-align: 0.2rem; }
</style>
