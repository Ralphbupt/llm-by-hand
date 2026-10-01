<script lang="ts">
  /**
   * "Show answer" for a learner who is stuck. Appears after a failed attempt.
   * Asks once for confirmation, with a "Don't ask me again" box that is remembered in this browser.
   */
  import { revealNeedsConfirm, setRevealNeedsConfirm } from '@lib/progress'

  let { onreveal }: { onreveal: () => void } = $props()
  let asking = $state(false)
  let noAsk = $state(false)

  function click() {
    if (revealNeedsConfirm()) asking = true
    else onreveal()
  }
  function confirm() {
    if (noAsk) setRevealNeedsConfirm(false)
    asking = false
    onreveal()
  }
</script>

{#if !asking}
  <button class="reveal-btn" onclick={click}>Stuck? Show answer</button>
{:else}
  <div class="ask" role="group" aria-label="Show the answer?">
    <p>Showing the answer keeps this level at two stars at most. One more try usually teaches more. Show it anyway?</p>
    <label><input type="checkbox" bind:checked={noAsk} /> Don’t ask me again</label>
    <div class="btns">
      <button class="yes" onclick={confirm}>Show answer</button>
      <button onclick={() => (asking = false)}>Keep trying</button>
    </div>
  </div>
{/if}

<style>
  .reveal-btn {
    margin-top: 0.6rem; font: inherit; font-size: 0.82rem; padding: 0.2rem 0.7rem;
    border: 1px dashed var(--line); border-radius: 4px; background: transparent; color: var(--dim); cursor: pointer;
  }
  .reveal-btn:hover { color: var(--fg); border-color: var(--dim); }
  .ask { margin-top: 0.6rem; padding: 0.6rem 0.8rem; border: 1px solid var(--warn); border-radius: 6px; background: var(--bg); font-size: 0.9rem; }
  .ask p { margin: 0 0 0.4rem; }
  .ask label { display: flex; gap: 0.4rem; align-items: center; color: var(--dim); font-size: 0.82rem; cursor: pointer; }
  .btns { display: flex; gap: 0.5rem; margin-top: 0.5rem; flex-wrap: wrap; }
  .btns button { font: inherit; font-size: 0.85rem; padding: 0.25rem 0.8rem; border: 1px solid var(--line); border-radius: 4px; background: var(--card); color: var(--fg); cursor: pointer; }
  .btns .yes { border-color: var(--warn); color: var(--warn); }
</style>
