<script lang="ts">
  /**
   * The whole model as a diagram. Change the sizes; every block's shape and parameter count updates.
   *   variant 'decoder' (level 17, the default): the decoder-only model of content/2-theory/full-model/demo.py,
   *     72,106 parameters at the default size. Shapes for "427 = four hundred twenty seven" (L = 8).
   *   variant 'encdec' (N7): the encoder-decoder model of content/1-foundations/encoder-decoder/demo.py,
   *     171,232 parameters at the default size.
   */
  import LabFrame from './LabFrame.svelte'
  import { provideLang, useT } from '@lib/i18nSvelte'
  import type { Lang } from '@lib/i18n'
  let { variant = 'decoder', lang = 'en' }: { variant?: 'decoder' | 'encdec'; lang?: Lang } = $props()
  provideLang(lang)
  const t = useT({
    '({n}) ids': '({n}) 个 id',
    'Token embedding + position': 'token 嵌入 + 位置',
    'A lookup table with one row of {d} numbers for each of the {v} tokens (digits, “=”, the words, <pad>, <eos>), multiplied by √{d}. Then the position numbers are added. They are fixed, so they have no parameters.':
      '一张查找表，{v} 个 token（数字、“=”、英文单词、<pad>、<eos>）每个一行，每行 {d} 个数，再乘以 √{d}。然后加上位置数值。位置数值是固定的，所以没有参数。',
    'Decoder block × {n}': '解码器块 × {n}',
    'Each block: LayerNorm, masked self-attention ({h} heads of size {s}; each position sees only itself and earlier ones), added back to x; then LayerNorm, the FFN ({d} → {f} → {d}), added back. One block has {blk} parameters: attention {attn}, FFN {ffn}, two LayerNorms {ln}.':
      '每个块：LayerNorm，带掩码的自注意力（{h} 个头，每个大小 {s}；每个位置只看到自己和前面的位置），加回 x；然后 LayerNorm，FFN（{d} → {f} → {d}），再加回去。一个块有 {blk} 个参数：注意力 {attn}，FFN {ffn}，两个 LayerNorm {ln}。',
    'Final LayerNorm': '最后的 LayerNorm',
    'One more LayerNorm after the last block: a learned gain and shift (γ and β) for each of the {d} numbers.': '最后一个块之后再加一个 LayerNorm：{d} 个数每个都有学出来的缩放和平移（γ 和 β）。',
    'Output layer': '输出层',
    'A ({d} × {v}) matrix plus a bias. Every position gets {v} scores, one per token. The score at position t is the guess for token t + 1; the loss only counts the guesses that start at “=”.':
      '一个 ({d} × {v}) 的矩阵加一个偏置。每个位置得到 {v} 个分数，每个 token 一个。位置 t 的分数是对第 t + 1 个 token 的猜测；损失只算从“=”开始的那些猜测。',
    'Source embedding + position': '源嵌入 + 位置',
    'A lookup table with one row of {d} numbers per digit ({v} rows). Then the position numbers are added. They are fixed, so they have no parameters.':
      '一张查找表，每个数字一行，每行 {d} 个数（共 {v} 行）。然后加上位置数值。位置数值是固定的，所以没有参数。',
    'Encoder layer × {n}': '编码器层 × {n}',
    'Each layer: self-attention ({h} heads of size {s}), then the FFN ({d} → {f} → {d}), each with a residual and a LayerNorm. One layer has {n} parameters.':
      '每一层：自注意力（{h} 个头，每个大小 {s}），然后是 FFN（{d} → {f} → {d}），各带一个残差和一个 LayerNorm。一层有 {n} 个参数。',
    'The encoder’s output: one vector per input digit. It is not a layer. Every decoder layer reads it through cross-attention.': '编码器的输出：每个输入数字一个向量。它不是一层。每个解码器层都通过交叉注意力读它。',
    'Target embedding + position': '目标嵌入 + 位置',
    'The same kind of lookup table for the {v} output words.': '同样的查找表，给 {v} 个输出词用。',
    'Decoder layer × {n}': '解码器层 × {n}',
    'Each layer has three parts: masked self-attention (each word sees only earlier words), cross-attention (Q from the words, K and V from memory), and the FFN. One layer has {n} parameters.':
      '每一层有三部分：带掩码的自注意力（每个词只看到前面的词）、交叉注意力（Q 来自词，K 和 V 来自 memory）和 FFN。一层有 {n} 个参数。',
    'A ({d} × {v}) matrix plus a bias. Every position gets {v} scores, one per word. The score at position t is the guess for word t + 1.':
      '一个 ({d} × {v}) 的矩阵加一个偏置。每个位置得到 {v} 个分数，每个词一个。位置 t 的分数是对第 t + 1 个词的猜测。',
    'The whole model, block by block': '整个模型，一块一块地看',
    'Pick a block to see its input, its output and how many parameters it holds. Change the sizes below.': '选一个方块，看它的输入、输出和它有多少参数。在下面改变大小。',
    'One stack: reads “427 =”, writes the words': '一摞层：读“427 =”，写出英文单词',
    'Encoder: reads “427”': '编码器：读“427”',
    'Decoder: writes the words': '解码器：写出英文单词',
    'reads memory through cross-attention': '通过交叉注意力读 memory',
    '{p}% of all parameters': '占全部参数的 {p}%',
    'parameters:': '参数：',
    ' ({p}% of all)': '（占全部的 {p}%）',
    heads: '头数',
    layers: '层数',
    'Try a big setting': '试试大配置',
    'total parameters:': '参数总数：',
    'd_k per head': '每个头的 d_k',
    'fraction of all parameters': '占全部参数的比例',
    'not a layer (no parameters)': '不是一层（没有参数）',
  })
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
    { id: 'emb', side: 'one', name: t('Token embedding + position'), inS: t('({n}) ids', { n: `1, ${L}` }), outS: `(1, ${L}, ${d})`, params: V * d,
      what: t('A lookup table with one row of {d} numbers for each of the {v} tokens (digits, “=”, the words, <pad>, <eos>), multiplied by √{d}. Then the position numbers are added. They are fixed, so they have no parameters.', { d, v: V }) },
    { id: 'blk', side: 'one', name: t('Decoder block × {n}', { n: layers }), inS: `(1, ${L}, ${d})`, outS: `(1, ${L}, ${d})`, params: layers * blk,
      what: t('Each block: LayerNorm, masked self-attention ({h} heads of size {s}; each position sees only itself and earlier ones), added back to x; then LayerNorm, the FFN ({d} → {f} → {d}), added back. One block has {blk} parameters: attention {attn}, FFN {ffn}, two LayerNorms {ln}.', { h: heads, s: d / heads, d, f: dff, blk: blk.toLocaleString('en-US'), attn: attn.toLocaleString('en-US'), ffn: ffn.toLocaleString('en-US'), ln: (2 * ln).toLocaleString('en-US') }) },
    { id: 'norm', side: 'one', name: t('Final LayerNorm'), inS: `(1, ${L}, ${d})`, outS: `(1, ${L}, ${d})`, params: ln,
      what: t('One more LayerNorm after the last block: a learned gain and shift (γ and β) for each of the {d} numbers.', { d }) },
    { id: 'out', side: 'one', name: t('Output layer'), inS: `(1, ${L}, ${d})`, outS: `(1, ${L}, ${V})`, params: d * V + V,
      what: t('A ({d} × {v}) matrix plus a bias. Every position gets {v} scores, one per token. The score at position t is the guess for token t + 1; the loss only counts the guesses that start at “=”.', { d, v: V }) },
  ])
  const encdec = $derived<Block[]>([
    { id: 'semb', side: 'enc', name: t('Source embedding + position'), inS: t('({n}) ids', { n: `1, ${SRC_L}` }), outS: `(1, ${SRC_L}, ${d})`, params: SRC_V * d,
      what: t('A lookup table with one row of {d} numbers per digit ({v} rows). Then the position numbers are added. They are fixed, so they have no parameters.', { d, v: SRC_V }) },
    { id: 'enc', side: 'enc', name: t('Encoder layer × {n}', { n: layers }), inS: `(1, ${SRC_L}, ${d})`, outS: `(1, ${SRC_L}, ${d})`, params: layers * enc,
      what: t('Each layer: self-attention ({h} heads of size {s}), then the FFN ({d} → {f} → {d}), each with a residual and a LayerNorm. One layer has {n} parameters.', { h: heads, s: d / heads, d, f: dff, n: enc.toLocaleString('en-US') }) },
    { id: 'mem', side: 'enc', name: 'memory', inS: `(1, ${SRC_L}, ${d})`, outS: `(1, ${SRC_L}, ${d})`, params: 0,
      what: t('The encoder’s output: one vector per input digit. It is not a layer. Every decoder layer reads it through cross-attention.') },
    { id: 'temb', side: 'dec', name: t('Target embedding + position'), inS: t('({n}) ids', { n: `1, ${TGT_L}` }), outS: `(1, ${TGT_L}, ${d})`, params: TGT_V * d,
      what: t('The same kind of lookup table for the {v} output words.', { v: TGT_V }) },
    { id: 'dec', side: 'dec', name: t('Decoder layer × {n}', { n: layers }), inS: `(1, ${TGT_L}, ${d})`, outS: `(1, ${TGT_L}, ${d})`, params: layers * dec,
      what: t('Each layer has three parts: masked self-attention (each word sees only earlier words), cross-attention (Q from the words, K and V from memory), and the FFN. One layer has {n} parameters.', { n: dec.toLocaleString('en-US') }) },
    { id: 'out', side: 'dec', name: t('Output layer'), inS: `(1, ${TGT_L}, ${d})`, outS: `(1, ${TGT_L}, ${TGT_V})`, params: d * TGT_V + TGT_V,
      what: t('A ({d} × {v}) matrix plus a bias. Every position gets {v} scores, one per word. The score at position t is the guess for word t + 1.', { d, v: TGT_V }) },
  ])
  const blocks = $derived(variant === 'decoder' ? decoderOnly : encdec)
  const total = $derived(blocks.reduce((s, b) => s + b.params, 0))
  const cur = $derived(blocks.find((b) => b.id === sel) ?? blocks.find((b) => b.id === (variant === 'decoder' ? 'blk' : 'dec'))!)
  const fmt = (n: number) => n.toLocaleString('en-US')

  function preset(p: number[]) { [d, heads, layers, ratio] = p }
  const changed = $derived(d !== 64 || heads !== 4 || layers !== 2 || ratio !== 2)
</script>

<LabFrame
  title={t('The whole model, block by block')}
  hint={t('Pick a block to see its input, its output and how many parameters it holds. Change the sizes below.')}
  onreset={() => preset([64, 4, 2, 2])}
  resetDisabled={!changed}
>
  <div class="layout" class:two={variant === 'decoder'}>
  <div class="diagram" class:single={variant === 'decoder'}>
    {#each variant === 'decoder' ? ['one'] : ['enc', 'dec'] as side}
      <div class="col">
        <div class="colh">{side === 'one' ? t('One stack: reads “427 =”, writes the words') : side === 'enc' ? t('Encoder: reads “427”') : t('Decoder: writes the words')}</div>
        {#each blocks.filter((b) => b.side === side) as b}
          <button type="button" class="blk" class:on={cur.id === b.id} class:ghost={b.params === 0} aria-pressed={cur.id === b.id} onclick={() => (sel = b.id)}>
            <span class="nm">{b.name}</span>
            <span class="sh">{b.outS}</span>
            {#if b.id === 'dec'}<span class="reads">{t('reads memory through cross-attention')}</span>{/if}
            {#if b.params}<span class="bar" title={t('{p}% of all parameters', { p: ((100 * b.params) / total).toFixed(1) })}><i style="width: {(100 * b.params) / total}%"></i></span>{/if}
          </button>
        {/each}
      </div>
    {/each}
  </div>

  <div class="detail" aria-live="polite">
    <div class="dh"><b>{cur.name}</b> <span class="mono">{cur.inS} → {cur.outS}</span></div>
    <p>{cur.what}</p>
    <p class="mono">{t('parameters:')} {fmt(cur.params)}{cur.params ? t(' ({p}% of all)', { p: ((100 * cur.params) / total).toFixed(1) }) : ''}</p>
  </div>
  </div>

  {#snippet controls()}
    <label class="knob">d_model
      <select bind:value={d}>{#each dims as v}<option value={v}>{v}</option>{/each}</select>
    </label>
    <label class="knob">{t('heads')}
      <select bind:value={heads}>{#each [1, 2, 4, 8] as v}<option value={v}>{v}</option>{/each}</select>
    </label>
    <label class="knob">{t('layers')} <b>{layers}</b>
      <input type="range" min="1" max="6" bind:value={layers} />
    </label>
    <label class="knob">d_ff
      <select bind:value={ratio}><option value={2}>2 × d_model</option><option value={4}>4 × d_model</option></select>
    </label>
    <button type="button" class="lab-btn" onclick={() => preset([512, 8, 6, 4])}>{t('Try a big setting')}</button>
  {/snippet}

  {#snippet readout()}
    {t('total parameters:')} <b>{fmt(total)}</b> · {t('d_k per head')} = {d / heads}
  {/snippet}

  {#snippet legend()}
    <span class="lg"><i class="sw" style="background: color-mix(in srgb, var(--fg) 45%, var(--bg))"></i>{t('fraction of all parameters')}</span>
    <span class="lg"><i class="sw dash"></i>{t('not a layer (no parameters)')}</span>
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
