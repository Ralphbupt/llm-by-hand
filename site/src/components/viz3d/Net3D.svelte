<script lang="ts">
  /**
   * A network drawn in 3D from a `Net3DSpec` (lib/three/net.ts): layers of neurons (discs) or tensors (cells),
   * dense links as weight-colored lines (pos/neg, width by |w|, the largest ones sampled), conv links as a
   * receptive-field funnel, shared weights in one group color, a residual rail, attention arcs.
   * `step` picks what the picture shows: forward steps light up in `--accent` with values, backward steps in `--grad`
   * (the halo around a neuron grows with |∂L/∂a|, the lines switch to |∂L/∂W|). Colors come from `looksAt`, the same
   * function Net2D uses, so the two views always agree.
   *
   * Draw calls: discs 1, their rings 1, cells 1, rails 1, dense lines 3 (one per width), other lines 1, flow dots 1.
   * Changing the step only recolors. Labs wrap it with NetLab (layer list, panel, step buttons, the Flat view).
   */
  import type { Snippet } from 'svelte'
  import * as THREE from 'three'
  import { LineSegments2 } from 'three/examples/jsm/lines/LineSegments2.js'
  import { LineSegmentsGeometry } from 'three/examples/jsm/lines/LineSegmentsGeometry.js'
  import { LineMaterial } from 'three/examples/jsm/lines/LineMaterial.js'
  import Stage3D from './Stage3D.svelte'
  import type { Palette, Stage } from '@lib/three/stage'
  import { cellGeometry, cellMaterial, cellMesh, isDarkPalette, mix, toneColor, type Tone } from '@lib/three/kit'
  import { reducedMotion } from '@lib/settings'
  import {
    BUCKET_PX, flat, fmtNum, fmtShape, groupTones, itemsOf, layoutNet, looksAt, railY, segmentsOf, stateAt,
    type Item, type LaidNode, type Look, type Net3DSpec, type NetLayoutResult, type Rail, type Seg, type V3,
  } from '@lib/three/net'

  type Props = {
    spec: Net3DSpec
    /** −1 = before the first step */
    step?: number
    selected?: string | null
    onselect?: (id: string | null) => void
    ariaLabel?: string
    height?: string
    fallback?: Snippet
    /** write each neuron's value / gradient next to it (default: when the net has at most 24 neurons) */
    numbers?: boolean
  }
  let { spec, step = -1, selected = null, onselect, ariaLabel = 'A network in 3D', height = 'min(70vh, 26rem)', fallback, numbers }: Props = $props()

  let stage: Stage | null = null
  const root = new THREE.Group() // turned a quarter on phones (data flows down)
  const g = new THREE.Group() // layout coordinates, centered
  root.add(g)

  const sphere = new THREE.SphereGeometry(1, 24, 16)
  const cellGeo = cellGeometry(1)
  const discMat = new THREE.MeshBasicMaterial({ color: 0xffffff })
  const ringMat = new THREE.MeshBasicMaterial({ color: 0xffffff, side: THREE.BackSide })
  const cellMat = cellMaterial({ edge: 0.3, edgeColor: new THREE.Color() })
  const railMat = new THREE.MeshBasicMaterial({ color: 0xffffff })
  const box = new THREE.BoxGeometry(1, 1, 1)
  let discs: THREE.InstancedMesh | null = null
  let rings: THREE.InstancedMesh | null = null
  let cells: THREE.InstancedMesh | null = null
  let rails: THREE.InstancedMesh | null = null
  const lineObjs: LineSegments2[] = [] // 0..2 dense width buckets, 3 = all other lines

  // flow dots: one Points draw call moved in the vertex shader by uT (JS only advances one number per frame)
  const flowGeo = new THREE.BufferGeometry()
  const flowMat = new THREE.ShaderMaterial({
    uniforms: { uT: { value: 0 }, uSize: { value: 7 }, uColor: { value: new THREE.Color() } },
    vertexShader: `attribute vec3 aTo; attribute float aDelay; uniform float uT; uniform float uSize; varying float vOn;
      void main() { float t = clamp((uT - aDelay) / 0.55, 0.0, 1.0); vOn = (t > 0.0 && t < 1.0) ? 1.0 : 0.0;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(mix(position, aTo, t), 1.0); gl_PointSize = uSize; }`,
    fragmentShader: `uniform vec3 uColor; varying float vOn;
      void main() { vec2 c = gl_PointCoord - 0.5; if (vOn < 0.5 || dot(c, c) > 0.25) discard; gl_FragColor = vec4(uColor, 1.0);
        #include <colorspace_fragment>
      }`,
    depthTest: false,
  })
  const flow = new THREE.Points(flowGeo, flowMat)
  flow.frustumCulled = false
  flow.renderOrder = 5
  flow.visible = false

  // ---- structure (rebuilt only when the spec's structure changes) ----
  let laid: NetLayoutResult | null = null
  let items: { discs: Item[]; cells: Item[] } = { discs: [], cells: [] }
  let segs: Seg[] = []
  let railRecs: Rail[] = []
  let vertical = false
  let fitPts: V3[] = []
  let lastW = 0
  const neuronCount = $derived(spec.nodes.filter((n) => n.kind === 'neurons').reduce((a, n) => a + Math.min(24, n.shape.reduce((x, y) => x * y, 1)), 0))
  const showNumbers = $derived(numbers ?? neuronCount <= 24)

  const structKey = (s: Net3DSpec) => JSON.stringify([s.layout, s.nodes, s.edges.map((e) => [e.id, e.from, e.to, e.kind, e.window, e.shared, e.weights])])
  const maxEdges = () => Math.min(spec.caps?.maxEdgesPerLink ?? 512, matchMedia('(pointer: coarse)').matches ? 128 : 512)

  function build() {
    if (!stage) return
    vertical = stage.dom.clientWidth < 520
    const L = (laid = layoutNet(spec, { vertical }))
    root.rotation.z = vertical ? -Math.PI / 2 : 0
    g.position.set(-(L.lo[0] + L.hi[0]) / 2, -(L.lo[1] + L.hi[1]) / 2, -(L.lo[2] + L.hi[2]) / 2)

    for (const m of [discs, rings, cells, rails]) if (m) { m.dispose(); m.removeFromParent() }
    items = itemsOf(L)
    ;({ segs, rails: railRecs } = segmentsOf(spec, L, maxEdges()))
    const nd = items.discs.length, nc = items.cells.length
    discs = new THREE.InstancedMesh(sphere, discMat, Math.max(1, nd))
    rings = new THREE.InstancedMesh(sphere, ringMat, Math.max(1, nd))
    cells = cellMesh(cellGeo, cellMat, Math.max(1, nc))
    cells.count = nc
    for (const m of [discs, rings]) { m.frustumCulled = false; m.userData.sharedGeometry = true; m.userData.sharedMaterial = true; m.count = nd }
    const M = new THREE.Matrix4()
    // an add node (“+”) on the residual path is drawn a third larger, so the place where x comes back in is easy to find
    items.discs.forEach((d, n) => { const r = d.ln.size * (d.ln.node.kind === 'op' ? 1.3 : 1); discs!.setMatrixAt(n, M.makeScale(r, r, r).setPosition(...d.ln.items[d.k])) })
    items.cells.forEach((d, n) => {
      // a block of many cells is drawn solid (no gaps between cells: gaps a pixel wide beat into moiré); its cell
      // lines come from the shader, which fades them out when cells get too small to show them
      const dense = !!d.ln.dims && Math.max(d.ln.dims[1], d.ln.dims[2]) >= 10
      const c = d.ln.size * (dense ? 1 : 0.88)
      const s = d.ln.kind === 'box' ? [0.6, 0.84, 0.6] : [c, c, c]
      cells!.setMatrixAt(n, M.makeScale(s[0], s[1], s[2]).setPosition(...d.ln.items[d.k]))
    })
    // the residual rail: a flat band under the blocks, with thin posts up into both ends
    const ry = railY(L)
    rails = new THREE.InstancedMesh(box, railMat, Math.max(1, railRecs.length * 3))
    rails.frustumCulled = false
    rails.userData.sharedGeometry = true
    rails.userData.sharedMaterial = true
    let nr = 0
    for (const r of railRecs) {
      const x0 = r.a[0], x1 = r.b[0]
      rails.setMatrixAt(nr++, M.makeScale(Math.abs(x1 - x0), 0.03, 0.22).setPosition((x0 + x1) / 2, ry, 0))
      for (const [x, n] of [[x0, L.byId.get(r.e.from)!], [x1, L.byId.get(r.e.to)!]] as [number, LaidNode][]) {
        const y1 = n.center[1] - n.half[1]
        rails.setMatrixAt(nr++, M.makeScale(0.03, Math.max(0.01, y1 - ry), 0.03).setPosition(x, (ry + y1) / 2, 0))
      }
    }
    rails.count = nr
    g.add(discs, rings, cells, rails)
    if (!flow.parent) g.add(flow)

    // fit every node plus room for its labels
    // the same room on both sides, so the net sits in the middle of the canvas (the numbers on the right of the
    // last layer only need about half a unit; more would push the whole net to the left)
    const pts: V3[] = []
    // values ("0.0896 · ∂ 1" once gradients come back) need more room beside the last layer
    const side = showNumbers && !vertical ? (spec.steps?.some((x) => x.grads) ? 0.8 : 0.45) : 0.25
    for (const ln of L.nodes) {
      const [x, y, z] = ln.center, [hx, hy, hz] = ln.half
      // a row (a sentence) has its name on its left and a word under each disc: leave room for both
      const row = ln.node.along === 'x' && ln.kind === 'disc' && ln.node.kind === 'neurons'
      const left = row && !vertical ? side + 0.07 * ln.node.label.length : ln.column ? side + 0.09 * Math.max(ln.node.label.length, 6) : side
      const below = row && ln.node.names ? ln.size * 1.4 + 0.25 : 0.25
      // all eight corners: under an angled camera one diagonal alone would frame the net off center
      for (const px of [x - hx - left, x + hx + side]) for (const py of [y - hy - below, y + hy + (ln.node.kind === 'tensor' ? 0.8 : 0.3)]) for (const pz of [z - hz, z + hz]) pts.push([px, py, pz])
    }
    if (railRecs.length) pts.push([L.lo[0], ry - 0.5, 0]) // the rail and the labels under it
    root.updateMatrixWorld(true)
    fitPts = pts.map((p) => g.localToWorld(new THREE.Vector3(...p)).toArray() as V3)
    stage.fit(fitPts, { force: true })
  }

  /** break a label into lines of about `n` characters, at spaces */
  const wrap = (t: string, n: number) => t.split(' ').reduce((ls: string[], w) => {
    const last = ls[ls.length - 1]
    if (last !== undefined && (last + ' ' + w).length <= n) ls[ls.length - 1] = last + ' ' + w
    else ls.push(w)
    return ls
  }, []).join('\n')

  // colors mix in linear light, where a little dark text color on a light card hardly shows: in the light theme the
  // plain gray of a block's cells is mixed stronger (a curve that lifts the pale grays most and keeps their order), and a lit block without numbers takes nearly the full accent (as in Tensors3D)
  const colorOf = (pal: Palette, l: Look, cell = false) => {
    const light = cell && !isDarkPalette(pal)
    const amt = light && l.base === 'card' && l.tone === 'fg' && l.amt > 0 ? 1 - (1 - Math.min(1, l.amt * 2.4)) ** 3 : l.amt
    const c = mix(pal[l.base], toneColor(pal, l.tone as Tone), amt)
    if (!l.over) return c
    return mix(c, toneColor(pal, l.over.tone as Tone), light && l.over.amt >= 0.6 ? 0.85 : l.over.amt)
  }

  function paint() {
    if (!stage || !laid || !discs || !rings || !cells || !rails) return
    const pal = stage.palette()
    const lk = looksAt(spec, items, segs, railRecs, step, selected)
    const st = lk.state
    const back = lk.back
    const M = new THREE.Matrix4()
    cellMat.userData.uEdgeColor.value.copy(pal.fg)
    // block edges: stronger on a light background, where pale blocks would otherwise melt into the page
    cellMat.userData.uEdge.value = isDarkPalette(pal) ? 0.3 : 0.7
    items.discs.forEach((d, n) => {
      discs!.setColorAt(n, colorOf(pal, lk.discs[n]))
      const r = d.ln.size * (d.ln.node.kind === 'op' ? 1.3 : 1) * lk.rings[n].r
      rings!.setMatrixAt(n, M.makeScale(r, r, r).setPosition(...d.ln.items[d.k]))
      rings!.setColorAt(n, colorOf(pal, lk.rings[n]))
    })
    items.cells.forEach((_, n) => cells!.setColorAt(n, colorOf(pal, lk.cells[n], true)))
    for (const m of [discs, rings, cells]) { m.instanceMatrix.needsUpdate = true; if (m.instanceColor) m.instanceColor.needsUpdate = true }
    // the rail at rest: on a light page a 30% mix in linear light is barely visible (about 1.3:1), so it takes more
    railMat.color.copy(lk.railOn ? pal.accent : mix(pal.bg, pal.fg, isDarkPalette(pal) ? 0.3 : 0.62))

    // lines: dense ones grouped by width (one draw call per width), all others in one
    const pos: number[][] = [[], [], [], []], cols: number[][] = [[], [], [], []]
    segs.forEach((s, n) => {
      const l = lk.lines[n]
      if (l.hide) return
      const c = colorOf(pal, l)
      pos[l.bucket].push(...s.a, ...s.b)
      cols[l.bucket].push(c.r, c.g, c.b, c.r, c.g, c.b)
    })
    lineObjs.forEach((o, k) => {
      o.geometry.dispose()
      const geo = new LineSegmentsGeometry()
      if (pos[k].length) { geo.setPositions(pos[k]); geo.setColors(cols[k]) }
      o.geometry = geo
      o.visible = pos[k].length > 0
    })

    // labels: layer names, link names, and (for small nets) each neuron's value and gradient
    const Lb = stage.labels
    Lb.begin('n')
    for (const ln of laid.nodes) {
      const n = ln.node
      // name on the first line, shape on the second: narrow labels collide less along a row of blocks
      // a long column of names on a phone (it lies flat and far away there): one summary line instead of crowded names
      const squeeze = vertical && n.along !== 'x' && (n.names?.length ?? 0) > 6
      const txt = n.kind === 'tensor' ? `${n.label}\n${fmtShape(n.shape)}` : squeeze ? `${n.label}\n${n.names![0]} … ${n.names!.at(-1)}` : n.label
      const tone: Tone | undefined = selected === n.id || st.active.has(n.id) ? (back ? 'grad' : 'accent') : undefined
      // a row of discs (a sentence): its name sits outside the row, before its first disc, never on top of a disc
      const rowStart = n.kind === 'neurons' && n.along === 'x' && ln.items.length > 1 ? ln.items[0] : null
      if (rowStart) Lb.set('n', n.id, txt, [rowStart[0] - ln.size * 2, rowStart[1], rowStart[2]], {
        role: 'name', anchor: vertical ? 'above' : 'left', tone, parent: g,
      })
      // a block in a folded column (lines run in above and below it): its name on its left
      else if (ln.column && n.kind !== 'op') Lb.set('n', n.id, txt, [ln.center[0] - ln.half[0], ln.center[1], ln.center[2] + ln.half[2]], {
        role: 'name', anchor: 'left', tone, parent: g,
      })
      // a block's name sits on its back top edge, which is the highest point of the block under the tilted camera:
      // from the middle of the top it would sit on the front cells
      else Lb.set('n', n.id, txt, [ln.center[0], ln.center[1] + ln.half[1], ln.center[2] - (n.kind !== 'op' && !vertical ? ln.half[2] : 0)], {
        role: n.kind === 'op' ? 'op' : 'name', anchor: n.kind === 'op' ? 'center' : vertical ? 'right' : 'above', tone, parent: g,
      })
      // one name per disc (tokens, words, time steps): above a row, left of a column
      if (!squeeze) n.names?.forEach((t, k) => {
        const p = ln.items[k]
        if (!p) return
        const row = n.along === 'x'
        // a column's names go on its right (in one tidy line), unless the values already sit there
        // (on phones the column lies flat at the bottom: names under it, values one line further down)
        const side = showNumbers && !vertical ? -1 : 1
        Lb.set('n', `${n.id}:n${k}`, t, row ? [p[0], p[1] - ln.size * 1.4, p[2]] : [p[0] + side * ln.size * 1.5, p[1], p[2]], {
          role: 'axis', tone: 'fg', anchor: row ? (vertical ? 'left' : 'below') : vertical ? (side > 0 ? 'below' : 'above') : side > 0 ? 'right' : 'left', priority: 32, parent: g,
        })
      })
      if (showNumbers && n.kind === 'neurons') {
        const vals = flat(st.values[n.id]), grs = back ? flat(st.grads[n.id]) : []
        ln.items.forEach((p, k) => {
          const parts: string[] = []
          if (vals[k] !== undefined) parts.push(fmtNum(vals[k]))
          if (grs[k] !== undefined) parts.push(`∂ ${fmtNum(grs[k])}`)
          // an unrolled chain (rnn) has a line leaving each disc to the right: its value goes below that line,
          // in the corner between it and the input line coming up
          const corner = spec.layout === 'unrolled' && !vertical
          if (parts.length)
            Lb.set('n', `${n.id}:v${k}`, parts.join(' · '), corner ? [p[0] + ln.size * 0.9, p[1] - ln.size * 1.3, p[2]] : [p[0] + ln.size * (vertical && n.names ? 3.4 : 1.6), p[1], p[2]], {
              // on a backing plate: a value often sits on a line leaving its disc
              role: 'callout', tone: grs[k] !== undefined ? 'grad' : 'fg', anchor: vertical ? 'below' : 'right', priority: 30, parent: g,
            })
        })
      }
    }
    const tones = groupTones(spec)
    for (const e of spec.edges) {
      if (!e.label) continue
      const A = laid.byId.get(e.from), B = laid.byId.get(e.to)
      if (!A || !B) continue
      const same = Math.abs(A.center[0] - B.center[0]) < 1e-6
      const tone = (st.active.has(e.id) ? (back ? 'grad' : 'accent') : e.shared ? tones[e.shared] : 'dim') as Tone
      // a rail's name sits off the band, under its front edge, on a backing plate
      // between blocks the block names sit on top, so a link's name goes under the link (as in the flat view);
      // upright on a phone it goes beside the link
      const blocky = A.kind !== 'disc' || B.kind !== 'disc'
      const side = !same && e.kind !== 'residual' && (vertical || blocky)
      const mid: V3 = e.kind === 'residual' ? [(A.center[0] + B.center[0]) / 2, railY(laid), 0.14]
        : same ? [A.center[0], (A.center[1] + B.center[1]) / 2, 0]
        : vertical ? [(A.center[0] + B.center[0]) / 2, (A.center[1] + B.center[1]) / 2, 0]
        : blocky ? [(A.center[0] + B.center[0]) / 2, Math.min(A.center[1] - A.half[1], B.center[1] - B.half[1]), 0]
        : [(A.center[0] + B.center[0]) / 2, Math.max(A.center[1] + A.half[1], B.center[1] + B.half[1]), 0]
      // upright on a phone, the rail runs down the left of the column: its name goes beside it, in short lines
      const rail = e.kind === 'residual'
      Lb.set('n', `e:${e.id}`, rail && vertical ? wrap(e.label, 11) : e.label, mid, {
        role: rail ? 'callout' : 'axis', tone,
        anchor: rail ? (vertical ? 'left' : 'below') : same ? 'right' : side ? (vertical ? 'right' : 'below') : 'above',
        offset: rail && !vertical ? [0, 4] : side && vertical ? [6, 0] : undefined, parent: g,
      })
    }
    Lb.end('n')
    stage.render()
  }

  // ---- flow dots: run once per step change (nothing loops), skipped with reduced motion ----
  let raf = 0
  let lastStep = -1
  function startFlow() {
    cancelAnimationFrame(raf)
    flow.visible = false
    if (!stage || !laid || reducedMotion()) return
    const st = stateAt(spec, step)
    if (!st.step) return
    const back = st.dir === 'backward'
    const from: number[] = [], to: number[] = [], delay: number[] = []
    const add = (a: V3, b: V3, d: number) => { from.push(...(back ? b : a)); to.push(...(back ? a : b)); delay.push(d) }
    let n = 0
    for (const s of segs) {
      if (!st.active.has(s.e.id) || n > 200) continue
      if (s.arc && (Math.abs(s.w) < 0.2 || (st.step.focus?.[s.e.id] !== undefined && st.step.focus[s.e.id] !== s.i))) continue
      add(s.a, s.b, s.arc ? 0.1 : Math.random() * 0.35)
      n++
    }
    const ry = railY(laid)
    for (const r of railRecs) if (st.active.has(r.e.id)) for (let k = 0; k < 3; k++) add([r.a[0], ry, 0], [r.b[0], ry, 0], k * 0.12)
    if (!from.length) return
    flowGeo.setAttribute('position', new THREE.Float32BufferAttribute(from, 3))
    flowGeo.setAttribute('aTo', new THREE.Float32BufferAttribute(to, 3))
    flowGeo.setAttribute('aDelay', new THREE.Float32BufferAttribute(delay, 1))
    const pal = stage.palette()
    flowMat.uniforms.uColor.value.copy(back ? pal.grad : pal.accent)
    flowMat.uniforms.uSize.value = 7 * (stage.renderer?.getPixelRatio() ?? 1)
    flow.visible = true
    const t0 = performance.now(), ms = 1100
    const tick = (now: number) => {
      const t = (now - t0) / ms
      flowMat.uniforms.uT.value = t
      if (t >= 1) flow.visible = false
      stage?.render()
      if (t < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
  }

  function setup(s: Stage) {
    stage = s
    s.scene.add(root)
    for (let k = 0; k < 4; k++) {
      const o = new LineSegments2(new LineSegmentsGeometry(), new LineMaterial({ color: 0xffffff, linewidth: k < 3 ? BUCKET_PX[k] : 1.5, worldUnits: false, vertexColors: true }))
      o.frustumCulled = false
      lineObjs.push(o)
      g.add(o)
    }
    build()
    paint()
    lastKey = structKey(spec)
    lastStep = step
    s.onTheme(() => paint())

    // a click or tap (not a drag) on a disc or cell selects its layer
    const el = s.dom
    const ray = new THREE.Raycaster()
    let downAt: { x: number; y: number } | null = null
    const onDown = (e: PointerEvent) => (downAt = { x: e.clientX, y: e.clientY })
    const onUp = (e: PointerEvent) => {
      if (!downAt || !stage || !stage.pickReady() || Math.hypot(e.clientX - downAt.x, e.clientY - downAt.y) > 5) return
      const r = el.getBoundingClientRect()
      ray.setFromCamera(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1), stage.camera)
      const h = ray.intersectObjects([discs, cells].filter(Boolean) as THREE.Object3D[], false)[0]
      if (!h || h.instanceId === undefined) return
      const rec = h.object === discs ? items.discs[h.instanceId] : items.cells[h.instanceId]
      if (rec) onselect?.(selected === rec.ln.node.id ? null : rec.ln.node.id)
    }
    el.addEventListener('pointerdown', onDown)
    el.addEventListener('pointerup', onUp)
    // phones: data flows down; switch when the width crosses the line
    let wasVertical = vertical
    const ro = new ResizeObserver(() => {
      if (!stage) return
      if ((stage.dom.clientWidth < 520) !== wasVertical) {
        wasVertical = !wasVertical
        build()
        paint()
      } else if (Math.abs(stage.dom.clientWidth - lastW) > 2 && fitPts.length) stage.fit(fitPts, { force: true }) // the first fit ran before the view had its size
      lastW = stage.dom.clientWidth
    })
    ro.observe(el)
    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
      el.removeEventListener('pointerdown', onDown)
      el.removeEventListener('pointerup', onUp)
      for (const m of [discs, rings, cells, rails]) m?.dispose()
      for (const o of lineObjs) { o.geometry.dispose(); o.material.dispose() }
      lineObjs.length = 0
      for (const x of [sphere, cellGeo, box, flowGeo]) x.dispose()
      for (const m of [discMat, ringMat, cellMat, railMat, flowMat]) m.dispose()
      root.removeFromParent()
      g.clear()
      stage = null
      laid = null
    }
  }

  let lastKey = ''
  $effect(() => {
    const k = structKey(spec)
    void step
    void selected
    if (!stage) return
    if (k !== lastKey) { lastKey = k; build() }
    paint()
    if (step !== lastStep) { lastStep = step; startFlow() }
  })
</script>

<Stage3D opts={{ kind: 'points', view: { azimuth: spec.view?.azimuth ?? 20, elevation: spec.view?.elevation ?? 14 } }} {ariaLabel} {height} {fallback} onready={setup} />
