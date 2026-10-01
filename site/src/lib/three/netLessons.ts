/**
 * Net3D specs for the branch and theory lessons (conv, RNN, seq2seq, autoencoder, encoder-decoder, the full model). Shapes and
 * numbers come from the lessons and their data files; `netSpecs` lists every builder (the tests draw each one).
 */
import type { Net3DSpec, NetNode, NetStep, NetValues } from './net'
import { rnnScalar } from '../classic'
import { backpropSpec, mlpSpec, MLP_EXAMPLE } from './netSpecs'

const r4 = (v: number) => Math.round(v * 1e4) / 1e4
const f = (v: number) => String(r4(v)).replace('-', '−')

// ---- N1 convolutions: (1, 28, 28) → conv → pool → conv → pool → 10 scores (the lesson's 5,258-number network) ----
export function convSpec(): Net3DSpec {
  const T = (id: string, label: string, shape: number[], params: number, title: string, note: string): NetNode =>
    ({ id, label, kind: 'tensor', shape, axes: ['channels', 'rows', 'cols'], params, title, note })
  return {
    id: 'conv', layout: 'row', view: { azimuth: 28, elevation: 20 },
    nodes: [
      T('img', 'picture', [1, 28, 28], 0, 'picture', 'One gray picture: 1 channel of 28 × 28 pixels.'),
      T('c1', 'conv 1', [8, 26, 26], 80, 'conv 1 (8 filters, 3×3)', '8 filters of 3 × 3: 72 weights and 8 biases. Each makes one channel.'),
      T('p1', 'pool', [8, 13, 13], 0, 'pool 1 (2×2 max)', 'Keeps the largest number in each 2 × 2 block. No weights.'),
      T('c2', 'conv 2', [16, 11, 11], 1168, 'conv 2 (16 filters, 8×3×3)', 'Each filter reads all 8 channels: 8 × 3 × 3 = 72 weights, 16 filters, plus 16 biases.'),
      T('p2', 'pool', [16, 5, 5], 0, 'pool 2 (2×2 max)', '16 channels of 5 × 5 = 400 numbers.'),
      { id: 'out', label: 'scores', kind: 'neurons', shape: [10], params: 4010, title: 'dense → 10 scores', names: '0123456789'.split(''), note: 'All 400 numbers, flattened, into a dense layer: 400 · 10 + 10.' },
    ],
    edges: [
      { id: 'k1', from: 'img', to: 'c1', kind: 'conv', window: { size: 3, stride: 1 }, label: '3×3' },
      { id: 'q1', from: 'c1', to: 'p1', kind: 'conv', window: { size: 2, stride: 2 }, label: '2×2' },
      { id: 'k2', from: 'p1', to: 'c2', kind: 'conv', window: { size: 3, stride: 1 }, label: '3×3' },
      { id: 'q2', from: 'c2', to: 'p2', kind: 'conv', window: { size: 2, stride: 2 }, label: '2×2' },
      { id: 'fc', from: 'p2', to: 'out', kind: 'copy', label: 'flatten, dense' },
    ],
    steps: [
      { id: 's1', dir: 'forward', title: 'conv 1', active: ['img', 'k1', 'c1'], text: 'Each output cell reads one 3 × 3 window of the picture. 28 − 3 + 1 = 26, and 8 filters make 8 channels.' },
      { id: 's2', dir: 'forward', title: 'pool', active: ['c1', 'q1', 'p1'], text: 'Each cell keeps the largest of a 2 × 2 block: 26 → 13. The channels stay 8.' },
      { id: 's3', dir: 'forward', title: 'conv 2', active: ['p1', 'k2', 'c2'], text: 'A 3 × 3 window again, but through all 8 channels at once: 13 − 3 + 1 = 11, now 16 channels.' },
      { id: 's4', dir: 'forward', title: 'pool', active: ['c2', 'q2', 'p2'], text: '11 → 5 (the last odd row and column are dropped).' },
      { id: 's5', dir: 'forward', title: 'scores', active: ['p2', 'fc', 'out'], text: '16 × 5 × 5 = 400 numbers become 10 digit scores.' },
    ],
  }
}

// ---- N3 RNN: the same cell four times, h flows right, the gradient shrinks on its way back ----------------------
export const RNN_EXAMPLE = { xs: [1, 0, 0, 0], wx: 1, wh: 0.5, b: 0 }

export function rnnNumbers(e = RNN_EXAMPLE) {
  const hs = rnnScalar(e.xs, e.wx, e.wh, e.b)
  // ∂h_T/∂h_t: start at 1 at the last step, multiply by w_h(1 − h²) per step back
  const T = hs.length
  const g = new Array(T).fill(0)
  g[T - 1] = 1
  for (let t = T - 2; t >= 0; t--) g[t] = g[t + 1] * e.wh * (1 - hs[t + 1] ** 2)
  return { hs, g }
}

export function rnnSpec(): Net3DSpec {
  const e = RNN_EXAMPLE
  const { hs, g } = rnnNumbers()
  const T = hs.length
  const nodes: NetNode[] = []
  const edges: Net3DSpec['edges'] = []
  for (let t = 1; t <= T; t++) {
    nodes.push({ id: `x${t}`, label: `x${t}`, title: `input x${t}`, kind: 'neurons', shape: [1], at: [(t - 1) * 2.1, -1.2, 0], note: `The input at step ${t}: ${e.xs[t - 1]}.` })
    nodes.push({
      id: `h${t}`, label: `h${t}`, title: `state h${t}`, kind: 'neurons', shape: [1], at: [(t - 1) * 2.1, 0, 0], group: 'cell', params: t === 1 ? 3 : 0,
      note: t === 1 ? 'The cell has 3 numbers: w_x, w_h and b. Every step uses the same three.' : 'The same cell as at step 1: no new weights.',
    })
    edges.push({ id: `wx${t}`, from: `x${t}`, to: `h${t}`, kind: 'dense', weights: [[e.wx]], shared: 'cell', label: 'w_x' })
    if (t > 1) edges.push({ id: `wh${t}`, from: `h${t - 1}`, to: `h${t}`, kind: 'recurrent', shared: 'cell', label: 'w_h' })
  }
  const steps: NetStep[] = []
  for (let t = 1; t <= T; t++) {
    const prev = t > 1 ? hs[t - 2] : 0
    steps.push({
      id: `f${t}`, dir: 'forward', title: `step ${t}`, active: [`x${t}`, `wx${t}`, `h${t}`, ...(t > 1 ? [`wh${t}`] : [])],
      values: { [`x${t}`]: [e.xs[t - 1]], [`h${t}`]: [r4(hs[t - 1])] },
      text: `h${t} = tanh(${e.wx} × ${e.xs[t - 1]} + ${e.wh} × ${f(prev)} + ${e.b}) = ${f(hs[t - 1])}.`,
    })
  }
  for (let t = T; t >= 1; t--) {
    steps.push({
      id: `b${t}`, dir: 'backward', title: `∂h${T}/∂h${t}`, active: [`h${t}`, ...(t < T ? [`wh${t + 1}`] : [])], grads: { [`h${t}`]: [r4(g[t - 1])] },
      text: t === T ? `Start at the last state: ∂h${T}/∂h${T} = 1.`
        : `One step back multiplies by w_h(1 − h${t + 1}²) = ${e.wh} × (1 − ${f(hs[t])}²) = ${f(e.wh * (1 - hs[t] ** 2))}, so ∂h${T}/∂h${t} = ${f(g[t - 1])}.${t === 1 ? ' The halo shrinks every step: the gradient vanishes.' : ''}`,
    })
  }
  return { id: 'rnn', layout: 'unrolled', nodes, edges, steps, view: { azimuth: 18, elevation: 16 } }
}

// ---- N5 seq2seq with attention: 427015 → words, the arcs are the trained model's weights -------------------------
export const ALIGN_427015 = {
  src: ['4', '2', '7', '0', '1', '5'],
  out: ['four', 'hundred', 'twenty', 'seven', 'thousand', 'fifteen', '<eos>'],
  weights: [
    [0.876, 0.122, 0.002, 0.0, 0.0, 0.0], [0.008, 0.005, 0.891, 0.071, 0.024, 0.001], [0.01, 0.835, 0.155, 0.0, 0.0, 0.0],
    [0.002, 0.009, 0.988, 0.001, 0.0, 0.001], [0.0, 0.0, 0.009, 0.148, 0.171, 0.671], [0.0, 0.0, 0.0, 0.002, 0.049, 0.949],
    [0.0, 0.0, 0.0, 0.004, 0.441, 0.554],
  ],
}

export function seq2seqSpec(): Net3DSpec {
  const a = ALIGN_427015
  const steps: NetStep[] = a.out.map((w, i) => {
    const order = a.weights[i].map((v, j) => [v, j]).sort((p, q) => q[0] - p[0])
    const top = order.filter(([v]) => v >= 0.1).map(([v, j]) => `“${a.src[j]}” (${v.toFixed(2)})`)
    return {
      id: `o${i}`, dir: 'forward', title: `writing “${w}”`, active: ['att', 'dec'], focus: { att: i },
      values: { dec: a.out.map((_, k) => (k === i ? 1 : k < i ? 0.35 : 0)) },
      text: `the decoder looks mostly at ${top.join(' and ')}.`,
    }
  })
  return {
    id: 's2s', layout: 'encdec', view: { azimuth: 16, elevation: 32 },
    nodes: [
      { id: 'enc', label: 'encoder states', title: 'encoder: one state per digit', kind: 'neurons', shape: [6], along: 'x', at: [0, 1.1, 0], names: a.src, note: 'The encoder reads 4 2 7 0 1 5 and keeps a state for every digit.' },
      { id: 'dec', label: 'decoder steps', title: 'decoder: one step per word', kind: 'neurons', shape: [7], along: 'x', at: [0, -1.1, 0], names: a.out, fill: 'progress', note: 'At every step the decoder mixes the encoder states with the attention weights.' },
    ],
    edges: [{ id: 'att', from: 'dec', to: 'enc', kind: 'attention', weights: a.weights }],
    steps,
  }
}

// ---- N6 autoencoder: 784 → 128 → 2 → 128 → 784, block size = how many numbers -----------------------------------
export function autoencoderSpec(): Net3DSpec {
  return {
    // straight on: two blocks of 784 must look the same size (an angle makes the nearer one look bigger)
    id: 'ae', layout: 'hourglass', view: { azimuth: 0, elevation: 10 },
    nodes: [
      { id: 'img', label: 'picture', title: 'picture (784 pixels)', kind: 'tensor', shape: [784], draw: [28, 28], note: '28 × 28 = 784 numbers.' },
      { id: 'e1', label: 'hidden', title: 'encoder hidden (128)', kind: 'tensor', shape: [128], draw: [16, 8], params: 784 * 128 + 128, note: '784 → 128 with ReLU.' },
      { id: 'code', label: 'code', title: 'code (2 numbers)', kind: 'neurons', shape: [2], params: 128 * 2 + 2, note: 'The bottleneck: the whole picture as 2 numbers.' },
      { id: 'd1', label: 'hidden', title: 'decoder hidden (128)', kind: 'tensor', shape: [128], draw: [16, 8], params: 2 * 128 + 128, note: '2 → 128 with ReLU.' },
      { id: 'out', label: 'rebuilt', title: 'rebuilt picture (784)', kind: 'tensor', shape: [784], draw: [28, 28], params: 128 * 784 + 784, note: '128 → 784, then sigmoid: each pixel between 0 and 1.' },
    ],
    edges: [
      { id: 'w1', from: 'img', to: 'e1', kind: 'copy', label: 'encoder' },
      { id: 'w2', from: 'e1', to: 'code', kind: 'copy' },
      { id: 'w3', from: 'code', to: 'd1', kind: 'copy', label: 'decoder' },
      { id: 'w4', from: 'd1', to: 'out', kind: 'copy' },
    ],
    steps: [
      { id: 'a1', dir: 'forward', title: 'encode', active: ['img', 'w1', 'e1'], text: '784 pixels → 128 numbers.' },
      { id: 'a2', dir: 'forward', title: 'squeeze', active: ['e1', 'w2', 'code'], text: '128 → 2. Everything the decoder will know is in these 2 numbers.' },
      { id: 'a3', dir: 'forward', title: 'decode', active: ['code', 'w3', 'd1'], text: '2 → 128: the decoder starts from the code alone.' },
      { id: 'a4', dir: 'forward', title: 'rebuild', active: ['d1', 'w4', 'out'], text: '128 → 784 pixels. Training makes this picture match the input.' },
    ],
  }
}

// ---- N7 encoder-decoder: one post-norm encoder layer of the microscope's tiny model, with the residual path -------
type Micro = { steps: { title: string; tensors: { name: string; axes: [string, number][]; values: NetValues }[] }[] }

/** A tensor's values from a microscope file (the first example when there is a batch axis), found by step title and name. */
function microValues(micro: Micro | undefined, title: string, name: string): NetValues | undefined {
  const t = micro?.steps.filter((s) => s.title === title).flatMap((s) => s.tensors).find((x) => x.name === name)
  if (!t) return undefined
  return (t.axes[0]?.[0] === 'B' ? (t.values as any[])[0] : t.values) as NetValues
}

/** The structure; with `micro` (encoder-decoder/microscope.json) the steps carry its real numbers. */
export function encdecSpec(micro?: Micro): Net3DSpec {
  const T = (id: string, label: string, shape: number[], title: string, note: string, draw?: number[]): NetNode =>
    ({ id, label, kind: 'tensor', shape, title, note, draw, axes: shape.length === 2 ? ['L_src', id === 'ffn' ? 'd_ff' : id === 'attn' ? 'L_src' : 'd_model'] : ['L_src'] })
  const nodes: NetNode[] = [
    { ...T('ids', 'ids', [2], 'token ids', 'The two digits of "89", as ids.', [2, 1]), fill: 'none' },
    T('emb', 'embed', [2, 6], 'embeddings', 'One row of 6 numbers per token, looked up in the table.'),
    T('x', 'x', [2, 6], 'x = embedding × √6 + positions', 'This is what the residual path carries into the layer.'),
    T('attn', 'attention', [2, 2], 'self-attention weights', 'How much each position looks at each position. Each row adds up to 1.'),
    { id: 'add1', label: '+', title: 'add', kind: 'op', shape: [2, 6], note: 'The attention output is added to x.' },
    T('ln1', 'LN1', [2, 6], 'LayerNorm 1, after the add', 'The sum is normalized. Post-norm: this normalized sum is what goes on along the residual path.'),
    T('ffn', 'FFN', [2, 12], 'FFN hidden (after ReLU)', 'Each position on its own: 6 → 12 → 6.'),
    { id: 'add2', label: '+', title: 'add', kind: 'op', shape: [2, 6], note: 'The FFN output is added to the LN1 output.' },
    T('mem', 'LN2: memory', [2, 6], 'LayerNorm 2 = encoder output (memory)', 'The sum is normalized again. The decoder reads this in cross-attention.'),
  ]
  const edges: Net3DSpec['edges'] = [
    { id: 'e0', from: 'ids', to: 'emb', kind: 'copy' },
    { id: 'e1', from: 'emb', to: 'x', kind: 'copy' },
    { id: 'e2', from: 'x', to: 'attn', kind: 'copy' },
    { id: 'e3', from: 'attn', to: 'add1', kind: 'copy' },
    { id: 'e4', from: 'add1', to: 'ln1', kind: 'copy' },
    { id: 'e5', from: 'ln1', to: 'ffn', kind: 'copy' },
    { id: 'e6', from: 'ffn', to: 'add2', kind: 'copy' },
    { id: 'e7', from: 'add2', to: 'mem', kind: 'copy' },
    { id: 'r1', from: 'x', to: 'add1', kind: 'residual', label: 'residual: x skips attention' },
    { id: 'r2', from: 'ln1', to: 'add2', kind: 'residual', label: 'residual: LN1 output skips the FFN' },
  ]
  const v = (id: string, title: string, name: string) => {
    const x = microValues(micro, title, name)
    return x ? { [id]: x } : undefined
  }
  const steps: NetStep[] = [
    { id: 'm1', dir: 'forward', title: 'token ids', active: ['ids'], values: v('ids', 'Token ids', 'src'), text: 'The input "89" as two token ids.' },
    { id: 'm2', dir: 'forward', title: 'embed', active: ['e0', 'emb'], values: v('emb', 'Look up the embeddings', 'embedding'), text: 'Each id picks one row of 6 numbers.' },
    { id: 'm3', dir: 'forward', title: 'add positions', active: ['e1', 'x'], values: v('x', 'Add the positions', 'x'), text: 'Scale by √6 and add the position rows: x, shape (2, 6).' },
    { id: 'm4', dir: 'forward', title: 'self-attention', active: ['e2', 'attn'], values: v('attn', 'Encoder self-attention', 'weights'), text: 'Each position mixes the rows it looks at. The weights are (2, 2).' },
    { id: 'm5', dir: 'forward', title: 'add x back', active: ['e3', 'r1', 'add1'], text: 'x goes around the attention block and is added to its output.' },
    { id: 'm6', dir: 'forward', title: 'LayerNorm 1', active: ['e4', 'ln1'], values: v('ln1', 'Add & norm, then the FFN', 'LN1(x + attention)'), text: 'Then LayerNorm normalizes the sum. From here on, the residual path carries this normalized sum, not x.' },
    { id: 'm7', dir: 'forward', title: 'FFN', active: ['e5', 'ffn'], values: v('ffn', 'Add & norm, then the FFN', 'FFN hidden (after ReLU)'), text: '6 → 12 → 6 on each position. The hidden layer is (2, 12).' },
    { id: 'm8', dir: 'forward', title: 'add, then LayerNorm 2', active: ['e6', 'r2', 'add2', 'e7', 'mem'], values: v('mem', 'Add & norm, then the FFN', 'memory'), text: 'The FFN output is added to the LN1 output, and LayerNorm 2 normalizes the sum. The result, (2, 6), is the memory.' },
  ]
  return { id: micro ? 'encdec-data' : 'encdec', layout: 'stack', nodes, edges, steps, view: { azimuth: 18, elevation: 18 }, scale: { gap: 1.0, cell: 0.3 }, fold: 2 }
}

// ---- 17 full model: the pre-norm decoder block of the microscope's tiny model, with the residual path -------------
/** The structure; with `micro` (full-model/microscope.json) the steps carry its real numbers. "8 9 =" is L = 3. */
export function fullModelSpec(micro?: Micro): Net3DSpec {
  const AX: Record<string, string> = { attn: 'L', ffn: 'd_ff', logits: 'tokens' }
  const T = (id: string, label: string, shape: number[], title: string, note: string, draw?: number[]): NetNode =>
    ({ id, label, kind: 'tensor', shape, title, note, draw, axes: shape.length === 2 ? ['L', AX[id] ?? 'd_model'] : ['L'] })
  const nodes: NetNode[] = [
    { ...T('ids', 'ids', [3], 'token ids', 'The input "8 9 =", as three ids.', [3, 1]), fill: 'none' },
    T('x', 'x', [3, 6], 'x = embedding × √6 + positions', 'This is what the residual path carries.'),
    T('ln1', 'LN1', [3, 6], 'LayerNorm 1', 'x normalized before attention. x itself stays on the residual path.'),
    T('attn', 'attention', [3, 3], 'masked self-attention weights', 'Each row uses itself and earlier rows only. The weights in each row sum to 1.'),
    { id: 'add1', label: '+', title: 'add', kind: 'op', shape: [3, 6], note: 'The attention output is added to x. No norm after it: the next norm comes before the FFN.' },
    T('ln2', 'LN2', [3, 6], 'LayerNorm 2', 'Normalized again, before the FFN.'),
    T('ffn', 'FFN', [3, 12], 'FFN hidden (after ReLU)', 'Each position on its own: 6 → 12 → 6.'),
    { id: 'add2', label: '+', title: 'add', kind: 'op', shape: [3, 6], note: 'The FFN output is added back. This is the block output.' },
    T('norm', 'final LN', [3, 6], 'final LayerNorm', 'One more LayerNorm after the last block.'),
    // drawn as three 3 × 14 sheets, one per position: a flat (3, 42) strip would be a thin line at this cell size
    T('logits', 'logits', [3, 42], 'logits', '42 scores per position, drawn as one 3 × 14 sheet each. Only the last position (after "=") picks the next token.', [3, 3, 14]),
  ]
  const edges: Net3DSpec['edges'] = [
    { id: 'e0', from: 'ids', to: 'x', kind: 'copy' },
    { id: 'e1', from: 'x', to: 'ln1', kind: 'copy' },
    { id: 'e2', from: 'ln1', to: 'attn', kind: 'copy' },
    { id: 'e3', from: 'attn', to: 'add1', kind: 'copy' },
    { id: 'e4', from: 'add1', to: 'ln2', kind: 'copy' },
    { id: 'e5', from: 'ln2', to: 'ffn', kind: 'copy' },
    { id: 'e6', from: 'ffn', to: 'add2', kind: 'copy' },
    { id: 'e7', from: 'add2', to: 'norm', kind: 'copy' },
    { id: 'e8', from: 'norm', to: 'logits', kind: 'copy' },
    { id: 'r1', from: 'x', to: 'add1', kind: 'residual', label: 'residual: x skips LN1 and attention' },
    { id: 'r2', from: 'add1', to: 'add2', kind: 'residual', label: 'and skips LN2 and the FFN' },
  ]
  const v = (id: string, title: string, name: string) => {
    const x = microValues(micro, title, name)
    return x ? { [id]: x } : undefined
  }
  const steps: NetStep[] = [
    { id: 'm1', dir: 'forward', title: 'token ids', active: ['ids'], values: v('ids', 'Token ids', 'ids'), text: 'The input "8 9 =" as three token ids.' },
    { id: 'm2', dir: 'forward', title: 'embed + positions', active: ['e0', 'x'], values: v('x', 'Add the positions', 'x'), text: 'Look up 6 numbers per token, scale by √6, add the position rows: x, shape (3, 6).' },
    { id: 'm3', dir: 'forward', title: 'LayerNorm 1', active: ['e1', 'ln1'], values: v('ln1', 'LayerNorm 1 (pre-norm)', 'LN1(x)'), text: 'Normalize first. The residual path keeps the un-normalized x.' },
    { id: 'm4', dir: 'forward', title: 'masked self-attention', active: ['e2', 'attn'], values: v('attn', 'Attention weights', 'weights'), text: 'The weights are (3, 3), with zeros above the diagonal: no row sees a later token.' },
    { id: 'm5', dir: 'forward', title: 'add to x', active: ['e3', 'r1', 'add1'], text: 'The residual path carries x around LN1 and attention. The attention output is added to x.' },
    { id: 'm6', dir: 'forward', title: 'LayerNorm 2', active: ['e4', 'ln2'], values: v('ln2', 'LayerNorm 2', 'LN2(x)'), text: 'Normalize again, before the FFN.' },
    { id: 'm7', dir: 'forward', title: 'FFN', active: ['e5', 'ffn'], values: v('ffn', 'FFN hidden', 'FFN hidden (after ReLU)'), text: '6 → 12 → 6 on each position. The hidden layer is (3, 12).' },
    { id: 'm8', dir: 'forward', title: 'add again', active: ['e6', 'r2', 'add2'], text: 'The FFN output is added to x once more. This (3, 6) is the block output.' },
    { id: 'm9', dir: 'forward', title: 'final LayerNorm', active: ['e7', 'norm'], values: v('norm', 'Final LayerNorm', 'final LN(x)'), text: 'One last LayerNorm after the blocks.' },
    { id: 'm10', dir: 'forward', title: 'logits', active: ['e8', 'logits'], values: v('logits', 'Output layer: logits', 'logits'), text: '42 scores per row. The last row picks the next token.' },
  ]
  return { id: micro ? 'full-data' : 'full', layout: 'stack', nodes, edges, steps, view: { azimuth: 18, elevation: 18 }, scale: { gap: 1.0, cell: 0.3 }, fold: 2 }
}

/** Every lesson spec (the tests lay each one out). */
export const netSpecs: Record<string, () => Net3DSpec> = {
  backprop: backpropSpec,
  mlp: () => mlpSpec(MLP_EXAMPLE, MLP_EXAMPLE.x, 'mlp-example'),
  conv: convSpec,
  rnn: rnnSpec,
  seq2seq: seq2seqSpec,
  autoencoder: autoencoderSpec,
  encdec: () => encdecSpec(),
  fullModel: () => fullModelSpec(),
}
