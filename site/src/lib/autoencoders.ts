/**
 * Level N6: the trained decoders (exported by content/1-foundations/autoencoders/demo.py --export) run in the browser.
 * decoder: 2 numbers → ReLU(z @ W1 + b1) (128) → sigmoid(h @ W2 + b2) (784 pixels in [0, 1]).
 * Big weight tables are stored as int8 with one scale per table.
 */
export type Q8 = { shape: number[]; scale: number; b64: string }
export type DecoderJSON = { W1: Q8; b1: number[]; W2: Q8; b2: number[] }
export type ModelJSON = { codes: number[][]; decoder: DecoderJSON }
export type ModelsJSON = { labels: number[]; ae: ModelJSON; vae: ModelJSON }

function atobAny(s: string): Uint8Array {
  if (typeof atob === 'function') return Uint8Array.from(atob(s), (c) => c.charCodeAt(0))
  return new Uint8Array(Buffer.from(s, 'base64'))
}

/** int8 table → row-major Float32Array of shape [rows, cols] */
export function dequant(q: Q8): Float32Array {
  const bytes = atobAny(q.b64)
  const out = new Float32Array(bytes.length)
  const i8 = new Int8Array(bytes.buffer, bytes.byteOffset, bytes.length)
  for (let i = 0; i < i8.length; i++) out[i] = i8[i] * q.scale
  return out
}

export type Decoder = { W1: Float32Array; b1: number[]; W2: Float32Array; b2: number[]; H: number }

export function loadDecoder(d: DecoderJSON): Decoder {
  return { W1: dequant(d.W1), b1: d.b1, W2: dequant(d.W2), b2: d.b2, H: d.W1.shape[1] }
}

/** Decode one 2-number code into 784 pixel values in [0, 1]. */
export function decode(dec: Decoder, z: [number, number]): Float32Array {
  const { W1, b1, W2, b2, H } = dec
  const h = new Float32Array(H)
  for (let j = 0; j < H; j++) h[j] = Math.max(0, z[0] * W1[j] + z[1] * W1[H + j] + b1[j])
  const out = new Float32Array(784)
  for (let p = 0; p < 784; p++) {
    let s = b2[p]
    for (let j = 0; j < H; j++) if (h[j] !== 0) s += h[j] * W2[j * 784 + p]
    out[p] = 1 / (1 + Math.exp(-s))
  }
  return out
}

/** z = μ + σ·ε (the reparameterization trick) */
export const reparam = (mu: number, sigma: number, eps: number) => mu + sigma * eps

/** One standard normal sample from a uniform generator (Box–Muller). */
export function gauss(rand: () => number = Math.random): number {
  const u = 1 - rand(), v = rand()
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v)
}
