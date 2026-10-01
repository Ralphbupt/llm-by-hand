/** Level 19 and 20 helpers. Every function matches content/2-theory/modern-llm/demo.py or inference-cost/demo.py. */

export function layerNorm(x: number[], eps = 0) {
  const mean = x.reduce((a, b) => a + b, 0) / x.length
  const variance = x.reduce((a, b) => a + (b - mean) ** 2, 0) / x.length
  const std = Math.sqrt(variance + eps)
  return { mean, std, out: x.map((v) => (v - mean) / std) }
}

export function rmsNorm(x: number[], eps = 0) {
  const meanSq = x.reduce((a, b) => a + b * b, 0) / x.length
  const rms = Math.sqrt(meanSq + eps)
  return { meanSq, rms, out: x.map((v) => v / rms) }
}

/** RoPE for one pair of numbers: rotate by pos × theta radians. */
export function rotate(v: [number, number], pos: number, theta = 0.5): [number, number] {
  const a = pos * theta
  const c = Math.cos(a)
  const s = Math.sin(a)
  return [c * v[0] - s * v[1], s * v[0] + c * v[1]]
}

export const dot = (a: number[], b: number[]) => a.reduce((acc, v, i) => acc + v * b[i], 0)
export const silu = (z: number) => z / (1 + Math.exp(-z))

/** Bytes of K and V stored per token: 2 (K and V) × heads × d_head × layers × bytes per number. */
export const kvBytesPerToken = (nKv: number, dHead: number, layers: number, bytes = 2) => 2 * nKv * dHead * layers * bytes
