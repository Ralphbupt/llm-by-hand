/**
 * The shared 3D look (AUTHORING.md "Visual style → 3D"): semantic tones, color ramps, the one light setup,
 * tensor cells (one instanced draw call per block, edges drawn in the shader), screen-width lines, arrows, dots,
 * floor grids, and freeing GPU memory.
 */
import * as THREE from 'three'
import { Line2 } from 'three/examples/jsm/lines/Line2.js'
import { LineGeometry } from 'three/examples/jsm/lines/LineGeometry.js'
import { LineMaterial } from 'three/examples/jsm/lines/LineMaterial.js'
import { LineSegments2 } from 'three/examples/jsm/lines/LineSegments2.js'
import { LineSegmentsGeometry } from 'three/examples/jsm/lines/LineSegmentsGeometry.js'
import type { Palette } from './stage'

/** Semantic color tokens (AUTHORING.md "Color tokens"). 'cat-N' are plain categories. */
export type Tone = 'accent' | 'ok' | 'warn' | 'fg' | 'dim' | 'pos' | 'neg' | 'grad' | 'cat-1' | 'cat-2' | 'cat-3' | 'cat-4' | 'cat-5'

export function toneColor(p: Palette, t: Tone): THREE.Color {
  return t.startsWith('cat-') ? p.cat[Number(t.slice(4)) - 1] ?? p.fg : p[t as Exclude<Tone, `cat-${number}`>] ?? p.fg
}

export const mix = (a: THREE.Color, b: THREE.Color, t: number) => a.clone().lerp(b, Math.min(1, Math.max(0, t)))

/** True when the page background is dark. */
export const isDarkPalette = (p: Palette) => p.bg.r + p.bg.g + p.bg.b < 1.2

// ---- ramps ---------------------------------------------------------------------------------
/**
 * seq  — sizes and losses: card → a strong gray (toward fg), lightness changes in one direction. Neutral on purpose:
 *        the learner's point (accent), the minimum (ok) and errors (warn) are the only colors on top of it
 * div  — signed values: neg ← card → pos, 0 (t = 0.5) is the card color
 * prob — a probability between two classes: cat-3 ← card → cat-1, 0.5 is the card color
 */
export type RampKind = 'seq' | 'div' | 'prob'
export function ramp(p: Palette, kind: RampKind, ends?: { low: THREE.Color; high: THREE.Color }): (t: number) => THREE.Color {
  if (ends) return (t) => mix(ends.low, ends.high, t)
  if (kind === 'seq') {
    // dark mode: stop at a middle gray, so light paths and points on top of it keep their contrast
    const lo = mix(p.card, p.fg, 0.07), hi = mix(p.card, p.fg, isDarkPalette(p) ? 0.38 : 0.55)
    return (t) => mix(lo, hi, Math.pow(Math.min(1, Math.max(0, t)), 0.8))
  }
  const [a, b] = kind === 'div' ? [p.neg, p.pos] : [p.cat[2], p.cat[0]]
  const mid = mix(p.card, p.fg, 0.06)
  return (t) => (t < 0.5 ? mix(a, mid, t * 2) : mix(mid, b, (t - 0.5) * 2))
}

// ---- lights and materials -------------------------------------------------------------------
/**
 * One light setup for every view, calibrated for three's physical lights (diffuse is divided by π):
 * a face pointing up shows the token color exactly, a face toward the camera ~0.88, faces turned away 0.65.
 * Subtle shading for depth, no shine (Lambert materials only).
 */
export function addLights(scene: THREE.Scene) {
  scene.add(new THREE.AmbientLight(0xffffff, 0.65 * Math.PI))
  const sun = new THREE.DirectionalLight(0xffffff, 0.45 * Math.PI)
  sun.position.set(3, 6, 4)
  scene.add(sun)
}

export const matte = (color: THREE.Color, o: THREE.MeshLambertMaterialParameters = {}) => new THREE.MeshLambertMaterial({ color, ...o })

// ---- tensor cells --------------------------------------------------------------------------
/**
 * A unit box whose faces carry a fixed brightness (front 1, top 1.12, sides 0.78, back 0.9, bottom 0.7), so cells
 * need no lights: the front face is exactly the legend color. Shared by every cell of a view (one per stage).
 */
export function cellGeometry(size: number): THREE.BoxGeometry {
  const g = new THREE.BoxGeometry(size, size, size)
  // BoxGeometry face order: +x, −x, +y, −y, +z, −z; 4 vertices each
  const shade = [0.78, 0.78, 1.12, 0.7, 1, 0.9]
  const c = new Float32Array(24 * 3)
  for (let v = 0; v < 24; v++) c.fill(shade[Math.floor(v / 4)], v * 3, v * 3 + 3)
  g.setAttribute('color', new THREE.BufferAttribute(c, 3))
  return g
}

export type CellMaterial = THREE.MeshBasicMaterial & { userData: { uEdgeColor: { value: THREE.Color }; uEdge: { value: number }; uEdgeAlpha: { value: number } } }

/**
 * Material for instanced cells. Cell edges are drawn in the fragment shader (~1 px at any distance, no extra draw
 * call): `edge` = how far edges go toward `edgeColor` (0..1); `edgeAlpha` > 0 makes edges more opaque than the fill
 * (outlines of faded "ghost" cells).
 */
export function cellMaterial(o: { edge: number; edgeColor: THREE.Color; opacity?: number; edgeAlpha?: number }): CellMaterial {
  const translucent = (o.opacity ?? 1) < 1
  const m = new THREE.MeshBasicMaterial({
    vertexColors: true, transparent: translucent, opacity: o.opacity ?? 1, depthWrite: !translucent,
  }) as CellMaterial
  m.userData.uEdgeColor = { value: o.edgeColor.clone() }
  m.userData.uEdge = { value: o.edge }
  m.userData.uEdgeAlpha = { value: o.edgeAlpha ?? -1 }
  m.onBeforeCompile = (s) => {
    s.uniforms.uEdgeColor = m.userData.uEdgeColor
    s.uniforms.uEdge = m.userData.uEdge
    s.uniforms.uEdgeAlpha = m.userData.uEdgeAlpha
    s.vertexShader = s.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec2 vCellUv;')
      .replace('#include <uv_vertex>', '#include <uv_vertex>\nvCellUv = uv;')
    s.fragmentShader = s.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying vec2 vCellUv;\nuniform vec3 uEdgeColor;\nuniform float uEdge;\nuniform float uEdgeAlpha;')
      .replace('#include <color_fragment>', `#include <color_fragment>
        vec2 cellEd = min(vCellUv, 1.0 - vCellUv);
        float cellD = min(cellEd.x, cellEd.y);
        float cellW = max(fwidth(cellD), 1e-4);
        float cellLine = 1.0 - smoothstep(cellW * 0.7, cellW * 1.7, cellD);
        // cells only a few pixels wide: their grid lines would beat into moire, so they fade out completely
        // (the block then reads as one solid block; its faces keep their own shading)
        float cellPx = 1.0 / max(max(fwidth(vCellUv.x), fwidth(vCellUv.y)), 1e-4);
        cellLine *= smoothstep(5.5, 11.0, cellPx);
        diffuseColor.rgb = mix(diffuseColor.rgb, uEdgeColor, cellLine * uEdge);
        if (uEdgeAlpha > 0.0) diffuseColor.a = mix(diffuseColor.a, uEdgeAlpha, cellLine);`)
  }
  m.customProgramCacheKey = () => 'llmbh-cell'
  return m
}

/** An InstancedMesh with room for `capacity` cells; set `.count` to how many are used. */
export function cellMesh(geo: THREE.BufferGeometry, mat: THREE.Material, capacity: number): THREE.InstancedMesh {
  const m = new THREE.InstancedMesh(geo, mat, Math.max(1, capacity))
  m.instanceMatrix.setUsage(THREE.DynamicDrawUsage)
  m.setColorAt(0, new THREE.Color()) // allocate instanceColor
  m.instanceColor!.setUsage(THREE.DynamicDrawUsage)
  m.count = 0
  m.frustumCulled = false // the bounding sphere of an instanced mesh does not follow its instances
  m.userData.sharedGeometry = true
  m.userData.sharedMaterial = true
  return m
}

// ---- lines ---------------------------------------------------------------------------------
/** A polyline whose width is in CSS pixels (WebGL's own lines are 1 device pixel, too thin at DPR 2). */
export function fatLine(points: THREE.Vector3[], color: THREE.Color, px = 2.5, o: { dashed?: boolean } = {}): Line2 {
  const g = new LineGeometry()
  g.setPositions(points.flatMap((p) => [p.x, p.y, p.z]))
  const m = new LineMaterial({ color: color.getHex(THREE.SRGBColorSpace), linewidth: px, worldUnits: false, dashed: !!o.dashed, dashSize: 0.05, gapSize: 0.035 })
  m.color.copy(color)
  const l = new Line2(g, m)
  if (o.dashed) l.computeLineDistances()
  return l
}

/** Many segments in one draw call, each vertex with its own color: positions/colors are flat xyz / rgb per endpoint. */
export function fatSegments(positions: number[], colors: number[] | null, color: THREE.Color, px = 1.5): LineSegments2 {
  const g = new LineSegmentsGeometry()
  g.setPositions(positions)
  if (colors) g.setColors(colors)
  const m = new LineMaterial({ color: 0xffffff, linewidth: px, worldUnits: false, vertexColors: !!colors })
  if (!colors) m.color.copy(color)
  return new LineSegments2(g, m)
}

/** Thin (1 device px) segments for hairlines: grids, contours. */
export function hairlines(positions: number[], color: THREE.Color, o: { dashed?: boolean } = {}): THREE.LineSegments {
  const g = new THREE.BufferGeometry()
  g.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  const m = o.dashed ? new THREE.LineDashedMaterial({ color, dashSize: 0.04, gapSize: 0.03 }) : new THREE.LineBasicMaterial({ color })
  const l = new THREE.LineSegments(g, m)
  if (o.dashed) l.computeLineDistances()
  return l
}

// ---- arrows and dots -----------------------------------------------------------------------
const UP = new THREE.Vector3(0, 1, 0)
/** A solid arrow (cylinder + cone) from `from` to `to`; `r` is the shaft radius in world units. */
export function arrow3(from: THREE.Vector3, to: THREE.Vector3, color: THREE.Color, r = 0.012): THREE.Group {
  const g = new THREE.Group()
  const d = to.clone().sub(from)
  const len = d.length()
  if (len < 1e-6) return g
  const headLen = Math.min(len * 0.35, r * 9), headR = r * 3
  const mat = matte(color)
  const shaft = new THREE.Mesh(new THREE.CylinderGeometry(r, r, len - headLen, 10), mat)
  shaft.position.y = (len - headLen) / 2
  const head = new THREE.Mesh(new THREE.ConeGeometry(headR, headLen, 16), mat)
  head.position.y = len - headLen / 2
  g.add(shaft, head)
  g.position.copy(from)
  g.quaternion.setFromUnitVectors(UP, d.normalize())
  return g
}

/** Spheres in one draw call: one shared unit sphere, scaled and colored per instance. */
export function dots(items: { at: THREE.Vector3; r: number; color: THREE.Color }[], sphere: THREE.BufferGeometry): THREE.InstancedMesh {
  const m = new THREE.InstancedMesh(sphere, new THREE.MeshLambertMaterial({ color: 0xffffff }), Math.max(1, items.length))
  setDots(m, items)
  m.userData.sharedGeometry = true
  m.frustumCulled = false
  return m
}

/** Move/recolor the spheres of a dots() mesh in place (no new GPU objects); grows only when needed. */
export function setDots(m: THREE.InstancedMesh, items: { at: THREE.Vector3; r: number; color: THREE.Color }[]) {
  const M = new THREE.Matrix4(), S = new THREE.Vector3(), Q = new THREE.Quaternion()
  items.forEach((it, i) => {
    M.compose(it.at, Q, S.setScalar(it.r))
    m.setMatrixAt(i, M)
    m.setColorAt(i, it.color)
  })
  m.count = items.length
  m.instanceMatrix.needsUpdate = true
  if (m.instanceColor) m.instanceColor.needsUpdate = true
}

// ---- floor ---------------------------------------------------------------------------------
/** Grid lines on the plane y = `y`: one line at each x in `xs` (from z0 to z1) and each z in `zs` (from x0 to x1). */
export function floorGrid(xs: number[], zs: number[], ext: { x0: number; x1: number; z0: number; z1: number }, y: number, color: THREE.Color) {
  const pos: number[] = []
  for (const x of xs) pos.push(x, y, ext.z0, x, y, ext.z1)
  for (const z of zs) pos.push(ext.x0, y, z, ext.x1, y, z)
  return hairlines(pos, color)
}

// ---- freeing GPU memory --------------------------------------------------------------------
/**
 * Free the geometries, materials and textures under `o` (call before rebuilding a group).
 * Objects with userData.sharedGeometry / sharedMaterial keep theirs (they belong to the stage).
 */
export function disposeObject(o: THREE.Object3D) {
  o.traverse((x) => {
    const m = x as THREE.Mesh
    if (m.geometry && !x.userData.sharedGeometry) m.geometry.dispose()
    if (m.material && !x.userData.sharedMaterial) {
      const mats = Array.isArray(m.material) ? m.material : [m.material]
      for (const mat of mats) {
        for (const v of Object.values(mat)) if (v instanceof THREE.Texture) v.dispose()
        mat.dispose()
      }
    }
    if ((x as THREE.InstancedMesh).isInstancedMesh) (x as THREE.InstancedMesh).dispose()
  })
}

/** Remove a group's children and free what they own. */
export function clearGroup(g: THREE.Object3D) {
  disposeObject(g)
  // disposeObject also visited g itself; it owns nothing, so that is harmless
  g.clear()
}
