<script lang="ts">
  /**
   * Latent space lab. A trained autoencoder squeezes 784 pixels into 16 numbers and back.
   * The walk slider moves from the 3 to the 7 in two ways: by mixing pixels, and by mixing the 16-number codes.
   * All pictures were computed by content/2-theory/a3-latent-and-dit/export.py.
   */
  import { onMount } from 'svelte'
  import { themeColors } from '@lib/diffusion'
  import { onThemeChange } from '@lib/settings'
  import LabFrame from './LabFrame.svelte'

  type Data = { labels: number[]; digits: number[][]; codes: number[][]; decoded: number[][]; walk: number[][] }
  let data = $state<Data | null>(null)
  let error = $state<string | null>(null)
  let pick = $state(0)
  let k = $state(0)
  let cvs: Record<string, HTMLCanvasElement> = {}
  let bars = $state<HTMLCanvasElement>()

  function paint(cv: HTMLCanvasElement | undefined, a: number[] | undefined) {
    if (!cv || !a) return
    const c = themeColors(cv)
    const W = cv.clientWidth || 120, cell = W / 28, dpr = window.devicePixelRatio || 1
    cv.width = Math.round(W * dpr); cv.height = Math.round(W * dpr)
    const g = cv.getContext('2d')!
    g.setTransform(dpr, 0, 0, dpr, 0, 0)
    g.fillStyle = c.bg; g.fillRect(0, 0, W, W); g.fillStyle = c.fg
    for (let i = 0; i < 784; i++) {
      if (!a[i]) continue
      g.globalAlpha = a[i] / 255
      g.fillRect((i % 28) * cell, Math.floor(i / 28) * cell, cell + 0.5, cell + 0.5)
    }
    g.globalAlpha = 1
  }

  function drawBars() {
    if (!bars || !data) return
    const code = data.codes[pick]
    const c = themeColors(bars)
    const W = bars.clientWidth || 280, H = 90, dpr = window.devicePixelRatio || 1
    bars.width = Math.round(W * dpr); bars.height = Math.round(H * dpr)
    const g = bars.getContext('2d')!
    g.setTransform(dpr, 0, 0, dpr, 0, 0)
    g.clearRect(0, 0, W, H)
    const m = Math.max(...data.codes.flat().map(Math.abs))
    const bw = W / 16
    g.strokeStyle = c.line; g.beginPath(); g.moveTo(0, H / 2); g.lineTo(W, H / 2); g.stroke()
    code.forEach((v, i) => {
      g.fillStyle = v >= 0 ? c.pos : c.neg   // the sign of each code number
      const h = (v / m) * (H / 2 - 4)
      g.fillRect(i * bw + 2, H / 2 - Math.max(h, 0), bw - 4, Math.abs(h))
    })
  }

  function resetAll() { pick = 0; k = 0 }

  const blend = $derived(
    data ? data.digits[0].map((v, i) => Math.round(((8 - k) * v + k * data!.digits[1][i]) / 8)) : undefined,
  )

  function drawAll() {
    if (!data) return
    paint(cvs.orig, data.digits[pick]); paint(cvs.dec, data.decoded[pick])
    paint(cvs.blend, blend); paint(cvs.walk, data.walk[k])
    drawBars()
  }
  $effect(() => { void pick; void k; void data; requestAnimationFrame(drawAll) })

  onMount(() => {
    fetch('/data/latents-and-dit/digits.json').then((r) => r.json()).then((d) => (data = d)).catch((e) => (error = String(e)))
    addEventListener('resize', drawAll)   // the canvases only exist once the data has loaded
    const offTheme = onThemeChange(drawAll)
    return () => { removeEventListener('resize', drawAll); offTheme() }
  })
</script>

<LabFrame
  title="Squeeze a picture into 16 numbers, and back"
  hint="A trained autoencoder keeps 16 numbers per picture. Then walk from one digit to another in two ways."
  onreset={resetAll}
  resetDisabled={pick === 0 && k === 0}
>
  {#if error}<p class="err">Could not load the digits: {error}</p>{/if}
  {#if data}
    <div>
      <div class="row3">
        <figure><canvas bind:this={cvs.orig} aria-label="The original digit"></canvas><figcaption>784 pixels</figcaption></figure>
        <figure class="mid">
          <canvas bind:this={bars} class="bars" aria-label="The 16 code numbers as bars above and below zero"></canvas>
          <figcaption>16 numbers: [{data.codes[pick].map((v) => v.toFixed(1)).join(', ')}]</figcaption>
        </figure>
        <figure><canvas bind:this={cvs.dec} aria-label="The digit rebuilt from the 16 numbers"></canvas><figcaption>decoded back to 784</figcaption></figure>
      </div>
    </div>
    <div class="walk">
      <label class="slider">
        <span>walk from the {data.labels[0]} to the {data.labels[1]}: <b>{k} / 8</b></span>
        <input type="range" min="0" max="8" step="1" bind:value={k} aria-label="Walk between the two digits" />
      </label>
      <div class="row2">
        <figure><canvas bind:this={cvs.blend} aria-label="Mixing the pixels"></canvas><figcaption>mix the pixels</figcaption></figure>
        <figure><canvas bind:this={cvs.walk} aria-label="Mixing the codes, then decoding"></canvas><figcaption>mix the 16 numbers, then decode</figcaption></figure>
      </div>
    </div>
  {:else if !error}
    <p class="loading">Loading the trained autoencoder…</p>
  {/if}

  {#snippet controls()}
    {#if data}
      <div class="seg" role="group" aria-label="Digit">
        <span class="lbl">digit</span>
        {#each data.labels as l, i}<button type="button" class="lab-btn" class:on={pick === i} aria-pressed={pick === i} onclick={() => (pick = i)}>{l}</button>{/each}
      </div>
    {/if}
  {/snippet}

  {#snippet readout()}
    {#if data}784 numbers in, 16 numbers kept ({(784 / 16).toFixed(0)} times fewer), 784 numbers out.{:else}loading…{/if}
  {/snippet}

  {#snippet legend()}
    <span><i class="sw pos"></i>positive code number</span>
    <span><i class="sw neg"></i>negative code number</span>
  {/snippet}
</LabFrame>

<style>
  .row3 { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 2fr) minmax(0, 1fr); gap: 0.7rem; align-items: start; }
  @media (max-width: 560px) { .row3 { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); } .mid { grid-column: 1 / -1; order: 3; } }
  .row2 { display: grid; grid-template-columns: repeat(2, minmax(0, 10rem)); gap: 0.7rem; }
  figure { margin: 0; min-width: 0; }
  figure canvas { width: 100%; aspect-ratio: 1; display: block; border: 1px solid var(--line); border-radius: 6px; }
  figure canvas.bars { aspect-ratio: auto; height: 90px; }
  figcaption { font-size: 0.78rem; color: var(--dim); margin-top: 0.25rem; font-family: var(--mono); overflow-wrap: anywhere; }
  .walk { margin-top: 0.9rem; border-top: 1px dashed var(--line); padding-top: 0.7rem; }
  .slider { display: grid; gap: 0.2rem; font-size: 0.9rem; margin-bottom: 0.5rem; max-width: 22rem; }
  .slider input { width: 100%; min-height: 2rem; accent-color: var(--accent); }
  .seg { display: inline-flex; flex-wrap: wrap; align-items: center; gap: 0.4rem; }
  .seg .lab-btn { font-family: var(--mono); min-width: 2.5rem; }
  .seg .lab-btn.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  .lbl { color: var(--dim); font-size: 0.82rem; }
  /* reserve the lab's height while the data loads, so the page doesn't jump */
  .loading { min-height: 24rem; display: grid; place-items: center; margin: 0; color: var(--dim); border: 1px dashed var(--line); border-radius: 6px; }
  .err { color: var(--warn); }
  .sw { display: inline-block; width: 0.7rem; height: 0.7rem; border-radius: 2px; margin-right: 0.35rem; vertical-align: -0.05rem; }
  .sw.pos { background: var(--pos); } .sw.neg { background: var(--neg); }
</style>
