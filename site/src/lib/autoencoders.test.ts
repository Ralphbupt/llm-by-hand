import fs from 'node:fs'
import { describe, expect, it } from 'vitest'
import { decode, loadDecoder, reparam, type ModelsJSON } from './autoencoders'

const data = JSON.parse(fs.readFileSync(new URL('../../public/data/autoencoders/models.json', import.meta.url), 'utf8')) as ModelsJSON

describe('autoencoder lab data (from demo.py --export)', () => {
  it('has 40 test digits per class and their codes', () => {
    expect(data.labels.length).toBe(400)
    expect(data.ae.codes.length).toBe(400)
    expect(data.vae.codes[0].length).toBe(2)
  })
  it('decodes a code into 784 pixels in [0, 1], and a 1 looks thin: fewer bright pixels than an 8', () => {
    const dec = loadDecoder(data.vae.decoder)
    const mean = (d: number) => {
      const idx = data.labels.map((l, i) => [l, i]).filter(([l]) => l === d).map(([, i]) => i)
      const z = [0, 1].map((k) => idx.reduce((s, i) => s + data.vae.codes[i][k], 0) / idx.length) as [number, number]
      return decode(dec, z).reduce((s, v) => s + v, 0)
    }
    const img = decode(dec, [0, 0])
    expect(img.length).toBe(784)
    expect(Math.min(...img)).toBeGreaterThanOrEqual(0)
    expect(Math.max(...img)).toBeLessThanOrEqual(1)
    expect(mean(1)).toBeLessThan(mean(8))
  })
  it('reparameterization: μ = 1, σ = 0.5, ε = −2 gives 0', () => {
    expect(reparam(1, 0.5, -2)).toBe(0)
  })
})
