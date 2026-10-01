<script lang="ts">
  /**
   * Greedy decoding, one step at a time, with a real trained model. Used by two levels:
   *   level 17 (data 'full-model', the default): a decoder-only model; steps carry `att`, the last row's
   *     self-attention over the whole input (digits, "=", words so far), last layer, heads averaged.
   *   N7 (data 'encoder-decoder'): the encoder-decoder model; steps carry `cross`, cross-attention over the digits.
   * Data: site/public/data/<data>/decode.json (written by content/<part>/<data>/export.py). It holds two snapshots,
   * keys `epoch<N>`: the earlier one is the early model, the later one the final model.
   */
  import { onMount } from 'svelte'
  import LabFrame from './LabFrame.svelte'

  type Step = { input: string[]; last: number[]; logits: number[]; pick: string; cross?: number[]; att?: number[] }
  type Case = { n: number; truth: string[]; steps: Step[] }
  type Data = { vocab: string[]; curve: { epoch: number; loss: number; acc: number }[]; [snap: `epoch${number}`]: Case[] }

  let { data: slug = 'full-model' }: { data?: string } = $props()
  let data = $state<Data | null>(null)
  let failed = $state(false)
  let which = $state<'final' | 'early'>('final')
  let ci = $state(3)
  let k = $state(0)      // how many steps have been taken

  onMount(async () => {
    try { data = await (await fetch(`/data/${slug}/decode.json`)).json() } catch { failed = true }
  })

  // the two snapshots, by epoch number: [early, final]
  const snaps = $derived(data ? (Object.keys(data).filter((key) => /^epoch\d+$/.test(key)) as `epoch${number}`[])
    .map((key) => ({ key, epoch: Number(key.slice(5)) })).sort((a, b) => a.epoch - b.epoch) : [])
  const early = $derived(snaps[0])
  const final = $derived(snaps[snaps.length - 1])
  const snap = $derived(which === 'early' ? early : final)
  const cases = $derived(data && snap ? data[snap.key] : [])
  const cs = $derived(cases[ci] ?? null)
  const step = $derived(cs && k > 0 ? cs.steps[k - 1] : null)
  const next = $derived(cs && k < cs.steps.length ? cs.steps[k] : null)
  const out = $derived(cs ? cs.steps.slice(0, k).map((s) => s.pick) : [])
  const finished = $derived(cs ? k === cs.steps.length : false)
  const cross = $derived(cs ? cs.steps.some((s) => s.cross) : false)    // encoder-decoder data
  const dModel = $derived(cs ? cs.steps[0].last.length : 0)
  const V = $derived(data ? data.vocab.length : 0)
  const top = $derived(step && data
    ? step.logits.map((v, i) => ({ w: data!.vocab[i], v })).sort((a, b) => b.v - a.v).slice(0, 8) : [])
  const maxAbs = $derived(step ? Math.max(...step.last.map(Math.abs)) : 1)
  const lo = $derived(top.length ? Math.min(0, top[top.length - 1].v) : 0)
  const hi = $derived(top.length ? top[0].v : 1)

  function choose(i: number) { ci = i; k = 0 }
  function cell(v: number) {
    const p = Math.round((70 * Math.abs(v)) / maxAbs)
    return `background: color-mix(in srgb, var(${v >= 0 ? '--pos' : '--neg'}) ${p}%, var(--bg))`
  }
  const words = (a: string[]) => a.filter((w) => w !== '<eos>').join(' ')
  // the word the model should have picked at this step (from the reference answer, <eos> after the last word)
  const truthNow = $derived(cs && k > 0 ? (cs.truth[k - 1] ?? '<eos>') : null)
  const wrong = $derived(step && truthNow !== null && step.pick !== truthNow)
  const truthRank = $derived(step && data && truthNow ? step.logits.map((v, i) => ({ w: data!.vocab[i], v })).sort((a, b) => b.v - a.v).findIndex((t) => t.w === truthNow) : -1)
</script>

<LabFrame
  title="Greedy decoding, one word at a time"
  hint="Pick a number for the trained model to read aloud, then press Next step to watch it choose each word."
>
  {#if failed}
    <p class="dim">Could not load the recorded model. Reload the page to try again.</p>
  {:else if !data || !cs}
    <div class="skeleton" aria-hidden="true"></div>
    <p class="dim">Loading the trained model’s recording…</p>
  {:else}
    <div class="pickers">
      <div class="seg" role="group" aria-label="Number to read aloud">
        <span class="seglbl">Read aloud</span>
        <span class="chips">
          {#each cases as c, i}
            <button type="button" class="chip" class:on={ci === i} aria-pressed={ci === i} onclick={() => choose(i)}>{c.n}</button>
          {/each}
        </span>
      </div>
      <div class="seg" role="group" aria-label="Which model">
        <span class="seglbl">Model</span>
        <span class="chips">
          <button type="button" class="chip" class:on={which === 'early'} aria-pressed={which === 'early'} onclick={() => { which = 'early'; k = 0 }}>after {early?.epoch} epochs</button>
          <button type="button" class="chip" class:on={which === 'final'} aria-pressed={which === 'final'} onclick={() => { which = 'final'; k = 0 }}>after {final?.epoch} epochs</button>
        </span>
      </div>
    </div>

    {#if cross}
      <div class="src">
        {#each String(cs.n).split('') as dgt, j}
          <div class="dg">
            <span class="d">{dgt}</span>
            <span class="cb"><i style="height: {step?.cross ? 100 * step.cross[j] : 0}%"></i></span>
            <span class="cv">{step?.cross ? step.cross[j].toFixed(2) : ''}</span>
          </div>
        {/each}
        <p class="dim small">Bars: where cross-attention looked while choosing this step’s word (last layer, heads averaged).</p>
      </div>
    {/if}

    <div class="flow">
      <div>
        <div class="lbl">{cross ? 'Decoder input' : 'Input'}{step ? ` · ${step.input.length} row${step.input.length > 1 ? 's' : ''}` : ''}</div>
        {#if !cross}
          <div class="toks">
            {#each (step ? step.input : next ? next.input : []) as t, j}
              <div class="dg at">
                <span class="cb"><i style="height: {step?.att ? 100 * step.att[j] : 0}%"></i></span>
                <span class="cv">{step?.att ? step.att[j].toFixed(2) : ''}</span>
                <span class="tok" class:last={step && j === step.input.length - 1}>{t}</span>
              </div>
            {/each}
            {#if step}<span class="note">← only the last row picks the next word</span>{/if}
          </div>
          <p class="dim small">Bars: where the last row’s attention looked while choosing this step’s word (last layer, heads averaged).</p>
        {:else}
          <div class="toks">
            {#each (step ? step.input : next ? next.input : []) as t, j}<span class="tok" class:last={step && j === step.input.length - 1}>{t}</span>{/each}
            {#if step}<span class="note">← only the last row picks the next word</span>{/if}
          </div>
        {/if}
      </div>
      {#if step}
        <div>
          <div class="lbl">Last row of the {cross ? 'decoder' : 'model'}’s output: {dModel} numbers</div>
          <div class="strip">{#each step.last as v}<i style={cell(v)} title={v.toFixed(2)}></i>{/each}</div>
          <div class="mono small">[{step.last.slice(0, 4).map((v) => v.toFixed(2)).join(', ')}, …]</div>
        </div>
        <div>
          <div class="lbl">× output layer ({dModel} × {V}) + bias → {V} scores (top 8 shown)</div>
          <div class="bars">
            {#each top as t, i}
              <div class="br" class:win={i === 0} class:truth={wrong && t.w === truthNow}>
                <span class="w">{t.w}</span>
                <span class="track"><i style="width: {(100 * (t.v - lo)) / (hi - lo || 1)}%"></i></span>
                <span class="v mono">{t.v.toFixed(1)}</span>
              </div>
            {/each}
          </div>
          <div class="pick">argmax → <b>{step.pick}</b>
            {#if wrong}<span class="miss">· the right word was <b>{truthNow}</b>{truthRank >= 0 ? ` (ranked ${truthRank + 1})` : ''}</span>{/if}</div>
        </div>
      {:else}
        <p class="dim small">Press <b>Next step</b>: {cross ? 'the model reads the digits once, then writes the first word.' : 'the model reads the digits and “=”, then writes the first word.'}</p>
      {/if}
    </div>
  {/if}

  {#snippet controls()}
    <button type="button" class="lab-btn" onclick={() => (k = Math.max(0, k - 1))} disabled={!cs || k === 0}>‹ Back</button>
    <button type="button" class="lab-btn primary" onclick={() => (k = k + 1)} disabled={!cs || finished}>Next step ›</button>
    <button type="button" class="lab-btn ghost" onclick={() => (k = 0)} disabled={!cs || k === 0}>Start again</button>
    {#if cs}<span class="stepn mono">step {k} / {cs.steps.length}</span>{/if}
  {/snippet}

  {#snippet readout()}
    {#if cs}
      output so far: <b>{words(out) || '…'}</b>
      {#if finished}
        {#if words(out) === cs.truth.join(' ')}<span class="ok">✓ correct</span>
        {:else}<span class="bad">✗ should be “{cs.truth.join(' ')}”</span>{/if}
      {/if}
    {:else}…{/if}
  {/snippet}

  {#snippet legend()}
    <span class="lg"><i class="sw" style="background: color-mix(in srgb, var(--pos) 70%, var(--bg))"></i>positive number</span>
    <span class="lg"><i class="sw" style="background: color-mix(in srgb, var(--neg) 70%, var(--bg))"></i>negative number</span>
    <span class="lg"><i class="sw" style="background: var(--accent)"></i>the word it picks</span>
    <span class="lg"><i class="sw" style="background: var(--ok)"></i>the right word, when it picks wrong</span>
  {/snippet}
</LabFrame>

<style>
  .skeleton { height: 12rem; border-radius: 6px; background: var(--bg); border: 1px dashed var(--line); }
  .pickers { display: grid; gap: 0.5rem; }
  /* the label in its own column; wrapped chips line up under the first chip, not under the label */
  .seg { display: grid; grid-template-columns: 5.5rem 1fr; gap: 0.35rem; align-items: start; }
  .seglbl { font-size: 0.82rem; color: var(--dim); min-height: 2.1rem; display: flex; align-items: center; }
  .chips { display: flex; flex-wrap: wrap; gap: 0.35rem; }
  .chip { font: inherit; font-family: var(--mono); font-size: 0.85rem; padding: 0.25rem 0.75rem; min-height: 2.1rem; border: 1px solid var(--field);
    border-radius: 999px; background: var(--bg); color: var(--fg); cursor: pointer; }
  .chip.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  .chip:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .tok.last { border-color: var(--accent); color: var(--accent); }
  .note { font-size: 0.8rem; color: var(--dim); align-self: center; }
  .br.truth .w { color: var(--ok); font-weight: 700; }
  .br.truth .track i { background: var(--ok); }
  .miss { color: var(--dim); font-size: 0.88rem; margin-left: 0.3rem; }
  .miss b { color: var(--ok); }
  .dim { color: var(--dim); }
  .small { font-size: 0.8rem; margin: 0.3rem 0 0; }
  .mono { font-family: var(--mono); font-size: 0.82rem; }
  .src { display: flex; flex-wrap: wrap; gap: 0.6rem; align-items: flex-end; margin: 0.3rem 0; }
  .src p { flex-basis: 100%; }
  .dg.at { width: auto; min-width: 2.6rem; }
  .dg { display: flex; flex-direction: column; align-items: center; gap: 0.2rem; width: 2.6rem; }
  .d { font-family: var(--mono); font-size: 1.3rem; font-weight: 700; }
  .cb { width: 1.2rem; height: 3rem; background: var(--line); border-radius: 3px; display: flex; align-items: flex-end; overflow: hidden; }
  .cb i { display: block; width: 100%; background: var(--accent); transition: height 0.2s; }
  .cv { font-family: var(--mono); font-size: 0.75rem; color: var(--dim); min-height: 1em; }
  .flow { display: grid; gap: 0.8rem; }
  .lbl { font-size: 0.8rem; color: var(--dim); margin-bottom: 0.25rem; }
  .toks { display: flex; flex-wrap: wrap; gap: 0.3rem; min-height: 1.6rem; }
  .tok { font-family: var(--mono); font-size: 0.82rem; padding: 0.1rem 0.45rem; border: 1px solid var(--line); border-radius: 4px; background: var(--bg); }
  .strip { display: grid; grid-template-columns: repeat(32, minmax(0, 1fr)); gap: 1px; max-width: 520px; }
  .strip i { display: block; aspect-ratio: 1; border-radius: 1px; }
  .bars { display: grid; gap: 0.2rem; max-width: 420px; }
  .br { display: grid; grid-template-columns: 5.5rem minmax(0, 1fr) 2.8rem; gap: 0.5rem; align-items: center; font-size: 0.85rem; }
  .w { font-family: var(--mono); overflow: hidden; text-overflow: ellipsis; }
  .track { height: 0.75rem; background: var(--line); border-radius: 2px; overflow: hidden; }
  .track i { display: block; height: 100%; background: var(--dim); transition: width 0.2s; }
  .br.win .track i { background: var(--accent); }
  .br.win .w { color: var(--accent); font-weight: 700; }
  .v { text-align: right; color: var(--dim); }
  .pick { margin-top: 0.4rem; font-size: 0.92rem; }
  .pick b { color: var(--accent); font-family: var(--mono); }
  .stepn { color: var(--dim); }
  .ok { color: var(--ok); margin-left: 0.5rem; }
  .bad { color: var(--warn); margin-left: 0.5rem; }
  .lg { display: inline-flex; align-items: center; gap: 0.35rem; }
  .sw { width: 0.85rem; height: 0.7rem; border-radius: 2px; display: inline-block; }
  @media (prefers-reduced-motion: reduce) { .track i, .cb i { transition: none; } }
  /* phones: touch targets at least 40px tall; 16px fields so iOS does not zoom */
  @media (max-width: 760px) { .chip, .seglbl { min-height: 2.5rem; } }
</style>
