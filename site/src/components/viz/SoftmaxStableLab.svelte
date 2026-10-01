<script lang="ts">
  /**
   * Softmax two ways, in float32 or float16: straight from e^z, and after subtracting the largest score.
   * Every intermediate is rounded to the chosen format, the way NumPy computes it, so inf and nan show up
   * exactly where they would in real code. Matches numbers-in-a-computer/demo.py.
   */
  import { onMount } from 'svelte'
  import { has, subscribe } from '@lib/progress'
  import { roundTo, show, type Fmt } from '@lib/floatbits'
  import LabFrame from './LabFrame.svelte'

  let { hide = {} }: { hide?: Record<string, string> } = $props()
  let solved = $state<Record<string, boolean>>({})
  onMount(() => {
    const sync = () => {
      const next: Record<string, boolean> = {}
      for (const id of Object.values(hide)) next[id] = has(id)
      solved = next
    }
    sync()
    return subscribe(sync)
  })
  const hideP = $derived(!!hide.p && !solved[hide.p])

  const START = { z: [1000, 1001], fmt: 'float32' as Fmt }
  const PRESETS: number[][] = [[1, 2], [1000, 1001], [-1000, -999], [88, 89], [10, 12]]
  let z = $state([...START.z])
  let texts = $state(START.z.map(String))
  let fmt = $state<Fmt>(START.fmt)
  const changed = $derived(fmt !== START.fmt || z[0] !== START.z[0] || z[1] !== START.z[1])

  const r = (v: number) => roundTo(v, fmt)
  const calc = $derived.by(() => {
    const zz = z.map(r)
    const e = zz.map((v) => r(Math.exp(v)))
    const s = r(e[0] + e[1])
    const p = e.map((v) => r(v / s))
    const m = Math.max(...zz)
    const d = zz.map((v) => r(v - m))
    const e2 = d.map((v) => r(Math.exp(v)))
    const s2 = r(e2[0] + e2[1])
    const p2 = e2.map((v) => r(v / s2))
    return { e, s, p, m, d, e2, s2, p2 }
  })
  const bad = (v: number) => !Number.isFinite(v)
  const fmtV = (v: number) => show(v, 3)
  const fmtZ = (v: number) => show(v, 7)

  function setText(k: number, t: string) {
    texts[k] = t
    const v = Number(t.trim().replace('−', '-'))
    if (t.trim() !== '' && Number.isFinite(v)) z[k] = v
  }
  function preset(p: number[]) { z = [...p]; texts = p.map(String) }
  function reset() { preset(START.z); fmt = START.fmt }
</script>

<LabFrame title="Softmax two ways" hint="Pick two scores and a format. Watch where inf and nan appear." onreset={reset} resetDisabled={!changed}>
  <div class="tw">
    <table>
      <thead>
        <tr><th></th><th>score 0</th><th>score 1</th><th>sum</th></tr>
      </thead>
      <tbody>
        <tr class="grp"><th colspan="4">directly from e<sup>z</sup></th></tr>
        <tr><th>z</th><td>{fmtZ(z[0])}</td><td>{fmtZ(z[1])}</td><td></td></tr>
        <tr><th>e<sup>z</sup></th>{#each calc.e as v}<td class:bad={bad(v)}>{fmtV(v)}</td>{/each}<td class:bad={bad(calc.s)}>{fmtV(calc.s)}</td></tr>
        <tr><th>p</th>{#each calc.p as v}<td class:bad={bad(v)}><b>{fmtV(v)}</b></td>{/each}<td></td></tr>
        <tr class="grp"><th colspan="4">subtract the largest score first ({fmtZ(calc.m)})</th></tr>
        <tr><th>z − max</th>{#each calc.d as v}<td>{fmtZ(v)}</td>{/each}<td></td></tr>
        <tr><th>e<sup>z − max</sup></th>{#each calc.e2 as v}<td>{fmtV(v)}</td>{/each}<td>{fmtV(calc.s2)}</td></tr>
        <tr><th>p</th>{#each calc.p2 as v}<td class="good" class:q={hideP}><b>{hideP ? '?' : fmtV(v)}</b></td>{/each}<td></td></tr>
      </tbody>
    </table>
  </div>

  {#snippet controls()}
    <div class="ctl">
      <div class="row" role="group" aria-label="format">
        {#each ['float32', 'float16'] as f}
          <button class="lab-btn fmt" class:on={fmt === f} aria-pressed={fmt === f} onclick={() => (fmt = f as Fmt)}>{f}</button>
        {/each}
      </div>
      <div class="row">
        <label>score 0 <input type="text" inputmode="decimal" value={texts[0]} oninput={(e) => setText(0, e.currentTarget.value)} /></label>
        <label>score 1 <input type="text" inputmode="decimal" value={texts[1]} oninput={(e) => setText(1, e.currentTarget.value)} /></label>
      </div>
      <div class="row">
        {#each PRESETS as p}
          <button class="lab-btn ghost" onclick={() => preset(p)}>[{p.map((v) => show(v)).join(', ')}]</button>
        {/each}
      </div>
    </div>
  {/snippet}

  {#snippet readout()}
    {#if bad(calc.p[0]) || bad(calc.p[1])}
      straight: <span class="bad">p = [{calc.p.map(fmtV).join(', ')}]</span> · subtract max first: {hideP ? 'answer the question below to see p' : `p = [${calc.p2.map(fmtV).join(', ')}]`}
    {:else}
      both ways give {hideP ? 'the same p (answer the question below to see it)' : `p = [${calc.p2.map(fmtV).join(', ')}]`}
    {/if}
  {/snippet}

  {#snippet legend()}
    <span class="key"><b class="bad">inf, nan</b> too big for {fmt}, or a result of inf / inf</span>
    <span class="key"><b class="good">0.73</b> the probabilities that softmax should give</span>
  {/snippet}
</LabFrame>

<style>
  .tw { overflow-x: auto; }
  table { border-collapse: collapse; font-family: var(--mono); font-size: 0.85rem; width: auto; }
  th { font-weight: 400; color: var(--dim); text-align: left; padding: 0.2rem 0.7rem 0.2rem 0; white-space: nowrap; }
  thead th { font-size: 0.78rem; text-align: right; }
  thead th:first-child { text-align: left; }
  td { text-align: right; padding: 0.2rem 0.7rem; border-bottom: 1px solid var(--line); font-variant-numeric: tabular-nums; min-width: 4.5rem; }
  tr.grp th { color: var(--fg); padding-top: 0.6rem; font-family: system-ui, -apple-system, sans-serif; font-size: 0.82rem; }
  .bad { color: var(--warn); }
  .good { color: var(--ok); }
  .q { color: var(--warn); }
  .ctl { display: flex; flex-direction: column; gap: 0.5rem; width: 100%; }
  .row { display: flex; flex-wrap: wrap; gap: 0.4rem 0.8rem; align-items: center; }
  label { font-size: 0.85rem; display: inline-flex; gap: 0.4rem; align-items: center; }
  input { font-family: var(--mono); font-size: 0.9rem; width: 6rem; padding: 0.35rem 0.4rem; border: 1px solid var(--field); border-radius: 4px; background: var(--bg); color: var(--fg); }
  .fmt { font-family: var(--mono); font-size: 0.8rem; }
  .fmt.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  .key { display: inline-flex; align-items: center; gap: 0.4rem; }
</style>
