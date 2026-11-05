<script lang="ts">
  /**
   * The same 2→6→1 XOR network, written in numpy (left) and PyTorch (right).
   * Point at, tap or focus a line: the matching lines on both sides light up and the panel says what changed.
   */
  import LabFrame from './LabFrame.svelte'
  import { provideLang, useT } from '@lib/i18nSvelte'
  import type { Lang } from '@lib/i18n'

  let { lang = 'en' }: { lang?: Lang } = $props()
  provideLang(lang)
  const t = useT({
    '    # nothing to clear: new gradient arrays every step': '    # 不用清零：每一步都是新的梯度数组',
    'Data': '数据',
    'The same numbers. A tensor is an array that can also live on a GPU and remember how it was computed. float32 is the usual type for training. NumPy defaults to float64.': '同样的数。张量是一种数组，它还可以放在 GPU 上，并记住自己是怎么算出来的。训练时通常用 float32。NumPy 默认用 float64。',
    'Parameters': '参数',
    'In NumPy you create every weight array yourself. nn.Linear creates a weight and a bias and registers them, so model.parameters() can hand every one of them to the optimizer.': '在 NumPy 里，每个权重数组都要你自己创建。nn.Linear 会创建一个权重和一个偏置，并把它们登记下来，这样 model.parameters() 就能把它们全部交给优化器。',
    'The loop': '循环',
    'PyTorch does not run the loop for you. How many steps, which data, when to stop: you decide all of these.': 'PyTorch 不会替你跑循环。走多少步、用哪些数据、什么时候停：这些都由你决定。',
    'Forward': '前向传播',
    'The same matrix multiplications. nn.Sequential runs the layers in order. While it computes, PyTorch also records every operation: that record is what backward walks through.': '同样的矩阵乘法。nn.Sequential 按顺序运行各层。计算的同时，PyTorch 还记下每一个运算：backward 走的就是这份记录。',
    'Loss': '损失',
    'binary_cross_entropy_with_logits does the sigmoid and the loss together, which stays accurate even for huge scores. The NumPy side computes p first, then the loss.': 'binary_cross_entropy_with_logits 把 sigmoid 和损失一起算，分数非常大时也依然准确。NumPy 这边先算 p，再算损失。',
    'Backward': '反向传播',
    'This is the part PyTorch does for you: four lines of chain rule become loss.backward(). It walks the recorded operations in reverse and fills .grad on every parameter, with the same numbers your hand-written lines give.': '这就是 PyTorch 替你做的部分：四行链式法则变成了 loss.backward()。它倒着走过记下的运算，把每个参数的 .grad 填好，得到的数和你手写的那几行完全一样。',
    'Update': '更新',
    'opt.step() does P -= lr * P.grad for every parameter it was given. Fancier optimizers change only this line.': 'opt.step() 对交给它的每个参数做 P -= lr * P.grad。更高级的优化器只改这一行。',
    'Clearing gradients': '清零梯度',
    'loss.backward() adds into .grad. It never clears it. So every step must start with opt.zero_grad(), or the old gradients are added to the new ones. In NumPy this problem never happens, because each step makes new gradient arrays.': 'loss.backward() 把梯度加进 .grad，从不清零。所以每一步都必须先调用 opt.zero_grad()，否则旧梯度会加到新梯度上。在 NumPy 里不会有这个问题，因为每一步都会生成新的梯度数组。',
    'same': '相同',
    'PyTorch helps': 'PyTorch 帮你做',
    'still your job': '仍然要你来做',
    'same math': '数学相同',
    'PyTorch does this': 'PyTorch 全包了',
    'NumPy: you write everything': 'NumPy：每一行都要你写',
    'One network, written twice': '同一个网络，写两遍',
    'Point at or tap a line, or pick a part below. The matching lines are highlighted on both sides.': '把鼠标指向某一行（手机上点一下），或在下面选一个部分。两边对应的行都会高亮。',
    'Parts of the training script': '训练脚本的各个部分',
    'line': '行',
    'lines': '行',
    '{title}: NumPy {a} {la} → PyTorch {b} {lb}': '{title}：NumPy {a} {la} → PyTorch {b} {lb}',
    'dashed: still your job in PyTorch': '虚线：用 PyTorch 时仍然要你来做',
    'the part you picked': '你选中的部分',
  })

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
  const COLS: [string, Line[]][] = [[t('NumPy: you write everything'), NP], ['PyTorch', PT]]
  const lineWord = (n: number) => t(n === 1 ? 'line' : 'lines')
</script>

<LabFrame
  title={t('One network, written twice')}
  hint={t('Point at or tap a line, or pick a part below. The matching lines are highlighted on both sides.')}
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
              style="padding-left: calc(0.6rem + {indent(l.code) + 2}ch); text-indent: -2ch">{(t(l.code) || ' ').trimStart() || ' '}</button>
          {/each}
        </div>
      </div>
    {/each}
  </div>
  {#if sel}
    <div class="say">
      <div class="h"><b>{t(SAY[sel].title)}</b> <span class="who" class:yours={SAY[sel].who === 'still your job'}>{t(SAY[sel].who)}</span></div>
      <p>{t(SAY[sel].text)}</p>
    </div>
  {/if}

  {#snippet controls()}
    <div class="chips" role="group" aria-label={t('Parts of the training script')}>
      {#each ['data', 'params', 'loop', 'forward', 'loss', 'zero', 'backward', 'step'] as g}
        <button type="button" aria-pressed={sel === g} class="lab-btn chip" class:on={sel === g} class:yours={SAY[g].who === 'still your job'}
          onclick={() => (sel = g)}>{t(SAY[g].title)}</button>
      {/each}
    </div>
  {/snippet}

  {#snippet readout()}
    {t('{title}: NumPy {a} {la} → PyTorch {b} {lb}', { title: t(SAY[sel].title), a: count(NP, sel), la: lineWord(count(NP, sel)), b: count(PT, sel), lb: lineWord(count(PT, sel)) })}
  {/snippet}

  {#snippet legend()}
    <span><i class="sw dash"></i>{t('dashed: still your job in PyTorch')}</span>
    <span><i class="sw on"></i>{t('the part you picked')}</span>
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
