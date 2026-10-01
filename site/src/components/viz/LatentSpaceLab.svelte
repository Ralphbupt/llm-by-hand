<script lang="ts">
  /**
   * Explore a 2-number code space. Each dot is a real test digit's code; the big labels sit at each digit's average code.
   * Drag anywhere: the trained decoder (run here, in the browser) draws the picture for that code.
   * "Random code" samples a code the way you would to make a new picture, and says whether it fell in an empty region.
   * "Draw 200" samples 200 at once and counts how many fall in empty regions, per model, so the two can be compared.
   * The dots of the digit nearest your code are highlighted, so you can see which cluster you are in.
   */
  import { onMount } from 'svelte'
  import { decode, gauss, loadDecoder, type Decoder, type ModelsJSON } from '@lib/autoencoders'
  import { onThemeChange } from '@lib/settings'
  import LabFrame from './LabFrame.svelte'

  let { start = 'ae' }: { start?: 'ae' | 'vae' } = $props()

  let data = $state<ModelsJSON | null>(null)
  let model = $state<'ae' | 'vae'>('ae')
  let z = $state<[number, number]>([0, 0])
  let sampled = $state(false)
  let moved = $state(false) // the learner moved the code away from where this model starts
  let plane: HTMLCanvasElement
  let pic: HTMLCanvasElement
  const decs: Partial<Record<'ae' | 'vae', Decoder>> = {}

  const codes = $derived(data ? data[model].codes : [])
  const stats = $derived.by(() => {
    if (!codes.length) return { mean: [0, 0], std: [1, 1] }
    const mean = [0, 1].map((k) => codes.reduce((s, c) => s + c[k], 0) / codes.length)
    const std = [0, 1].map((k) => Math.sqrt(codes.reduce((s, c) => s + (c[k] - mean[k]) ** 2, 0) / codes.length))
    return { mean, std }
  })
  // the region drawn: centered on the sampling rings (the middle of the picture is where random codes come from),
  // wide enough for the 2-std ring and for 97% of the codes on each side, plus a margin. A few far outliers may fall
  // outside: framing every one of them pushed the rings into a corner and squeezed the clusters together.
  const box = $derived.by(() => {
    if (!codes.length) return { x0: -3, x1: 3, y0: -3, y1: 3 }
    const range = (k: number) => {
      const m = model === 'vae' ? 0 : stats.mean[k], sd = model === 'vae' ? 1 : stats.std[k]
      const dev = codes.map((c) => Math.abs(c[k] - m)).sort((p, q) => p - q)
      const half = Math.max(2 * sd, dev[Math.floor(0.97 * (dev.length - 1))]) * 1.08
      return [m - half, m + half]
    }
    const [x0, x1] = range(0), [y0, y1] = range(1)
    return { x0, x1, y0, y1 }
  })
  const centroids = $derived.by(() => {
    if (!data) return []
    return Array.from({ length: 10 }, (_, d) => {
      const idx = data!.labels.map((l, i) => (l === d ? i : -1)).filter((i) => i >= 0)
      return { d, x: idx.reduce((s, i) => s + codes[i][0], 0) / idx.length, y: idx.reduce((s, i) => s + codes[i][1], 0) / idx.length }
    })
  })
  const nearest = $derived.by(() => {
    let best = Infinity, lab = -1
    codes.forEach((c, i) => {
      const d = Math.hypot(c[0] - z[0], c[1] - z[1])
      if (d < best) { best = d; lab = data!.labels[i] }
    })
    return { dist: best, label: lab }
  })
  const emptyAt = (x: number, y: number) => {
    let best = Infinity
    for (const c of codes) best = Math.min(best, Math.hypot(c[0] - x, c[1] - y))
    return best > 0.25 * ((stats.std[0] + stats.std[1]) / 2)
  }
  const empty = $derived(nearest.dist > 0.25 * ((stats.std[0] + stats.std[1]) / 2))

  // "Draw 200": the samples of the last batch (cleared when the model changes) and each model's share of misses
  let batch = $state<{ x: number; y: number; empty: boolean }[]>([])
  let share = $state<Partial<Record<'ae' | 'vae', { miss: number; n: number }>>>({})
  function drawMany(n = 200) {
    const [mx, my] = model === 'vae' ? [0, 0] : stats.mean
    const [sx, sy] = model === 'vae' ? [1, 1] : stats.std
    batch = Array.from({ length: n }, () => {
      const x = mx + sx * gauss(), y = my + sy * gauss()
      return { x, y, empty: emptyAt(x, y) }
    })
    share = { ...share, [model]: { miss: batch.filter((b) => b.empty).length, n } }
    sampled = false
    moved = true
  }
  const pct = (m: { miss: number; n: number }) => Math.round((100 * m.miss) / m.n)

  // digit labels at their average code, pushed apart on the map so no two overlap and none sits under your code's
  // marker (map units: the canvas is 360 wide). A label that had to move gets a leader line back to its average code.
  const placed = $derived.by(() => {
    const W = 360
    const pts = centroids.map((c) => ({ d: c.d, x: ((c.x - box.x0) / (box.x1 - box.x0)) * W, y: W - ((c.y - box.y0) / (box.y1 - box.y0)) * W }))
    const cx = pts.map((p) => p.x), cy = pts.map((p) => p.y)
    // plates are 14 × 18 map units: keep at least 25 across or 27 down between two label centers (a clear gap, so
    // neighbors read as separate digits, not as one number)
    const RX = 25, RY = 27
    // the marker: a ring of radius 9 with ticks out to 18
    const mx = ((z[0] - box.x0) / (box.x1 - box.x0)) * W, my = W - ((z[1] - box.y0) / (box.y1 - box.y0)) * W
    const MX = 7 + 20, MY = 9 + 20
    // the middle the labels fan out from: the middle of the sampling rings (the map is centered on them)
    const ox0 = W / 2, oy0 = W / 2
    for (let it = 0; it < 160; it++) {
      for (let i = 0; i < pts.length; i++) {
        for (let j = i + 1; j < pts.length; j++) {
          const dx = pts[j].x - pts[i].x, dy = pts[j].y - pts[i].y
          const ox = RX - Math.abs(dx), oy = RY - Math.abs(dy)
          if (ox <= 0 || oy <= 0) continue
          // the label further from the middle of the map moves outward, straight away from the middle (the clusters
          // crowd the middle, so labels fan out around it and a leader line leads back); the inner one stays put
          const di = Math.hypot(pts[i].x - ox0, pts[i].y - oy0), dj = Math.hypot(pts[j].x - ox0, pts[j].y - oy0)
          const q = dj >= di ? pts[j] : pts[i]
          let ux = q.x - ox0, uy = q.y - oy0
          const ul = Math.hypot(ux, uy)
          if (ul < 1e-6) { const t = (q.d / 10) * 2 * Math.PI; ux = Math.cos(t); uy = Math.sin(t) } else { ux /= ul; uy /= ul }
          const step = Math.min(ox / Math.max(Math.abs(ux), 0.3), oy / Math.max(Math.abs(uy), 0.3), 6) + 0.5
          q.x += ux * step; q.y += uy * step
        }
        const p = pts[i]
        const dx = p.x - mx, dy = p.y - my
        const ox = MX - Math.abs(dx), oy = MY - Math.abs(dy)
        if (ox > 0 && oy > 0) {
          if (ox / MX < oy / MY) p.x += ox * (dx < 0 ? -1 : 1)
          else p.y += oy * (dy < 0 ? -1 : 1)
        }
      }
    }
    return pts.map((p, i) => ({ ...p, cx: cx[i], cy: cy[i], x: Math.min(W - 9, Math.max(9, p.x)), y: Math.min(W - 11, Math.max(11, p.y)) }))
  })

  function css(name: string) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  }

  function drawPlane() {
    if (!plane || !data) return
    const S = plane.width
    const g = plane.getContext('2d')!
    const toX = (x: number) => ((x - box.x0) / (box.x1 - box.x0)) * S
    const toY = (y: number) => S - ((y - box.y0) / (box.y1 - box.y0)) * S
    g.fillStyle = css('--bg'); g.fillRect(0, 0, S, S)
    // the sampling region: 1 and 2 std around where random codes come from
    const [mx, my] = model === 'vae' ? [0, 0] : stats.mean
    const [sx, sy] = model === 'vae' ? [1, 1] : stats.std
    g.strokeStyle = css('--dim'); g.setLineDash([4, 4]); g.lineWidth = 1
    for (const k of [1, 2]) {
      g.beginPath()
      g.ellipse(toX(mx), toY(my), (k * sx / (box.x1 - box.x0)) * S, (k * sy / (box.y1 - box.y0)) * S, 0, 0, 2 * Math.PI)
      g.stroke()
    }
    g.setLineDash([])
    // real codes: the cluster of the digit nearest your code stands out (bigger, full ink), the rest stay faint,
    // so moving your code across the map lights up one digit's cluster at a time
    const near = nearest.label
    for (const pass of [0, 1]) {
      g.fillStyle = css(pass ? '--fg' : '--dim')
      g.globalAlpha = pass ? 0.95 : 0.35
      const r = (pass ? 2.8 : 1.9) * (S / 360)
      codes.forEach((c, i) => {
        if ((data!.labels[i] === near) !== !!pass) return
        g.beginPath(); g.arc(toX(c[0]), toY(c[1]), r, 0, 2 * Math.PI); g.fill()
      })
    }
    g.globalAlpha = 1
    // the last "Draw 200" batch: hits as small accent rings, misses (empty regions) as warn crosses
    const u = S / 360
    for (const b of batch) {
      const x = toX(b.x), y = toY(b.y)
      if (b.empty) {
        g.strokeStyle = css('--warn'); g.lineWidth = 1.6 * u
        g.beginPath(); g.moveTo(x - 3 * u, y - 3 * u); g.lineTo(x + 3 * u, y + 3 * u); g.moveTo(x + 3 * u, y - 3 * u); g.lineTo(x - 3 * u, y + 3 * u); g.stroke()
      } else {
        g.strokeStyle = css('--accent'); g.lineWidth = 1.2 * u
        g.beginPath(); g.arc(x, y, 2.6 * u, 0, 2 * Math.PI); g.stroke()
      }
    }
    // digit labels at each digit's average code, pushed apart, each on a small backing plate; a label that had to
    // move far from its average code gets a thin leader line back to it. The label of the nearest digit is in full
    // ink; a label under your code's marker fades, so the marker stays readable
    const px = toX(z[0]), py = toY(z[1]), r = 9 * (S / 360)
    g.font = `700 ${Math.round(16 * u)}px ui-monospace, monospace`
    g.textAlign = 'center'; g.textBaseline = 'middle'
    g.strokeStyle = css('--dim'); g.lineWidth = 1 * u
    for (const c of placed) {
      if (Math.hypot(c.x - c.cx, c.y - c.cy) < 11) continue
      g.globalAlpha = 0.7
      g.beginPath(); g.moveTo(c.cx * u, c.cy * u); g.lineTo(c.x * u, c.y * u); g.stroke()
    }
    for (const c of placed) {
      const x = c.x * u, y = c.y * u
      const under = Math.abs(x - px) < 7 * u + r && Math.abs(y - py) < 9 * u + r
      g.fillStyle = css('--bg'); g.globalAlpha = under ? 0.5 : 0.85
      g.beginPath(); g.roundRect(x - 7 * u, y - 9 * u, 14 * u, 18 * u, 3 * u); g.fill()
      g.globalAlpha = under ? 0.35 : 1
      g.fillStyle = css(c.d === near ? '--fg' : '--dim'); g.fillText(String(c.d), x, y + 0.5 * u)
    }
    g.globalAlpha = 1
    // the current code
    const col = sampled && empty ? css('--warn') : css('--accent')
    g.strokeStyle = col; g.lineWidth = 2.5 * (S / 360)
    g.beginPath(); g.arc(px, py, r, 0, 2 * Math.PI); g.stroke()
    g.beginPath(); g.moveTo(px - 2 * r, py); g.lineTo(px - r, py); g.moveTo(px + r, py); g.lineTo(px + 2 * r, py)
    g.moveTo(px, py - 2 * r); g.lineTo(px, py - r); g.moveTo(px, py + r); g.lineTo(px, py + 2 * r); g.stroke()
  }

  function drawPic() {
    const dec = decs[model]
    if (!pic || !dec) return
    const img = decode(dec, z)
    const g = pic.getContext('2d')!
    const bg = hex(css('--bg')), fg = hex(css('--fg'))
    const id = g.createImageData(28, 28)
    for (let p = 0; p < 784; p++) {
      const v = img[p]
      for (let c = 0; c < 3; c++) id.data[p * 4 + c] = Math.round(bg[c] + (fg[c] - bg[c]) * v)
      id.data[p * 4 + 3] = 255
    }
    g.putImageData(id, 0, 0)
  }
  function hex(s: string): number[] {
    const m = s.replace('#', '')
    const full = m.length === 3 ? m.split('').map((c) => c + c).join('') : m
    return [0, 2, 4].map((i) => parseInt(full.slice(i, i + 2), 16) || 0)
  }

  function setModel(m: 'ae' | 'vae') {
    if (!data) return
    model = m
    sampled = false
    moved = false
    batch = []
    decs[m] ??= loadDecoder(data[m].decoder)
    const c = centroids.find((c) => c.d === 3)!
    z = [c.x, c.y]
  }
  function randomCode() {
    const [mx, my] = model === 'vae' ? [0, 0] : stats.mean
    const [sx, sy] = model === 'vae' ? [1, 1] : stats.std
    z = [mx + sx * gauss(), my + sy * gauss()]
    sampled = true
    moved = true
    batch = []
  }
  function fromPointer(e: PointerEvent) {
    const r = plane.getBoundingClientRect()
    const fx = (e.clientX - r.left) / r.width, fy = (e.clientY - r.top) / r.height
    z = [box.x0 + fx * (box.x1 - box.x0), box.y1 - fy * (box.y1 - box.y0)]
    sampled = false
    moved = true
  }
  let dragging = false
  // arrow keys move the code by 1/40 of the map (Shift: two steps)
  function key(e: KeyboardEvent) {
    const step = ((box.x1 - box.x0) / 40) * (e.shiftKey ? 2 : 1)
    const d: Record<string, [number, number]> = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, step], ArrowDown: [0, -step] }
    if (d[e.key]) { e.preventDefault(); z = [z[0] + d[e.key][0], z[1] + d[e.key][1]]; sampled = false; moved = true }
  }

  onMount(() => {
    fetch('/data/autoencoders/models.json').then((r) => r.json()).then((j: ModelsJSON) => {
      data = j
      setModel(start)
    })
    return onThemeChange(() => { drawPlane(); drawPic() })
  })

  $effect(() => {
    void z[0]; void z[1]; void model; void data; void sampled; void batch
    drawPlane()
    drawPic()
  })

  const f = (v: number) => (Math.abs(v) < 0.005 ? '0.00' : v.toFixed(2))
</script>

<LabFrame
  title="The code space: every point is a picture"
  hint="Drag on the map (or focus it and use the arrow keys) to pick a 2-number code. The trained decoder draws it, here in your browser."
  onreset={() => { share = {}; setModel(start) }}
  resetDisabled={!moved && model === start}
>
  <div class="row">
    <div class="planewrap">
      <canvas bind:this={plane} width="720" height="720" class="plane" tabindex="0" role="slider"
        aria-valuenow={Number(z[0].toFixed(2))} aria-valuetext={`code (${f(z[0])}, ${f(z[1])})`}
        aria-label="Code space: drag or use the arrow keys to choose a 2-number code"
        onpointerdown={(e) => { dragging = true; (e.currentTarget as Element).setPointerCapture(e.pointerId); fromPointer(e) }}
        onpointermove={(e) => dragging && fromPointer(e)} onpointerup={() => (dragging = false)} onpointercancel={() => (dragging = false)}
        onkeydown={key}></canvas>
      {#if !data}<p class="loading">Loading the trained decoders…</p>{/if}
    </div>
    <div class="side">
      <div class="cap">the decoder’s picture</div>
      <canvas bind:this={pic} width="28" height="28" class="pic" class:off={sampled && empty} aria-label="The decoder’s picture for the chosen code"></canvas>
      <p class="mono">code (<b>{f(z[0])}</b>, <b>{f(z[1])}</b>)</p>
    </div>
  </div>

  {#snippet controls()}
    <div class="seg" role="group" aria-label="Model">
      <button type="button" aria-pressed={model === 'ae'} class:on={model === 'ae'} onclick={() => setModel('ae')}>Plain autoencoder</button>
      <button type="button" aria-pressed={model === 'vae'} class:on={model === 'vae'} onclick={() => setModel('vae')}>VAE</button>
    </div>
    <button type="button" class="lab-btn primary" onclick={randomCode} disabled={!data}>Random code</button>
    <button type="button" class="lab-btn" onclick={() => drawMany()} disabled={!data}>Draw 200</button>
  {/snippet}

  {#snippet readout()}
    {#if !data}
      <span class="idle">Loading…</span>
    {:else if batch.length && share[model]}
      {@const m = share[model]!}
      {@const other = share[model === 'ae' ? 'vae' : 'ae']}
      <span>{m.miss} of {m.n} random codes landed in empty regions ({pct(m)}%).</span>
      {#if other}<span class="idle"> {model === 'ae' ? 'VAE' : 'Plain autoencoder'}: {pct(other)}%.</span>{:else}<span class="idle"> Switch to the {model === 'ae' ? 'VAE' : 'plain autoencoder'} and draw 200 again to compare.</span>{/if}
    {:else if sampled}
      <span class:warn={empty}>{empty ? 'Random code landed in an empty region: no real digit has a code nearby.' : `Random code landed among real codes (nearest: a ${nearest.label}).`}</span>
    {:else}
      code ({f(z[0])}, {f(z[1])}) · nearest real code: a <b>{nearest.label}</b>.
    {/if}
  {/snippet}

  {#snippet legend()}
    <span><i class="dot"></i>codes of 400 real test digits</span>
    <span><b class="big">3</b>each digit’s average code</span>
    <span><i class="ring"></i>1 and 2 std of {model === 'vae' ? 'N(0, 1), where the VAE draws new codes' : 'this model’s codes, where you would draw random ones'}</span>
    <span><i class="cross"></i>your code</span>
    {#if batch.length}<span><i class="hit"></i>a random code among real codes</span><span><i class="miss">×</i>a random code in an empty region</span>{/if}
    <span>Highlighted dots: the digit nearest your code.</span>
  {/snippet}
</LabFrame>

<style>
  .row { display: grid; grid-template-columns: minmax(0, 22rem) minmax(0, 1fr); gap: 1rem 1.2rem; align-items: start; }
  @media (max-width: 600px) { .row { grid-template-columns: minmax(0, 1fr); } }
  .planewrap { min-width: 0; position: relative; }
  .plane { width: 100%; aspect-ratio: 1; border: 1px solid var(--line); border-radius: 6px; cursor: crosshair; touch-action: none; display: block; background: var(--bg); }
  .plane:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .loading { position: absolute; inset: 0; margin: 0; display: grid; place-items: center; color: var(--dim); font-size: 0.85rem; pointer-events: none; }
  .side { display: grid; gap: 0.4rem; justify-items: start; min-width: 0; }
  @media (max-width: 600px) { .side { grid-template-columns: auto minmax(0, 1fr); align-items: center; column-gap: 0.9rem; } .side .cap { grid-column: 1 / -1; } }
  .cap { font-size: 0.8rem; color: var(--dim); }
  .pic { width: 10.5rem; height: 10.5rem; image-rendering: pixelated; border: 1px solid var(--line); border-radius: 6px; }
  .pic.off { border-color: var(--warn); }
  @media (max-width: 600px) { .pic { width: 8rem; height: 8rem; } }
  .mono { font-family: var(--mono); font-size: 0.88rem; margin: 0; }
  .warn { color: var(--warn); }
  .idle { font-family: system-ui, -apple-system, sans-serif; color: var(--dim); }
  .seg { display: inline-flex; border: 1px solid var(--field); border-radius: 6px; overflow: hidden; }
  .seg button { font: inherit; font-size: 0.85rem; min-height: 2.1rem; padding: 0.2rem 0.8rem; border: 0; background: var(--bg); color: var(--fg); cursor: pointer; }
  .seg button + button { border-left: 1px solid var(--field); }
  .seg button.on { color: var(--accent); background: var(--highlight); }
  .seg button:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
  @media (max-width: 760px) { .seg button { min-height: 2.5rem; } }
  .dot { display: inline-block; width: 0.45rem; height: 0.45rem; border-radius: 50%; background: var(--dim); opacity: 0.7; margin-right: 0.4rem; vertical-align: 0.05em; }
  .big { font-family: var(--mono); color: var(--fg); margin-right: 0.4rem; }
  .ring { display: inline-block; width: 0.9rem; height: 0.6rem; border: 1.5px dashed var(--dim); border-radius: 50%; margin-right: 0.4rem; vertical-align: -0.05em; }
  .hit { display: inline-block; width: 0.55rem; height: 0.55rem; border: 1.5px solid var(--accent); border-radius: 50%; margin-right: 0.4rem; vertical-align: 0; }
  .miss { font-style: normal; color: var(--warn); font-weight: 700; margin-right: 0.35rem; }
  .cross { display: inline-block; width: 0.7rem; height: 0.7rem; border: 2px solid var(--accent); border-radius: 50%; margin-right: 0.4rem; vertical-align: -0.1em; }
</style>
