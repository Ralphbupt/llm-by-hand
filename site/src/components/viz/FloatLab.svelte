<script lang="ts">
  /**
   * Float lab: type a number and see the bits a float32, float16 or bfloat16 stores for it,
   * what number those bits really mean, and how far that is from what you typed.
   * Tap a bit to flip it. Same formats and rounding as numbers-in-a-computer/demo.py.
   */
  import { decode, encode, facts, FORMATS, show, type Bits, type Fmt } from '@lib/floatbits'
  import LabFrame from './LabFrame.svelte'

  const START = { fmt: 'float16' as Fmt, typed: 0.1 }
  const PRESETS: [number, string][] = [[0.1, '0.1'], [6, '6'], [256.75, '256.75'], [65504, '65504'], [70000, '70000'], [1e-8, '1e−8']]
  let fmt = $state<Fmt>(START.fmt)
  let typed = $state<number | null>(START.typed)
  let text = $state(String(START.typed))
  let bits = $state<Bits>(encode(START.typed, START.fmt))

  const F = $derived(FORMATS[fmt])
  const info = $derived(facts(fmt))
  const value = $derived(decode(bits, fmt))
  const changed = $derived(fmt !== START.fmt || typed !== START.typed)
  const toList = (n: number, len: number) => Array.from({ length: len }, (_, i) => (n >> (len - 1 - i)) & 1)
  const expBits = $derived(toList(bits.exp, F.E))
  // mantissa can be 23 bits: >> works on 32-bit ints, fine
  const mantBits = $derived(toList(bits.mant, F.M))
  const special = $derived(bits.exp === 2 ** F.E - 1 ? (bits.mant ? 'nan' : 'inf') : bits.exp === 0 ? 'sub' : 'normal')

  function store(v: number) {
    typed = v
    bits = encode(v, fmt)
  }
  function onText() {
    const v = Number(text.trim().replace('−', '-'))
    if (text.trim() !== '' && !Number.isNaN(v)) store(v)
  }
  function setFmt(f: Fmt) {
    const v = typed ?? value
    fmt = f
    bits = encode(v, f)
  }
  function flip(part: 'sign' | 'exp' | 'mant', k: number) {
    if (part === 'sign') bits = { ...bits, sign: bits.sign ^ 1 }
    else if (part === 'exp') bits = { ...bits, exp: bits.exp ^ (1 << (F.E - 1 - k)) }
    else bits = { ...bits, mant: bits.mant ^ (1 << (F.M - 1 - k)) }
    typed = null
    text = show(decode(bits, fmt), 8).replace('−', '-')
  }
  function reset() {
    fmt = START.fmt
    text = String(START.typed)
    store(START.typed)
  }
  const err = $derived(typed === null || !Number.isFinite(value) ? null : Math.abs(value - typed))
  const full = (v: number) => (Number.isFinite(v) ? String(Number(v.toPrecision(12))).replace('-', '−') : show(v))
</script>

<LabFrame title="What the bits store" hint="Type a number or pick one, then tap a bit to flip it." onreset={reset} resetDisabled={!changed}>
  <div class="bits" aria-label="bits">
    <div class="grp">
      <div class="glab s">sign</div>
      <div class="cells">
        <button class="bit s" class:one={bits.sign} aria-pressed={!!bits.sign} aria-label="sign bit" onclick={() => flip('sign', 0)}>{bits.sign}</button>
      </div>
    </div>
    <div class="grp">
      <div class="glab e">exponent ({F.E} bits) = {bits.exp}</div>
      <div class="cells">
        {#each expBits as b, k}
          <button class="bit e" class:one={b} aria-pressed={!!b} aria-label={`exponent bit ${k}`} onclick={() => flip('exp', k)}>{b}</button>
        {/each}
      </div>
    </div>
    <div class="grp wide">
      <div class="glab m">mantissa ({F.M} bits) = {bits.mant}</div>
      <div class="cells">
        {#each mantBits as b, k}
          <button class="bit m" class:one={b} aria-pressed={!!b} aria-label={`mantissa bit ${k}`} onclick={() => flip('mant', k)}>{b}</button>
        {/each}
      </div>
    </div>
  </div>

  <div class="dec">
    {#if special === 'normal'}
      (−1)<sup>{bits.sign}</sup> × (1 + {bits.mant}/{2 ** F.M}) × 2<sup>{bits.exp} − {info.bias}</sup> = <b>{full(value)}</b>
    {:else if special === 'sub'}
      exponent all 0s (a tiny “subnormal” number): (−1)<sup>{bits.sign}</sup> × {bits.mant}/{2 ** F.M} × 2<sup>{1 - info.bias}</sup> = <b>{full(value)}</b>
    {:else}
      exponent all 1s: <b class="bad">{special === 'inf' ? (bits.sign ? '−inf' : 'inf') : 'nan'}</b>
    {/if}
  </div>

  <table class="facts">
    <tbody>
      <tr><th>largest</th><td>{show(info.largest, 5)}</td><th>gap after 1</th><td>{show(info.gapAfter1, 3)}</td></tr>
      <tr><th>smallest normal</th><td>{show(info.smallestNormal, 3)}</td><th>numbers in [1, 2)</th><td>{info.perOctave}</td></tr>
    </tbody>
  </table>

  {#snippet controls()}
    <div class="ctl">
      <div class="fmts" role="group" aria-label="format">
        {#each Object.keys(FORMATS) as f}
          <button class="lab-btn fmt" class:on={fmt === f} aria-pressed={fmt === f} onclick={() => setFmt(f as Fmt)}>{f}</button>
        {/each}
      </div>
      <label class="num">number <input type="text" inputmode="decimal" bind:value={text} oninput={onText} aria-label="number to store" /></label>
      <div class="presets">
        {#each PRESETS as [p, label]}
          <button class="lab-btn ghost" onclick={() => { text = String(p); store(p) }}>{label}</button>
        {/each}
      </div>
    </div>
  {/snippet}

  {#snippet readout()}
    {#if typed === null}
      these bits mean {full(value)} in {fmt}
    {:else if err === null}
      {show(typed, 6)} in {fmt} → <b class="bad">{full(value)}</b>: too big or too small for this format
    {:else if err === 0}
      {show(typed, 6)} in {fmt} → <b>{full(value)}</b>, stored exactly
    {:else}
      {show(typed, 6)} in {fmt} → <b>{full(value)}</b>, off by {show(err, 2)}
    {/if}
  {/snippet}

  {#snippet legend()}
    <span class="key"><i class="k s"></i>sign: 0 is +, 1 is −</span>
    <span class="key"><i class="k e"></i>exponent: which power of 2</span>
    <span class="key"><i class="k m"></i>mantissa: where between that power and the next</span>
  {/snippet}
</LabFrame>

<style>
  .bits { display: flex; flex-wrap: wrap; gap: 0.6rem 0.9rem; align-items: flex-start; }
  .grp.wide { flex: 1 1 14rem; }
  .glab { font-family: var(--mono); font-size: 0.76rem; margin-bottom: 0.2rem; }
  .glab.s { color: var(--cat-1); } .glab.e { color: var(--cat-2); } .glab.m { color: var(--cat-3); }
  .cells { display: flex; flex-wrap: wrap; gap: 3px; }
  .bit {
    width: 1.75rem; height: 2.5rem; padding: 0; border-radius: 3px; cursor: pointer;
    font-family: var(--mono); font-size: 0.9rem; background: var(--bg); color: var(--dim);
    border: 1.5px solid var(--line);
  }
  .bit.s { border-color: var(--cat-1); } .bit.e { border-color: var(--cat-2); } .bit.m { border-color: var(--cat-3); }
  .bit.one { color: var(--fg); font-weight: 700; background: var(--highlight); }
  .bit:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
  .dec { font-family: var(--mono); font-size: 0.88rem; margin-top: 0.7rem; overflow-wrap: anywhere; }
  .bad { color: var(--warn); }
  .facts { border-collapse: collapse; font-family: var(--mono); font-size: 0.78rem; margin-top: 0.5rem; width: auto; }
  .facts th { font-weight: 400; color: var(--dim); text-align: left; padding: 0.1rem 0.5rem 0.1rem 0; }
  .facts td { text-align: right; padding: 0.1rem 1rem 0.1rem 0; font-variant-numeric: tabular-nums; }
  .ctl { display: flex; flex-direction: column; gap: 0.5rem; width: 100%; }
  .fmts, .presets { display: flex; flex-wrap: wrap; gap: 0.35rem; }
  .fmt { font-family: var(--mono); font-size: 0.8rem; }
  .fmt.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  .num { font-size: 0.85rem; display: inline-flex; gap: 0.4rem; align-items: center; }
  .num input { font-family: var(--mono); font-size: 0.9rem; width: 9rem; padding: 0.35rem 0.4rem; border: 1px solid var(--field); border-radius: 4px; background: var(--bg); color: var(--fg); }
  .key { display: inline-flex; align-items: center; gap: 0.4rem; }
  .k { width: 0.9rem; height: 0.9rem; border-radius: 2px; flex: none; border: 1.5px solid; }
  .k.s { border-color: var(--cat-1); } .k.e { border-color: var(--cat-2); } .k.m { border-color: var(--cat-3); }
</style>
