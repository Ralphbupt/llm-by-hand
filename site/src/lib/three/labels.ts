/**
 * HTML labels for the 3D views: plain text in a layer over the canvas, moved to its 3D anchor on every frame.
 * They use the site's fonts and rem sizes (so the Settings text size reaches them), stay sharp at any pixel ratio,
 * have a halo in the page background color (readable on any surface, in both themes), never rotate or mirror,
 * and the lower-priority one of two overlapping labels hides (see placeLabels in geom.ts).
 *
 *   labels.begin('axes')                       // start a set; labels of this set not touched again are removed
 *   labels.set('axes', 'x', 'w', [1, 0, 0], { role: 'axis', anchor: 'right' })
 *   labels.end('axes')
 */
import * as THREE from 'three'
import { placeLabels, type LabelItem } from './geom'
import type { Tone } from './kit'

/** tick: numbers on an axis · axis: an axis name · name: a block/word name · op: an operator (@, =, →) · callout: a note on a point */
export type LabelRole = 'tick' | 'axis' | 'name' | 'op' | 'callout'
export type LabelAnchor = 'center' | 'above' | 'below' | 'left' | 'right'
export type LabelOpts = {
  role?: LabelRole
  /** a semantic color token; default per role (fg, or dim for ticks and axes) */
  tone?: Tone
  /** a raw CSS color (only for Points3D's legacy `color`) */
  color?: string
  /** higher wins a collision; default by role: op 50, name 40, callout 35, axis 20, tick 10 */
  priority?: number
  /** read top to bottom (CSS writing-mode), e.g. a row-axis name down the left edge; 'upright' stacks the letters */
  vertical?: boolean | 'upright'
  /** where the text sits relative to its anchor point */
  anchor?: LabelAnchor
  /** extra screen offset in px */
  offset?: [number, number]
  /** the anchor is in this object's local coordinates (it follows the object) */
  parent?: THREE.Object3D
  /** false: never fade behind an occluder (for a marker that is itself drawn on top of everything) */
  occlude?: boolean
  /** never hide in a collision (step further away instead): for names that are the only legend of a mark */
  keep?: boolean
}

const PRIORITY: Record<LabelRole, number> = { op: 50, name: 40, callout: 35, axis: 20, tick: 10 }

type Entry = {
  el: HTMLSpanElement
  text: string
  at: THREE.Vector3
  o: LabelOpts
  w: number; h: number; measured: boolean
  seen: boolean
  shown: boolean
  x: number; y: number
  occluded: boolean
}

export class LabelLayer {
  readonly el: HTMLDivElement
  private items = new Map<string, Entry>()
  private v = new THREE.Vector3()
  /** labels whose anchor is hidden behind these objects are drawn faded (checked at most ~8 times a second) */
  occluders: THREE.Object3D[] = []
  /** marks drawn in the scene (a learner's point, a minimum): no label may sit on them (radius in CSS px) */
  obstacles: { at: THREE.Vector3; r: number }[] = []
  private ray = new THREE.Raycaster()
  private lastOcc = 0
  private occTimer: ReturnType<typeof setTimeout> | null = null
  /** asks the stage for one more frame (set by the stage) */
  requestFrame: () => void = () => {}

  constructor(parent: HTMLElement) {
    this.el = document.createElement('div')
    this.el.className = 'stage3d-labels'
    this.el.setAttribute('aria-hidden', 'true') // the view's aria-label and the lab's text carry the meaning
    parent.appendChild(this.el)
  }

  /** Start (re)declaring the labels of one set. */
  begin(set: string) {
    for (const [k, e] of this.items) if (k.startsWith(set + ':')) e.seen = false
  }

  /** Add or update one label. `at` is in world units (or in `parent`'s local units). */
  set(set: string, key: string, text: string, at: THREE.Vector3 | [number, number, number], o: LabelOpts = {}) {
    const id = `${set}:${key}`
    let e = this.items.get(id)
    if (!e) {
      const el = document.createElement('span')
      el.className = 'l3d'
      this.el.appendChild(el)
      e = { el, text: '', at: new THREE.Vector3(), o: {}, w: 0, h: 0, measured: false, seen: true, shown: true, x: NaN, y: NaN, occluded: false }
      this.items.set(id, e)
    }
    e.seen = true
    if (Array.isArray(at)) e.at.set(at[0], at[1], at[2])
    else e.at.copy(at)
    const role = o.role ?? 'name'
    const styleKey = `${role}|${o.tone ?? ''}|${o.color ?? ''}|${o.vertical ?? ''}`
    const prevKey = `${e.o.role ?? 'name'}|${e.o.tone ?? ''}|${e.o.color ?? ''}|${e.o.vertical ?? ''}`
    if (text !== e.text || styleKey !== prevKey || !e.el.dataset.role) {
      e.el.textContent = text
      e.el.dataset.role = role
      e.el.classList.toggle('v', !!o.vertical)
      e.el.classList.toggle('up', o.vertical === 'upright')
      e.el.style.color = o.color ?? (o.tone ? `var(--${o.tone})` : '')
      e.text = text
      e.measured = false
    }
    e.o = o
  }

  /** Remove the labels of `set` that were not declared since begin(set). */
  end(set: string) {
    for (const [k, e] of this.items)
      if (k.startsWith(set + ':') && !e.seen) { e.el.remove(); this.items.delete(k) }
  }

  /** Remove every label of one set (or all). */
  clear(set?: string) {
    for (const [k, e] of this.items)
      if (!set || k.startsWith(set + ':')) { e.el.remove(); this.items.delete(k) }
  }

  /** Sizes change with the text-size setting or fonts loading: measure again on the next update. */
  invalidate() {
    for (const e of this.items.values()) e.measured = false
  }

  /** Project every label for this camera and place them (W×H = the view in CSS px). */
  update(camera: THREE.Camera, W: number, H: number) {
    const list = [...this.items.values()]
    // measure in one pass (reads), then write positions (no layout thrashing)
    for (const e of list) if (!e.measured) { e.w = e.el.offsetWidth; e.h = e.el.offsetHeight; e.measured = e.w > 0 }
    const items: LabelItem[] = list.map((e) => {
      const p = this.v.copy(e.at)
      if (e.o.parent) e.o.parent.localToWorld(p)
      p.project(camera)
      if (p.z > 1 || p.z < -1) return { x: NaN, y: NaN, w: e.w, h: e.h, priority: 0 }
      let x = (p.x * 0.5 + 0.5) * W, y = (-p.y * 0.5 + 0.5) * H
      const a = e.o.anchor ?? 'center'
      if (a === 'center') { x -= e.w / 2; y -= e.h / 2 }
      else if (a === 'above') { x -= e.w / 2; y -= e.h + 4 }
      else if (a === 'below') { x -= e.w / 2; y += 4 }
      else if (a === 'left') { x -= e.w + 6; y -= e.h / 2 }
      else { x += 6; y -= e.h / 2 }
      x += e.o.offset?.[0] ?? 0
      y += e.o.offset?.[1] ?? 0
      const role = e.o.role ?? 'name'
      return { x, y, w: e.w, h: e.h, priority: e.o.priority ?? PRIORITY[role], nudge: role !== 'tick' && role !== 'op', keep: e.o.keep }
    })
    // obstacles go first, at the top priority: labels that would cover them move (or hide, for ticks)
    const obs: LabelItem[] = this.obstacles.map((o) => {
      const p = this.v.copy(o.at).project(camera)
      if (p.z > 1 || p.z < -1) return { x: NaN, y: NaN, w: 0, h: 0, priority: 0 }
      return { x: (p.x * 0.5 + 0.5) * W - o.r, y: (-p.y * 0.5 + 0.5) * H - o.r, w: 2 * o.r, h: 2 * o.r, priority: 1e9 }
    })
    const placed = placeLabels([...obs, ...items], W, H).slice(obs.length)
    this.checkOcclusion(camera, list)
    placed.forEach((p, i) => {
      const e = list[i]
      if (p.show !== e.shown) { e.el.classList.toggle('hidden', !p.show); e.shown = p.show }
      if (p.show && (p.x !== e.x || p.y !== e.y)) {
        e.el.style.transform = `translate(${Math.round(p.x)}px, ${Math.round(p.y)}px)`
        e.x = p.x; e.y = p.y
      }
    })
  }

  /** Fade labels whose anchor is behind an occluder (a hill of the surface in front of a tick). Throttled. */
  private checkOcclusion(camera: THREE.Camera, list: Entry[]) {
    if (!this.occluders.length) return
    const now = performance.now()
    if (now - this.lastOcc < 120) {
      // the camera may have stopped: check once more a moment later
      if (!this.occTimer) this.occTimer = setTimeout(() => { this.occTimer = null; this.requestFrame() }, 140)
      return
    }
    this.lastOcc = now
    const eye = new THREE.Vector3().setFromMatrixPosition(camera.matrixWorld)
    const dir = new THREE.Vector3()
    for (const e of list) {
      if (e.o.occlude === false) {
        if (e.occluded) { e.el.classList.remove('occluded'); e.occluded = false }
        continue
      }
      const p = this.v.copy(e.at)
      if (e.o.parent) e.o.parent.localToWorld(p)
      const dist = dir.subVectors(p, eye).length()
      this.ray.set(eye, dir.normalize())
      this.ray.far = dist - 0.03
      const hidden = this.ray.intersectObjects(this.occluders, false).length > 0
      if (hidden !== e.occluded) { e.el.classList.toggle('occluded', hidden); e.occluded = hidden }
    }
  }

  dispose() {
    if (this.occTimer) clearTimeout(this.occTimer)
    this.items.clear()
    this.el.remove()
  }
}
