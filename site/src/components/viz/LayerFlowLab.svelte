<script lang="ts">
  /**
   * variant 'decoder' (default): one decoder-only block in pre-norm form (LayerNorm → sublayer → add), as
   * GPT-style models stack it, plus the final LayerNorm after the last block.
   * variant 'encdec': the 2017 design, an encoder layer and a decoder layer (post-norm "add & norm",
   * cross-attention reading the encoder's memory).
   * Both show the layer as stacks of blocks. Tap a block: its input and output shapes,
   * where its Q, K, V come from, its weights, and what goes wrong without it. Shapes follow the sliders.
   * Under the diagram, the tensors the selected block works on: first as a "shape table" (every tensor, its
   * dimension names and sizes, one line on what happens), or as 3D blocks (one sentence of the batch).
   */
  import Tensors3D from '../viz3d/Tensors3D.svelte'
  import LabFrame from './LabFrame.svelte'
  type Variant = 'decoder' | 'encdec'
  let { variant = 'decoder' }: { variant?: Variant } = $props()
  const encdec = $derived(variant === 'encdec')
  const defaultSel = () => (variant === 'encdec' ? 'd-ca' : 'g-sa')

  // encdec: the memory → cross-attention line, measured from the two buttons it joins
  let flowEl: HTMLDivElement | undefined = $state()
  let wire = $state('')
  function measureWire() {
    if (!flowEl || !encdec) return
    const from = flowEl.querySelector<HTMLElement>('[data-b="e-n2"]')
    const to = flowEl.querySelector<HTMLElement>('[data-b="d-ca"]')
    if (!from || !to) return
    const f = flowEl.getBoundingClientRect(), a = from.getBoundingClientRect(), b = to.getBoundingClientRect()
    const x0 = a.right - f.left, y0 = a.top + a.height / 2 - f.top
    const x1 = b.left - f.left, y1 = b.top + b.height / 2 - f.top
    const xm = (x0 + x1) / 2
    wire = `M${x0},${y0} H${xm} V${y1} H${x1 - 1}`
  }
  $effect(() => {
    if (!flowEl || !encdec) return
    measureWire()
    const ro = new ResizeObserver(measureWire)
    ro.observe(flowEl)
    return () => ro.disconnect()
  })
  let B = $state(1)
  let Ls = $state(5)
  let Lt = $state(4)
  let d = $state(8)
  let h = $state(2)
  const dff = $derived(4 * d)
  let view = $state('table')

  // kinds: 'norm' = post-norm "add & norm" (encdec); 'ln' = LayerNorm alone and 'add' = residual add (pre-norm)
  type Block = { id: string; name: string; kind: 'in' | 'attn' | 'norm' | 'ffn' | 'ln' | 'add' }
  const enc: Block[] = [
    { id: 'e-in', name: 'source words + PE', kind: 'in' },
    { id: 'e-sa', name: 'self-attention', kind: 'attn' },
    { id: 'e-n1', name: 'add & norm', kind: 'norm' },
    { id: 'e-ffn', name: 'FFN', kind: 'ffn' },
    { id: 'e-n2', name: 'add & norm → memory', kind: 'norm' },
  ]
  const dec: Block[] = [
    { id: 'd-in', name: 'target words + PE', kind: 'in' },
    { id: 'd-sa', name: 'masked self-attention', kind: 'attn' },
    { id: 'd-n1', name: 'add & norm', kind: 'norm' },
    { id: 'd-ca', name: 'cross-attention', kind: 'attn' },
    { id: 'd-n2', name: 'add & norm', kind: 'norm' },
    { id: 'd-ffn', name: 'FFN', kind: 'ffn' },
    { id: 'd-n3', name: 'add & norm', kind: 'norm' },
  ]
  // decoder-only, pre-norm: x → LN → sublayer → add back to x, twice; a final LN after the last block
  const gpt: Block[] = [
    { id: 'g-in', name: 'tokens + PE', kind: 'in' },
    { id: 'g-n1', name: 'LayerNorm', kind: 'ln' },
    { id: 'g-sa', name: 'masked self-attention', kind: 'attn' },
    { id: 'g-a1', name: 'add (residual)', kind: 'add' },
    { id: 'g-n2', name: 'LayerNorm', kind: 'ln' },
    { id: 'g-ffn', name: 'FFN', kind: 'ffn' },
    { id: 'g-a2', name: 'add (residual) → next block', kind: 'add' },
    { id: 'g-nf', name: 'final LayerNorm', kind: 'ln' },
  ]
  let sel = $state(defaultSel())
  const block = $derived([...enc, ...dec, ...gpt].find((b) => b.id === sel)!)
  // the token length the selected block works on (the source for encoder blocks)
  const Lq = $derived(sel.startsWith('e') ? Ls : Lt)
  const masked = $derived(sel === 'd-sa' || sel === 'g-sa')
  // the sublayer an 'ln' block feeds or an 'add' block adds back
  const sub = $derived(sel === 'g-n1' || sel === 'g-a1' ? 'attention' : 'FFN')
  const changed = $derived(B !== 1 || Ls !== 5 || Lt !== 4 || d !== 8 || h !== 2 || sel !== defaultSel())
  function reset() { B = 1; Ls = 5; Lt = 4; d = 8; h = 2; sel = defaultSel() }

  // the shape table: every tensor the selected block touches, with dimension names and real sizes (batch included)
  type Row = { name: string; dims: string[]; size: number[]; note: string }
  const ledger = $derived.by((): Row[] => {
    const L = Lq
    const Lname = sel === 'd-ca' ? 'L_tgt' : 'L'
    const Kname = sel === 'd-ca' ? 'L_src' : 'L'
    const Lk = sel === 'd-ca' ? Ls : L
    const dk = d / h
    switch (block.kind) {
      case 'in': return [
        { name: 'ids', dims: ['B', 'L'], size: [B, L], note: 'one token id per word' },
        { name: 'vectors + PE', dims: ['B', 'L', 'd_model'], size: [B, L, d], note: 'each id looked up as a vector; its position vector added' },
      ]
      case 'ffn': return [
        { name: 'x', dims: ['B', 'L', 'd_model'], size: [B, L, d], note: 'each word is processed separately' },
        { name: 'hidden', dims: ['B', 'L', 'd_ff'], size: [B, L, dff], note: 'widen to 4 × d_model, then ReLU' },
        { name: 'out', dims: ['B', 'L', 'd_model'], size: [B, L, d], note: 'narrow back to d_model' },
      ]
      case 'norm': return [
        { name: 'x + block(x)', dims: ['B', 'L', 'd_model'], size: [B, L, d], note: 'residual: same shape, so the two can be added' },
        { name: 'LayerNorm', dims: ['B', 'L', 'd_model'], size: [B, L, d], note: `one mean and std per word: ${B * L} of them` },
      ]
      case 'ln': return [
        { name: 'x', dims: ['B', 'L', 'd_model'], size: [B, L, d], note: sel === 'g-nf' ? 'the last block’s output' : 'the residual path as it arrives' },
        { name: 'mean, std', dims: ['B', 'L'], size: [B, L], note: 'one pair per word, over its d_model numbers' },
        { name: 'LN(x)', dims: ['B', 'L', 'd_model'], size: [B, L, d], note: sel === 'g-nf' ? 'goes to the output layer' : `goes only into ${sub}; x itself stays unchanged on the residual path` },
      ]
      case 'add': return [
        { name: 'x', dims: ['B', 'L', 'd_model'], size: [B, L, d], note: 'the residual path: unchanged since the last add' },
        { name: `${sub}(LN(x))`, dims: ['B', 'L', 'd_model'], size: [B, L, d], note: 'the sublayer’s output, same shape as x' },
        { name: 'x + …', dims: ['B', 'L', 'd_model'], size: [B, L, d], note: sel === 'g-a2' ? 'added number by number; the next block’s input' : 'added number by number; the new x' },
      ]
      default: return [
        { name: 'Q per head', dims: ['B', 'heads', Lname, 'd_k'], size: [B, h, L, dk], note: sel === 'd-ca' ? 'from the decoder, d_model split into heads' : sel === 'g-sa' ? 'from the normalized x, d_model split into heads' : 'd_model split into heads' },
        { name: sel === 'd-ca' ? 'K, V from memory' : 'K, V per head', dims: ['B', 'heads', Kname, 'd_k'], size: [B, h, Lk, dk], note: sel === 'd-ca' ? 'from the encoder’s output' : sel === 'g-sa' ? 'from the same normalized x as Q' : 'from the same words as Q' },
        { name: 'weights', dims: ['B', 'heads', Lname, Kname], size: [B, h, L, Lk], note: masked ? 'one row per query word; the causal mask blocks the future' : 'one row per query word, one column per key word' },
        { name: 'out', dims: ['B', Lname, 'd_model'], size: [B, L, d], note: 'heads side by side again, then W_O' },
      ]
    }
  })

  // 3D shapes for the selected block. Wide d_model is drawn narrower (the table keeps the real size).
  // Titles stay short so neighbours never overlap; the shape table above names every dimension.
  const MAXD = 16
  const shapes3d = $derived.by(() => {
    const L = Lq
    const dd = Math.min(d, MAXD), dk = Math.max(1, Math.round(dd / h)), realDk = d / h
    const t = (name: string, real: number[]) => `${name} (${real.join(', ')})`
    const head0 = (n: number, m: number) => [{ from: [0, 0, 0] as [number, number, number], to: [0, n - 1, m - 1] as [number, number, number], tone: 'accent' as const }]
    const word0 = (w: number) => [{ from: [0, 0, 0] as [number, number, number], to: [0, 0, w - 1] as [number, number, number], tone: 'accent' as const }]
    if (block.kind === 'in') return [
      { shape: [L], title: t('ids', [L]), axes: ['L'] }, '→',
      { shape: [L, dd], title: t('vectors', [L, d]), axes: ['L', 'd'] },
    ]
    if (block.kind === 'ffn') return [
      { shape: [L, dd], title: t('x', [L, d]), axes: ['L', 'd'] }, '→',
      { shape: [L, Math.min(4 * d, 4 * MAXD)], title: t('hidden', [L, 4 * d]), axes: ['L', '4d'], highlight: word0(Math.min(4 * d, 4 * MAXD)) }, '→',
      { shape: [L, dd], title: t('out', [L, d]), axes: ['L', 'd'], highlight: word0(dd) },
    ]
    if (block.kind === 'norm') return [
      { shape: [L, dd], title: t('x + f(x)', [L, d]), axes: ['L', 'd'], highlight: word0(dd) }, '→',
      { shape: [L, dd], title: t('norm', [L, d]), axes: ['L', 'd'], highlight: word0(dd) },
    ]
    if (block.kind === 'ln') return [
      { shape: [L, dd], title: t('x', [L, d]), axes: ['L', 'd'], highlight: word0(dd) }, '→',
      { shape: [L, dd], title: t('LN(x)', [L, d]), axes: ['L', 'd'], highlight: word0(dd) },
    ]
    if (block.kind === 'add') return [
      { shape: [L, dd], title: t('x', [L, d]), axes: ['L', 'd'], highlight: word0(dd) }, '+',
      { shape: [L, dd], title: t(sub, [L, d]), axes: ['L', 'd'], highlight: word0(dd) }, '→',
      { shape: [L, dd], title: t('sum', [L, d]), axes: ['L', 'd'], highlight: word0(dd) },
    ]
    const Lk = sel === 'd-ca' ? Ls : L
    // N7: only the result (weights) is full accent; the inputs Q and K mark head 0 in a muted tone
    const inHead = (n: number, m: number) => (encdec ? head0(n, m).map((r) => ({ ...r, tone: 'dim' as const })) : head0(n, m))
    return [
      { shape: [h, L, dk], title: t('Q', [h, L, realDk]), axes: ['h', 'L_q', 'd_k'], highlight: inHead(L, dk) }, '@',
      { shape: [h, Lk, dk], title: t('K', [h, Lk, realDk]), axes: ['h', 'L_k', 'd_k'], highlight: inHead(Lk, dk) }, '→',
      { shape: [h, L, Lk], title: t('weights', [h, L, Lk]), axes: ['h', 'L_q', 'L_k'], highlight: head0(L, Lk) }, '→',
      { shape: [L, dd], title: t('out', [L, d]), axes: ['L_q', 'd'] },
    ]
  })
  const shapeNote = $derived.by(() => {
    const parts: string[] = []
    if (block.kind === 'attn') parts.push(`The highlighted front slice is head 0; the ${h} heads are stacked front to back.`)
    if (block.kind === 'ffn') parts.push('One word (the highlighted row) widens to 4 × d_model numbers and comes back to d_model.')
    if (block.kind === 'norm' || block.kind === 'ln') parts.push('One word (the highlighted row) gets its own mean and std.')
    if (block.kind === 'add') parts.push('Cell by cell: each number of x is added to the same cell of the sublayer’s output.')
    if (d > MAXD) parts.push(`Drawn with d_model = ${MAXD}; the labels give the real sizes.`)
    parts.push(`One sentence is drawn, so the batch dimension B (${B} here) is left out.`)
    return parts.join(' ')
  })

  const s = (...n: number[]) => `(${n.join(', ')})`
  // split text so every "( … )" tuple stays on one line
  const tup = (t: string): [string, boolean][] => t.split(/(\([^)]*\))/).filter(Boolean).map((p) => [p, p.startsWith('(')])
  type Info = { what: string; inp: string; out: string; extra: string[]; qkv?: string; without: string; params: number }
  const info = $derived.by((): Info => {
    const L = Lq
    const x = `(B, L, d_model) = ${s(B, L, d)}`
    const attnParams = 4 * d * d
    switch (sel) {
      case 'e-in': return { what: 'Each source word is looked up as a vector (level 13), and its position vector is added.', inp: s(B, Ls) + ' token ids', out: x, extra: [], without: 'Without PE, the encoder cannot distinguish "dog bites man" from "man bites dog".', params: 0 }
      case 'd-in': return { what: 'The target words written so far, shifted right by one, plus position vectors.', inp: s(B, Lt) + ' token ids', out: x, extra: [], without: 'Without PE, the decoder does not know which word comes next.', params: 0 }
      case 'e-sa': return { what: 'Every source word looks at every source word.', inp: x, out: x, qkv: 'Q, K, V all come from the source words.', extra: [`weights per head (B, L, L) = ${s(B, Ls, Ls)}, ${h} heads, d_k = ${d / h}`], without: 'Without it, each word is processed alone and never sees its context.', params: attnParams }
      case 'd-sa': return { what: 'Every target word looks at itself and the target words before it.', inp: x, out: x, qkv: 'Q, K, V all come from the target words. A causal mask blocks the future.', extra: [`weights per head (B, L, L) = ${s(B, Lt, Lt)}, ${h} heads`, `causal mask (L, L) = ${s(Lt, Lt)}`], without: 'Without the mask, training would let each word copy the answer it is supposed to predict.', params: attnParams }
      case 'd-ca': return { what: 'Every target word looks at the source sentence. This is how the decoder reads the input.', inp: `${x} and memory ${s(B, Ls, d)}`, out: x, qkv: 'Q comes from the decoder. K and V come from memory, the encoder’s output.', extra: [`weights per head (B, L_tgt, L_src) = ${s(B, Lt, Ls)}: one row per target word, one column per source word`], without: 'Without it, the decoder never sees the source: it can only write a sentence, not translate one.', params: attnParams }
      case 'g-in': return { what: 'Each token is looked up as a vector, and its position vector is added. This x starts the residual path that runs through every block.', inp: s(B, Lt) + ' token ids', out: x, extra: [], without: 'Without PE, the block cannot distinguish "dog bites man" from "man bites dog".', params: 0 }
      case 'g-n1': case 'g-n2': return { what: `LayerNorm each word’s vector, but only the copy that goes into ${sub}. The residual path is not normalized: x itself goes unchanged to the add below.`, inp: x, out: x, extra: [`one mean and std per word: ${B * L} of them`], without: `Without it, the numbers fed to ${sub} grow or shrink as more blocks are added, and training becomes unstable.`, params: 2 * d }
      case 'g-sa': return { what: 'Every word looks at itself and the words before it.', inp: x, out: x, qkv: 'Q, K, V all come from the same normalized x (the LayerNorm just above). A causal mask blocks the future.', extra: [`weights per head (B, L, L) = ${s(B, Lt, Lt)}, ${h} heads, d_k = ${d / h}`, `causal mask (L, L) = ${s(Lt, Lt)}`], without: 'Without it, each word is processed alone and never sees its context. Without the mask, training would let each word copy the next word it is supposed to predict.', params: attnParams }
      case 'g-a1': case 'g-a2': return { what: `Residual: x skips the LayerNorm and ${sub} unchanged, and ${sub}’s output is added to it: x + ${sub}(LN(x)).${sel === 'g-a2' ? ' The sum is the next block’s input.' : ''}`, inp: `${x} + ${x}`, out: x, extra: [], without: 'Without the residual, each block must compute the whole vector again by itself, and in a deep stack the values and the gradients get smaller and smaller.', params: 0 }
      case 'g-nf': return { what: 'After the last block, one more LayerNorm. The residual path was never normalized along the way, so this one normalizes it before the output layer.', inp: x, out: x, extra: [`one mean and std per word: ${B * L} of them`], without: 'Without it, the output layer gets sums that grew a little in every block.', params: 2 * d }
      case 'e-ffn': case 'd-ffn': case 'g-ffn': return { what: 'The same small MLP runs on every word separately: widen, ReLU, narrow.', inp: x, out: x, extra: [`hidden ${s(B, L, dff)}`], without: 'Without it, the layer only mixes words; no step uses ReLU on each word’s own numbers.', params: 2 * d * dff }
      default: return { what: 'Add the block’s input back to its output (residual), then LayerNorm each word.', inp: `${x} + ${x}`, out: x, extra: [`one mean and std per word: ${B * L} of them`], without: 'Without the residual, deep stacks lose the values of x; without the norm, the numbers slowly grow or shrink.', params: 2 * d }
    }
  })
</script>

<LabFrame
  title={encdec ? 'One encoder layer and one decoder layer' : 'One decoder block (pre-norm)'}
  hint="Select a block to see what it does and the shapes it works on. The sliders change the sizes."
  views={[{ id: 'table', label: 'Shape table' }, { id: '3d', label: '3D' }]}
  bind:view
  onreset={reset}
  resetDisabled={!changed}
>
  <div class="flow" class:one={!encdec} bind:this={flowEl}>
    {#if encdec}
    {#if wire}
      <svg class="wire" class:hot={sel === 'd-ca' || sel === 'e-n2'} aria-hidden="true">
        <defs><marker id="lf-wire-head" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="8" markerHeight="8" markerUnits="userSpaceOnUse" orient="auto"><path d="M0,0 L8,4 L0,8 z" /></marker></defs>
        <path d={wire} marker-end="url(#lf-wire-head)" />
      </svg>
    {/if}
    <div class="stack" role="group" aria-label="Encoder layer">
      <div class="title">encoder layer</div>
      {#each enc as b, i}
        {#if i}<div class="arrow" aria-hidden="true">↓</div>{/if}
        <button type="button" class="blk {b.kind}" data-b={b.id} class:on={sel === b.id} aria-pressed={sel === b.id} onclick={() => (sel = b.id)}>{b.name}</button>
      {/each}
      <div class="mem">memory {s(B, Ls, d)} → to the decoder’s cross-attention</div>
    </div>
    <div class="stack" role="group" aria-label="Decoder layer">
      <div class="title">decoder layer</div>
      {#each dec as b, i}
        {#if i}<div class="arrow" aria-hidden="true">↓</div>{/if}
        <button type="button" class="blk {b.kind}" data-b={b.id} class:on={sel === b.id} aria-pressed={sel === b.id} onclick={() => (sel = b.id)}>{b.name}{b.id === 'd-ca' ? ' ← memory' : ''}</button>
      {/each}
    </div>
    {:else}
    <div class="stack" role="group" aria-label="Decoder block">
      <div class="title">decoder block</div>
      {#each gpt as b, i}
        {#if b.id === 'g-nf'}<div class="mem gap">… the next blocks, then after the last one:</div>
        {:else if i}<div class="arrow" aria-hidden="true">↓</div>{/if}
        <button type="button" class="blk {b.kind}" class:on={sel === b.id} aria-pressed={sel === b.id} onclick={() => (sel = b.id)}>{b.name}</button>
      {/each}
      <div class="mem foot">residual path: x goes around each LayerNorm and its sublayer, and is added back at “add”</div>
    </div>
    {/if}
    <div class="detail">
      <div class="dname">{block.name}</div>
      <p>{info.what}</p>
      <dl>
        <dt>input</dt><dd>{#each tup(info.inp) as [t, nw]}{#if nw}<span class="nw">{t}</span>{:else}{t}{/if}{/each}</dd>
        <dt>output</dt><dd>{#each tup(info.out) as [t, nw]}{#if nw}<span class="nw">{t}</span>{:else}{t}{/if}{/each}</dd>
        {#if info.qkv}<dt>Q, K, V</dt><dd class="txt">{info.qkv}</dd>{/if}
        {#each info.extra as e}<dt>shape</dt><dd>{#each tup(e) as [t, nw]}{#if nw}<span class="nw">{t}</span>{:else}{t}{/if}{/each}</dd>{/each}
        <dt>parameters</dt><dd>{info.params.toLocaleString('en-US')}</dd>
      </dl>
      <p class="without"><b>Remove it:</b> {info.without}</p>
    </div>
  </div>

  <div class="shapes">
    <div class="sh-title">Inside “{block.name}”, tensor by tensor</div>
    {#if view === '3d'}
      <Tensors3D tensors={shapes3d} height="min(260px, 70vw)" view={{ fov: 9 }} ariaLabel="The tensors the selected block works on, drawn as 3D blocks" />
      <p class="note3">{shapeNote}</p>
    {:else}
      <div class="ledger" role="table" aria-label={`Shapes inside ${block.name}`}>
        <div class="lr head" role="row"><span role="columnheader">tensor</span><span role="columnheader">shape</span><span role="columnheader">what happens</span></div>
        {#each ledger as r, i}
          <div class="lr" role="row">
            <span class="ln" role="cell"><i>{i + 1}</i>{r.name}</span>
            <span class="shp" role="cell"><code><span class="nw">({r.dims.join(', ')})</span> = <span class="nw">({r.size.join(', ')})</span></code></span>
            <span class="nt" role="cell">{r.note}</span>
          </div>
        {/each}
      </div>
    {/if}
  </div>

  {#snippet controls()}
    <div class="sizes">
      <label><span>batch B</span><input type="range" min="1" max="4" bind:value={B} /><b>{B}</b></label>
      {#if encdec}<label><span>source words</span><input type="range" min="2" max="8" bind:value={Ls} /><b>{Ls}</b></label>{/if}
      <label><span>{encdec ? 'target words' : 'tokens L'}</span><input type="range" min="2" max="8" bind:value={Lt} /><b>{Lt}</b></label>
      <label><span>d_model</span><select bind:value={d}>{#each [4, 8, 16, 512] as v}<option value={v}>{v}</option>{/each}</select></label>
      <label><span>heads</span><select bind:value={h}>{#each [1, 2, 4] as v}<option value={v}>{v}</option>{/each}</select></label>
    </div>
  {/snippet}

  {#snippet readout()}
    {block.name}: output {info.out} · {info.params.toLocaleString('en-US')} parameters
  {/snippet}

  {#snippet legend()}
    <span class="key"><i class="k attn"></i>attention</span>
    <span class="key"><i class="k ffn"></i>feed-forward (FFN)</span>
    {#if encdec}
      <span class="key"><i class="k norm"></i>residual + LayerNorm</span>
    {:else}
      <span class="key"><i class="k ln"></i>LayerNorm</span>
      <span class="key"><i class="k add"></i>residual add</span>
    {/if}
    <span class="key"><i class="k in"></i>input</span>
  {/snippet}
</LabFrame>

<style>
  .flow { position: relative; display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1.3fr); gap: 1rem; align-items: start; }
  .wire { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; overflow: visible; }
  .wire path { fill: none; stroke: var(--accent); stroke-width: 1.5; }
  .wire marker path { fill: var(--accent); stroke: none; }
  .wire.hot > path { stroke-width: 3; }
  .flow.one { grid-template-columns: minmax(0, 1fr) minmax(0, 1.3fr); }
  .stack { display: flex; flex-direction: column; align-items: stretch; min-width: 0; }
  .title { font-size: 0.78rem; color: var(--dim); font-family: var(--mono); margin-bottom: 0.3rem; }
  .arrow { text-align: center; color: var(--dim); font-size: 0.8rem; line-height: 1.1; }
  .blk { font: inherit; font-size: 0.85rem; line-height: 1.25; padding: 0.45rem 0.5rem; min-height: 2.5rem; border: 1.5px solid var(--line); border-left-width: 4px;
    border-radius: 6px; background: var(--bg); color: var(--fg); cursor: pointer; text-align: center; transition: background 0.15s; }
  .blk.attn { border-color: var(--cat-2); }
  .blk.ffn { border-color: var(--cat-3); }
  .blk.norm { border-style: dashed; border-left-style: solid; border-color: var(--field); color: var(--dim); }
  .blk.in { border-color: var(--field); }
  .blk.ln { border-color: var(--field); color: var(--dim); }
  .blk.add { border-style: dashed; border-left-style: solid; border-color: var(--field); color: var(--dim); }
  .blk:hover { border-top-color: var(--fg); border-right-color: var(--fg); border-bottom-color: var(--fg); }
  /* the shared "on" style of .lab-btn[aria-pressed]; the thick left edge keeps the block's kind color */
  .blk.on { border-top-color: var(--accent); border-right-color: var(--accent); border-bottom-color: var(--accent); background: var(--highlight); color: var(--accent); }
  .blk:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .mem { margin-top: 0.5rem; font-size: 0.78rem; color: var(--dim); font-family: var(--mono); }
  .mem.gap { margin: 0.7rem 0 0.4rem; }
  .mem.foot { margin-bottom: 1rem; line-height: 1.45; }
  .detail { border: 1px solid var(--line); border-radius: 6px; padding: 0.7rem 0.9rem; background: var(--bg); min-width: 0; }
  .detail p { margin: 0.3rem 0; font-size: 0.88rem; }
  .dname { font-weight: 650; }
  dl { display: grid; grid-template-columns: auto 1fr; gap: 0.15rem 0.7rem; margin: 0.5rem 0; font-size: 0.82rem; }
  dt { color: var(--dim); }
  dd { margin: 0; font-family: var(--mono); overflow-wrap: anywhere; }
  dd.txt { font-family: inherit; }
  .without b { color: var(--fg); font-weight: 700; }
  .shapes { display: flex; flex-direction: column; gap: 0.4rem; min-width: 0; }
  .sh-title { font-size: 0.82rem; color: var(--dim); }
  .ledger { display: grid; border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
  .lr { display: grid; grid-template-columns: minmax(8rem, 0.9fr) minmax(0, 1.6fr) minmax(0, 1.5fr); gap: 0.2rem 1rem; padding: 0.45rem 0.7rem; align-items: start; font-size: 0.85rem; }
  .lr + .lr { border-top: 1px solid var(--line); }
  .lr.head { font-size: 0.75rem; color: var(--dim); background: var(--bg); padding-block: 0.3rem; margin: 0; border-bottom: 0; } /* global .head adds a margin */
  .ln { font-weight: 600; display: flex; align-items: baseline; gap: 0.45rem; }
  .ln i { font-style: normal; font-size: 0.72rem; color: var(--dim); font-family: var(--mono); }
  .lr code { font-family: var(--mono); font-size: 0.82rem; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; color: var(--fg); }
  .nw { white-space: nowrap; }
  .nt { color: var(--dim); font-size: 0.82rem; }
  .note3 { margin: 0.2rem 0 0; font-size: 0.8rem; color: var(--dim); }
  .sizes { display: flex; flex-wrap: wrap; gap: 0.2rem 1.4rem; font-size: 0.85rem; }
  .sizes label { display: inline-flex; align-items: center; gap: 0.5rem; min-height: 2.5rem; }
  .sizes span { color: var(--dim); font-family: var(--mono); }
  .sizes input { width: 6.5rem; accent-color: var(--accent); }
  .sizes b { font-family: var(--mono); min-width: 1ch; }
  select { font: inherit; font-family: var(--mono); background: var(--bg); color: var(--fg); border: 1px solid var(--field); border-radius: 4px; padding: 0.25rem 0.3rem; min-height: 2.1rem; }
  .key { display: inline-flex; align-items: center; gap: 0.4rem; }
  .k { width: 1rem; height: 0.8rem; border-radius: 3px; border: 1.5px solid var(--line); border-left-width: 4px; background: var(--bg); }
  .k.attn { border-color: var(--cat-2); }
  .k.ffn { border-color: var(--cat-3); }
  .k.norm { border-color: var(--field); border-style: dashed; border-left-style: solid; }
  .k.in { border-color: var(--field); }
  .k.ln { border-color: var(--field); }
  .k.add { border-color: var(--field); border-style: dashed; border-left-style: solid; }
  @media (max-width: 760px) {
    .flow { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 0.7rem; }
    .flow.one { grid-template-columns: minmax(0, 1fr); }
    .detail { grid-column: 1 / -1; }
    .blk { font-size: 0.8rem; padding: 0.4rem 0.35rem; }
    .lr { grid-template-columns: 1fr; gap: 0.1rem; }
    .lr.head { display: none; }
    .sizes { gap: 0 1rem; }
    .sizes label { flex: 1 1 100%; }
    .sizes input { flex: 1; width: auto; }
    .sizes span { min-width: 7.5rem; }
  }
  @media (prefers-reduced-motion: reduce) { .blk { transition: none; } }
</style>
