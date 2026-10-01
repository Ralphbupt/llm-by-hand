/**
 * The three.js "stage" shared by every 3D view (Surface3D, Points3D, Tensors3D; mounted by Stage3D.svelte).
 *
 * - One look: the same lights, an angled default camera per kind, auto-fit to the content, orbit limits, no pan.
 * - Render on demand: nothing redraws unless something changed, and nothing draws while the view is offscreen.
 * - WebGL contexts are a scarce page-wide resource: each view takes one only while it may be seen; at most
 *   MAX_LIVE are alive at once (the least recently seen offscreen view gives its context back, and makes a new one
 *   when it scrolls back), and a destroyed view releases its context at once (forceContextLoss).
 * - Input never steals the page: the wheel scrolls the page until the view is clicked (or Ctrl/⌘ is held); on touch,
 *   one finger scrolls the page until the view is tapped, two fingers always turn and pinch-zoom.
 *   Keyboard: arrow keys turn, + / − zoom, 0 resets, Esc releases.
 * - Labels are HTML (labels.ts), projected every frame.
 */
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { reducedMotion } from '@lib/settings'
import { anglesFromDir, bounds, boundsChange, dirFromAngles, fitView, pickVictims, type Slot, type V3 } from './geom'
import { addLights } from './kit'
import { LabelLayer } from './labels'

export { mix } from './kit'

export type Palette = {
  bg: THREE.Color; fg: THREE.Color; dim: THREE.Color; line: THREE.Color
  accent: THREE.Color; ok: THREE.Color; warn: THREE.Color; card: THREE.Color
  /** semantic extras (see AUTHORING.md "Color tokens") */
  pos: THREE.Color; neg: THREE.Color; grad: THREE.Color
  cat: [THREE.Color, THREE.Color, THREE.Color, THREE.Color, THREE.Color]
}

/** Read the site's color tokens (they change with light/dark mode). */
export function readPalette(el: Element = document.documentElement): Palette {
  const cs = getComputedStyle(el)
  const c = (name: string, fallback: string) => new THREE.Color((cs.getPropertyValue(name) || fallback).trim())
  return {
    bg: c('--bg', '#ffffff'), fg: c('--fg', '#1c1c1a'), dim: c('--dim', '#77776f'), line: c('--line', '#dcdcd6'),
    accent: c('--accent', '#2563eb'), ok: c('--ok', '#15803d'), warn: c('--warn', '#c2410c'), card: c('--card', '#f7f7f5'),
    pos: c('--pos', '#0f7a84'), neg: c('--neg', '#b0279a'), grad: c('--grad', '#6d3fd4'),
    cat: [c('--cat-1', '#4f5bd5'), c('--cat-2', '#0a7566'), c('--cat-3', '#c0386b'), c('--cat-4', '#a16207'), c('--cat-5', '#5f6b7a')],
  }
}

// ---- WebGL availability and the page-wide context budget ------------------------------------

export { webglAvailable } from './webgl'

const coarsePointer = () => typeof matchMedia !== 'undefined' && matchMedia('(pointer: coarse)').matches
/** Live WebGL contexts allowed per page (browsers drop the oldest after ~16; phones have less memory). */
export const MAX_LIVE = 4
type Holder = Slot & { release: () => void }
const holders = new Map<number, Holder>()
let nextId = 1
let clock = 0
function maxLive() {
  try { const v = Number(localStorage.getItem('llmbh-max3d')); if (v >= 1) return v } catch { /* default */ } // debug: test eviction
  return coarsePointer() ? MAX_LIVE - 1 : MAX_LIVE
}
function claim(h: Holder) {
  const max = maxLive()
  for (const id of pickVictims([...holders.values()], h.id, max)) holders.get(id)?.release()
}
/** How many views hold a WebGL context right now (for checks). */
export const liveContexts = () => [...holders.values()].filter((h) => h.live).length

// ---- the stage -----------------------------------------------------------------------------

export type StageKind = 'surface' | 'points' | 'tensors'
/** Camera direction in degrees: azimuth turns from straight in front (+z) toward the right (+x); elevation lifts. */
export type ViewAngles = { azimuth?: number; elevation?: number; fov?: number }
export type StageState = {
  /** the view has the wheel / one-finger drag (after a click or tap inside) */
  active: boolean
  /** keyboard focus is on the view */
  focused: boolean
  /** touch-first device */
  coarse: boolean
  /** no live context right now: released to save memory or lost; tap to bring it back */
  paused: boolean
}
export type StageOpts = {
  kind?: StageKind
  view?: ViewAngles
  /** legacy: a camera position; only its direction from `target` is used (the distance is fitted) */
  camera?: V3
  target?: V3
  fov?: number
  onState?: (s: StageState) => void
}

const PRESET: Record<StageKind, Required<ViewAngles> & { minPolar: number; maxPolar: number }> = {
  surface: { azimuth: 34, elevation: 28, fov: 30, minPolar: 8, maxPolar: 86 },
  points: { azimuth: 34, elevation: 22, fov: 30, minPolar: 8, maxPolar: 120 },
  tensors: { azimuth: 20, elevation: 18, fov: 16, minPolar: 4, maxPolar: 176 },
}

export type Stage = {
  scene: THREE.Scene
  camera: THREE.PerspectiveCamera
  controls: OrbitControls
  /** null while the view holds no WebGL context (offscreen and released) */
  readonly renderer: THREE.WebGLRenderer | null
  /** the element that receives pointer events (for picking) */
  dom: HTMLElement
  /** true when the current click began on an already active view. The click that activates the view only
   *  activates it; picking handlers check this so that click never moves the learner's point. */
  pickReady: () => boolean
  labels: LabelLayer
  palette: () => Palette
  /** Ask for one redraw on the next animation frame. */
  render: () => void
  /** Draw right now (used once after building a scene, so the first frame never waits on rAF). */
  renderNow: () => void
  /** Called after a theme change so the view can recolor its objects. */
  onTheme: (fn: (p: Palette) => void) => void
  /**
   * Frame these points (world units; include label anchors). The camera moves only when the content's bounds changed
   * by more than 15% (so highlight changes never move it), keeps the reader's angles, and eases (unless reduced motion).
   */
  fit: (points: V3[], o?: { force?: boolean }) => void
  /** Back to the default angle, fitted to the content. */
  resetView: () => void
  setActive: (on: boolean) => void
  dispose: () => void
}

export function createStage(view: HTMLElement, opts: StageOpts = {}): Stage {
  const kind = opts.kind ?? 'surface'
  const preset = PRESET[kind]
  const coarse = coarsePointer()
  const motion = () => !reducedMotion()

  if (getComputedStyle(view).position === 'static') view.style.position = 'relative'
  // the element OrbitControls listens on: the wheel gate on `view` (capture) can stop events before they reach it
  const surface = document.createElement('div')
  surface.className = 'stage3d-surface'
  view.appendChild(surface)
  const labels = new LabelLayer(view)
  labels.requestFrame = () => render()
  const msg = document.createElement('button')
  msg.type = 'button'
  msg.className = 'stage3d-msg'
  msg.hidden = true
  msg.textContent = '3D view paused to save memory · tap to show it'
  view.appendChild(msg)

  const scene = new THREE.Scene()
  addLights(scene)
  const camera = new THREE.PerspectiveCamera(opts.fov ?? opts.view?.fov ?? preset.fov, 1, 0.05, 100)
  const target0 = new THREE.Vector3(...(opts.target ?? [0, 0, 0]))
  let homeDir: V3 = opts.camera
    ? [opts.camera[0] - target0.x, opts.camera[1] - target0.y, opts.camera[2] - target0.z]
    : dirFromAngles(opts.view?.azimuth ?? preset.azimuth, opts.view?.elevation ?? preset.elevation)
  if (opts.view && opts.camera) homeDir = dirFromAngles(opts.view.azimuth ?? anglesFromDir(homeDir).azimuth, opts.view.elevation ?? anglesFromDir(homeDir).elevation)
  camera.position.copy(target0).addScaledVector(new THREE.Vector3(...homeDir).normalize(), 5)

  const controls = new OrbitControls(camera, surface)
  controls.target.copy(target0)
  controls.enablePan = false
  controls.enableDamping = motion()
  controls.dampingFactor = 0.12
  controls.minPolarAngle = (preset.minPolar * Math.PI) / 180
  controls.maxPolarAngle = (preset.maxPolar * Math.PI) / 180
  controls.update()

  let pal = readPalette(view)
  const themeFns: ((p: Palette) => void)[] = []

  // ---- renderer: created while the view may be seen, released under the context budget ----
  let renderer: THREE.WebGLRenderer | null = null
  let W = 300, H = 300
  let visible = false
  let dirty = true
  let disposed = false
  const holder: Holder = { id: nextId++, live: false, visible: false, lastSeen: 0, pinned: false, release: () => release() }
  holders.set(holder.id, holder)

  const state: StageState = { active: false, focused: false, coarse, paused: false }
  const emit = () => opts.onState?.({ ...state })
  const setPaused = (p: boolean) => { if (state.paused !== p) { state.paused = p; msg.hidden = !p; emit() } }

  function acquire(): boolean {
    if (renderer) return true
    if (disposed) return false
    claim(holder)
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'low-power' })
    } catch {
      renderer = null
      setPaused(true)
      return false
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, coarse ? 1.5 : 2))
    renderer.setClearColor(pal.bg, 1)
    renderer.setSize(W, H, false)
    const cv = renderer.domElement
    cv.className = 'stage3d-canvas'
    cv.addEventListener('webglcontextlost', onLost)
    surface.appendChild(cv)
    holder.live = true
    setPaused(false)
    dirty = true
    return true
  }
  // the browser took the context away (too many on the page, GPU reset): drop it, make a new one when seen
  const onLost = (e: Event) => {
    e.preventDefault()
    release()
    if (visible) setTimeout(() => { if (visible && !disposed && acquire()) render() }, 50)
  }
  function release() {
    if (!renderer) return
    const r = renderer
    renderer = null
    holder.live = false
    r.domElement.removeEventListener('webglcontextlost', onLost)
    // detach every geometry/material from this renderer (their CPU data stays; a new renderer uploads them again)
    scene.traverse((o) => {
      const m = o as THREE.Mesh
      m.geometry?.dispose?.()
      const mat = m.material as THREE.Material | THREE.Material[] | undefined
      if (Array.isArray(mat)) mat.forEach((x) => x.dispose())
      else mat?.dispose?.()
    })
    r.dispose()
    r.forceContextLoss()
    r.domElement.remove()
    if (visible) setPaused(true)
  }
  msg.addEventListener('click', (e) => { e.stopPropagation(); if (acquire()) render() })

  // ---- drawing ----
  const draw = () => {
    if (disposed) return
    if (!visible || !renderer) { dirty = true; return }
    dirty = false
    renderer.render(scene, camera)
    labels.update(camera, W, H)
  }
  let queued = false
  let tween: null | { t0: number; ms: number; from: THREE.Spherical; to: THREE.Spherical; tf: THREE.Vector3; tt: THREE.Vector3 } = null
  const render = () => {
    if (queued || disposed) return
    queued = true
    requestAnimationFrame(() => {
      queued = false
      if (disposed) return
      let more = false
      if (tween) {
        const k = Math.min(1, (performance.now() - tween.t0) / tween.ms)
        const e = 1 - Math.pow(1 - k, 3)
        const s = new THREE.Spherical(
          tween.from.radius + (tween.to.radius - tween.from.radius) * e,
          tween.from.phi + (tween.to.phi - tween.from.phi) * e,
          tween.from.theta + (tween.to.theta - tween.from.theta) * e,
        )
        controls.target.lerpVectors(tween.tf, tween.tt, e)
        camera.position.setFromSpherical(s).add(controls.target)
        if (k >= 1) tween = null
        else more = true
      }
      // damping needs a few extra frames to settle after the pointer is released
      if (controls.update()) more = true
      draw()
      if (more) render()
    })
  }
  controls.addEventListener('change', render)
  controls.addEventListener('start', () => { tween = null })

  /** Move the camera to pos/target, eased unless the reader asked for less motion. */
  function moveTo(pos: THREE.Vector3, target: THREE.Vector3, ms = 250) {
    if (!motion() || ms <= 0) {
      tween = null
      controls.target.copy(target)
      camera.position.copy(pos)
      controls.update()
      render()
      return
    }
    const from = new THREE.Spherical().setFromVector3(camera.position.clone().sub(controls.target))
    const to = new THREE.Spherical().setFromVector3(pos.clone().sub(target))
    // turn the short way round
    while (to.theta - from.theta > Math.PI) to.theta -= 2 * Math.PI
    while (to.theta - from.theta < -Math.PI) to.theta += 2 * Math.PI
    tween = { t0: performance.now(), ms, from, to, tf: controls.target.clone(), tt: target.clone() }
    render()
  }

  // ---- fitting ----
  let fitPts: V3[] | null = null
  let fitBounds: [V3, V3] | null = null
  function placeFor(points: V3[], dir: V3) {
    const [lo, hi] = bounds(points)
    const tanV = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2))
    const tanH = tanV * camera.aspect
    const v = fitView(points, dir, tanH, tanV, 0.07)
    const D = Math.max(0.5, v.distance)
    const r = Math.hypot(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]) / 2 || 1
    controls.minDistance = D * 0.35
    controls.maxDistance = D * 2.6
    camera.near = Math.max(0.01, Math.min(D * 0.05, r * 0.05))
    camera.far = D * 2.6 + r * 4
    camera.updateProjectionMatrix()
    const t = new THREE.Vector3(...v.center)
    return { pos: t.clone().addScaledVector(new THREE.Vector3(...dir).normalize(), D), target: t }
  }
  const currentDir = (): V3 => {
    const d = camera.position.clone().sub(controls.target)
    return [d.x, d.y, d.z]
  }
  function fit(points: V3[], o: { force?: boolean } = {}) {
    if (!points.length) return
    const b = bounds(points)
    const first = !fitBounds
    if (!first && !o.force && boundsChange(fitBounds!, b) <= 0.15) { fitPts = points; return }
    fitPts = points
    fitBounds = b
    const p = placeFor(points, first ? homeDir : currentDir())
    moveTo(p.pos, p.target, first ? 0 : 250)
  }
  function resetView() {
    if (!fitPts) return
    const p = placeFor(fitPts, homeDir)
    moveTo(p.pos, p.target, 300)
  }

  // ---- size, visibility, theme ----
  const resize = () => {
    const w = view.clientWidth || 300, h = view.clientHeight || 300
    const aspectChanged = Math.abs(w / h - W / H) > 0.02
    W = w; H = h
    renderer?.setSize(W, H, false)
    camera.aspect = W / H
    camera.updateProjectionMatrix()
    labels.invalidate()
    // keep the content framed when the box changes shape (phone rotation, sidebar)
    if (aspectChanged && fitPts) { const p = placeFor(fitPts, currentDir()); moveTo(p.pos, p.target, 0) }
    render()
  }
  const ro = new ResizeObserver(resize)
  ro.observe(view)
  resize()

  const io = new IntersectionObserver((entries) => {
    for (const en of entries) {
      visible = en.isIntersecting
      holder.visible = visible
      holder.lastSeen = ++clock
      // coming into view (or near it): take a context if this view gave its own back, then draw what changed
      if (visible && (renderer || acquire()) && dirty) render()
    }
  }, { rootMargin: '300px 0px' })
  io.observe(view)

  // the text-size setting changes rem sizes: measure labels again
  const scaleObs = new MutationObserver(() => { labels.invalidate(); render() })
  scaleObs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-scale', 'data-motion'] })

  const mq = window.matchMedia('(prefers-color-scheme: dark)')
  const THEME_EVENT = 'llmbh:theme' // fired by the settings menu (lib/settings.ts)
  const retheme = () => {
    pal = readPalette(view)
    renderer?.setClearColor(pal.bg, 1)
    themeFns.forEach((f) => f(pal))
    render()
  }
  mq.addEventListener('change', retheme)
  window.addEventListener(THEME_EVENT, retheme)

  // ---- input gate ----------------------------------------------------------------------------
  const ONE_FINGER_OFF = null as unknown as THREE.TOUCH
  const setActive = (on: boolean) => {
    state.active = on
    holder.pinned = on
    // touch: one finger turns only when active; two fingers always turn and pinch-zoom
    controls.touches.ONE = on ? THREE.TOUCH.ROTATE : ONE_FINGER_OFF
    controls.touches.TWO = THREE.TOUCH.DOLLY_ROTATE
    surface.style.touchAction = on ? 'none' : 'pan-y'
    view.classList.toggle('stage3d-active', on)
    emit()
  }
  setActive(false)

  // the wheel scrolls the page unless the view is active or Ctrl/⌘ is held (trackpad pinch sends Ctrl + wheel):
  // stopped here, in the capture phase, before OrbitControls (on `surface`) sees it
  const onWheel = (e: WheelEvent) => { if (!state.active && !e.ctrlKey && !e.metaKey) e.stopPropagation() }
  view.addEventListener('wheel', onWheel, { capture: true, passive: true })
  // two fingers: keep the page still while they turn/zoom the view (one finger keeps scrolling the page)
  const onTouchMove = (e: TouchEvent) => { if (e.touches.length >= 2 && e.cancelable) e.preventDefault() }
  surface.addEventListener('touchmove', onTouchMove, { passive: false })

  let downAt: { x: number; y: number; t: number } | null = null
  let activeAtDown = false
  const onDown = (e: PointerEvent) => { downAt = { x: e.clientX, y: e.clientY, t: performance.now() }; activeAtDown = state.active }
  const onUp = (e: PointerEvent) => {
    // a click / tap (not a drag) activates the view
    if (downAt && !state.active && Math.hypot(e.clientX - downAt.x, e.clientY - downAt.y) < 6 && performance.now() - downAt.t < 600) setActive(true)
    downAt = null
  }
  surface.addEventListener('pointerdown', onDown, { capture: true })
  surface.addEventListener('pointerup', onUp, { capture: true })
  const onLeave = (e: PointerEvent) => { if (e.pointerType === 'mouse' && state.active) setActive(false) }
  view.addEventListener('pointerleave', onLeave)
  const onDocDown = (e: PointerEvent) => { if (state.active && !view.contains(e.target as Node)) setActive(false) }
  document.addEventListener('pointerdown', onDocDown)

  // keyboard (when the view has focus): arrows turn, + / − zoom, 0 / Home reset, Esc releases
  const orbitBy = (dAz: number, dEl: number, zoom = 1) => {
    const s = new THREE.Spherical().setFromVector3(camera.position.clone().sub(controls.target))
    s.theta += dAz
    s.phi = Math.min(controls.maxPolarAngle, Math.max(controls.minPolarAngle, s.phi - dEl))
    s.radius = Math.min(controls.maxDistance, Math.max(controls.minDistance, s.radius * zoom))
    moveTo(new THREE.Vector3().setFromSpherical(s).add(controls.target), controls.target.clone(), 160)
  }
  const onKey = (e: KeyboardEvent) => {
    if (e.altKey || e.ctrlKey || e.metaKey) return
    const step = (e.shiftKey ? 30 : 15) * (Math.PI / 180)
    const k = e.key
    if (k === 'ArrowLeft') orbitBy(-step, 0)
    else if (k === 'ArrowRight') orbitBy(step, 0)
    else if (k === 'ArrowUp') orbitBy(0, step * 0.66)
    else if (k === 'ArrowDown') orbitBy(0, -step * 0.66)
    else if (k === '+' || k === '=') orbitBy(0, 0, 0.85)
    else if (k === '-' || k === '_') orbitBy(0, 0, 1 / 0.85)
    else if (k === '0' || k === 'Home') resetView()
    else if (k === 'Escape' && state.active) setActive(false)
    else return
    // handled here: keep the page's own shortcuts (← / → change lesson) from also firing
    e.preventDefault()
    e.stopPropagation()
  }
  view.addEventListener('keydown', onKey)
  const onDocKey = (e: KeyboardEvent) => { if (e.key === 'Escape' && state.active && !view.contains(document.activeElement)) setActive(false) }
  document.addEventListener('keydown', onDocKey)
  const onFocus = () => { state.focused = view.matches(':focus-visible'); emit() }
  const onBlur = () => { state.focused = false; emit() }
  view.addEventListener('focus', onFocus)
  view.addEventListener('blur', onBlur)

  const stage: Stage = {
    scene, camera, controls, labels, dom: surface, pickReady: () => activeAtDown,
    get renderer() { return renderer },
    palette: () => pal,
    render,
    renderNow: draw,
    onTheme: (fn) => themeFns.push(fn),
    fit,
    resetView,
    setActive,
    dispose: () => {
      if (disposed) return
      release()
      disposed = true
      holders.delete(holder.id)
      io.disconnect()
      ro.disconnect()
      scaleObs.disconnect()
      view.removeEventListener('wheel', onWheel, { capture: true })
      view.removeEventListener('pointerleave', onLeave)
      view.removeEventListener('keydown', onKey)
      view.removeEventListener('focus', onFocus)
      view.removeEventListener('blur', onBlur)
      surface.removeEventListener('touchmove', onTouchMove)
      surface.removeEventListener('pointerdown', onDown, { capture: true })
      surface.removeEventListener('pointerup', onUp, { capture: true })
      document.removeEventListener('pointerdown', onDocDown)
      document.removeEventListener('keydown', onDocKey)
      mq.removeEventListener('change', retheme)
      window.removeEventListener(THEME_EVENT, retheme)
      controls.dispose()
      // free everything still in the scene (geometries, materials, textures)
      scene.traverse((o) => {
        const m = o as THREE.Mesh
        m.geometry?.dispose?.()
        const mat = m.material as THREE.Material | THREE.Material[] | undefined
        for (const x of Array.isArray(mat) ? mat : mat ? [mat] : []) {
          for (const v of Object.values(x)) if (v instanceof THREE.Texture) v.dispose()
          x.dispose()
        }
      })
      scene.clear()
      labels.dispose()
      surface.remove()
      msg.remove()
      view.classList.remove('stage3d-active')
    },
  }
  if (import.meta.env.DEV) {
    const w = window as unknown as { __llmbh3d?: { stages: Set<Stage>; live: () => number } }
    w.__llmbh3d ??= { stages: new Set(), live: liveContexts }
    w.__llmbh3d.stages.add(stage)
    const d = stage.dispose
    stage.dispose = () => { w.__llmbh3d?.stages.delete(stage); d() }
  }
  return stage
}
