<script lang="ts" module>
  // the same rule the lessons use (rehypeNoWrapVectors in astro.config.mjs): a short vector such as "car = [0, 2]"
  // never breaks across lines, so the numbers a learner copies from a question stay together on a phone
  const VEC = /\[[−-]?\d[\d.,\s−-]*,[\d.,\s−-]*\]/g
  export function splitVectors(text: string): { t: string; vec: boolean }[] {
    const out: { t: string; vec: boolean }[] = []
    let at = 0
    for (const m of text.matchAll(VEC)) {
      if (m.index! > at) out.push({ t: text.slice(at, m.index), vec: false })
      out.push({ t: m[0], vec: true })
      at = m.index! + m[0].length
    }
    if (at < text.length) out.push({ t: text.slice(at), vec: false })
    return out
  }
  // `code` in question and hint text is shown as code, as in the lessons (no literal backticks on the page)
  export function splitText(text: string): { t: string; kind: 'text' | 'vec' | 'code' }[] {
    const out: { t: string; kind: 'text' | 'vec' | 'code' }[] = []
    text.split(/(`[^`\n]+`)/).forEach((piece, i) => {
      if (i % 2) out.push({ t: piece.slice(1, -1), kind: 'code' })
      else for (const p of splitVectors(piece)) if (p.t) out.push({ t: p.t, kind: p.vec ? 'vec' : 'text' })
    })
    return out
  }
</script>

<script lang="ts">
  let { text }: { text: string } = $props()
  const parts = $derived(splitText(String(text ?? '')))
</script>

{#each parts as p}{#if p.kind === 'vec'}<span class="vec-nw">{p.t}</span>{:else if p.kind === 'code'}<code class:code-nw={p.t.length <= 24}>{p.t}</code>{:else}{p.t}{/if}{/each}
