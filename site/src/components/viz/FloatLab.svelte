<script lang="ts">
  /**
   * Float lab: type a number and see the bits a float32, float16 or bfloat16 stores for it,
   * what number those bits really mean, and how far that is from what you typed.
   * Tap a bit to flip it. Same formats and rounding as numbers-in-a-computer/demo.py.
   */
  import { decode, encode, facts, FORMATS, show, type Bits, type Fmt } from '@lib/floatbits'
  import LabFrame from './LabFrame.svelte'
  import { provideLang, useT } from '@lib/i18nSvelte'
  import type { Lang } from '@lib/i18n'

  let { lang = 'en' }: { lang?: Lang } = $props()
  provideLang(lang)
  const t = useT({
    'What the bits store': '比特里存的是什么',
    'Type a number or pick one, then tap a bit to flip it.': '输入一个数或者选一个，然后点一下某一位把它翻转。',
    'bits': '比特',
    'sign': '符号位',
    'sign bit': '符号位',
    'exponent ({n} bits) = {v}': '指数位（{n} 位）= {v}',
    'exponent bit {k}': '指数位第 {k} 位',
    'mantissa ({n} bits) = {v}': '尾数（{n} 位）= {v}',
    'mantissa bit {k}': '尾数第 {k} 位',
    'exponent all 0s (a tiny “subnormal” number):': '指数位全是 0（一个极小的“次正规数”）：',
    'exponent all 1s:': '指数位全是 1：',
    'largest': '最大的数',
    'gap after 1': '1 之后的间隔',
    'smallest normal': '最小的正规数',
    'numbers in [1, 2)': '[1, 2) 里有几个数',
    'format': '格式',
    'number': '数',
    'number to store': '要存的数',
    'these bits mean {v} in {fmt}': '这些比特在 {fmt} 里表示 {v}',
    'too big or too small for this format': '对这个格式来说太大或太小',
    'stored exactly': '存得一点不差',
    'off by {e}': '差了 {e}',
    'sign: 0 is +, 1 is −': '符号位：0 是 +，1 是 −',
    'exponent: which power of 2': '指数位：2 的几次幂',
    'mantissa: where between that power and the next': '尾数：落在这个幂和下一个幂之间的哪里',
  })

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

<LabFrame title={t('What the bits store')} hint={t('Type a number or pick one, then tap a bit to flip it.')} onreset={reset} resetDisabled={!changed}>
  <div class="bits" aria-label={t('bits')}>
    <div class="grp">
      <div class="glab s">{t('sign')}</div>
      <div class="cells">
        <button class="bit s" class:one={bits.sign} aria-pressed={!!bits.sign} aria-label={t('sign bit')} onclick={() => flip('sign', 0)}>{bits.sign}</button>
      </div>
    </div>
    <div class="grp">
      <div class="glab e">{t('exponent ({n} bits) = {v}', { n: F.E, v: bits.exp })}</div>
      <div class="cells">
        {#each expBits as b, k}
          <button class="bit e" class:one={b} aria-pressed={!!b} aria-label={t('exponent bit {k}', { k })} onclick={() => flip('exp', k)}>{b}</button>
        {/each}
      </div>
    </div>
    <div class="grp wide">
      <div class="glab m">{t('mantissa ({n} bits) = {v}', { n: F.M, v: bits.mant })}</div>
      <div class="cells">
        {#each mantBits as b, k}
          <button class="bit m" class:one={b} aria-pressed={!!b} aria-label={t('mantissa bit {k}', { k })} onclick={() => flip('mant', k)}>{b}</button>
        {/each}
      </div>
    </div>
  </div>

  <div class="dec">
    {#if special === 'normal'}
      (−1)<sup>{bits.sign}</sup> × (1 + {bits.mant}/{2 ** F.M}) × 2<sup>{bits.exp} − {info.bias}</sup> = <b>{full(value)}</b>
    {:else if special === 'sub'}
      {t('exponent all 0s (a tiny “subnormal” number):')} (−1)<sup>{bits.sign}</sup> × {bits.mant}/{2 ** F.M} × 2<sup>{1 - info.bias}</sup> = <b>{full(value)}</b>
    {:else}
      {t('exponent all 1s:')} <b class="bad">{special === 'inf' ? (bits.sign ? '−inf' : 'inf') : 'nan'}</b>
    {/if}
  </div>

  <table class="facts">
    <tbody>
      <tr><th>{t('largest')}</th><td>{show(info.largest, 5)}</td><th>{t('gap after 1')}</th><td>{show(info.gapAfter1, 3)}</td></tr>
      <tr><th>{t('smallest normal')}</th><td>{show(info.smallestNormal, 3)}</td><th>{t('numbers in [1, 2)')}</th><td>{info.perOctave}</td></tr>
    </tbody>
  </table>

  {#snippet controls()}
    <div class="ctl">
      <div class="fmts" role="group" aria-label={t('format')}>
        {#each Object.keys(FORMATS) as f}
          <button class="lab-btn fmt" class:on={fmt === f} aria-pressed={fmt === f} onclick={() => setFmt(f as Fmt)}>{f}</button>
        {/each}
      </div>
      <label class="num">{t('number')} <input type="text" inputmode="decimal" bind:value={text} oninput={onText} aria-label={t('number to store')} /></label>
      <div class="presets">
        {#each PRESETS as [p, label]}
          <button class="lab-btn ghost" onclick={() => { text = String(p); store(p) }}>{label}</button>
        {/each}
      </div>
    </div>
  {/snippet}

  {#snippet readout()}
    {#if typed === null}
      {t('these bits mean {v} in {fmt}', { v: full(value), fmt })}
    {:else if err === null}
      {show(typed, 6)} in {fmt} → <b class="bad">{full(value)}</b>: {t('too big or too small for this format')}
    {:else if err === 0}
      {show(typed, 6)} in {fmt} → <b>{full(value)}</b>, {t('stored exactly')}
    {:else}
      {show(typed, 6)} in {fmt} → <b>{full(value)}</b>, {t('off by {e}', { e: show(err, 2) })}
    {/if}
  {/snippet}

  {#snippet legend()}
    <span class="key"><i class="k s"></i>{t('sign: 0 is +, 1 is −')}</span>
    <span class="key"><i class="k e"></i>{t('exponent: which power of 2')}</span>
    <span class="key"><i class="k m"></i>{t('mantissa: where between that power and the next')}</span>
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
