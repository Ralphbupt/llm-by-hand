import { describe, expect, it } from 'vitest'
import g from '../../public/data/goldens/core.json'
import {
  allClose, attention, causalMask, layerNormRows, matmul,
  maskedSoftmaxRows, relu, shape, softmaxRows, transpose,
} from './num'

const close = (a: unknown, b: unknown) => expect(allClose(a, b, 1e-9)).toBe(true)

describe('和 numpy 对拍(goldens 由 export/export_goldens.py 生成)', () => {
  it('注意力:3 个词 2 维', () => {
    const c = g.attention_3x2
    const r = attention(c.X, c.X, c.X, c.d_k)
    close(r.scores, c.scores)
    close(r.weights, c.weights)
    close(r.out, c.out)
  })

  it('矩阵乘 (3,4)@(4,2)', () => {
    close(matmul(g.matmul_3x4_4x2.a, g.matmul_3x4_4x2.b), g.matmul_3x4_4x2.out)
  })

  it('带 causal mask 的 softmax', () => {
    close(maskedSoftmaxRows(g.masked_softmax_4.scores, g.masked_softmax_4.mask), g.masked_softmax_4.weights)
  })

  it('LayerNorm 逐行', () => {
    close(layerNormRows(g.layernorm_2x5.x), g.layernorm_2x5.out)
  })

  it('ReLU', () => {
    close(relu(g.relu_2x3.x), g.relu_2x3.out)
  })
})

describe('基本性质', () => {
  it('形状与转置', () => {
    expect(shape([[1, 2, 3], [4, 5, 6]])).toEqual([2, 3])
    expect(transpose([[1, 2, 3], [4, 5, 6]])).toEqual([[1, 4], [2, 5], [3, 6]])
  })

  it('throws when shapes do not match', () => {
    expect(() => matmul([[1, 2]], [[1, 2]])).toThrow(/Shapes do not match/)
  })

  it('softmax 每行加起来是 1', () => {
    softmaxRows([[1, 2, 3], [0, 0, 0]]).forEach((r) =>
      expect(r.reduce((a, b) => a + b, 0)).toBeCloseTo(1, 12),
    )
  })

  it('causal mask 是上三角', () => {
    expect(causalMask(3)).toEqual([
      [false, true, true],
      [false, false, true],
      [false, false, false],
    ])
  })
})
