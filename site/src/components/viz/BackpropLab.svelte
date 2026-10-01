<script lang="ts">
  /**
   * Backprop lab: z = w·x + b → a = sigmoid(z) → L = (a − y)².
   * Forward values are always shown. "Step back" walks the gradient from L toward w and b,
   * one multiplication at a time ("Undo step" walks it forward again). The nudge check compares the result with
   * (L(w + ε) − L(w − ε)) / 2ε for any ε you choose.
   * Wide screens: the chain runs left → right. Narrow: top → bottom (w, x, b → z → a → L), so nothing is cut off.
   */
  import { onMount } from 'svelte'
  import { has, subscribe } from '@lib/progress'
  import LabFrame from './LabFrame.svelte'

  // A gradient that a question on the page asks for stays "?" until that question is solved.
  type Key = 'dLda' | 'dLdz' | 'dLdw'
  let { hide = {} }: { hide?: Partial<Record<Key, string>> } = $props()
  let solved = $state<Record<string, boolean>>({})
  onMount(() => {
    const sync = () => {
      const next: Record<string, boolean> = {}
      for (const id of Object.values(hide)) if (id) next[id] = has(id)
      solved = next
    }
    sync()
    return subscribe(sync)
  })
  const locked = (k: Key) => !!hide[k] && !solved[hide[k]!]

  let x = $state(2)
  let w = $state(0.5)
  let b = $state(-1)
  let y = $state(1)
  let stage = $state(0)
  let logEps = $state(-5)

  const sig = (z: number) => 1 / (1 + Math.exp(-z))
  const lossAt = (ww: number, bb: number) => (sig(ww * x + bb) - y) ** 2

  const fw = $derived.by(() => {
    const z = w * x + b
    const a = sig(z)
    const L = (a - y) ** 2
    const dLda = 2 * (a - y)
    const dadz = a * (1 - a)
    const dLdz = dLda * dadz
    return { z, a, L, dLda, dadz, dLdz, dLdw: dLdz * x, dLdb: dLdz, dLdx: dLdz * w }
  })

  const eps = $derived(10 ** logEps)
  const numeric = $derived((lossAt(w + eps, b) - lossAt(w - eps, b)) / (2 * eps))
  const gap = $derived(Math.abs(numeric - fw.dLdw))

  const f = (v: number) => (Number.isFinite(v) ? String(Number(v.toFixed(4))) : '—')
  const e = (v: number) => (v === 0 ? '0' : v.toExponential(2))
  /** format a gradient, or "?" while its question is unsolved */
  const gf = (k: Key, v: number) => (locked(k) ? '?' : f(v))

  function edit(set: (v: number) => void, ev: Event) {
    const v = parseFloat((ev.currentTarget as HTMLInputElement).value)
    if (Number.isFinite(v)) {
      set(v)
      stage = 0
    }
  }
  function resetAll() {
    x = 2; w = 0.5; b = -1; y = 1
    stage = 0
    logEps = -5
  }
  const changed = $derived(x !== 2 || w !== 0.5 || b !== -1 || y !== 1 || stage !== 0 || logEps !== -5)
  const STEPS = 4
  const show = (n: number) => stage >= n

  // gradient shown in each box: null = not reached yet, NaN = "?" (a question, or "work it out" at step 2)
  const leafG = $derived({
    w: show(4) ? (locked('dLdw') ? NaN : fw.dLdw) : null,
    x: show(4) ? (locked('dLdz') ? NaN : fw.dLdx) : null,
    b: show(4) ? (locked('dLdz') ? NaN : fw.dLdb) : null,
  })
  const zG = $derived(show(3) ? (locked('dLdz') ? NaN : fw.dLdz) : show(2) ? NaN : null)
  const aG = $derived(show(1) ? (locked('dLda') ? NaN : fw.dLda) : null)
  const lG = $derived(show(1) ? 1 : null)
  // the box the gradient reached last (the current step)
  const cur = $derived(['', 'a', 'a', 'z', 'leaves'][stage])

  const STEP_TEXT = [
    'Forward pass done. Press “Step back” to start the gradient at L.',
    'Step 1 of 4: the gradient leaves L and reaches a.',
    'Step 2 of 4: at a, multiply by the local gradient a(1 − a). Compute ∂L/∂z.',
    'Step 3 of 4: the gradient reaches z.',
    'Step 4 of 4: the gradient reaches w, x and b. Done.',
  ]
</script>

{#snippet grad(sym: string, g: number | null)}
  {#if g === null}<span class="g off">∂L/∂{sym} ·</span>
  {:else}<span class="g">∂L/∂{sym} = <b class:ask={Number.isNaN(g)}>{Number.isNaN(g) ? '?' : f(g)}</b></span>{/if}
{/snippet}
{#snippet gv(k: Key, v: number)}<b class="gv" class:ask={locked(k)}>{gf(k, v)}</b>{/snippet}

<LabFrame
  title="Send the gradient back from L, one link at a time"
  hint="Press “Step back” to move the gradient one box further back. The numbers in w, x, b and the target y can be edited."
  onreset={resetAll}
  resetDisabled={!changed}
>
  <div class="bp">
    <div class="chain" role="group" aria-label="Computation graph: z = w·x + b, a = σ(z), L = (a − y)²">
      <div class="leaves" class:reached={show(4)} class:cur={cur === 'leaves'}>
        {#each [['w', w, (v: number) => (w = v)], ['x', x, (v: number) => (x = v)], ['b', b, (v: number) => (b = v)]] as [name, v, set]}
          <div class="node leaf">
            <label class="nm" for="bp-{name}">{name}</label>
            <input id="bp-{name}" class="val in" type="number" step="0.1" value={v} aria-label="{name} (editable)"
              oninput={(ev) => edit(set as (v: number) => void, ev)} />
            {@render grad(name as string, leafG[name as 'w' | 'x' | 'b'])}
          </div>
        {/each}
      </div>

      <svg class="fan wide" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        {#each [17, 50, 83] as y0}<path d="M0,{y0} C55,{y0} 45,50 100,50" class:g={show(4)} />{/each}
      </svg>
      <svg class="fan tall" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        {#each [17, 50, 83] as x0}<path d="M{x0},0 C{x0},55 50,45 50,100" class:g={show(4)} />{/each}
      </svg>

      <div class="node" class:reached={zG !== null} class:cur={cur === 'z'}>
        <span class="nm">z = w·x + b</span>
        <span class="val">{f(fw.z)}</span>
        {@render grad('z', zG)}
      </div>
      <div class="arr" class:g={show(3)} aria-hidden="true"></div>
      <div class="node" class:reached={aG !== null} class:cur={cur === 'a'}>
        <span class="nm">a = σ(z)</span>
        <span class="val">{f(fw.a)}</span>
        {@render grad('a', aG)}
      </div>
      <div class="arr" class:g={show(1)} aria-hidden="true"></div>
      <div class="node" class:reached={lG !== null}>
        <span class="nm">L = (a − y)²</span>
        <span class="val">{f(fw.L)}</span>
        {@render grad('L', lG)}
        <label class="tgt">target y <input class="in" type="number" step="0.1" value={y} oninput={(ev) => edit((v) => (y = v), ev)} /></label>
      </div>
    </div>

    <ol class="log">
      <li>Forward: z = {f(w)}·{f(x)} + {f(b)} = <b>{f(fw.z)}</b>, a = σ({f(fw.z)}) = <b>{f(fw.a)}</b>, L = ({f(fw.a)} − {f(y)})² = <b>{f(fw.L)}</b></li>
      {#if show(1)}<li>At L: local gradient ∂L/∂a = 2(a − y) = 2 × ({f(fw.a - y)}) = {@render gv('dLda', fw.dLda)}</li>{/if}
      {#if show(2)}<li>At a: local gradient ∂a/∂z = a(1 − a) = {f(fw.a)} × {f(1 - fw.a)} = <b class="gv">{f(fw.dadz)}</b>.
        Chain rule: ∂L/∂z = ∂L/∂a × ∂a/∂z = {gf('dLda', fw.dLda)} × {f(fw.dadz)} = {#if show(3)}{@render gv('dLdz', fw.dLdz)}{:else}<b class="gv ask">?</b> <span class="dim">(compute it, then step back)</span>{/if}</li>{/if}
      {#if show(4)}<li>At z: local gradients ∂z/∂w = x = {f(x)}, ∂z/∂b = 1, ∂z/∂x = w = {f(w)}.
        So ∂L/∂w = {gf('dLdz', fw.dLdz)} × {f(x)} = {@render gv('dLdw', fw.dLdw)}, ∂L/∂b = {@render gv('dLdz', fw.dLdb)}</li>{/if}
    </ol>

  </div>

  {#snippet controls()}
    <button class="lab-btn primary" onclick={() => (stage = Math.min(STEPS, stage + 1))} disabled={stage >= STEPS}>← Step back</button>
    <button class="lab-btn" onclick={() => (stage = Math.max(0, stage - 1))} disabled={stage <= 0}>Undo step →</button>
    <span class="count">step {stage} / {STEPS}</span>
  {/snippet}

  {#snippet readout()}{STEP_TEXT[stage]}{/snippet}

  {#snippet legend()}
    <span><b class="sw fwd">0.5</b> forward value</span>
    <span><b class="sw gr">∂L/∂·</b> gradient, flowing back</span>
    <span><span class="sw cur-sw"></span> where the gradient is now</span>
  {/snippet}
</LabFrame>

<LabFrame
  title="Check ∂L/∂w with a small change"
  hint="Change w by ε both ways and compare the slope with the chain-rule answer. Move ε to change the size of the change."
  onreset={() => (logEps = -5)}
  resetDisabled={logEps === -5}
>
  <div class="mono">
    <div>(L(w + ε) − L(w − ε)) / 2ε = <b>{locked('dLdw') ? '?' : numeric.toPrecision(10)}</b></div>
    <div>chain rule ∂L/∂w = <b>{locked('dLdw') ? '?' : fw.dLdw.toPrecision(10)}</b></div>
  </div>
  {#snippet controls()}
    <label class="eps">ε = <b>{e(eps)}</b> <input type="range" min="-14" max="0" step="1" bind:value={logEps} aria-label="epsilon, as a power of ten" /></label>
  {/snippet}
  {#snippet readout()}difference = <b class:okc={gap < 1e-8} class:badc={gap > 1e-6}>{e(gap)}</b>{/snippet}
</LabFrame>

<style>
  .bp { container-type: inline-size; display: grid; gap: 0.9rem; }

  /* the chain: leaves | fan | z → a → L */
  .chain { display: grid; grid-template-columns: minmax(5.4rem, 0.8fr) 2.2rem minmax(7.6rem, 1fr) 1.8rem minmax(7.6rem, 1fr) 1.8rem minmax(8.4rem, 1fr);
    align-items: center; }
  .leaves { display: grid; gap: 0.45rem; }
  .node { display: grid; justify-items: center; gap: 0.1rem; padding: 0.45rem 0.4rem; border-radius: 8px; background: var(--bg);
    border: 1.5px solid var(--line); font-family: var(--mono); text-align: center; min-width: 0;
    transition: border-color 0.2s, box-shadow 0.2s; }
  .node.reached, .leaves.reached .node { border-color: var(--grad); }
  .node.cur, .leaves.cur .node { box-shadow: 0 0 0 3px var(--highlight); border-color: var(--accent); }
  .nm { font-size: 0.8rem; color: var(--dim); white-space: nowrap; }
  .val { font-size: 1.05rem; font-weight: 700; color: var(--fg); font-variant-numeric: tabular-nums; }
  .g { font-size: 0.8rem; color: var(--grad); white-space: nowrap; font-variant-numeric: tabular-nums; }
  .g b { font-weight: 700; }
  .g.off { color: var(--dim); opacity: 0.7; }
  .ask { color: var(--warn) !important; }
  .in { font: inherit; font-family: var(--mono); width: 4.6rem; text-align: center; padding: 0.15rem 0.2rem; min-height: 2rem;
    border: 1px solid var(--field); border-bottom-style: dashed; border-radius: 5px; background: var(--card); color: var(--fg); }
  .val.in { font-size: 1rem; font-weight: 700; }
  .in:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
  .tgt { display: inline-flex; align-items: center; gap: 0.35rem; margin-top: 0.3rem; font-size: 0.78rem; color: var(--dim); }
  .tgt .in { width: 3.8rem; font-size: 0.85rem; }

  .fan { width: 100%; height: 100%; overflow: visible; }
  .fan path { fill: none; stroke: var(--dim); stroke-width: 1.4; vector-effect: non-scaling-stroke; transition: stroke 0.2s; }
  .fan path.g { stroke: var(--grad); stroke-width: 2; }
  .fan.tall { display: none; }

  /* arrows: forward → in dim; once the gradient has flowed back along an edge it points ← in the gradient color */
  .arr { position: relative; height: 0; border-top: 1.5px solid var(--dim); margin: 0 0.2rem; transition: border-color 0.2s; }
  .arr::after { content: ''; position: absolute; right: -1px; top: -6px; border: 5px solid transparent; border-right: 0; border-left: 8px solid var(--dim); }
  .arr.g { border-top: 2px solid var(--grad); }
  .arr.g::after { right: auto; left: -1px; border-left: 0; border-right: 8px solid var(--grad); }

  /* narrow: top → bottom */
  @container (max-width: 36rem) {
    .chain { grid-template-columns: minmax(0, 1fr); justify-items: center; }
    .leaves { grid-template-columns: repeat(3, minmax(0, 1fr)); width: 100%; }
    .chain > .node { width: min(100%, 15rem); }
    .fan.wide { display: none; }
    .fan.tall { display: block; width: 70%; height: 1.8rem; }
    .arr { height: 1.5rem; width: 0; border-top: 0; border-left: 1.5px solid var(--dim); margin: 0.15rem 0; }
    .arr::after { right: auto; top: auto; bottom: -1px; left: -6px; border: 5px solid transparent; border-bottom: 0; border-top: 8px solid var(--dim); }
    .arr.g { border-top: 0; border-left: 2px solid var(--grad); }
    .arr.g::after { bottom: auto; top: -1px; border-top: 0; border-bottom: 8px solid var(--grad); }
    .in { min-height: 2.5rem; }
  }

  .log { margin: 0; padding-left: 1.9rem; font-family: var(--mono); font-size: 0.8rem; line-height: 1.55; display: grid; gap: 0.35rem; }
  .log b { color: var(--fg); }
  .log b.gv { color: var(--grad); }
  .dim { color: var(--dim); }
  .eps { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; font-family: var(--mono); min-height: 2.5rem; }
  .eps input { width: 11rem; max-width: 100%; accent-color: var(--accent); }
  .mono { font-family: var(--mono); font-size: 0.85rem; display: grid; gap: 0.15rem; overflow-wrap: anywhere; }
  .okc { color: var(--ok); }
  .badc { color: var(--warn); }
  .count { font-family: var(--mono); font-size: 0.8rem; color: var(--dim); }

  .sw { font-family: var(--mono); font-size: 0.78rem; margin-right: 0.3rem; }
  .sw.fwd { color: var(--fg); }
  .sw.gr { color: var(--grad); }
  .cur-sw { display: inline-block; width: 0.9rem; height: 0.7rem; vertical-align: -0.05rem; border: 1.5px solid var(--accent); border-radius: 3px; box-shadow: 0 0 0 2px var(--highlight); }
  @media (prefers-reduced-motion: reduce) { .node, .arr, .fan path { transition: none; } }
</style>
