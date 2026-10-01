<script lang="ts">
  /**
   * Level 21: two real training runs of the reference GPT, epoch by epoch.
   * Data: site/public/data/write-a-gpt/curve_{answer,all}.json (content/2-theory/write-a-gpt/export.py).
   */
  import { onMount } from 'svelte'
  import { reducedMotion } from '@lib/settings'
  import { readable } from '@lib/readable'
  import LabFrame from './LabFrame.svelte'

  type Row = { epoch: number; loss: number; acc: number; answers: string[] }
  type Run = { probes: string[]; truth: string[]; epochs: Row[] }
  const MAX = 60

  let runs = $state<Record<string, Run> | null>(null)
  let failed = $state(false)
  let mode = $state<'all' | 'answer'>('all')
  let ep = $state(7)
  let timer: ReturnType<typeof setInterval> | null = null
  let playing = $state(false)

  onMount(() => {
    Promise.all(['answer', 'all'].map((m) => fetch(`/data/write-a-gpt/curve_${m}.json`).then((r) => r.json())))
      .then(([answer, all]) => (runs = { answer, all }))
      .catch(() => (failed = true))
    return () => stop()
  })

  function reset() { stop(); mode = 'all'; ep = 7 }
  function stop() { if (timer) clearInterval(timer); timer = null; playing = false }
  function play() {
    if (playing) return stop()
    if (ep >= MAX) ep = 1
    if (reducedMotion()) { ep = MAX; return } // no animation: show the end of the run
    playing = true
    timer = setInterval(() => { if (ep >= MAX) stop(); else ep += 1 }, 180)
  }

  // accuracy chart (top) and training-loss chart (bottom) share the epoch axis
  const W = 560, H = 230, P = { l: 52, r: 12, t: 12, b: 34 }
  const LH = 156, LP = { t: 10, b: 40 }, LMAX = 1.8
  const sx = (e: number) => P.l + ((e - 1) / (MAX - 1)) * (W - P.l - P.r)
  const sy = (a: number) => P.t + (1 - a) * (H - P.t - P.b)
  const ly = (l: number) => LP.t + (1 - Math.min(l, LMAX) / LMAX) * (LH - LP.t - LP.b)
  const path = (rows: Row[]) => rows.slice(0, MAX).map((r, i) => `${i ? 'L' : 'M'}${sx(r.epoch).toFixed(1)},${sy(r.acc).toFixed(1)}`).join(' ')
  const lpath = (rows: Row[]) => rows.slice(0, MAX).map((r, i) => `${i ? 'L' : 'M'}${sx(r.epoch).toFixed(1)},${ly(r.loss).toFixed(1)}`).join(' ')
  const cur = $derived(runs ? runs[mode].epochs[ep - 1] : null)
  const other = $derived(mode === 'all' ? 'answer' : 'all')
  const runName = (m: string) => (m === 'all' ? 'loss on every position' : 'loss on the answer digits only')
  // area under this run's curve up to the current epoch: the part already "played"
  const area = (rows: Row[]) => {
    const r = rows.slice(0, ep)
    if (!r.length) return ''
    return `${path(r)} L${sx(r[r.length - 1].epoch).toFixed(1)},${sy(0)} L${sx(r[0].epoch).toFixed(1)},${sy(0)} Z`
  }
</script>

<LabFrame
  title="Two real training runs, epoch by epoch"
  hint="Drag the epoch slider or press Play. Switch runs to compare the two loss settings."
  onreset={reset} resetDisabled={mode === 'all' && ep === 7 && !playing}
>
  {#if failed}
    <p class="dim">Could not load the training runs. Reload the page to try again.</p>
  {:else if !runs || !cur}
    <div class="skeleton" aria-hidden="true"></div>
    <p class="dim">Loading the training runs…</p>
  {:else}
    <svg use:readable viewBox="0 0 {W} {H}" role="img" aria-label={`Accuracy on 1,000 unseen problems, by epoch. At epoch ${ep}: ${(cur.acc * 100).toFixed(1)}%.`}>
      {#each [0, 0.25, 0.5, 0.75, 0.95, 1] as g}
        <line x1={P.l} x2={W - P.r} y1={sy(g)} y2={sy(g)} class:goal={g === 0.95} class="grid" />
        <!-- 95% sits right under 100%, so it gets its label on the right instead of the axis -->
        {#if g === 0.95}
          <text x={W - P.r - 4} y={sy(g) + 13} class="tick goal-t" text-anchor="end">95% goal</text>
        {:else}
          <text x={P.l - 6} y={sy(g) + 5} class="tick" text-anchor="end">{Math.round(g * 100)}%</text>
        {/if}
      {/each}
      {#each [1, 10, 20, 30, 40, 50, 60] as e}
        <text x={sx(e)} y={H - 12} class="tick" text-anchor="middle">{e}</text>
      {/each}
      <text x={W - P.r - 4} y={sy(0) - 8} class="axt" text-anchor="end">unseen problems fully correct</text>
      <path d={path(runs[other].epochs)} class="other" />
      <path d={area(runs[mode].epochs)} class="area" />
      <path d={path(runs[mode].epochs)} class="main ahead" />
      <path d={path(runs[mode].epochs.slice(0, ep))} class="main" />
      <line x1={sx(ep)} x2={sx(ep)} y1={P.t} y2={H - P.b} class="cursor" />
      <circle cx={sx(ep)} cy={sy(cur.acc)} r="5" class="dot" />
    </svg>

    <svg use:readable viewBox="0 0 {W} {LH}" role="img" aria-label={`Training loss by epoch. At epoch ${ep}: ${cur.loss.toFixed(3)}.`}>
      {#each [0, 0.5, 1, 1.5] as g}
        <line x1={P.l} x2={W - P.r} y1={ly(g)} y2={ly(g)} class="grid" />
        {#if g === 0 || g === 1}<text x={P.l - 6} y={ly(g) + 4} class="tick" text-anchor="end">{g}</text>{/if}
      {/each}
      {#each [1, 10, 20, 30, 40, 50, 60] as e}
        <text x={sx(e)} y={LH - 20} class="tick" text-anchor="middle">{e}</text>
      {/each}
      <text x={W - P.r} y={LH - 2} class="axt" text-anchor="end">epoch →</text>
      <text x={W - P.r - 4} y={LP.t + 16} class="axt" text-anchor="end">training loss</text>
      <path d={lpath(runs[other].epochs)} class="other" />
      <path d={lpath(runs[mode].epochs)} class="main ahead" />
      <path d={lpath(runs[mode].epochs.slice(0, ep))} class="main" />
      <line x1={sx(ep)} x2={sx(ep)} y1={LP.t} y2={LH - LP.b} class="cursor" />
      <circle cx={sx(ep)} cy={ly(cur.loss)} r="5" class="dot" />
    </svg>

    <div class="probes-h">Eight problems the model never trained on, answered by the model after epoch {ep}:</div>
    <div class="probes">
      {#each runs[mode].probes as p, i}
        {@const right = cur.answers[i] === runs[mode].truth[i]}
        <div class="pr" class:ok={right}>
          <span class="mono">{p}=</span><b class="mono">{cur.answers[i] || '∅'}</b>
          <span class="mk" aria-label={right ? 'right' : 'wrong'}>{right ? '✓' : '✗'}</span>
        </div>
      {/each}
    </div>
  {/if}

  {#snippet controls()}
    <button type="button" class="lab-btn primary play" onclick={play} disabled={!runs}>{playing ? '❚❚ Pause' : '▶ Play'}</button>
    <label class="knob"><span>epoch <b>{ep}</b></span><input type="range" min="1" max={MAX} bind:value={ep} oninput={stop} aria-label="epoch" /></label>
    <span class="seg" role="group" aria-label="Which run">
      <span class="seglbl">run</span>
      <button type="button" class="lab-btn" aria-pressed={mode === 'all'} onclick={() => (mode = 'all')}>loss on every position</button>
      <button type="button" class="lab-btn" aria-pressed={mode === 'answer'} onclick={() => (mode = 'answer')}>loss on the answer digits only</button>
    </span>
  {/snippet}

  {#snippet readout()}
    {#if cur}
      epoch {ep} · unseen accuracy <b>{(cur.acc * 100).toFixed(1)}%</b> · training loss <b>{cur.loss.toFixed(3)}</b>
    {:else}
      Loading…
    {/if}
  {/snippet}

  {#snippet legend()}
    <span class="lg"><i class="ln"></i>this run ({runName(mode)})</span>
    <span class="lg"><i class="ln oth"></i>the other run</span>
    <span class="lg"><i class="ln goal"></i>95% goal</span>
    <span class="lg"><b class="okc">✓</b> right <b class="bad">✗</b> wrong</span>
  {/snippet}
</LabFrame>

<style>
  .dim { color: var(--dim); font-size: 0.88rem; margin: 0; }
  .skeleton { height: 18rem; border-radius: 6px; background: var(--bg); border: 1px dashed var(--line); }
  .mono { font-family: var(--mono); font-size: 0.85rem; }
  svg { width: 100%; height: auto; display: block; }
  svg + svg { margin-top: 0.3rem; }
  .grid { stroke: var(--line); stroke-width: 1; }
  .grid.goal { stroke: var(--ok); stroke-dasharray: 4 3; }
  .tick { fill: var(--dim); font-size: 11px; font-family: var(--mono); }
  .goal-t { fill: var(--ok); }
  .main { fill: none; stroke: var(--accent); stroke-width: 2.4; }
  .main.ahead { opacity: 0.22; }
  .area { fill: var(--accent); opacity: 0.1; stroke: none; }
  .axt { fill: var(--dim); font-size: 10.5px; font-family: var(--mono); }
  .other { fill: none; stroke: var(--dim); stroke-width: 1.4; stroke-dasharray: 4 3; opacity: 0.7; }
  .cursor { stroke: var(--fg); stroke-width: 1; opacity: 0.35; }
  .dot { fill: var(--accent); stroke: var(--card); stroke-width: 2; }
  .probes-h { font-size: 0.82rem; color: var(--dim); margin: 0.8rem 0 0.35rem; }
  .probes { display: grid; grid-template-columns: repeat(auto-fill, minmax(7.5rem, 1fr)); gap: 0.35rem; }
  .pr { display: flex; gap: 0.3rem; align-items: baseline; padding: 0.25rem 0.5rem; border: 1px solid var(--line); border-radius: 4px; background: var(--bg); }
  .pr b { color: var(--warn); }
  .pr.ok b { color: var(--ok); }
  .mk { margin-left: auto; font-size: 0.8rem; color: var(--warn); }
  .pr.ok .mk { color: var(--ok); }
  .play { min-width: 6.2rem; }
  .knob { display: inline-flex; flex-wrap: wrap; gap: 0.2rem 0.5rem; align-items: center; font-family: var(--mono); font-size: 0.85rem; flex: 1 1 14rem; }
  .knob b { color: var(--accent); display: inline-block; min-width: 1.4rem; text-align: right; }
  .knob input { flex: 1 1 8rem; min-width: 8rem; accent-color: var(--accent); min-height: 2.1rem; }
  .seg { display: inline-flex; align-items: center; gap: 0.35rem; flex-wrap: wrap; }
  .seglbl { font-size: 0.85rem; color: var(--dim); }
  .lg { display: inline-flex; align-items: center; gap: 0.35rem; }
  .ln { display: inline-block; width: 1.2rem; border-top: 2.4px solid var(--accent); }
  .ln.oth { border-top: 1.5px dashed var(--dim); }
  .ln.goal { border-top: 1.5px dashed var(--ok); }
  .okc { color: var(--ok); }
  .bad { color: var(--warn); margin-left: 0.4rem; }
  @media (max-width: 560px) {
    .knob input { min-height: 2.5rem; }
  }
</style>
