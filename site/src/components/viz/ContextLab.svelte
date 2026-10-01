<script lang="ts">
  /**
   * Context lab: the same word "apple" in two sentences.
   * Its own vector is identical in both. Averaging with the neighbors (a crude preview of attention)
   * pulls it toward the meaning the sentence needs.
   */
  import { onMount } from 'svelte'
  import { has, subscribe } from '@lib/progress'
  import LabFrame from './LabFrame.svelte'

  // A value that a question on the page asks for stays "?" until that question is solved.
  let { hide = {} }: { hide?: Record<string, string | undefined> } = $props()
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
  const locked = (k: string) => !!hide[k] && !solved[hide[k]!]

  const DIMS = ['fruit', 'tech', 'sweet', 'action']
  const VOCAB: Record<string, number[]> = {
    apple: [1, 1, 0, 0],
    sweet: [1, 0, 1, 0],
    releases: [0, 1, 0, 1],
    phone: [0, 1, 0, 0],
  }
  const SENTENCES = [['sweet', 'apple'], ['apple', 'releases', 'phone']]
  let mix = $state(false)

  const avg = (ws: string[]) => DIMS.map((_, d) => ws.reduce((s, w) => s + VOCAB[w][d], 0) / ws.length)
  const fmt = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(3))
</script>

<LabFrame
  title="Same word, two sentences"
  hint="Check the box to average every word in the sentence with equal weights, a simple first version of attention."
  onreset={() => (mix = false)}
  resetDisabled={!mix}
>
  <div class="cols">
    {#each SENTENCES as s}
      {@const out = mix ? avg(s) : VOCAB.apple}
      <div class="card">
        <p class="sent">{#each s as w, i}{i ? ' ' : ''}<span class:apple={w === 'apple'}>{w}</span>{/each}</p>
        <table>
          <thead><tr><th></th>{#each DIMS as d}<th>{d}</th>{/each}</tr></thead>
          <tbody>
            {#each s as w}
              <tr class:apple={w === 'apple'}><td>{w}</td>{#each VOCAB[w] as v}<td>{v}</td>{/each}</tr>
            {/each}
            <tr class="out"><td>apple →</td>{#each out as v}<td>{#if mix && locked('mix')}<span class="q">?</span>{:else}<span class="bar" style="--h:{v}"></span>{fmt(v)}{/if}</td>{/each}</tr>
          </tbody>
        </table>
      </div>
    {/each}
  </div>

  {#snippet controls()}
    <label class="tog"><input type="checkbox" bind:checked={mix} /> Average with the neighbors (equal weights)</label>
  {/snippet}

  {#snippet readout()}
    {#if mix}
      Now “apple” leans toward fruit in the first sentence and toward tech in the second. Level 14 replaces equal weights with weights the model computes.
    {:else}
      With a lookup table, “apple” gets exactly the same vector in both sentences: fruit 1, tech 1.
    {/if}
  {/snippet}
</LabFrame>

<style>
  .tog { display: inline-flex; gap: 0.5rem; align-items: center; font-size: 0.9rem; cursor: pointer; min-height: 2.2rem; }
  .tog input { width: 1.1rem; height: 1.1rem; accent-color: var(--accent); }
  .cols { display: flex; flex-wrap: wrap; gap: 1rem; }
  .card { flex: 1 1 260px; min-width: 0; overflow-x: auto; }
  .sent { font-size: 1rem; margin: 0 0 0.4rem; }
  .sent .apple { color: var(--accent); font-weight: 700; }
  table { font-family: var(--mono); font-size: 0.85rem; width: auto; }
  th, td { padding: 0.15rem 0.45rem; text-align: center; }
  th { color: var(--dim); font-weight: 400; }
  td:first-child { text-align: left; }
  tr.apple td { color: var(--accent); }
  tr.out td { font-weight: 700; border-top: 2px solid var(--fg); }
  .bar { display: inline-block; width: 0.35rem; height: calc(var(--h) * 0.9rem); background: var(--accent); margin-right: 0.25rem; vertical-align: bottom; opacity: 0.6; transition: height 0.2s; }
  @media (prefers-reduced-motion: reduce) { .bar { transition: none; } }
  .q { color: var(--warn); font-weight: 700; }
</style>
