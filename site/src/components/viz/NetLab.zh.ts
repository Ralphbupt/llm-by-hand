/**
 * Chinese for the words inside the Net3D lesson specs (@lib/three/netSpecs, netLessons): layer titles and notes,
 * link labels, axis names, step titles and step texts. Fixed strings are looked up in ZH; strings built with
 * numbers go through RULES. Anything not matched stays English. NetLab applies this when the page is Chinese.
 */
import type { Net3DSpec } from '@lib/three/net'

const ZH: Record<string, string> = {
  // level 6, backprop
  'input x': '输入 x',
  'output a (sigmoid)': '输出 a（sigmoid）',
  'loss L = (a − y)²': '损失 L = (a − y)²',
  'Two inputs: x = [2, 1]. The target is y = 1.': '两个输入：x = [2, 1]。目标值是 y = 1。',
  'h = sigmoid(x · W1 + b1). Neuron 1 is the neuron from section 1: 2 × 0.5 + 0 × 1 − 1 = 0.': 'h = sigmoid(x · W1 + b1)。神经元 1 就是第 1 节的那个神经元：2 × 0.5 + 0 × 1 − 1 = 0。',
  'a = sigmoid(h · W2 + b2).': 'a = sigmoid(h · W2 + b2)。',
  'The squared error against the target y = 1.': '和目标值 y = 1 之间的平方误差。',
  'input': '输入',
  'hidden layer': '隐藏层',
  'output': '输出',
  'loss': '损失',
  'into W2': '进入 W2',
  'back to h': '回到 h',
  'into W1': '进入 W1',
  'x = [2, 1], and the target is y = 1.': 'x = [2, 1]，目标值是 y = 1。',
  // level 5, mlp
  'output p (sigmoid)': '输出 p（sigmoid）',
  'The two input numbers of one example.': '一个样本的两个输入数。',
  // N1, conv
  'picture': '图片',
  'conv 1': '卷积 1',
  'conv 2': '卷积 2',
  'pool': '池化',
  'scores': '分数',
  'conv 1 (8 filters, 3×3)': '卷积 1（8 个卷积核，3×3）',
  'pool 1 (2×2 max)': '池化 1（2×2 最大值）',
  'conv 2 (16 filters, 8×3×3)': '卷积 2（16 个卷积核，8×3×3）',
  'pool 2 (2×2 max)': '池化 2（2×2 最大值）',
  'dense → 10 scores': '全连接 → 10 个分数',
  'One gray picture: 1 channel of 28 × 28 pixels.': '一张灰度图片：1 个通道，28 × 28 像素。',
  '8 filters of 3 × 3: 72 weights and 8 biases. Each makes one channel.': '8 个 3 × 3 的卷积核：72 个权重和 8 个偏置。每个卷积核生成一个通道。',
  'Keeps the largest number in each 2 × 2 block. No weights.': '在每个 2 × 2 块里只留下最大的数。没有权重。',
  'Each filter reads all 8 channels: 8 × 3 × 3 = 72 weights, 16 filters, plus 16 biases.': '每个卷积核读全部 8 个通道：8 × 3 × 3 = 72 个权重，16 个卷积核，再加 16 个偏置。',
  '16 channels of 5 × 5 = 400 numbers.': '16 个 5 × 5 的通道 = 400 个数。',
  'All 400 numbers, flattened, into a dense layer: 400 · 10 + 10.': '把全部 400 个数展平，送进一个全连接层：400 · 10 + 10。',
  'flatten, dense': '展平，全连接',
  'Each output cell reads one 3 × 3 window of the picture. 28 − 3 + 1 = 26, and 8 filters make 8 channels.': '每个输出格读图片的一个 3 × 3 窗口。28 − 3 + 1 = 26，8 个卷积核生成 8 个通道。',
  'Each cell keeps the largest of a 2 × 2 block: 26 → 13. The channels stay 8.': '每格留下一个 2 × 2 块里最大的数：26 → 13。通道还是 8 个。',
  'A 3 × 3 window again, but through all 8 channels at once: 13 − 3 + 1 = 11, now 16 channels.': '又是一个 3 × 3 窗口，但一次穿过全部 8 个通道：13 − 3 + 1 = 11，现在是 16 个通道。',
  '11 → 5 (the last odd row and column are dropped).': '11 → 5（多出来的最后一行和一列被丢掉）。',
  '16 × 5 × 5 = 400 numbers become 10 digit scores.': '16 × 5 × 5 = 400 个数变成 10 个数字的分数。',
  'channels': '通道',
  'rows': '行',
  'cols': '列',
  // N3, rnn
  'The cell has 3 numbers: w_x, w_h and b. Every step uses the same three.': '这个单元有 3 个数：w_x、w_h 和 b。每一步都用这同样的三个。',
  'The same cell as at step 1: no new weights.': '和第 1 步是同一个单元：没有新的权重。',
  // N5, seq2seq
  'encoder states': '编码器状态',
  'decoder steps': '解码器步骤',
  'encoder: one state per digit': '编码器：每个数字一个状态',
  'decoder: one step per word': '解码器：每个词一步',
  'The encoder reads 4 2 7 0 1 5 and keeps a state for every digit.': '编码器读入 4 2 7 0 1 5，为每个数字保留一个状态。',
  'At every step the decoder mixes the encoder states with the attention weights.': '每一步，解码器都按注意力权重把编码器状态混合起来。',
  // N6, autoencoder
  'hidden': '隐藏层',
  'code': '编码',
  'rebuilt': '重建',
  'picture (784 pixels)': '图片（784 个像素）',
  'encoder hidden (128)': '编码器隐藏层（128）',
  'code (2 numbers)': '编码（2 个数）',
  'decoder hidden (128)': '解码器隐藏层（128）',
  'rebuilt picture (784)': '重建的图片（784）',
  '28 × 28 = 784 numbers.': '28 × 28 = 784 个数。',
  '784 → 128 with ReLU.': '784 → 128，用 ReLU。',
  'The bottleneck: the whole picture as 2 numbers.': '瓶颈：整张图片变成 2 个数。',
  '2 → 128 with ReLU.': '2 → 128，用 ReLU。',
  '128 → 784, then sigmoid: each pixel between 0 and 1.': '128 → 784，再经过 sigmoid：每个像素在 0 到 1 之间。',
  'encoder': '编码器',
  'decoder': '解码器',
  'encode': '编码',
  'squeeze': '压缩',
  'decode': '解码',
  'rebuild': '重建',
  '784 pixels → 128 numbers.': '784 个像素 → 128 个数。',
  '128 → 2. Everything the decoder will know is in these 2 numbers.': '128 → 2。解码器能知道的一切，都在这 2 个数里。',
  '2 → 128: the decoder starts from the code alone.': '2 → 128：解码器只从编码出发。',
  '128 → 784 pixels. Training makes this picture match the input.': '128 → 784 个像素。训练让这张图片和输入对上。',
  // N7, encoder-decoder
  'embed': '嵌入',
  'attention': '注意力',
  'LN2: memory': 'LN2：memory',
  'token ids': 'token id',
  'embeddings': '嵌入',
  'x = embedding × √6 + positions': 'x = 嵌入 × √6 + 位置',
  'self-attention weights': '自注意力权重',
  'add': '相加',
  'LayerNorm 1, after the add': '相加之后的 LayerNorm 1',
  'FFN hidden (after ReLU)': 'FFN 隐藏层（ReLU 之后）',
  'LayerNorm 2 = encoder output (memory)': 'LayerNorm 2 = 编码器输出（memory）',
  'The two digits of "89", as ids.': '“89”的两个数字，表示成 id。',
  'One row of 6 numbers per token, looked up in the table.': '每个 token 一行 6 个数，从表里查出来。',
  'This is what the residual path carries into the layer.': '这就是残差通路带进这一层的东西。',
  'How much each position looks at each position. Each row adds up to 1.': '每个位置看每个位置的程度。每一行加起来是 1。',
  'The attention output is added to x.': '注意力的输出加到 x 上。',
  'The sum is normalized. Post-norm: this normalized sum is what goes on along the residual path.': '对和做归一化。post-norm：沿残差通路继续往下走的，就是这个归一化后的和。',
  'Each position on its own: 6 → 12 → 6.': '每个位置单独计算：6 → 12 → 6。',
  'The FFN output is added to the LN1 output.': 'FFN 的输出加到 LN1 的输出上。',
  'The sum is normalized again. The decoder reads this in cross-attention.': '再对和做一次归一化。解码器在交叉注意力里读的就是它。',
  'residual: x skips attention': '残差：x 跳过注意力',
  'residual: LN1 output skips the FFN': '残差：LN1 的输出跳过 FFN',
  'add positions': '加上位置',
  'self-attention': '自注意力',
  'add x back': '把 x 加回来',
  'add, then LayerNorm 2': '相加，再做 LayerNorm 2',
  'The input "89" as two token ids.': '输入“89”，表示成两个 token id。',
  'Each id picks one row of 6 numbers.': '每个 id 取出一行 6 个数。',
  'Scale by √6 and add the position rows: x, shape (2, 6).': '乘以 √6，再加上位置行：得到 x，形状 (2, 6)。',
  'Each position mixes the rows it looks at. The weights are (2, 2).': '每个位置把它看的那些行混合起来。权重是 (2, 2)。',
  'x goes around the attention block and is added to its output.': 'x 绕过注意力块，加到它的输出上。',
  'Then LayerNorm normalizes the sum. From here on, the residual path carries this normalized sum, not x.': '然后 LayerNorm 对和做归一化。从这里开始，残差通路带的是这个归一化后的和，而不是 x。',
  'The FFN output is added to the LN1 output, and LayerNorm 2 normalizes the sum. The result, (2, 6), is the memory.': 'FFN 的输出加到 LN1 的输出上，LayerNorm 2 再对和做归一化。结果 (2, 6) 就是 memory。',
  // 17, full model
  'final LN': '最后的 LN',
  'masked self-attention weights': '掩码自注意力权重',
  'final LayerNorm': '最后的 LayerNorm',
  'The input "8 9 =", as three ids.': '输入“8 9 =”，表示成三个 id。',
  'This is what the residual path carries.': '这就是残差通路带着的东西。',
  'x normalized before attention. x itself stays on the residual path.': '在注意力之前把 x 归一化。x 本身留在残差通路上。',
  'Each row uses itself and earlier rows only. The weights in each row sum to 1.': '每一行只用它自己和前面的行。每一行的权重加起来是 1。',
  'The attention output is added to x. No norm after it: the next norm comes before the FFN.': '注意力的输出加到 x 上。之后不做归一化：下一次归一化在 FFN 之前。',
  'Normalized again, before the FFN.': '在 FFN 之前再归一化一次。',
  'The FFN output is added back. This is the block output.': 'FFN 的输出加回来。这就是这个块的输出。',
  'One more LayerNorm after the last block.': '最后一个块之后再做一次 LayerNorm。',
  '42 scores per position, drawn as one 3 × 14 sheet each. Only the last position (after "=") picks the next token.': '每个位置 42 个分数，各画成一张 3 × 14 的薄片。只有最后一个位置（“=”之后）选出下一个 token。',
  'residual: x skips LN1 and attention': '残差：x 跳过 LN1 和注意力',
  'and skips LN2 and the FFN': '并跳过 LN2 和 FFN',
  'embed + positions': '嵌入 + 位置',
  'masked self-attention': '掩码自注意力',
  'add to x': '加到 x 上',
  'add again': '再加一次',
  'The input "8 9 =" as three token ids.': '输入“8 9 =”，表示成三个 token id。',
  'Look up 6 numbers per token, scale by √6, add the position rows: x, shape (3, 6).': '每个 token 查出 6 个数，乘以 √6，再加上位置行：得到 x，形状 (3, 6)。',
  'Normalize first. The residual path keeps the un-normalized x.': '先归一化。残差通路保留没归一化的 x。',
  'The weights are (3, 3), with zeros above the diagonal: no row sees a later token.': '权重是 (3, 3)，对角线以上都是 0：没有哪一行能看到后面的 token。',
  'The residual path carries x around LN1 and attention. The attention output is added to x.': '残差通路带着 x 绕过 LN1 和注意力。注意力的输出加到 x 上。',
  'Normalize again, before the FFN.': '在 FFN 之前再归一化一次。',
  'The FFN output is added to x once more. This (3, 6) is the block output.': 'FFN 的输出再一次加到 x 上。这个 (3, 6) 就是块的输出。',
  'One last LayerNorm after the blocks.': '所有块之后，最后做一次 LayerNorm。',
  '42 scores per row. The last row picks the next token.': '每行 42 个分数。最后一行选出下一个 token。',
}

/** Strings with numbers in them: the first rule that matches wins. */
const RULES: [RegExp, string | ((...m: string[]) => string)][] = [
  // backprop
  [/^(z = .*), so (.*)\.$/, '$1，所以 $2。'],
  [/^∂L\/∂a = 2\(a − y\) = (.*)\. The same start as section 1\.$/, '∂L/∂a = 2(a − y) = $1。和第 1 节的起点一样。'],
  [/^(∂L\/∂z = .*) = (\S+)\. Each weight into a gets h × (\S+): (∂L\/∂W2 = .*)\.$/, '$1 = $2。每个进入 a 的权重得到 h × $3：$4。'],
  [/^The same lines carry the gradient back: (.*)\. The biggest weight \(2\) sends back the most\.$/, '同样的线把梯度送回去：$1。最大的权重（2）送回的最多。'],
  [/^Through the sigmoid: (.*)\. Then ∂L\/∂W1 = x × that: row x₁ = 2 gives (.*), row x₂ = 1 gives (.*)\.$/, '经过 sigmoid：$1。然后 ∂L/∂W1 = x × 它：x₁ = 2 这一行得到 $2，x₂ = 1 这一行得到 $3。'],
  // mlp
  [/^hidden (\S+) \((\w+)\)$/, '隐藏层 $1（$2）'],
  [/^Each neuron: a weighted sum of the (\d+) numbers before it, plus a bias, then (\w+)\.$/, '每个神经元：对前面 $1 个数求加权和，加上偏置，再经过 $2。'],
  // rnn
  [/^input (\S+)$/, '输入 $1'],
  [/^state (\S+)$/, '状态 $1'],
  [/^step (\d+)$/, '第 $1 步'],
  [/^The input at step (\d+): (.*)\.$/, '第 $1 步的输入：$2。'],
  [/^Start at the last state: (.*)\.$/, '从最后一个状态出发：$1。'],
  [/^One step back multiplies by (.*), so (.*?)\.( The halo shrinks every step: the gradient vanishes\.)?$/,
    (_, a, b, end) => `往回一步要乘以 ${a}，所以 ${b}。${end ? '光晕每一步都在缩小：梯度消失了。' : ''}`],
  // seq2seq
  [/^writing “(.*)”$/, '写出“$1”'],
  [/^the decoder looks mostly at (.*)\.$/, (_, a) => `解码器主要在看${a.replace(/ and /g, ' 和 ')}。`],
  // encoder-decoder, full model
  [/^6 → 12 → 6 on each position\. The hidden layer is (\(.*\))\.$/, '每个位置上 6 → 12 → 6。隐藏层是 $1。'],
  // a formula with a full stop (x = …, L = …, h1 = tanh(…) = …, H = relu(…) = …)
  [/^([A-Za-z]\w* = [^A-Za-z]*(?:(?:sigmoid|relu|tanh)\([^)]*\)[^A-Za-z]*)?)\.$/, '$1。'],
]

export function zhSpecText(s: string | undefined): string | undefined {
  if (!s) return s
  if (ZH[s]) return ZH[s]
  for (const [re, to] of RULES) {
    if (re.test(s)) return typeof to === 'string' ? s.replace(re, to) : s.replace(re, to as (...m: string[]) => string)
  }
  return s
}

/** A copy of the spec with every visible word in Chinese (ids, shapes and numbers unchanged). */
export function zhSpec(spec: Net3DSpec): Net3DSpec {
  const z = zhSpecText
  return {
    ...spec,
    nodes: spec.nodes.map((n) => ({ ...n, label: z(n.label)!, title: z(n.title), note: z(n.note), axes: n.axes?.map((a) => z(a)!) })),
    edges: spec.edges.map((e) => ({ ...e, label: z(e.label) })),
    steps: spec.steps?.map((st) => ({ ...st, title: z(st.title)!, text: z(st.text) })),
  }
}
