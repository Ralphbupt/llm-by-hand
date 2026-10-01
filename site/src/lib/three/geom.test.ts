import { describe, expect, it } from 'vitest'
import {
  fitView, anglesFromDir, bounds, boundsChange, contourSegments, dirFromAngles, fitDistance, fmtTick, needsSeeThrough,
  niceStep, niceTicks, pickVictims, placeLabels, type V3,
} from './geom'

describe('ticks', () => {
  it('picks 1-2-2.5-5 steps', () => {
    expect(niceStep(10, 5)).toBe(2)
    expect(niceStep(5.2, 5)).toBe(2)
    expect(niceStep(1, 4)).toBe(0.25)
    expect(niceStep(0)).toBe(1)
  })
  it('covers the range with round numbers', () => {
    expect(niceTicks(-1, 4, 5)).toEqual([-1, 0, 1, 2, 3, 4])
    expect(niceTicks(-3, 3, 4)).toEqual([-2, 0, 2])
    expect(niceTicks(-3, 3, 6)).toEqual([-3, -2, -1, 0, 1, 2, 3])
    expect(niceTicks(0, 1, 4)).toEqual([0, 0.25, 0.5, 0.75, 1])
    expect(niceTicks(4, -1, 5)).toEqual([-1, 0, 1, 2, 3, 4])
    expect(niceTicks(0.1, 0.35, 5)).toEqual([0.1, 0.15, 0.2, 0.25, 0.3, 0.35])
  })
  it('formats with a real minus and no -0', () => {
    expect(fmtTick(-1.5)).toBe('−1.5')
    expect(fmtTick(-0)).toBe('0')
    expect(fmtTick(0.30000000000000004)).toBe('0.3')
  })
})

describe('camera', () => {
  it('turns azimuth from +z toward +x and back', () => {
    const d = dirFromAngles(90, 0)
    expect(d[0]).toBeCloseTo(1); expect(d[2]).toBeCloseTo(0)
    const a = anglesFromDir(dirFromAngles(32, 24))
    expect(a.azimuth).toBeCloseTo(32); expect(a.elevation).toBeCloseTo(24)
  })
  it('fits a unit cube seen straight on', () => {
    const pts: V3[] = []
    for (const x of [-1, 1]) for (const y of [-1, 1]) for (const z of [-1, 1]) pts.push([x, y, z])
    const t = Math.tan(Math.PI / 8) // 45° field of view
    const D = fitDistance(pts, [0, 0, 0], [0, 0, 1], t, t, 0)
    // the near face (z = 1) is the binding one: D = 1 + 1/tan(22.5°)
    expect(D).toBeCloseTo(1 + 1 / t)
    // a margin needs more distance
    expect(fitDistance(pts, [0, 0, 0], [0, 0, 1], t, t, 0.1)).toBeGreaterThan(D)
  })
  it('centers a box seen from above in the picture', () => {
    const pts: V3[] = []
    for (const x of [-1, 1]) for (const y of [0, 1]) for (const z of [-1, 1]) pts.push([x, y, z])
    const t = Math.tan(Math.PI / 12)
    const dir = dirFromAngles(30, 30)
    const v = fitView(pts, dir, t * 1.3, t, 0.05)
    // projected extents are symmetric around the picture center after fitting
    const back = dir, right = [Math.cos(Math.PI / 6), 0, -Math.sin(Math.PI / 6)]
    const up = [back[1] * right[2] - back[2] * right[1], back[2] * right[0] - back[0] * right[2], back[0] * right[1] - back[1] * right[0]]
    const ys = pts.map((p) => {
      const q = [p[0] - v.center[0], p[1] - v.center[1], p[2] - v.center[2]]
      const depth = v.distance - (q[0] * back[0] + q[1] * back[1] + q[2] * back[2])
      return (q[0] * up[0] + q[1] * up[1] + q[2] * up[2]) / depth
    })
    expect(Math.max(...ys) + Math.min(...ys)).toBeCloseTo(0, 3)
  })
  it('measures how much bounds changed', () => {
    const a = bounds([[0, 0, 0], [1, 1, 1]])
    expect(boundsChange(a, a)).toBe(0)
    expect(boundsChange(a, bounds([[0, 0, 0], [1.1, 1, 1]]))).toBeCloseTo(0.1 / 1.1)
  })
})

describe('context budget', () => {
  const s = (id: number, live: boolean, visible: boolean, lastSeen: number, pinned = false) => ({ id, live, visible, lastSeen, pinned })
  it('releases nothing under the cap', () => {
    expect(pickVictims([s(1, true, true, 1), s(2, false, false, 0)], 2, 4)).toEqual([])
  })
  it('releases offscreen views first, least recently seen first', () => {
    const slots = [s(1, true, true, 9), s(2, true, false, 5), s(3, true, false, 2), s(4, true, true, 1), s(5, false, true, 10)]
    expect(pickVictims(slots, 5, 4)).toEqual([3])
    expect(pickVictims(slots, 5, 2)).toEqual([3, 2, 4])
  })
  it('never releases a pinned view or the requester', () => {
    expect(pickVictims([s(1, true, false, 0, true), s(2, true, true, 1)], 2, 1)).toEqual([])
  })
})

describe('label placement', () => {
  it('hides the lower-priority label of two that overlap', () => {
    const out = placeLabels([
      { x: 10, y: 10, w: 40, h: 12, priority: 1 },
      { x: 20, y: 12, w: 40, h: 12, priority: 5 },
    ], 200, 100)
    expect(out[1].show).toBe(true)
    expect(out[0].show).toBe(false)
  })
  it('nudges a label up when it may', () => {
    const out = placeLabels([
      { x: 20, y: 40, w: 40, h: 12, priority: 5 },
      { x: 20, y: 40, w: 40, h: 12, priority: 1, nudge: true },
    ], 200, 100)
    expect(out[1]).toEqual({ x: 20, y: 26, show: true })
  })
  it('keeps a "keep" label: it steps further away instead of hiding', () => {
    const out = placeLabels([
      { x: 20, y: 40, w: 40, h: 12, priority: 5 },
      { x: 20, y: 26, w: 40, h: 12, priority: 5 },
      { x: 20, y: 40, w: 40, h: 12, priority: 1, keep: true },
    ], 200, 100)
    expect(out[2]).toEqual({ x: 20, y: 54, show: true })
  })
  it('pulls a label back inside the view instead of clipping it', () => {
    const [p] = placeLabels([{ x: -10, y: 5, w: 60, h: 12, priority: 1 }], 200, 100)
    expect(p).toEqual({ x: 2, y: 5, show: true })
  })
  it('hides a label whose anchor is far outside', () => {
    expect(placeLabels([{ x: 400, y: 5, w: 20, h: 12, priority: 1 }], 200, 100)[0].show).toBe(false)
  })
})

describe('contours', () => {
  it('draws one segment across a ramp', () => {
    // 2×2 grid rising left to right: the level 0.5 crosses the middle of the top and bottom edges
    expect(contourSegments([0, 1, 0, 1], 2, [0.5])).toEqual([0, 0.5, 1, 0.5])
  })
  it('skips cells with missing values', () => {
    expect(contourSegments([0, NaN, 0, 1], 2, [0.5])).toEqual([])
  })
})

describe('tensors', () => {
  it('goes see-through only when a highlight starts behind the front slice', () => {
    expect(needsSeeThrough(1, [{ from: [0, 1, 1] }])).toBe(false)
    expect(needsSeeThrough(4, [{ from: [0, 0, 2] }])).toBe(false)
    expect(needsSeeThrough(4, [{ from: [2, 0, 0] }])).toBe(true)
  })
})
