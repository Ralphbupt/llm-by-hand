<script lang="ts">
  /**
   * The whole model as a diagram. Change the sizes; every block's shape and parameter count updates.
   *   variant 'decoder' (level 17, the default): the decoder-only model of content/2-theory/full-model/demo.py,
   *     72,106 parameters at the default size. Shapes for "427 = four hundred twenty seven" (L = 8).
   *   variant 'encdec' (N7): the encoder-decoder model of content/1-foundations/encoder-decoder/demo.py,
   *     171,232 parameters at the default size.
   */
  import LabFrame from './LabFrame.svelte'
  let { variant = 'decoder' }: { variant?: 'decoder' | 'encdec' } = $props()
  const SRC_V = 13, TGT_V = 32, SRC_L = 3, TGT_L = 5
  const V = 42, L = 8      // decoder-only: 42 tokens; the longest input is 8 tokens ("427 = four hundred twenty seven")

  let d = $state(64)
  let heads = $state(4)
  let layers = $state(2)
  let ratio = $state(2)
  let sel = $state('')      // '' = the main block (the decoder stack)

  const dims = [16, 32, 64, 128, 256, 512]
  const dff = $derived(d * ratio)
  const attn = $derived(4 * d * d + d)             // W_Q, W_K, W_V (no bias) + W_O with bias
  const ffn = $derived(2 * d * dff + dff + d)
  const ln = $derived(2 * d)
  const enc = $derived(attn + ffn + 2 * ln)
  const dec = $derived(2 * attn + ffn + 3 * ln)
  const blk = $derived(attn + ffn + 2 * ln)        // decoder-only block: pre-norm attention + pre-norm FFN

  type Block = { id: string; name: string; inS: string; outS: string; params: number; what: string; side: 'enc' | 'dec' | 'one' }
  const decoderOnly = $derived<Block[]>([
    { id: 'emb', side: 'one', name: 'Token embedding + position', inS: `(1, ${L}) ids`, outS: `(1, ${L}, ${d})`, params: V * d,
      what: `A lookup table with one row of ${d} numbers for each of the ${V} tokens (digits, “=”, the words, <pad>, <eos>), multiplied by √${d}. Then the position numbers are added. They are fixed, so they have no parameters.` },
    { id: 'blk', side: 'one', name: `Decoder block × ${layers}`, inS: `(1, ${L}, ${d})`, outS: `(1, ${L}, ${d})`, params: layers * blk,
      what: `Each block: LayerNorm, masked self-attention (${heads} heads of size ${d / heads}; each position sees only itself and earlier ones), added back to x; then LayerNorm, the FFN (${d} → ${dff} → ${d}), added back. One block has ${blk.toLocaleString('en-US')} parameters: attention ${attn.toLocaleString('en-US')}, FFN ${ffn.toLocaleString('en-US')}, two LayerNorms ${(2 * ln).toLocaleString('en-US')}.` },
    { id: 'norm', side: 'one', name: 'Final LayerNorm', inS: `(1, ${L}, ${d})`, outS: `(1, ${L}, ${d})`, params: ln,
      what: `One more LayerNorm after the last block: a learned gain and shift (γ and β) for each of the ${d} numbers.` },
    { id: 'out', side: 'one', name: 'Output layer', inS: `(1, ${L}, ${d})`, outS: `(1, ${L}, ${V})`, params: d * V + V,
      what: `A (${d} × ${V}) matrix plus a bias. Every position gets ${V} scores, one per token. The score at position t is the guess for token t + 1; the loss only counts the guesses that start at “=”.` },
  ])
  const encdec = $derived<Block[]>([
    { id: 'semb', side: 'enc', name: 'Source embedding + position', inS: `(1, ${SRC_L}) ids`, outS: `(1, ${SRC_L}, ${d})`, params: SRC_V * d,
      what: `A lookup table with one row of ${d} numbers per digit (${SRC_V} rows). Then the position numbers are added. They are fixed, so they have no parameters.` },
    { id: 'enc', side: 'enc', name: `Encoder layer × ${layers}`, inS: `(1, ${SRC_L}, ${d})`, outS: `(1, ${SRC_L}, ${d})`, params: layers * enc,
      what: `Each layer: self-attention (${heads} heads of size ${d / heads}), then the FFN (${d} → ${dff} → ${d}), each with a residual and a LayerNorm. One layer has ${enc.toLocaleString('en-US')} parameters.` },
    { id: 'mem', side: 'enc', name: 'memory', inS: `(1, ${SRC_L}, ${d})`, outS: `(1, ${SRC_L}, ${d})`, params: 0,
      what: `The encoder’s output: one vector per input digit. It is not a layer. Every decoder layer reads it through cross-attention.` },
    { id: 'temb', side: 'dec', name: 'Target embedding + position', inS: `(1, ${TGT_L}) ids`, outS: `(1, ${TGT_L}, ${d})`, params: TGT_V * d,
      what: `The same kind of lookup table for the ${TGT_V} output words.` },
    { id: 'dec', side: 'dec', name: `Decoder layer × ${layers}`, inS: `(1, ${TGT_L}, ${d})`, outS: `(1, ${TGT_L}, ${d})`, params: layers * dec,
      what: `Each layer has three parts: masked self-attention (each word sees only earlier words), cross-attention (Q from the words, K and V from memory), and the FFN. One layer has ${dec.toLocaleString('en-US')} parameters.` },
    { id: 'out', side: 'dec', name: 'Output layer', inS: `(1, ${TGT_L}, ${d})`, outS: `(1, ${TGT_L}, ${TGT_V})`, params: d * TGT_V + TGT_V,
      what: `A (${d} × ${TGT_V}) matrix plus a bias. Every position gets ${TGT_V} scores, one per word. The score at position t is the guess for word t + 1.` },
  ])
  const blocks = $derived(variant === 'decoder' ? decoderOnly : encdec)
  const total = $derived(blocks.reduce((s, b) => s + b.params, 0))
  const cur = $derived(blocks.find((b) => b.id === sel) ?? blocks.find((b) => b.id === (variant === 'decoder' ? 'blk' : 'dec'))!)
  const fmt = (n: number) => n.toLocaleString('en-US')

  function preset(p: number[]) { [d, heads, layers, ratio] = p }
  const changed = $derived(d !== 64 || heads !== 4 || layers !== 2 || ratio !== 2)
</script>

<LabFrame
  title="The whole model, block by block"
  hint="Pick a block to see its input, its output and how many parameters it holds. Change the sizes below."
  onreset={() => preset([64, 4, 2, 2])}
  resetDisabled={!changed}
>
  <div class="layout" class:two={variant === 'decoder'}>
  <div class="diagram" class:single={variant === 'decoder'}>
    {#each variant === 'decoder' ? ['one'] : ['enc', 'dec'] as side}
      <div class="col">
        <div class="colh">{side === 'one' ? 'One stack: reads “427 =”, writes the words' : side === 'enc' ? 'Encoder: reads “427”' : 'Decoder: writes the words'}</div>
        {#each blocks.filter((b) => b.side === side) as b}
          <button type="button" class="blk" class:on={cur.id === b.id} class:ghost={b.params === 0} aria-pressed={cur.id === b.id} onclick={() => (sel = b.id)}>
            <span class="nm">{b.name}</span>
            <span class="sh">{b.outS}</span>
            {#if b.id === 'dec'}<span class="reads">reads memory through cross-attention</span>{/if}
            {#if b.params}<span class="bar" title={`${((100 * b.params) / total).toFixed(1)}% of all parameters`}><i style="width: {(100 * b.params) / total}%"></i></span>{/if}
          </button>
        {/each}
      </div>
    {/each}
  </div>

  <div class="detail" aria-live="polite">
    <div class="dh"><b>{cur.name}</b> <span class="mono">{cur.inS} → {cur.outS}</span></div>
    <p>{cur.what}</p>
    <p class="mono">parameters: {fmt(cur.params)}{cur.params ? ` (${((100 * cur.params) / total).toFixed(1)}% of all)` : ''}</p>
  </div>
  </div>

  {#snippet controls()}
    <label class="knob">d_model
      <select bind:value={d}>{#each dims as v}<option value={v}>{v}</option>{/each}</select>
    </label>
    <label class="knob">heads
      <select bind:value={heads}>{#each [1, 2, 4, 8] as v}<option value={v}>{v}</option>{/each}</select>
    </label>
    <label class="knob">layers <b>{layers}</b>
      <input type="range" min="1" max="6" bind:value={layers} />
    </label>
    <label class="knob">d_ff
      <select bind:value={ratio}><option value={2}>2 × d_model</option><option value={4}>4 × d_model</option></select>
    </label>
    <button type="button" class="lab-btn" onclick={() => preset([512, 8, 6, 4])}>Try a big setting</button>
  {/snippet}

  {#snippet readout()}
    total parameters: <b>{fmt(total)}</b> · d_k per head = {d / heads}
  {/snippet}

  {#snippet legend()}
    <span class="lg"><i class="sw" style="background: color-mix(in srgb, var(--fg) 45%, var(--bg))"></i>fraction of all parameters</span>
    <span class="lg"><i class="sw dash"></i>not a layer (no parameters)</span>
  {/snippet}
</LabFrame>

<style>
  .knob { display: inline-flex; gap: 0.4rem; align-items: center; font-size: 0.85rem; color: var(--dim); margin-right: 0.4rem; }
  .knob b { color: var(--fg); font-family: var(--mono); }
  select { font: inherit; font-size: 0.88rem; min-height: 2.1rem; background: var(--bg); color: var(--fg); border: 1px solid var(--field); border-radius: 6px; padding: 0.1rem 0.4rem; }
  input[type='range'] { width: 7rem; accent-color: var(--accent); }
  .diagram { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.8rem; }
  .diagram.single { grid-template-columns: minmax(0, 1fr); }
  .layout { display: flex; flex-direction: column; gap: 0.8rem; }
  /* one stack: the list on the left, the selected block's details on the right */
  @media (min-width: 700px) {
    .layout.two { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 1rem; align-items: start; }
    .layout.two .detail { position: sticky; top: 1rem; }
  }
  @media (max-width: 560px) { .diagram, .diagram.single { grid-template-columns: minmax(0, 1fr); } }
  .col { display: flex; flex-direction: column; gap: 0.4rem; min-width: 0; }
  .colh { font-size: 0.82rem; color: var(--dim); }
  .blk { display: grid; grid-template-columns: 1fr auto; gap: 0.2rem 0.6rem; text-align: left; font: inherit; font-size: 0.88rem;
    padding: 0.5rem 0.65rem; border: 1.5px solid var(--line); border-radius: 6px; background: var(--bg); color: var(--fg); cursor: pointer; }
  .blk:hover { border-color: var(--fg); }
  /* the shared "on" style of .lab-btn[aria-pressed] */
  .blk.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  .blk:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .blk.ghost { border-style: dashed; }
  .sh { font-family: var(--mono); font-size: 0.8rem; color: var(--dim); }
  .reads { grid-column: 1 / -1; font-size: 0.78rem; color: var(--dim); }
  .reads::before { content: '← '; }
  .bar { grid-column: 1 / -1; height: 4px; background: var(--line); border-radius: 2px; overflow: hidden; }
  .bar i { display: block; height: 100%; background: color-mix(in srgb, var(--fg) 45%, var(--bg)); }
  .detail { padding: 0.6rem 0.8rem; border-left: 3px solid var(--accent); background: var(--bg); border-radius: 4px; font-size: 0.9rem; }
  .detail p { margin: 0.3rem 0 0; }
  .dh { display: flex; flex-wrap: wrap; gap: 0.2rem 0.8rem; align-items: baseline; }
  .mono { font-family: var(--mono); font-size: 0.85rem; }
  .lg { display: inline-flex; align-items: center; gap: 0.35rem; }
  .sw { width: 0.9rem; height: 0.55rem; border-radius: 2px; display: inline-block; }
  .sw.dash { border: 1.5px dashed var(--field); }
  /* phones: touch targets at least 40px tall; 16px fields so iOS does not zoom */
  @media (max-width: 760px) { select { min-height: 2.5rem; font-size: 16px; } input[type='range'] { min-height: 2.5rem; } }
</style>
