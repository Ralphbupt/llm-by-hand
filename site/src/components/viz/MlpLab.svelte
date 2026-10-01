<script lang="ts">
  import { onMount } from 'svelte'
  import LabFrame from './LabFrame.svelte'
  import { readable } from '@lib/readable'
  import { reducedMotion } from '@lib/settings'
  /**
   * MLP lab: a 2→6→1 network learns XOR live. Training really runs gradient descent in the browser,
   * 20 steps per frame; the background is the current decision boundary.
   * Turn the activation off and it can never learn: two linear layers stacked are still one line.
   */
  const XS = [[0, 0], [0, 1], [1, 0], [1, 1]]
  const YS = [0, 1, 1, 0]
  const H = 6      // measured: with H=6, lr=1 it learns within 500 steps every time; H=4 gets stuck ~2% of the time
  const GRID = 21
  const LO = -0.25, HI = 1.25

  let act = $state(true)     // is the activation on?
  let lr = $state(1)
  let running = $state(false)
  let ui = $state({ steps: 0, loss: 0, grid: [] as number[][], preds: [0, 0, 0, 0] })
  let losses = $state<number[]>([])  // $state so the loss curve redraws

  let W1: number[][], b1: number[], W2: number[][], b2: number
  let raf = 0

  const sig = (z: number) => 1 / (1 + Math.exp(-z))
  const randn = () => {
    const u = Math.random() || 1e-9
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * Math.random())
  }

  function reset() {
    stop()
    W1 = [Array.from({ length: H }, randn), Array.from({ length: H }, randn)]
    b1 = new Array(H).fill(0)
    W2 = Array.from({ length: H }, () => [randn()])
    b2 = 0
    losses = []
    snapshot(0)
  }

  /** forward: one sample → hidden layer → output probability */
  function fwd(x: number[]) {
    const a1 = new Array(H)
    for (let h = 0; h < H; h++) {
      const z = x[0] * W1[0][h] + x[1] * W1[1][h] + b1[h]
      a1[h] = act ? Math.tanh(z) : z
    }
    let z2 = b2
    for (let h = 0; h < H; h++) z2 += a1[h] * W2[h][0]
    return { a1, p: sig(z2) }
  }

  /** one full-batch step: forward → loss → backward → update */
  function step() {
    const gW1 = [new Array(H).fill(0), new Array(H).fill(0)]
    const gb1 = new Array(H).fill(0)
    const gW2 = new Array(H).fill(0)
    let gb2 = 0, loss = 0

    for (let n = 0; n < 4; n++) {
      const x = XS[n], y = YS[n]
      const { a1, p } = fwd(x)
      loss += -(y * Math.log(p + 1e-9) + (1 - y) * Math.log(1 - p + 1e-9)) / 4
      const dz2 = (p - y) / 4                                   // gradient of BCE + sigmoid combined
      gb2 += dz2
      for (let h = 0; h < H; h++) {
        gW2[h] += a1[h] * dz2
        const da1 = dz2 * W2[h][0]
        const dz1 = act ? da1 * (1 - a1[h] * a1[h]) : da1       // tanh' = 1 - tanh²
        gb1[h] += dz1
        gW1[0][h] += x[0] * dz1
        gW1[1][h] += x[1] * dz1
      }
    }

    for (let h = 0; h < H; h++) {
      W2[h][0] -= lr * gW2[h]
      b1[h] -= lr * gb1[h]
      W1[0][h] -= lr * gW1[0][h]
      W1[1][h] -= lr * gW1[1][h]
    }
    b2 -= lr * gb2
    return loss
  }

  function snapshot(steps: number) {
    const grid: number[][] = []
    for (let r = 0; r < GRID; r++) {
      const row: number[] = []
      const y = HI - (r / (GRID - 1)) * (HI - LO)
      for (let c = 0; c < GRID; c++) {
        row.push(fwd([LO + (c / (GRID - 1)) * (HI - LO), y]).p)
      }
      grid.push(row)
    }
    ui = { steps, loss: losses.at(-1) ?? 0, grid, preds: XS.map((x) => fwd(x).p) }
  }

  function loop() {
    let loss = 0
    for (let i = 0; i < 20; i++) loss = step()
    losses.push(loss)
    snapshot(ui.steps + 20)
    if (running && ui.steps < 6000) raf = requestAnimationFrame(loop)
    else running = false
  }

  /** run N steps at once (no rAF, so it works in a background tab) */
  function burst(n: number) {
    stop()
    let loss = 0
    for (let i = 0; i < n; i++) {
      loss = step()
      if (i % 20 === 0) losses.push(loss)
    }
    snapshot(ui.steps + n)
  }

  function start() {
    if (running) return stop()
    // reduced motion: jump ahead instead of animating
    if (reducedMotion()) return burst(500)
    running = true
    raf = requestAnimationFrame(loop)
  }
  function stop() {
    running = false
    cancelAnimationFrame(raf)
  }

  // onMount, not $effect: $effect would track `act` read inside reset() and rerun on every change
  onMount(() => {
    reset()
    return stop
  })

  const sx = (x: number) => ((x - LO) / (HI - LO)) * 100
  const ok = $derived(ui.preds.every((p, n) => (p > 0.5 ? 1 : 0) === YS[n]))
  const curve = $derived(
    losses.slice(-200).map((l, i, a) => `${8 + (i / Math.max(1, a.length - 1)) * 91},${38 - Math.min(35, l * 44)}`).join(' '),
  )
</script>

<LabFrame
  title="A 2 → 6 → 1 network learns XOR"
  hint="Press Train and watch the background bend around the four points. Then turn the activation off and try again."
>
  <div class="pic">
    <div class="boardwrap">
      <svg viewBox="0 0 100 100" class="board" use:readable aria-label="What the network answers for every point of the plane, with the four XOR points">
        {#each ui.grid as row, r}
          {#each row as p, c}
            <rect x={(c / GRID) * 100} y={(r / GRID) * 100} width={100 / GRID + 0.4} height={100 / GRID + 0.4} style="--p: {p}" />
          {/each}
        {/each}
        {#each XS as x, n}
          <circle cx={sx(x[0])} cy={100 - sx(x[1])} r="4.4" class="pt" class:one={YS[n] === 1} />
          {#if (ui.preds[n] > 0.5 ? 1 : 0) !== YS[n]}<circle cx={sx(x[0])} cy={100 - sx(x[1])} r="6.4" class="miss" />{/if}
          <text x={sx(x[0])} y={100 - sx(x[1]) + 1.6} class="lbl" class:one={YS[n] === 1}>{YS[n]}</text>
        {/each}
        <text x="98" y="97" class="axis end">x1 →</text>
        <text x="2" y="6" class="axis">x2 ↑</text>
      </svg>
    </div>

    <div class="side">
      <svg viewBox="0 0 100 44" class="curve" use:readable aria-label="Loss curve">
        <line x1="8" y1="38" x2="99" y2="38" class="ax" />
        <line x1="8" y1="3" x2="8" y2="38" class="ax" />
        <text x="10" y="7" class="tick">loss</text>
        <text x="7" y="38" class="tick end">0</text>
        <text x="99" y="43" class="tick end">steps →</text>
        {#if losses.length > 1}
          <polyline points={curve} />
        {:else}
          <text x="53" y="23" class="empty">Train to draw the loss</text>
        {/if}
      </svg>
      <div class="cap">loss while training (last 200 records)</div>

      <div class="scroll">
        <table>
          <thead><tr><th>input</th><th>target</th><th>output</th></tr></thead>
          <tbody>
            {#each XS as x, n}
              <tr>
                <td>[{x[0]}, {x[1]}]</td>
                <td>{YS[n]}</td>
                <td class:wrong={(ui.preds[n] > 0.5 ? 1 : 0) !== YS[n]}>{ui.preds[n].toFixed(3)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  </div>

  {#snippet controls()}
    <button onclick={start} class="lab-btn primary">{running ? 'Pause' : 'Train'}</button>
    <button class="lab-btn" onclick={() => burst(500)}>Run 500 steps</button>
    <button class="lab-btn" onclick={reset}>New random weights</button>
    <label class="sw"><input type="checkbox" bind:checked={act} onchange={reset} /> activation on (tanh)</label>
  {/snippet}

  {#snippet readout()}
    steps {ui.steps} · loss (cross-entropy) {ui.steps ? ui.loss.toFixed(4) : '—'} ·
    <span class:good={ok} class:bad={!ok}>{ok ? '✓ all 4 correct' : '✗ not learned yet'}</span>
  {/snippet}

  {#snippet legend()}
    <span class="key"><i class="k-bg"></i>background: how sure the network is of 1</span>
    <span class="key"><i class="k-one"></i>target 1</span>
    <span class="key"><i class="k-zero"></i>target 0</span>
    <span class="key"><i class="k-miss"></i>a wrong answer</span>
  {/snippet}
</LabFrame>

<style>
  .pic { display: grid; grid-template-columns: minmax(0, 280px) minmax(0, 1fr); gap: 1.2rem; align-items: start; }
  @media (max-width: 620px) { .pic { grid-template-columns: minmax(0, 1fr); } }
  .boardwrap, .side { min-width: 0; }
  .board { width: 100%; aspect-ratio: 1; border: 1px solid var(--line); border-radius: 6px; display: block; }
  .board rect {
    /* opaque colors: overlapping translucent cells drew darker seams. One hue: neutral at p ≈ 0, accent at p ≈ 1 */
    fill: color-mix(in srgb, var(--accent) calc(var(--p) * 62%), var(--bg));
    shape-rendering: crispEdges;
  }
  .pt { fill: var(--bg); stroke: var(--fg); stroke-width: 1; }
  .pt.one { fill: var(--fg); }
  .miss { fill: none; stroke: var(--warn); stroke-width: 1.4; }
  .lbl { font-size: 4px; text-anchor: middle; fill: var(--fg); pointer-events: none; font-family: var(--mono); font-weight: 700; }
  .lbl.one { fill: var(--bg); }
  .axis { font-size: 3.6px; fill: var(--fg); font-family: var(--mono); }
  .end { text-anchor: end; }
  .curve { width: 100%; height: auto; aspect-ratio: 100 / 44; border: 1px solid var(--line); border-radius: 4px; background: var(--bg); display: block; }
  .curve polyline { fill: none; stroke: var(--accent); stroke-width: 0.8; vector-effect: non-scaling-stroke; }
  .ax { stroke: var(--line); stroke-width: 0.4; }
  .tick { font-size: 3.2px; fill: var(--dim); font-family: var(--mono); }
  .empty { font-size: 3.6px; fill: var(--dim); text-anchor: middle; font-family: system-ui, sans-serif; }
  .cap { margin: 0.3rem 0 0.7rem; font-size: 0.8rem; color: var(--dim); }
  .scroll { overflow-x: auto; }
  table { font-family: var(--mono); font-size: 0.85rem; width: auto; }
  th, td { border: 1px solid var(--line); padding: 0.2rem 0.6rem; text-align: right; }
  th { color: var(--dim); font-weight: 400; }
  td.wrong { color: var(--warn); }
  .sw { font-size: 0.88rem; color: var(--dim); display: flex; gap: 0.4rem; align-items: center; min-height: 2.1rem; }
  .sw input { accent-color: var(--accent); width: 1.05rem; height: 1.05rem; }
  .good { color: var(--ok); }
  .bad { color: var(--warn); }
  .key { display: inline-flex; align-items: center; gap: 0.4rem; }
  .key i { flex: none; display: inline-block; width: 0.85rem; height: 0.85rem; border-radius: 50%; }
  .k-bg { border-radius: 2px !important; width: 1.4rem !important; background: linear-gradient(90deg, var(--bg), color-mix(in srgb, var(--accent) 62%, var(--bg))); border: 1px solid var(--line); }
  .k-one { background: var(--fg); }
  .k-zero { border: 1.5px solid var(--fg); }
  .k-miss { border: 2px solid var(--warn); }
</style>
