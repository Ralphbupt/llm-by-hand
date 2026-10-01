<script lang="ts">
  /**
   * The home page's first moment: compute one attention score by hand.
   * Three words with two numbers each; the score table has one "?" (cat · dog). Get it right and the
   * row turns into attention weights. Nothing is saved; it's a taste of what every level feels like.
   */
  const words = ['cat', 'dog', 'car'] as const
  const X = [[2, 0], [1, 1], [0, 2]]
  const dot = (a: number[], b: number[]) => a[0] * b[0] + a[1] * b[1]
  const S = X.map((a) => X.map((b) => dot(a, b)))
  // weights for cat's row (softmax of [4, 2, 0])
  const e = S[0].map((v) => Math.exp(v - 4))
  const sum = e.reduce((a, b) => a + b, 0)
  const W = e.map((v) => v / sum)

  let value = $state('')
  let phase = $state<'idle' | 'wrong' | 'right'>('idle')
  let tries = $state(0)

  function check() {
    const v = Number(value.trim())
    if (value.trim() !== '' && v === S[0][1]) phase = 'right'
    else {
      phase = 'wrong'
      tries++
    }
  }
</script>

<div class="try" class:right={phase === 'right'}>
  <p class="ask">Try one before you start. Each word is two numbers:</p>
  <div class="vecs">
    {#each words as w, i}
      <div class="vec" class:hi={i < 2 && phase !== 'right'}><span class="w">{w}</span><span class="n">[{X[i].join(', ')}]</span></div>
    {/each}
  </div>

  <p class="ask">How strongly does <b>cat</b> look at <b>dog</b>? Multiply them number by number, then add.</p>
  <table class="scores" aria-label="Scores: every word dotted with every word">
    <thead><tr><th></th>{#each words as w}<th>{w}</th>{/each}</tr></thead>
    <tbody>
      {#each words as w, i}
        <tr>
          <th>{w}</th>
          {#each words as _, j}
            <td class:target={i === 0 && j === 1} class:row={i === 0 && phase === 'right'}>
              {#if i === 0 && j === 1}
                {#if phase === 'right'}{S[0][1]}{:else}
                  <input
                    aria-label="cat · dog"
                    inputmode="numeric"
                    bind:value
                    placeholder="?"
                    onkeydown={(ev) => ev.key === 'Enter' && check()}
                  />
                {/if}
              {:else if i === 1 && j === 0 && phase !== 'right'}<span class="mirror" title="The same as cat · dog">·</span>{:else}{S[i][j]}{/if}
            </td>
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>

  {#if phase === 'right'}
    <div class="weights" aria-live="polite">
      <p>Right: 2 × 1 + 0 × 1 = 2. Turn cat’s row into weights that add up to 1, and you get attention:</p>
      <div class="bars">
        {#each words as w, j}
          <div class="bar"><span class="lbl">{w}</span><span class="fill" style:width="{W[j] * 100}%"></span><span class="pct">{W[j].toFixed(2)}</span></div>
        {/each}
      </div>
      <p class="done">That is one attention score, computed by hand. Level 14 builds the rest from here.</p>
    </div>
  {:else}
    <div class="row-btn">
      <button onclick={check}>Check</button>
      {#if phase === 'wrong'}
        <span class="hint" aria-live="polite">{tries > 1 ? 'cat = [2, 0], dog = [1, 1]: 2 × 1 + 0 × 1.' : 'Not quite. Multiply the first numbers, multiply the second numbers, add.'}</span>
      {/if}
    </div>
  {/if}
</div>

<style>
  .try {
    border: 1px solid var(--line); border-radius: 14px; padding: 1.1rem 1.2rem 1.2rem;
    background: color-mix(in srgb, var(--card) 92%, transparent); backdrop-filter: blur(2px);
    font-size: 0.93rem; transition: border-color 0.2s;
  }
  .try.right { border-color: var(--ok); }
  .ask { margin: 0 0 0.6rem; color: var(--dim); }
  .ask b { color: var(--fg); }
  .vecs { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.9rem; }
  .vec { display: flex; gap: 0.4rem; align-items: baseline; padding: 0.25rem 0.6rem; border: 1px solid var(--line); border-radius: 8px; background: var(--bg); }
  .vec.hi { border-color: var(--accent); }
  .vec .w { font-weight: 600; }
  .vec .n, .scores, .pct { font-family: 'JetBrains Mono Variable', var(--mono); font-variant-numeric: tabular-nums; }
  .scores { width: auto; border-collapse: separate; border-spacing: 4px; margin: 0 0 0.8rem -4px; font-size: 1rem; }
  .scores th { color: var(--dim); font-weight: 500; font-size: 0.8rem; text-align: center; border: 0; padding: 0 0.3rem; }
  .scores td { width: 3.2rem; height: 2.4rem; text-align: center; border: 1px solid var(--line); border-radius: 6px; background: var(--bg); padding: 0; }
  .scores td.target { border-color: var(--warn); }
  .mirror { color: var(--dim); }
  .scores td.row { border-color: var(--ok); color: var(--ok); }
  .scores input {
    width: 100%; height: 100%; border: 0; background: transparent; color: var(--warn); text-align: center;
    font: inherit; font-weight: 700; outline: none;
  }
  .scores input::placeholder { color: var(--warn); opacity: 1; }
  .scores td.target:focus-within { box-shadow: 0 0 0 2px var(--warn); }
  .row-btn { display: flex; gap: 0.8rem; align-items: center; flex-wrap: wrap; }
  .row-btn button {
    font: inherit; font-weight: 600; padding: 0.35rem 1rem; border-radius: 8px; border: 1px solid var(--accent);
    background: var(--accent); color: var(--bg); cursor: pointer;
  }
  .hint { color: var(--warn); font-size: 0.86rem; }
  .weights p { margin: 0 0 0.6rem; }
  .bars { display: grid; gap: 0.35rem; margin-bottom: 0.7rem; }
  .bar { display: grid; grid-template-columns: 2.6rem 1fr 3rem; align-items: center; gap: 0.5rem; }
  .bar .lbl { font-weight: 600; font-size: 0.85rem; }
  .bar .fill { height: 0.7rem; border-radius: 4px; background: var(--ok); animation: grow 0.6s ease-out both; }
  .bar .pct { text-align: right; font-size: 0.85rem; }
  .done { color: var(--ok); font-weight: 600; margin: 0; }
  @keyframes grow { from { width: 0; } }
  @media (prefers-reduced-motion: reduce) { .bar .fill { animation: none; } }
</style>
