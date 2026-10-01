/**
 * Net3D specs for the lessons. Every number is computed here from the weights (never typed in by hand), and
 * net.test.ts checks them against the lessons' worked examples.
 */
import type { Net3DSpec, NetEdge, NetNode, NetStep } from './net'

const sigmoid = (z: number) => 1 / (1 + Math.exp(-z))
const r4 = (v: number) => Math.round(v * 1e4) / 1e4
const f = (v: number) => {
  const s = String(r4(v))
  return (s === '-0' ? '0' : s).replace('-', '−')
}
const list = (v: number[]) => `[${v.map(f).join(', ')}]`
/** x @ W + b for one example: x (n), W (n, m), b (m) */
const affine = (x: number[], W: number[][], b: number[]) => b.map((bj, j) => x.reduce((a, xi, i) => a + xi * W[i][j], bj))

// ---- level 6, backprop: a 2 → 3 → 1 net that grows out of the lesson's one-neuron example -------------------------

/**
 * Sigmoid everywhere and the squared loss, as in section 1. Hidden neuron 1 is section 1's neuron
 * (x = 2, w = 0.5, b = −1, so z = 0 and a = 0.5), and the output also lands on z = 0, a = 0.5, L = 0.25 with y = 1,
 * so the backward pass starts with the same ∂L/∂a = −1 and ∂L/∂z = −0.25.
 */
export const BACKPROP_NET = {
  x: [2, 1],
  y: 1,
  W1: [[0.5, 1, -1], [0, -1, 1]],
  b1: [-1, 0, 0],
  W2: [[2], [1], [1]],
  b2: [-2],
}

export function backpropNumbers(n = BACKPROP_NET) {
  const z1 = affine(n.x, n.W1, n.b1)
  const h = z1.map(sigmoid)
  const z2 = affine(h, n.W2, n.b2)[0]
  const a = sigmoid(z2)
  const L = (a - n.y) ** 2
  const dA = 2 * (a - n.y) // ∂L/∂a
  const dZ2 = dA * a * (1 - a) // ∂L/∂z at the output
  const dW2 = h.map((hi) => [hi * dZ2]) // (3, 1)
  const dH = n.W2.map((row) => row[0] * dZ2) // ∂L/∂h
  const dZ1 = dH.map((d, j) => d * h[j] * (1 - h[j]))
  const dW1 = n.x.map((xi) => dZ1.map((d) => xi * d)) // (2, 3)
  return { z1, h, z2, a, L, dA, dZ2, dW2, dH, dZ1, dW1, db1: dZ1, db2: dZ2 }
}

export function backpropSpec(): Net3DSpec {
  const n = BACKPROP_NET
  const k = backpropNumbers()
  const nodes: NetNode[] = [
    { id: 'x', label: 'x', title: 'input x', kind: 'neurons', shape: [2], note: 'Two inputs: x = [2, 1]. The target is y = 1.' },
    { id: 'h', label: 'h', title: 'hidden h (sigmoid)', kind: 'neurons', shape: [3], params: 9, note: 'h = sigmoid(x · W1 + b1). Neuron 1 is the neuron from section 1: 2 × 0.5 + 0 × 1 − 1 = 0.' },
    { id: 'a', label: 'a', title: 'output a (sigmoid)', kind: 'neurons', shape: [1], params: 4, note: 'a = sigmoid(h · W2 + b2).' },
    { id: 'L', label: 'L', title: 'loss L = (a − y)²', kind: 'neurons', shape: [1], params: 0, note: 'The squared error against the target y = 1.' },
  ]
  const edges: NetEdge[] = [
    { id: 'W1', from: 'x', to: 'h', kind: 'dense', weights: n.W1, label: 'W1' },
    { id: 'W2', from: 'h', to: 'a', kind: 'dense', weights: n.W2, label: 'W2' },
    { id: 'sq', from: 'a', to: 'L', kind: 'copy', label: '(a − y)²' },
  ]
  const steps: NetStep[] = [
    { id: 'f0', dir: 'forward', title: 'input', active: ['x'], values: { x: n.x }, text: 'x = [2, 1], and the target is y = 1.' },
    {
      id: 'f1', dir: 'forward', title: 'hidden layer', active: ['W1', 'h'], values: { h: k.h },
      text: `z = x · W1 + b1 = ${list(k.z1)}, so h = sigmoid(z) = ${list(k.h)}.`,
    },
    {
      id: 'f2', dir: 'forward', title: 'output', active: ['W2', 'a'], values: { a: [k.a] },
      text: `z = h · W2 + b2 = 2 × 0.5 + 0.7311 + 0.2689 − 2 = ${f(k.z2)}, so a = sigmoid(0) = ${f(k.a)}.`,
    },
    { id: 'f3', dir: 'forward', title: 'loss', active: ['sq', 'L'], values: { L: [k.L] }, loss: k.L, text: `L = (${f(k.a)} − 1)² = ${f(k.L)}.` },
    {
      id: 'b0', dir: 'backward', title: '∂L/∂a', active: ['sq', 'a'], grads: { L: [1], a: [k.dA] },
      text: `∂L/∂a = 2(a − y) = ${f(k.dA)}. The same start as section 1.`,
    },
    {
      id: 'b1', dir: 'backward', title: 'into W2', active: ['a', 'W2'], grads: { W2: k.dW2 },
      text: `∂L/∂z = ${f(k.dA)} × a(1 − a) = ${f(k.dA)} × 0.25 = ${f(k.dZ2)}. Each weight into a gets h × ${f(k.dZ2)}: ∂L/∂W2 = ${list(k.dW2.map((r) => r[0]))}.`,
    },
    {
      id: 'b2', dir: 'backward', title: 'back to h', active: ['W2', 'h'], grads: { h: k.dH },
      text: `The same lines carry the gradient back: ∂L/∂h = W2 × ${f(k.dZ2)} = ${list(k.dH)}. The biggest weight (2) sends back the most.`,
    },
    {
      id: 'b3', dir: 'backward', title: 'into W1', active: ['h', 'W1'], grads: { W1: k.dW1 },
      text: `Through the sigmoid: ∂L/∂z = ∂L/∂h × h(1 − h) = ${list(k.dZ1)}. Then ∂L/∂W1 = x × that: row x₁ = 2 gives ${list(k.dW1[0])}, row x₂ = 1 gives ${list(k.dW1[1])}.`,
    },
  ]
  return { id: 'backprop-231', layout: 'row', nodes, edges, steps }
}

// ---- level 5, mlp: the worked example, then any width and depth --------------------------------------------------

export type DenseNet = { sizes: number[]; W: number[][][]; b: number[][]; act: 'relu' | 'tanh' }

/** The lesson's hand example: x = [2, 1], ReLU, W1 = [[1, −1], [0, 1]], b1 = 0, W2 = [[2], [−1]], b2 = 0.5. */
export const MLP_EXAMPLE: DenseNet & { x: number[] } = {
  sizes: [2, 2, 1], act: 'relu', x: [2, 1],
  W: [[[1, -1], [0, 1]], [[2], [-1]]], b: [[0, 0], [0.5]],
}

/** A seeded random net 2 → width × depth → 1 (tanh), weights ~ N(0, 1/fan-in), so every picture is the same each visit. */
export function seededNet(width: number, depth: number, seed = 7): DenseNet {
  let s = seed >>> 0
  const rnd = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 2 ** 32)
  const normal = () => Math.sqrt(-2 * Math.log(rnd() + 1e-12)) * Math.cos(2 * Math.PI * rnd())
  const sizes = [2, ...Array(depth).fill(width), 1]
  const W = sizes.slice(0, -1).map((fi, l) => Array.from({ length: fi }, () => Array.from({ length: sizes[l + 1] }, () => r4(normal() / Math.sqrt(fi)))))
  const b = sizes.slice(1).map((m) => Array.from({ length: m }, () => r4(normal() * 0.2)))
  return { sizes, W, b, act: 'tanh' }
}

export function denseForward(net: DenseNet, x: number[]) {
  const acts: number[][] = [x]
  net.W.forEach((W, l) => {
    const z = affine(acts[l], W, net.b[l])
    const last = l === net.W.length - 1
    acts.push(z.map((v) => (last ? sigmoid(v) : net.act === 'relu' ? Math.max(0, v) : Math.tanh(v))))
  })
  return acts
}

export function mlpSpec(net: DenseNet, x: number[], id: string): Net3DSpec {
  const acts = denseForward(net, x)
  const L = net.sizes.length
  const name = (l: number) => (l === 0 ? 'x' : l === L - 1 ? 'p' : L === 3 ? 'H' : `H${l}`)
  const nodes: NetNode[] = net.sizes.map((m, l) => ({
    id: `l${l}`, label: name(l), kind: 'neurons', shape: [m],
    title: l === 0 ? 'input x' : l === L - 1 ? 'output p (sigmoid)' : `hidden ${name(l)} (${net.act})`,
    note: l === 0 ? 'The two input numbers of one example.' : `Each neuron: a weighted sum of the ${net.sizes[l - 1]} numbers before it, plus a bias, then ${l === L - 1 ? 'sigmoid' : net.act}.`,
  }))
  const edges: NetEdge[] = net.W.map((W, l) => ({ id: `W${l + 1}`, from: `l${l}`, to: `l${l + 1}`, kind: 'dense', weights: W, label: `W${l + 1}` }))
  const steps: NetStep[] = acts.map((a, l) => ({
    id: `s${l}`, dir: 'forward', title: l === 0 ? 'input' : name(l),
    active: l === 0 ? ['l0'] : [`W${l}`, `l${l}`],
    values: { [`l${l}`]: a.map(r4) },
    text: l === 0 ? `x = ${list(a)}.` : `${name(l)} = ${l === L - 1 ? 'sigmoid' : net.act}(${name(l - 1)} · W${l} + b${l}) = ${list(a.slice(0, 8))}${a.length > 8 ? ' …' : ''}.`,
  }))
  return { id, layout: 'row', nodes, edges, steps }
}
