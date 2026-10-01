<script lang="ts">
  /**
   * The same 2→6→1 XOR network, written in numpy (left) and PyTorch (right).
   * Point at, tap or focus a line: the matching lines on both sides light up and the panel says what changed.
   */
  import LabFrame from './LabFrame.svelte'

  type Line = { code: string; g?: string }
  const NP: Line[] = [
    { code: 'X = np.array([[0,0],[0,1],[1,0],[1,1]], dtype=float)', g: 'data' },
    { code: 'y = np.array([[0],[1],[1],[0]], dtype=float)', g: 'data' },
    { code: 'W1 = rng.normal(0, 1, (2, 6)); b1 = np.zeros(6)', g: 'params' },
    { code: 'W2 = rng.normal(0, 1, (6, 1)); b2 = np.zeros(1)', g: 'params' },
    { code: '' },
    { code: 'for step in range(2000):', g: 'loop' },
    { code: '    a1 = np.tanh(X @ W1 + b1)', g: 'forward' },
    { code: '    p = sigmoid(a1 @ W2 + b2)', g: 'forward' },
    { code: '    loss = -np.mean(y*np.log(p) + (1-y)*np.log(1-p))', g: 'loss' },
    { code: '    # nothing to clear: new gradient arrays every step', g: 'zero' },
    { code: '    dz2 = (p - y) / len(X)', g: 'backward' },
    { code: '    dW2 = a1.T @ dz2;  db2 = dz2.sum(0)', g: 'backward' },
    { code: '    dz1 = (dz2 @ W2.T) * (1 - a1**2)', g: 'backward' },
    { code: '    dW1 = X.T @ dz1;   db1 = dz1.sum(0)', g: 'backward' },
    { code: '    for P, G in [(W1,dW1), (b1,db1), (W2,dW2), (b2,db2)]:', g: 'step' },
    { code: '        P -= lr * G', g: 'step' },
  ]
  const PT: Line[] = [
    { code: 'X = torch.tensor([[0,0],[0,1],[1,0],[1,1]], dtype=torch.float32)', g: 'data' },
    { code: 'y = torch.tensor([[0],[1],[1],[0]], dtype=torch.float32)', g: 'data' },
    { code: 'model = nn.Sequential(nn.Linear(2, 6), nn.Tanh(), nn.Linear(6, 1))', g: 'params' },
    { code: 'opt = torch.optim.SGD(model.parameters(), lr=lr)', g: 'params' },
    { code: '' },
    { code: 'for step in range(2000):', g: 'loop' },
    { code: '    logits = model(X)', g: 'forward' },
    { code: '    loss = F.binary_cross_entropy_with_logits(logits, y)', g: 'loss' },
    { code: '    opt.zero_grad()', g: 'zero' },
    { code: '    loss.backward()', g: 'backward' },
    { code: '    opt.step()', g: 'step' },
  ]
  const SAY: Record<string, { title: string; text: string; who: string }> = {
    data: { title: 'Data', who: 'same',
      text: 'The same numbers. A tensor is an array that can also live on a GPU and remember how it was computed. float32 is the usual type for training. NumPy defaults to float64.' },
    params: { title: 'Parameters', who: 'PyTorch helps',
      text: 'In NumPy you create every weight array yourself. nn.Linear creates a weight and a bias and registers them, so model.parameters() can hand every one of them to the optimizer.' },
    loop: { title: 'The loop', who: 'still your job',
      text: 'PyTorch does not run the loop for you. How many steps, which data, when to stop: you decide all of these.' },
    forward: { title: 'Forward', who: 'same math',
      text: 'The same matrix multiplications. nn.Sequential runs the layers in order. While it computes, PyTorch also records every operation: that record is what backward walks through.' },
    loss: { title: 'Loss', who: 'same math',
      text: 'binary_cross_entropy_with_logits does the sigmoid and the loss together, which stays accurate even for huge scores. The NumPy side computes p first, then the loss.' },
    backward: { title: 'Backward', who: 'PyTorch does this',
      text: 'This is the part PyTorch does for you: four lines of chain rule become loss.backward(). It walks the recorded operations in reverse and fills .grad on every parameter, with the same numbers your hand-written lines give.' },
    step: { title: 'Update', who: 'PyTorch helps',
      text: 'opt.step() does P -= lr * P.grad for every parameter it was given. Fancier optimizers change only this line.' },
    zero: { title: 'Clearing gradients', who: 'still your job',
      text: 'loss.backward() adds into .grad. It never clears it. So every step must start with opt.zero_grad(), or the old gradients are added to the new ones. In NumPy this problem never happens, because each step makes new gradient arrays.' },
  }
  const SEL0 = 'backward'
  let sel = $state<string>(SEL0)
  // leading spaces become padding, so a wrapped line continues 2 characters to the right of where it starts
  const indent = (code: string) => code.length - code.trimStart().length
  const count = (lines: Line[], g: string) => lines.filter((l) => l.g === g).length
  const COLS: [string, Line[]][] = [['NumPy: you write everything', NP], ['PyTorch', PT]]
</script>

<LabFrame
  title="One network, written twice"
  hint="Point at or tap a line, or pick a part below. The matching lines are highlighted on both sides."
  onreset={() => (sel = SEL0)}
  resetDisabled={sel === SEL0}
>
  <div class="cols">
    {#each COLS as [title, lines]}
      <div class="col">
        <div class="ttl">{title}</div>
        <div class="code" role="group" aria-label={title}>
          {#each lines as l}
            <button type="button" class="ln" class:on={l.g && l.g === sel} class:blank={!l.g}
              onpointerenter={() => l.g && (sel = l.g)} onfocus={() => l.g && (sel = l.g)} onclick={() => l.g && (sel = l.g)}
              tabindex={l.g ? 0 : -1}
              style="padding-left: calc(0.6rem + {indent(l.code) + 2}ch); text-indent: -2ch">{(l.code || ' ').trimStart() || ' '}</button>
          {/each}
        </div>
      </div>
    {/each}
  </div>
  {#if sel}
    <div class="say">
      <div class="h"><b>{SAY[sel].title}</b> <span class="who" class:yours={SAY[sel].who === 'still your job'}>{SAY[sel].who}</span></div>
      <p>{SAY[sel].text}</p>
    </div>
  {/if}

  {#snippet controls()}
    <div class="chips" role="group" aria-label="Parts of the training script">
      {#each ['data', 'params', 'loop', 'forward', 'loss', 'zero', 'backward', 'step'] as g}
        <button type="button" aria-pressed={sel === g} class="lab-btn chip" class:on={sel === g} class:yours={SAY[g].who === 'still your job'}
          onclick={() => (sel = g)}>{SAY[g].title}</button>
      {/each}
    </div>
  {/snippet}

  {#snippet readout()}
    {SAY[sel].title}: NumPy {count(NP, sel)} line{count(NP, sel) === 1 ? '' : 's'} → PyTorch {count(PT, sel)} line{count(PT, sel) === 1 ? '' : 's'}
  {/snippet}

  {#snippet legend()}
    <span><i class="sw dash"></i>dashed: still your job in PyTorch</span>
    <span><i class="sw on"></i>the part you picked</span>
  {/snippet}
</LabFrame>

<style>
  .cols { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 0.8rem; }
  @media (max-width: 760px) { .cols { grid-template-columns: minmax(0, 1fr); } }
  .col { min-width: 0; }
  .ttl { font-size: 0.78rem; color: var(--dim); font-family: var(--mono); margin-bottom: 0.25rem; }
  .code { background: var(--bg); border: 1px solid var(--line); border-radius: 4px; padding: 0.4rem 0; }
  /* long lines wrap with a hanging indent, so every character is visible without sideways scrolling */
  .ln { display: block; width: 100%; text-align: left; white-space: pre-wrap; overflow-wrap: anywhere; font: inherit; font-family: var(--mono); font-size: 0.76rem;
    line-height: 1.6; padding: 0.1rem 0.6rem; border: 0; border-left: 3px solid transparent; background: none; color: var(--fg); cursor: pointer;
    transition: background 0.15s; }
  .ln.on { border-left-color: var(--accent); background: var(--highlight); }
  .ln.blank { cursor: default; }
  .ln:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
  @media (prefers-reduced-motion: reduce) { .ln { transition: none; } }
  .chips { display: flex; flex-wrap: wrap; gap: 0.35rem; }
  .chip { font-size: 0.8rem; border-radius: 999px; padding: 0.3rem 0.8rem; color: var(--dim); }
  .chip.yours { border-style: dashed; }
  .chip.on { border-color: var(--accent); color: var(--accent); background: var(--highlight); }
  .say { margin-top: 0.8rem; border-left: 3px solid var(--accent); padding: 0.3rem 0.8rem; }
  .say p { margin: 0.3rem 0 0; font-size: 0.9rem; }
  .h { display: flex; flex-wrap: wrap; gap: 0.3rem 0.7rem; align-items: baseline; }
  .who { font-size: 0.76rem; font-family: var(--mono); color: var(--dim); border: 1px solid var(--line); border-radius: 999px; padding: 0 0.5rem; }
  .who.yours { border-style: dashed; border-color: var(--field); color: var(--fg); }
  .sw { display: inline-block; width: 1.1rem; height: 0.7rem; border-radius: 999px; margin-right: 0.35rem; vertical-align: -0.05rem; }
  .sw.dash { border: 1.5px dashed var(--field); }
  .sw.on { border-radius: 2px; width: 0.9rem; background: var(--highlight); border-left: 3px solid var(--accent); }
</style>
