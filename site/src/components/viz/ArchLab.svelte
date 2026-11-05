<script lang="ts">
  /**
   * The network-architecture lab: one Net3D placement per lesson, picked by `which`. Each one teaches one thing
   * (the title), says what to look at (the caption), and runs in NetLab (Flat / 3D, steps, layer list, panel).
   *   backprop  2 → 3 → 1, forward with values, then gradients flowing back (level 6)
   *   mlp       the lesson's 2 → 2 → 1 example, then any width and depth (level 5)
   *   conv      the 5,258-number digit network, with each layer's window as a funnel (N1)
   *   rnn       one cell unrolled 4 times, shared weights, a vanishing gradient (N3)
   *   seq2seq   attention arcs of the trained 427015 model (N5)
   *   autoencoder  784 → 128 → 2 → 128 → 784 (N6)
   *   encdec    one post-norm encoder layer of the N7 microscope model, with the residual path (N7)
   *   full      the pre-norm decoder block of the level 17 microscope model, with the residual path (17)
   */
  import { onMount } from 'svelte'
  import { has, subscribe } from '@lib/progress'
  import NetLab from './NetLab.svelte'
  import { backpropSpec, mlpSpec, MLP_EXAMPLE, seededNet } from '@lib/three/netSpecs'
  import { autoencoderSpec, convSpec, encdecSpec, fullModelSpec, rnnSpec, seq2seqSpec } from '@lib/three/netLessons'
  import type { Net3DSpec } from '@lib/three/net'
  import { provideLang, useT } from '@lib/i18nSvelte'
  import type { Lang } from '@lib/i18n'

  type Which = 'backprop' | 'mlp' | 'conv' | 'rnn' | 'seq2seq' | 'autoencoder' | 'encdec' | 'full'
  let { which, hide = {}, lang = 'en' }: { which: Which; hide?: { params?: string[] }; lang?: Lang } = $props()
  provideLang(lang)
  // `t` below is this placement's text, so the translator is `tx`
  const tx = useT({
    'Forward with numbers, then the gradient flows back along the same lines': '先带着数往前走，再让梯度沿着同样的线流回来',
    'Press Next to step. Select a layer to see its numbers.': '按“下一步”往前走。选一层，查看它的数。',
    'Look at the lines into h when you step back: each one turns into ∂L/∂w, and its width now shows the gradient, not the weight.': '往回走时，看看进入 h 的那些线：每条都变成了 ∂L/∂w，线的粗细现在表示梯度，而不是权重。',
    'A 2-3-1 network: inputs x, hidden layer h, output a, loss L. Steps run the forward pass with values, then the backward pass with gradients.': '一个 2-3-1 的网络：输入 x，隐藏层 h，输出 a，损失 L。各步先带着值做前向传播，再带着梯度做反向传播。',
    'Press Next to run the forward pass with x = [2, 1].': '按“下一步”，用 x = [2, 1] 做前向传播。',
    'Every line is one weight': '每条线是一个权重',
    'Pick a width and a depth. Press Next to run one example through it.': '选一个宽度和一个深度。按“下一步”，让一个样本穿过网络。',
    'Look at the lines between two hidden layers: width × width of them. Width 6 has four times as many as width 3.': '看两个隐藏层之间的线：一共有宽度 × 宽度条。宽度 6 的线是宽度 3 的四倍。',
    'A multi-layer network drawn as columns of neurons with a line for every weight.': '一个多层网络，画成一列列神经元，每个权重一条线。',
    'The picture gets smaller, the channels get deeper': '图片越来越小，通道越来越多',
    'Press Next to go one layer at a time. Turn the view to see the channels placed one behind another.': '按“下一步”，一次走一层。转动视图，可以看到通道一个接一个排在后面。',
    'Look at the cone of lines: one output cell reads only a small window of the layer before it, through every channel.': '看那个由线组成的锥形：一个输出格只读前一层的一个小窗口，但穿过每一个通道。',
    'A convolutional network: a 28 by 28 picture, conv to 8 channels of 26 by 26, pool, conv to 16 channels of 11 by 11, pool, then 10 scores.': '一个卷积网络：一张 28 × 28 的图片，卷积成 8 个 26 × 26 的通道，池化，再卷积成 16 个 11 × 11 的通道，池化，最后是 10 个分数。',
    'One cell, used four times': '一个单元，用了四次',
    'Press Next for the forward steps, then keep going to send the gradient back.': '按“下一步”走前向的各步，再继续按，把梯度送回去。',
    'Look at the color: every step is the same cell with the same three weights. Going back, the bright area shrinks at every step.': '看颜色：每一步都是同一个单元，用同样的三个权重。往回走时，亮的区域每一步都在缩小。',
    'A recurrent network unrolled over 4 time steps. Inputs below, states above, the same weights at every step.': '一个展开成 4 个时间步的循环网络。下面是输入，上面是状态，每一步用同样的权重。',
    'Each word reads the digits it needs': '每个词读它需要的那几个数字',
    'Press Next to write the words one at a time.': '按“下一步”，一次写出一个词。',
    'Look at where the bright arcs land: “seven” reaches back to the 7, and “thousand” and “fifteen” to the last three digits.': '看亮的弧线落在哪里：“seven”回头找 7，“thousand”和“fifteen”找最后三个数字。',
    'An encoder row of 6 digit states and a decoder row of 7 words, joined by attention arcs whose strength is the trained weight.': '一排 6 个数字状态的编码器，和一排 7 个词的解码器，由注意力弧线连起来，弧线的强弱就是训练出的权重。',
    'Squeeze 784 numbers through 2': '把 784 个数挤过 2 个数',
    'Press Next to follow one picture through the network.': '按“下一步”，跟着一张图片穿过网络。',
    'Look at the sizes: each block holds as many cells as it has numbers, so the code in the middle is almost nothing.': '看大小：每个块的格数就是它的数的个数，所以中间的编码几乎什么都没有。',
    'An autoencoder drawn as blocks: 784 pixels, 128, a code of 2, 128, 784 pixels.': '一个画成块的自编码器：784 个像素，128，2 个数的编码，128，784 个像素。',
    'In the 2017 layer, the residual path is normalized after every add': '在 2017 年的层里，每次相加之后都对残差通路做归一化',
    'Press Next to follow “89” through one encoder layer. Select a block for its numbers.': '按“下一步”，跟着“89”穿过一个编码器层。选一个块，查看它的数。',
    'Look at the residual path under the blocks: after each add, a LayerNorm rescales the sum. This is post-norm. Compare it with level 17’s block, where x is never normalized until the end.': '看块下面的残差通路：每次相加之后，都有一个 LayerNorm 重新缩放这个和。这就是 post-norm。和第 17 关的块比较一下，那里的 x 直到最后才归一化。',
    'One post-norm encoder layer: token ids, embeddings, x, self-attention, add, LayerNorm 1, FFN, add, LayerNorm 2 giving the memory, with a residual path under the blocks.': '一个 post-norm 的编码器层：token id，嵌入，x，自注意力，相加，LayerNorm 1，FFN，相加，LayerNorm 2 得到 memory，块下面是残差通路。',
    'Norm first, then add to the residual path': '先归一化，再加到残差通路上',
    'Press Next to follow “8 9 =” through one decoder block. Select a block for its numbers.': '按“下一步”，跟着“8 9 =”穿过一个解码器块。选一个块，查看它的数。',
    'Look at where the residual path starts: before LN1. Each LayerNorm gives its output only to its own sublayer, so x itself is never normalized until the final LayerNorm.': '看残差通路从哪里开始：在 LN1 之前。每个 LayerNorm 只把输出交给自己的子层，所以 x 本身直到最后的 LayerNorm 才被归一化。',
    'One pre-norm decoder block: token ids, x, LayerNorm 1, masked self-attention, add, LayerNorm 2, FFN, add, final LayerNorm, logits, with a residual path past each sublayer.': '一个 pre-norm 的解码器块：token id，x，LayerNorm 1，掩码自注意力，相加，LayerNorm 2，FFN，相加，最后的 LayerNorm，logits，每个子层旁边都有残差通路。',
    'Network': '网络',
    'Example 2 → 2 → 1': '例子 2 → 2 → 1',
    'width {w}': '宽度 {w}',
    'Depth': '深度',
    '{d} hidden': '{d} 个隐藏层',
  })

  // parameter counts stay hidden until these questions are answered
  let solved = $state(true)
  onMount(() => {
    const ids = hide.params ?? []
    if (!ids.length) return
    const sync = () => (solved = ids.every((id) => has(id)))
    sync()
    return subscribe(sync)
  })

  // mlp: the hand example, or a seeded random net of any width and depth
  let width = $state(0) // 0 = the lesson's example
  let depth = $state(1)
  const X = [0.5, -0.5]

  // encdec / full model: the microscope's real numbers, once loaded
  let micro = $state<any>(null)
  onMount(() => {
    if (which !== 'full' && which !== 'encdec') return
    fetch(`/data/${which === 'full' ? 'full-model' : 'encoder-decoder'}/microscope.json`).then((r) => (r.ok ? r.json() : null)).then((j) => (micro = j)).catch(() => {})
  })

  const spec = $derived.by((): Net3DSpec => {
    if (which === 'backprop') return backpropSpec()
    if (which === 'mlp') return width === 0 ? mlpSpec(MLP_EXAMPLE, MLP_EXAMPLE.x, 'mlp-example') : mlpSpec(seededNet(width, depth), X, `mlp-${width}-${depth}`)
    if (which === 'conv') return convSpec()
    if (which === 'rnn') return rnnSpec()
    if (which === 'seq2seq') return seq2seqSpec()
    if (which === 'autoencoder') return autoencoderSpec()
    if (which === 'encdec') return encdecSpec(micro ?? undefined)
    return fullModelSpec(micro ?? undefined)
  })

  const TEXT: Record<Which, { title: string; hint: string; caption: string; aria: string; idle?: string }> = {
    backprop: {
      title: 'Forward with numbers, then the gradient flows back along the same lines',
      hint: 'Press Next to step. Select a layer to see its numbers.',
      caption: 'Look at the lines into h when you step back: each one turns into ∂L/∂w, and its width now shows the gradient, not the weight.',
      aria: 'A 2-3-1 network: inputs x, hidden layer h, output a, loss L. Steps run the forward pass with values, then the backward pass with gradients.',
      idle: 'Press Next to run the forward pass with x = [2, 1].',
    },
    mlp: {
      title: 'Every line is one weight',
      hint: 'Pick a width and a depth. Press Next to run one example through it.',
      caption: 'Look at the lines between two hidden layers: width × width of them. Width 6 has four times as many as width 3.',
      aria: 'A multi-layer network drawn as columns of neurons with a line for every weight.',
    },
    conv: {
      title: 'The picture gets smaller, the channels get deeper',
      hint: 'Press Next to go one layer at a time. Turn the view to see the channels placed one behind another.',
      caption: 'Look at the cone of lines: one output cell reads only a small window of the layer before it, through every channel.',
      aria: 'A convolutional network: a 28 by 28 picture, conv to 8 channels of 26 by 26, pool, conv to 16 channels of 11 by 11, pool, then 10 scores.',
    },
    rnn: {
      title: 'One cell, used four times',
      hint: 'Press Next for the forward steps, then keep going to send the gradient back.',
      caption: 'Look at the color: every step is the same cell with the same three weights. Going back, the bright area shrinks at every step.',
      aria: 'A recurrent network unrolled over 4 time steps. Inputs below, states above, the same weights at every step.',
    },
    seq2seq: {
      title: 'Each word reads the digits it needs',
      hint: 'Press Next to write the words one at a time.',
      caption: 'Look at where the bright arcs land: “seven” reaches back to the 7, and “thousand” and “fifteen” to the last three digits.',
      aria: 'An encoder row of 6 digit states and a decoder row of 7 words, joined by attention arcs whose strength is the trained weight.',
    },
    autoencoder: {
      title: 'Squeeze 784 numbers through 2',
      hint: 'Press Next to follow one picture through the network.',
      caption: 'Look at the sizes: each block holds as many cells as it has numbers, so the code in the middle is almost nothing.',
      aria: 'An autoencoder drawn as blocks: 784 pixels, 128, a code of 2, 128, 784 pixels.',
    },
    encdec: {
      title: 'In the 2017 layer, the residual path is normalized after every add',
      hint: 'Press Next to follow “89” through one encoder layer. Select a block for its numbers.',
      caption: 'Look at the residual path under the blocks: after each add, a LayerNorm rescales the sum. This is post-norm. Compare it with level 17’s block, where x is never normalized until the end.',
      aria: 'One post-norm encoder layer: token ids, embeddings, x, self-attention, add, LayerNorm 1, FFN, add, LayerNorm 2 giving the memory, with a residual path under the blocks.',
    },
    full: {
      title: 'Norm first, then add to the residual path',
      hint: 'Press Next to follow “8 9 =” through one decoder block. Select a block for its numbers.',
      caption: 'Look at where the residual path starts: before LN1. Each LayerNorm gives its output only to its own sublayer, so x itself is never normalized until the final LayerNorm.',
      aria: 'One pre-norm decoder block: token ids, x, LayerNorm 1, masked self-attention, add, LayerNorm 2, FFN, add, final LayerNorm, logits, with a residual path past each sublayer.',
    },
  }
  const t = $derived.by(() => {
    const e = TEXT[which]
    return { title: tx(e.title), hint: tx(e.hint), caption: tx(e.caption), aria: tx(e.aria), idle: e.idle && tx(e.idle) }
  })
  // flat first for small, flat networks (exact numbers are the point); 3D where size and depth are the information
  const VIEW: Record<Which, 'flat' | '3d'> = { backprop: 'flat', mlp: 'flat', rnn: 'flat', seq2seq: 'flat', conv: '3d', autoencoder: '3d', encdec: '3d', full: '3d' }
  // long nets stand upright on phones (data flows down), so they get a taller view there: the middle term grows as the
  // window narrows (about 34rem at 390px wide, the lower bound on a desktop)
  const tall = (desk: string) => `clamp(${desk}, calc(46rem - 36vw), min(74vh, 34rem))`
  // small nets: a little taller on phones too, so their discs stay big enough to read and tap
  const mid = (desk: string) => `clamp(${desk}, calc(36rem - 30vw), min(66vh, 26rem))`
  const HEIGHT: Record<Which, string> = {
    backprop: mid('19rem'), mlp: mid('21rem'), conv: tall('19rem'), rnn: 'min(60vh, 18rem)',
    seq2seq: 'min(65vh, 22rem)', autoencoder: tall('20rem'), encdec: tall('20rem'), full: tall('20rem'),
  }
</script>

<NetLab {spec} initialView={VIEW[which]} height={HEIGHT[which]} title={t.title} hint={t.hint} caption={t.caption} ariaLabel={t.aria} idle={t.idle} hideParams={!solved}
  changed={which === 'mlp' && width !== 0} onreset={() => { width = 0; depth = 1 }} numbers={which === 'mlp' ? width === 0 || width * depth <= 8 : which === 'seq2seq' ? false : undefined}>
  {#snippet extra()}
    {#if which === 'mlp'}
      <span class="al-group" role="group" aria-label={tx('Network')}>
        <button type="button" class="lab-btn" aria-pressed={width === 0} onclick={() => (width = 0)}>{tx('Example 2 → 2 → 1')}</button>
        {#each [3, 6] as w}
          <button type="button" class="lab-btn" aria-pressed={width === w} onclick={() => (width = w)}>{tx('width {w}', { w })}</button>
        {/each}
      </span>
      {#if width !== 0}
        <span class="al-group" role="group" aria-label={tx('Depth')}>
          {#each [1, 2, 3] as d}
            <button type="button" class="lab-btn" aria-pressed={depth === d} onclick={() => (depth = d)}>{tx('{d} hidden', { d })}</button>
          {/each}
        </span>
      {/if}
    {/if}
  {/snippet}
</NetLab>

<style>
  .al-group { display: inline-flex; flex-wrap: wrap; gap: 0.3rem; margin-right: 0.5rem; }
</style>
