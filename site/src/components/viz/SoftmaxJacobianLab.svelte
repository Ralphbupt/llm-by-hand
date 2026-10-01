<script lang="ts">
  /**
   * Softmax backward for three scores. Edit the scores z and the incoming gradient dp:
   * the lab shows p = softmax(z), the Jacobian J = diag(p) − pᵀp with its row sums,
   * and dz computed two ways (dp @ J and the fast form p ⊙ (dp − dp·p)), which always agree.
   * Cells a question asks about stay "?" until it is solved.
   */
  import { onMount } from 'svelte'
  import { has, subscribe } from '@lib/progress'
  import { softmaxRows } from '@lib/num'
  import MatrixGrid from './MatrixGrid.svelte'
  import LabFrame from './LabFrame.svelte'

  /** keys: j11 (J[1][1]), j01 (J[0][1]), rows (the row sums), dz2 (dz) → exercise ids */
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
  const masked = (k: string) => !!hide[k] && !solved[hide[k]]

  const Z0 = [Math.LN2, 0, 0]
  const DP0 = [1, 0, 2]
  let z = $state([...Z0])
  let dp = $state([...DP0])

  const clean = (v: number) => (Math.abs(v) < 5e-5 ? 0 : v)
  const p = $derived(softmaxRows([z])[0])
  const J = $derived(p.map((pi, i) => p.map((pj, j) => clean((i === j ? pi : 0) - pi * pj))))
  const rowSums = $derived(J.map((r) => [clean(r.reduce((s, v) => s + v, 0))]))
  const dot = $derived(dp.reduce((s, v, i) => s + v * p[i], 0))
  const dzJac = $derived(p.map((_, j) => clean(J.reduce((s, row, i) => s + row[j] * dp[i], 0))))
  const dzFast = $derived(p.map((pi, i) => clean(pi * (dp[i] - dot))))

  // p1 = p2 at the start, so J[2][2] = J[1][1] and J[0][2] = J[0][1]: hide the twins too
  const jMask = $derived([
    ...(masked('j11') ? [{ i: 1, j: 1 }, { i: 2, j: 2 }] : []),
    ...(masked('j01') ? [{ i: 0, j: 1 }, { i: 1, j: 0 }, { i: 0, j: 2 }, { i: 2, j: 0 }] : []),
  ])
  const sumMask = $derived(masked('rows') ? [0, 1, 2].map((i) => ({ i, j: 0 })) : [])
  // the entries of dz add up to 0, so one visible entry would give the others away
  // dp · p in the readout is the first step of the dz question, so it hides with dz
  const dzMask = $derived(masked('dz2') ? [0, 1, 2].map((j) => ({ i: 0, j })) : [])
  const f = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(2))
  const changed = $derived(z.some((v, i) => v !== Z0[i]) || dp.some((v, i) => v !== DP0[i]))
  const labels = ['z0', 'z1', 'z2']
</script>

<LabFrame
  title="Softmax backward: one Jacobian, or one short formula"
  hint="Type new scores z or a new incoming gradient dp. Both ways of computing dz always give the same numbers."
  onreset={() => { z = [...Z0]; dp = [...DP0] }}
  resetDisabled={!changed}
>
  <div class="cols">
    <div class="col">
      <MatrixGrid value={[z]} label="scores z" editable onchange={(v) => (z = v[0])} />
      <MatrixGrid value={[p]} label="p = softmax(z)" />
      <MatrixGrid value={[dp]} label="dp (from the layer after)" editable onchange={(v) => (dp = v[0])} />
    </div>
    <div class="col">
      <div class="row">
        <MatrixGrid value={J} label="J = diag(p) − pᵀp" decimals={4} rowLabels={['p0', 'p1', 'p2']} colLabels={labels} masked={jMask} />
        <MatrixGrid value={rowSums} label="row sum" decimals={4} masked={sumMask} />
      </div>
      <MatrixGrid value={[dzJac]} label="dz = dp @ J" decimals={4} masked={dzMask} />
      <MatrixGrid value={[dzFast]} label="dz = p ⊙ (dp − dp·p)" decimals={4} masked={dzMask} />
    </div>
  </div>

  {#snippet readout()}
    {#if masked('dz2')}
      dp · p = <b class="q">?</b>, so each dzᵢ is pᵢ × (dpᵢ − dp · p).
    {:else}
      dp · p = {f(dot)}, so each dzᵢ is pᵢ × (dpᵢ − {f(dot)}).
    {/if}
  {/snippet}

  {#snippet legend()}
    <span class="key">row i of J: how pᵢ moves when each score moves</span>
    <span class="key"><b class="q">?</b> answer a question below to see this number</span>
  {/snippet}
</LabFrame>

<style>
  .cols { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 1.5rem; align-items: start; }
  .col { display: flex; flex-direction: column; gap: 0.8rem; min-width: 0; }
  .row { display: flex; gap: 0.8rem; flex-wrap: wrap; align-items: flex-end; }
  .key { display: inline-flex; align-items: center; gap: 0.4rem; }
  .q { color: var(--warn); }
  @media (max-width: 700px) { .cols { grid-template-columns: minmax(0, 1fr); } }
</style>
