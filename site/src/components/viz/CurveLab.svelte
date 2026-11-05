<script lang="ts">
  /**
   * Training-curve lab: a 1 → 32 → 1 tanh network trained with Adam on the same 10 points.
   * Plays the train and held-out loss step by step, draws the network's curve as it trains,
   * and marks where early stopping would stop.
   * With `dropout`, a switch turns on dropout (p = 0.3) on the hidden units while training.
   */
  import { onDestroy } from 'svelte'
  import { SNAP_X, trainOverfit, truth } from '@lib/training'
  import { reducedMotion } from '@lib/settings'
  import LabFrame from './LabFrame.svelte'
  import { readable } from '@lib/readable'
  import { provideLang, useT } from '@lib/i18nSvelte'
  import type { Lang } from '@lib/i18n'

  let { dropout: withDropout = false, lang = 'en' }: { dropout?: boolean; lang?: Lang } = $props()
  provideLang(lang)
  const t = useT({
    'The same run with dropout': '同样的训练，加上 dropout',
    'Train too long and the held-out loss rises again': '训练太久，留出集损失又会上升',
    'Train once without dropout, then check the dropout box and train again.': '先不加 dropout 训练一次，然后勾选 dropout 再训练一次。',
    'Press Train and watch both losses. The ring marks where early stopping would stop.': '按“训练”，看两条损失曲线。圆圈标出早停会停在哪里。',
    'Train and held-out loss over training steps, log scale': '训练损失和留出集损失随训练步数的变化，对数刻度',
    'step': '步',
    'loss': '损失',
    'press Train to play the run': '按“训练”播放这次训练',
    'Loss by training step, log scale.': '每个训练步的损失，对数刻度。',
    'The data and the network’s curve at the current step': '数据，以及网络在当前这一步的曲线',
    'The data and the network’s curve at step {s}.': '数据，以及网络在第 {s} 步的曲线。',
    'Pause': '暂停',
    'Play again': '再播一次',
    'Continue': '继续',
    'Train {n} steps': '训练 {n} 步',
    'dropout p = 0.3 on the hidden units': '在隐藏单元上使用 dropout，p = 0.3',
    'Step {s}: train': '第 {s} 步：训练',
    'held-out': '留出集',
    'Lowest held-out so far:': '目前最低的留出集损失：',
    'at step {s}.': '（第 {s} 步）。',
    'Early stopping would keep the weights from step {s}.': '早停会保留第 {s} 步的权重。',
    'A network with 32 hidden units has {n} parameters for 10 points. Press Train.': '一个有 32 个隐藏单元的网络，有 {n} 个参数，却只有 10 个点。按“训练”。',
    'train loss': '训练损失',
    'held-out loss': '留出集损失',
    'lowest held-out so far': '目前最低的留出集损失',
    '10 training points': '10 个训练点',
    'held-out points': '留出点',
    'the network now': '网络现在的曲线',
    'at its best step': '在它最好的那一步',
    'true curve': '真实曲线',
  })

  const H = 32, STEPS = 3000, EVERY = 20
  let drop = $state(false)
  const run = $derived(trainOverfit({ H, steps: STEPS, every: EVERY, dropout: drop ? 0.3 : 0, snapshots: true }))
  let shown = $state(0) // how many recorded points are visible
  let timer: ReturnType<typeof setInterval> | null = null
  let playing = $state(false)

  function play() {
    if (playing) return stop()
    if (shown >= run.curve.length) shown = 0
    if (reducedMotion()) { shown = run.curve.length; return } // no animation: jump to the end
    playing = true
    shown = Math.max(1, shown)
    timer = setInterval(() => {
      shown = Math.min(run.curve.length, shown + 2)
      if (shown >= run.curve.length) stop()
    }, 40)
  }
  function stop() {
    if (timer) clearInterval(timer)
    timer = null
    playing = false
  }
  function reset() {
    stop()
    drop = false
    shown = 0
  }
  onDestroy(stop)

  const vis = $derived(run.curve.slice(0, Math.max(1, shown)))
  const cur = $derived(vis.at(-1)!)
  const bestIdx = $derived(vis.reduce((bi, c, i) => (c.held < vis[bi].held ? i : bi), 0))
  const bestSoFar = $derived(vis[bestIdx])
  const done = $derived(shown >= run.curve.length)

  // log-scale loss chart: 0.001 … 1, steps 0 … 3000
  const lx = (s: number) => 10 + (s / STEPS) * 84
  const ly = (v: number) => 38 - ((Math.log10(Math.max(v, 1e-3)) + 3) / 3) * 34
  const line = (key: 'train' | 'held') => vis.map((c) => `${lx(c.step)},${ly(c[key])}`).join(' ')

  // the data and the network's curve at the shown step
  const sx = (x: number) => ((x + 1.05) / 2.1) * 100
  const sy = (y: number) => ((2 - Math.max(-3, Math.min(3, y))) / 4) * 60
  const snapLine = (k: number) => SNAP_X.map((x, i) => `${sx(x)},${sy(run.snaps[k][i])}`).join(' ')
  const f4 = (v: number) => v.toFixed(4)
</script>

<LabFrame
  title={withDropout ? t('The same run with dropout') : t('Train too long and the held-out loss rises again')}
  hint={withDropout ? t('Train once without dropout, then check the dropout box and train again.') : t('Press Train and watch both losses. The ring marks where early stopping would stop.')}
  onreset={reset}
  resetDisabled={shown === 0 && !drop}
>
  <div class="panes">
    <figure>
      <svg viewBox="-4 -2 104 48" use:readable aria-label={t('Train and held-out loss over training steps, log scale')}>
        <rect x="10" y="3" width="86" height="35" class="plot" />
        {#each [1, 0.1, 0.01, 0.001] as g}
          <line x1="10" x2="96" y1={ly(g)} y2={ly(g)} class="grid" /><text x="8.8" y={ly(g) + 1} class="tick end">{g}</text>
        {/each}
        {#each [0, 1000, 2000, 3000] as st}<text x={lx(st)} y="42" class="tick mid">{st}</text>{/each}
        <text x="96" y="45.6" class="tick end name">{t('step')}</text>
        <text x="1" y="1.6" class="tick name">{t('loss')}</text>
        <polyline points={line('train')} class="tr" />
        <polyline points={line('held')} class="ho" />
        {#if shown > 1}
          <line x1={lx(bestSoFar.step)} x2={lx(bestSoFar.step)} y1="3" y2="38" class="stop" />
          <circle cx={lx(bestSoFar.step)} cy={ly(bestSoFar.held)} r="1.4" class="bestpt" />
          <circle cx={lx(cur.step)} cy={ly(cur.held)} r="0.9" class="head" />
        {:else}
          <text x="53" y="22" class="tick mid">{t('press Train to play the run')}</text>
        {/if}
      </svg>
      <figcaption>{t('Loss by training step, log scale.')}</figcaption>
    </figure>
    <figure>
      <svg viewBox="0 0 100 60" class="data" use:readable aria-label={t('The data and the network’s curve at the current step')}>
        <polyline points={SNAP_X.map((x) => `${sx(x)},${sy(truth(x))}`).join(' ')} class="truth" />
        {#if shown > 1 && bestIdx !== vis.length - 1}
          <polyline points={snapLine(bestIdx)} class="ghost" />
        {/if}
        <polyline points={snapLine(Math.max(0, vis.length - 1))} class="fit" />
        {#each run.data.heldX as x, i}<circle cx={sx(x)} cy={sy(run.data.heldY[i])} r="0.8" class="held" />{/each}
        {#each run.data.trainX as x, i}<circle cx={sx(x)} cy={sy(run.data.trainY[i])} r="1.3" class="train" />{/each}
      </svg>
      <figcaption>{t('The data and the network’s curve at step {s}.', { s: cur.step })}</figcaption>
    </figure>
  </div>

  {#snippet controls()}
    <button class="lab-btn primary" onclick={play}>{playing ? t('Pause') : done ? t('Play again') : shown > 0 ? t('Continue') : t('Train {n} steps', { n: STEPS })}</button>
    {#if withDropout}
      <label class="chk"><input type="checkbox" bind:checked={drop} onchange={() => { stop(); shown = 0 }} /> {t('dropout p = 0.3 on the hidden units')}</label>
    {/if}
  {/snippet}

  {#snippet readout()}
    {#if shown > 0}
      {t('Step {s}: train', { s: cur.step })} <b>{f4(cur.train)}</b>, {t('held-out')} <b>{f4(cur.held)}</b>.
      {t('Lowest held-out so far:')} <b>{f4(bestSoFar.held)}</b> {t('at step {s}.', { s: bestSoFar.step })}
      {#if done}{t('Early stopping would keep the weights from step {s}.', { s: bestSoFar.step })}{/if}
    {:else}
      <span class="idle">{t('A network with 32 hidden units has {n} parameters for 10 points. Press Train.', { n: 3 * H + 1 })}</span>
    {/if}
  {/snippet}

  {#snippet legend()}
    <span><i class="ln tr"></i>{t('train loss')}</span>
    <span><i class="ln ho"></i>{t('held-out loss')}</span>
    <span><i class="ring"></i>{t('lowest held-out so far')}</span>
    <span><i class="dot train"></i>{t('10 training points')}</span>
    <span><i class="dot held"></i>{t('held-out points')}</span>
    <span><i class="ln fit"></i>{t('the network now')}</span>
    <span><i class="ln ghost"></i>{t('at its best step')}</span>
    <span><i class="ln truth"></i>{t('true curve')}</span>
  {/snippet}
</LabFrame>

<style>
  .panes { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 1rem; }
  @media (max-width: 560px) { .panes { grid-template-columns: minmax(0, 1fr); } }
  figure { margin: 0; min-width: 0; }
  figcaption { font-size: 0.8rem; color: var(--dim); margin-top: 0.3rem; }
  svg { width: 100%; display: block; overflow: visible; }
  .plot { fill: var(--bg); stroke: var(--line); stroke-width: 0.25; }
  .data { background: var(--bg); border: 1px solid var(--line); border-radius: 4px; overflow: hidden; }
  .grid { stroke: var(--line); stroke-width: 0.2; }
  .tick { font-size: 2.6px; fill: var(--dim); font-family: var(--mono); }
  .tick.name { fill: var(--fg); font-style: italic; }
  .end { text-anchor: end; }
  .mid { text-anchor: middle; }
  polyline.tr { fill: none; stroke: var(--cat-5); stroke-width: 0.5; }
  polyline.ho { fill: none; stroke: var(--cat-3); stroke-width: 0.6; }
  line.stop { stroke: var(--ok); stroke-width: 0.3; stroke-dasharray: 1 1; }
  .bestpt { fill: none; stroke: var(--ok); stroke-width: 0.5; }
  .head { fill: var(--cat-3); }
  .truth { fill: none; stroke: var(--ok); stroke-width: 0.4; stroke-dasharray: 1.5 1; }
  .fit { fill: none; stroke: var(--accent); stroke-width: 0.7; }
  .ghost { fill: none; stroke: var(--accent); stroke-width: 0.5; opacity: 0.35; }
  .train { fill: var(--cat-5); stroke: var(--bg); stroke-width: 0.3; }
  .held { fill: none; stroke: var(--cat-3); stroke-width: 0.3; }
  .ln { display: inline-block; width: 1rem; height: 0; border-top: 2px solid var(--accent); margin-right: 0.3rem; vertical-align: middle; }
  .ln.tr { border-top-color: var(--cat-5); }
  .ln.ho { border-top-color: var(--cat-3); }
  .ln.ghost { opacity: 0.35; }
  .ln.truth { border-top: 2px dashed var(--ok); }
  .ring { display: inline-block; width: 0.65rem; height: 0.65rem; border-radius: 50%; border: 1.5px solid var(--ok); margin-right: 0.3rem; vertical-align: -0.05rem; }
  .dot { display: inline-block; width: 0.6rem; height: 0.6rem; border-radius: 50%; margin-right: 0.3rem; vertical-align: -0.02rem; }
  .dot.train { background: var(--cat-5); }
  .dot.held { border: 1.5px solid var(--cat-3); }
  .chk { display: inline-flex; align-items: center; gap: 0.4rem; color: var(--dim); font-size: 0.85rem; min-height: 2.5rem; cursor: pointer; }
  .chk input { width: 1.1rem; height: 1.1rem; accent-color: var(--accent); }
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
</style>
