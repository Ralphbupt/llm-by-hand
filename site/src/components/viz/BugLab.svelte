<script lang="ts">
  /**
   * Bug lab: fit y = w·x + b to (1, 3), (2, 3), (3, 7), (4, 7) from w = 0.5, b = 0, in 32-bit floats,
   * with switchable bugs: a broadcast shape bug, a forgotten zero_grad, and the learning rate.
   * Every operation is rounded to float32 (Math.fround), so inf and NaN appear where PyTorch would show them.
   */
  import { readable } from '@lib/readable'
  import LabFrame from './LabFrame.svelte'

  const X = [1, 2, 3, 4], Y = [3, 3, 7, 7]
  const LRS = [0.001, 0.01, 0.05, 0.2]
  const r = Math.fround
  let lr = $state(0.05)
  let shapeBug = $state(false)
  let noZero = $state(false)

  type S = { w: number; b: number; gw: number; gb: number }
  let st = $state<S>({ w: 0.5, b: 0, gw: 0, gb: 0 })
  let losses = $state<number[]>([])

  function restart() { st = { w: 0.5, b: 0, gw: 0, gb: 0 }; losses = [] }
  function reset() { lr = 0.05; shapeBug = false; noZero = false; restart() }
  const mean = (a: number[]) => { let s = 0; for (const v of a) s = r(s + v); return r(s / a.length) }

  function step(n: number) {
    let { w, b, gw: aw, gb: ab } = st
    const L = [...losses]
    const lr32 = r(lr)
    for (let k = 0; k < n && L.length < 2000; k++) {
      let errs: number[] = [], xs: number[] = []
      if (shapeBug) {
        for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) { errs.push(r(r(r(w * X[i]) + b) - Y[j])); xs.push(X[i]) }
      } else {
        for (let i = 0; i < 4; i++) { errs.push(r(r(r(w * X[i]) + b) - Y[i])); xs.push(X[i]) }
      }
      L.push(mean(errs.map((e) => r(e * e))))
      let gw = mean(errs.map((e, i) => r(r(2 * e) * xs[i])))
      let gb = mean(errs.map((e) => r(2 * e)))
      if (noZero) { aw = r(aw + gw); ab = r(ab + gb); gw = aw; gb = ab }
      w = r(w - r(lr32 * gw)); b = r(b - r(lr32 * gb))
    }
    st = { w, b, gw: aw, gb: ab }
    losses = L
  }

  let firstInf = $derived(losses.findIndex((l) => !Number.isFinite(l)))
  let firstNan = $derived(losses.findIndex((l) => Number.isNaN(l)))
  let last = $derived(losses.at(-1))
  let changed = $derived(lr !== 0.05 || shapeBug || noZero || losses.length > 0)
  const fmt = (v: number) => (Number.isNaN(v) ? 'NaN' : !Number.isFinite(v) ? (v > 0 ? 'inf' : '−inf') : Math.abs(v) >= 1e5 ? v.toExponential(1) : String(Number(v.toFixed(3))))

  // ---- data plot: x 0..5, y −2..10
  const dx = (x: number) => 8 + (x / 5) * 88
  const dy = (y: number) => 56 - ((y + 2) / 12) * 52
  const clampY = (v: number) => Math.max(-2.5, Math.min(10.5, v))
  let lineOk = $derived(Number.isFinite(st.w) && Number.isFinite(st.b))

  // ---- loss plot: log10(loss) from −1 to 6, step 0..N
  let N = $derived(Math.max(50, losses.length))
  const lx = (i: number) => 10 + (i / Math.max(1, N - 1)) * 86
  const ly = (l: number) => 50 - ((Math.max(-1, Math.min(6, Math.log10(l))) + 1) / 7) * 44
  let curve = $derived(losses.map((l, i) => (Number.isFinite(l) ? `${lx(i)},${ly(l)}` : '')).filter(Boolean).join(' '))
</script>

<LabFrame
  title="Four points, one line, and some bugs"
  hint="Pick a learning rate, switch a bug on or off, then train. Changing a setting starts again from w = 0.5, b = 0."
  onreset={reset}
  resetDisabled={!changed}
>
  <div class="panes">
    <figure>
      <svg viewBox="0 0 100 62" use:readable aria-label="The four points, the best line and your line">
        {#each [0, 4, 8] as gy}
          <line x1="8" x2="96" y1={dy(gy)} y2={dy(gy)} class="grid" />
          <text x="6" y={dy(gy) + 1.2} class="tick end">{gy}</text>
        {/each}
        <line x1={dx(0)} x2={dx(5)} y1={dy(1)} y2={dy(9)} class="best" />
        {#if lineOk}
          <line x1={dx(0)} x2={dx(5)} y1={dy(clampY(st.b))} y2={dy(clampY(st.w * 5 + st.b))} class="fit" />
        {/if}
        {#each X as x, i}
          <circle cx={dx(x)} cy={dy(Y[i])} r="1.8" class="pt" />
          <text x={dx(x)} y="61" class="tick mid">x={x}</text>
        {/each}
      </svg>
      <figcaption>The 4 points, your line, and the best line (w = 1.6, b = 1).</figcaption>
    </figure>
    <figure>
      <svg viewBox="0 0 100 60" use:readable aria-label="Loss after each step, on a log scale">
        {#each [-1, 0, 2, 4, 6] as e}
          <line x1="10" x2="96" y1={ly(10 ** e)} y2={ly(10 ** e)} class="grid" />
          <text x="8" y={ly(10 ** e) + 1.2} class="tick end">{e === -1 ? '0.1' : e === 0 ? '1' : `1e${e}`}</text>
        {/each}
        <line x1="10" x2="96" y1={ly(0.8)} y2={ly(0.8)} class="floor" />
        {#if curve}<polyline points={curve} class="line" />{/if}
        {#if firstInf >= 0}
          <line x1={lx(firstInf)} x2={lx(firstInf)} y1="4" y2="50" class="bad" />
          <text x={lx(firstInf) - 1} y="8" class="tick end badt">inf</text>
        {/if}
        {#if firstNan >= 0}
          <line x1={lx(firstNan)} x2={lx(firstNan)} y1="4" y2="50" class="bad" />
          <text x={lx(firstNan) + 1} y="8" class="tick badt">NaN</text>
        {/if}
        {#if !losses.length}<text x="53" y="28" class="tick mid">train to draw the loss</text>{/if}
        <text x="10" y="58" class="tick">step 0</text>
        <text x="96" y="58" class="tick end">step {N - 1}</text>
      </svg>
      <figcaption>Loss after each step, log scale. Dashed: the best possible loss, 0.8.</figcaption>
    </figure>
  </div>

  {#snippet controls()}
    <button class="lab-btn primary" onclick={() => step(200)}>Train 200 steps</button>
    <button class="lab-btn" onclick={() => step(10)}>10 steps</button>
    <span class="knob" role="group" aria-label="learning rate">learning rate
      {#each LRS as v}
        <button class="lab-btn seg" class:on={lr === v} aria-pressed={lr === v} onclick={() => { lr = v; restart() }}>{v}</button>
      {/each}
    </span>
    <label class="tog"><input type="checkbox" bind:checked={shapeBug} onchange={restart} /> Shape bug: pred <code>(4, 1)</code>, y <code>(4,)</code></label>
    <label class="tog"><input type="checkbox" bind:checked={noZero} onchange={restart} /> Forget <code>zero_grad</code></label>
  {/snippet}

  {#snippet readout()}
    {#if last === undefined}
      Step 0: w = 0.5, b = 0. Press Train.
    {:else}
      After {losses.length} steps: loss {fmt(last)}, w = {fmt(st.w)}, b = {fmt(st.b)}.
      {#if firstInf >= 0} <span class="badt">Loss became inf at step {firstInf}{#if firstNan >= 0}, NaN at step {firstNan}{/if}.</span>{/if}
    {/if}
  {/snippet}

  {#snippet legend()}
    <span><i class="sw acc"></i>your line, your loss</span>
    <span><i class="sw okd"></i>the best line, the best loss</span>
    <span><i class="sw warn"></i>first inf / NaN</span>
  {/snippet}
</LabFrame>

<style>
  .panes { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 1rem; }
  @media (max-width: 600px) { .panes { grid-template-columns: minmax(0, 1fr); } }
  figure { margin: 0; min-width: 0; }
  figcaption { font-size: 0.8rem; color: var(--dim); margin-top: 0.3rem; }
  svg { width: 100%; display: block; border: 1px solid var(--line); border-radius: 4px; background: var(--bg); }
  .grid { stroke: var(--line); stroke-width: 0.25; }
  .tick { font-size: 3.4px; fill: var(--dim); font-family: var(--mono); }
  .mid { text-anchor: middle; }
  .end { text-anchor: end; }
  .best { stroke: var(--ok); stroke-width: 0.5; stroke-dasharray: 1.5 1.2; }
  .fit { stroke: var(--accent); stroke-width: 0.8; }
  .pt { fill: var(--fg); }
  .floor { stroke: var(--ok); stroke-width: 0.35; stroke-dasharray: 1.5 1.2; }
  .line { fill: none; stroke: var(--accent); stroke-width: 0.6; stroke-linejoin: round; }
  .bad { stroke: var(--warn); stroke-width: 0.4; stroke-dasharray: 1 1; }
  .badt { color: var(--warn); fill: var(--warn); }
  .knob { display: inline-flex; align-items: center; gap: 0.35rem; font-size: 0.85rem; color: var(--dim); flex-wrap: wrap; }
  .seg { min-width: 2.6rem; font-family: var(--mono); }
  .seg.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  .tog { display: inline-flex; gap: 0.45rem; align-items: center; font-size: 0.88rem; cursor: pointer; min-height: 2.5rem; }
  .tog input { width: 1.1rem; height: 1.1rem; accent-color: var(--accent); }
  .sw { display: inline-block; width: 1.1rem; height: 0; border-top: 2px solid; vertical-align: 0.25rem; margin-right: 0.35rem; }
  .sw.acc { border-color: var(--accent); }
  .sw.okd { border-top-style: dashed; border-color: var(--ok); }
  .sw.warn { border-top-style: dotted; border-color: var(--warn); }
</style>
