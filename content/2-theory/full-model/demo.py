"""
Level 17 · Putting it together

A small decoder-only Transformer learns to read numbers aloud. Each number is ONE sequence:

    4 2 7 = four hundred twenty seven <eos>

The model reads the digits and "=", then writes the words one at a time, and we print every step.

Run:  python demo.py      (needs torch; well under a minute on a laptop CPU)
"""
import math
import random
import time

import torch
import torch.nn as nn
import torch.nn.functional as F

torch.set_printoptions(precision=2, sci_mode=False)

# ---------------------------------------------------------------------------
# 1. Data: one sequence per number, digits then "=" then the words
# ---------------------------------------------------------------------------
ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen "
        "fourteen fifteen sixteen seventeen eighteen nineteen").split()
TENS = "twenty thirty forty fifty sixty seventy eighty ninety".split()


def words(n):
    """427 → ['four', 'hundred', 'twenty', 'seven']"""
    if n < 20:
        return [ONES[n]]
    if n < 100:
        return [TENS[n // 10 - 2]] + ([ONES[n % 10]] if n % 10 else [])
    return [ONES[n // 100], "hundred"] + (words(n % 100) if n % 100 else [])


PAD, EOS = 0, 1
VOCAB = ["<pad>", "<eos>"] + list("0123456789") + ["="] + ONES + TENS + ["hundred"]   # 42 tokens
ID = {t: i for i, t in enumerate(VOCAB)}
EQ = ID["="]
V = len(VOCAB)
MAX_X = 8            # longest x: 3 digits, "=", 4 words  (the full sequence has 9 tokens with <eos>)


def sequence(n):
    """427 → [6, 4, 9, 12, ..., 1]: the digits, "=", the words, <eos>."""
    return [ID[c] for c in str(n)] + [EQ] + [ID[w] for w in words(n)] + [EOS]


def make_xy(seq):
    """x = seq[:-1], y = seq[1:]. In y, only the answer counts: targets before the position of "=" in x
    (the digits and "=" themselves) are set to PAD, which the loss ignores."""
    x, y = seq[:-1], seq[1:]
    eq = x.index(EQ)
    y = [PAD if i < eq else t for i, t in enumerate(y)]
    return x, y


def tensors(nums):
    """A batch: x and y padded with PAD to the longest x in this batch."""
    xs, ys = zip(*(make_xy(sequence(n)) for n in nums))
    L = max(len(x) for x in xs)
    pad = lambda r: r + [PAD] * (L - len(r))
    return torch.tensor([pad(x) for x in xs]), torch.tensor([pad(y) for y in ys])


def split(seed=0):
    nums = list(range(1000))
    random.Random(seed).shuffle(nums)
    return nums[:900], nums[900:]        # 100 numbers are never trained on


# ---------------------------------------------------------------------------
# 2. The model: decoder blocks only (pre-norm), like level 21 but with LayerNorm
# ---------------------------------------------------------------------------
def causal_mask(L):
    return torch.triu(torch.ones(L, L, dtype=torch.bool), diagonal=1)   # True = not allowed to look


def pad_mask(ids):
    return (ids == PAD).unsqueeze(1)                                     # (B, 1, L): don't look at PAD keys


class MultiHead(nn.Module):
    def __init__(self, d, heads):
        super().__init__()
        self.h, self.dk = heads, d // heads
        self.Wq = nn.Linear(d, d, bias=False)
        self.Wk = nn.Linear(d, d, bias=False)
        self.Wv = nn.Linear(d, d, bias=False)
        self.Wo = nn.Linear(d, d)
        self.last = None                       # attention weights, kept only for the picture

    def forward(self, x, mask):
        B, L, d = x.shape
        q = self.Wq(x).view(B, L, self.h, self.dk).transpose(1, 2)     # (B, h, L, d_k)
        k = self.Wk(x).view(B, L, self.h, self.dk).transpose(1, 2)
        v = self.Wv(x).view(B, L, self.h, self.dk).transpose(1, 2)
        scores = q @ k.transpose(-2, -1) / math.sqrt(self.dk)          # (B, h, L, L)
        scores = scores.masked_fill(mask.unsqueeze(1), float("-inf"))
        w = F.softmax(scores, dim=-1)
        self.last = w.detach()
        return self.Wo((w @ v).transpose(1, 2).reshape(B, L, d))


class Block(nn.Module):
    def __init__(self, d, h, d_ff):
        super().__init__()
        self.n1, self.attn = nn.LayerNorm(d), MultiHead(d, h)
        self.n2, self.ff = nn.LayerNorm(d), nn.Sequential(nn.Linear(d, d_ff), nn.ReLU(), nn.Linear(d_ff, d))

    def forward(self, x, m):
        x = x + self.attn(self.n1(x), m)      # norm first, then attention, then add back
        return x + self.ff(self.n2(x))        # norm first, then the FFN, then add back


class Decoder(nn.Module):
    def __init__(self, d=64, heads=4, layers=2, d_ff=128, tok_std=None):
        super().__init__()
        self.d = d
        self.tok = nn.Embedding(V, d)
        # std 1/√d, so tok × √d has numbers of size about 1, like the PE
        nn.init.normal_(self.tok.weight, std=d ** -0.5 if tok_std is None else tok_std)
        pos = torch.arange(16).unsqueeze(1)
        div = torch.exp(-math.log(10000.0) * torch.arange(0, d, 2) / d)
        pe = torch.zeros(16, d)
        pe[:, 0::2], pe[:, 1::2] = torch.sin(pos * div), torch.cos(pos * div)
        self.register_buffer("pe", pe)                       # fixed, not trained
        self.blocks = nn.ModuleList(Block(d, heads, d_ff) for _ in range(layers))
        self.norm = nn.LayerNorm(d)
        self.head = nn.Linear(d, V)

    def hidden(self, ids):
        """ids (B, L) → the final-norm output (B, L, d): the rows the output layer reads."""
        x = self.tok(ids) * math.sqrt(self.d) + self.pe[: ids.size(1)]
        m = causal_mask(ids.size(1)) | pad_mask(ids)          # (B, L, L)
        for b in self.blocks:
            x = b(x, m)
        return self.norm(x)

    def forward(self, ids):
        return self.head(self.hidden(ids))                    # (B, L, 42)


def count(m):
    return sum(p.numel() for p in m.parameters())


# ---------------------------------------------------------------------------
# 3. Training: batch → forward → loss on the answer only → backward → update
# ---------------------------------------------------------------------------
EPOCHS, LR = 60, 1e-3


def train(epochs=EPOCHS, seed=0, on_epoch=None, tok_std=None):
    torch.manual_seed(seed)
    rng = random.Random(seed)
    train_nums, test_nums = split()
    model = Decoder(tok_std=tok_std)
    loss_fn = nn.CrossEntropyLoss(ignore_index=PAD)          # PAD targets (padding, digits, "=") don't count
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    for ep in range(1, epochs + 1):
        rng.shuffle(train_nums)
        total, n = 0.0, 0
        for i in range(0, len(train_nums), 64):
            x, y = tensors(train_nums[i:i + 64])                    # 1. a batch (B, L)
            logits = model(x)                                       # 2. forward (B, L, 42)
            loss = loss_fn(logits.reshape(-1, V), y.reshape(-1))    # 3. loss on (B*L, 42) vs (B*L,)
            opt.zero_grad()
            loss.backward()                                         # 4. backward
            opt.step()                                              #    and update
            total, n = total + loss.item(), n + 1
        if on_epoch:
            on_epoch(ep, total / n, model, test_nums)
    return model, test_nums


@torch.no_grad()
def read_aloud(model, n, steps=None):
    """Greedy decoding: feed the digits and "=", append the top token until <eos>.
    Returns the words, and (if steps is a list) a record of every step."""
    model.eval()
    ids = [ID[c] for c in str(n)] + [EQ]
    while len(ids) < MAX_X + 1:
        h = model.hidden(torch.tensor([ids]))                   # (1, len(ids), 64)
        last = h[0, -1]                                          # only the last row predicts the next token
        logits = model.head(last)                                # (42,)
        nxt = int(logits.argmax())
        if steps is not None:
            att = model.blocks[-1].attn.last[0].mean(0)[-1]      # last layer, heads averaged, last row
            steps.append({"input": [VOCAB[t] for t in ids], "last": last, "logits": logits,
                          "pick": VOCAB[nxt], "att": att})
        ids.append(nxt)
        if nxt == EOS:
            break
    model.train()
    answer = ids[len(str(n)) + 1:]
    return [VOCAB[t] for t in answer if t != EOS]


def accuracy(model, nums):
    return sum(read_aloud(model, n) == words(n) for n in nums) / len(nums)


if __name__ == "__main__":
    t0 = time.time()
    print("vocab size V =", V)
    print("  ids 0-1:", VOCAB[:2], " ids 2-11: digits  id 12: '='  ids 13-41:", VOCAB[13], "...", VOCAB[-1])

    seq = sequence(427)
    print("\n427 as one sequence:", [VOCAB[i] for i in seq], f"({len(seq)} tokens)")
    print("  ids:", seq)
    x, y = make_xy(seq)
    print("x = seq[:-1]:", x, [VOCAB[i] for i in x])
    print("y = seq[1:] :", seq[1:], [VOCAB[i] for i in seq[1:]])
    print("which targets count in the loss (target set to PAD = ignored):")
    for i, (xi, t, ym) in enumerate(zip(x, seq[1:], y)):
        print(f"  pos {i}: input {VOCAB[xi]:>8s} → target {VOCAB[t]:>8s}   {'counts' if ym != PAD else 'ignored'}")
    print("y for the loss:", y, f"→ {sum(t != PAD for t in y)} of {len(y)} positions count")

    torch.manual_seed(0)
    m = Decoder()
    blk = m.blocks[0]
    print("\nparameters (d_model=64, heads=4, layers=2, d_ff=128):")
    rows = [("token embedding (42 × 64)", count(m.tok)),
            ("one attention block (W_Q, W_K, W_V, W_O + bias)", count(blk.attn)),
            ("one FFN (64 → 128 → 64)", count(blk.ff)),
            ("one LayerNorm", count(blk.n1)),
            ("one block (attention + FFN + 2 LayerNorms)", count(blk)),
            ("2 blocks", 2 * count(blk)),
            ("final LayerNorm", count(m.norm)),
            ("output layer (64 × 42 + 42)", count(m.head)),
            ("position table (fixed, not trained)", 0)]
    for name, c in rows:
        print(f"  {name:50s} {c:7,d}")
    print(f"  {'TOTAL':50s} {count(m):7,d}")
    assert count(m) == count(m.tok) + 2 * count(blk) + count(m.norm) + count(m.head)

    with torch.no_grad():
        e = m.tok.weight * math.sqrt(m.d)
        print(f"  length of one row: token × √64 ≈ {e.norm(dim=1).mean():.2f}, position row = {m.pe[0].norm():.2f}"
              "  (similar sizes, so the model can see both)")

    xb, yb = tensors(list(range(64)))
    logits = m(xb)
    B, L = xb.shape
    print("\nbatch of the numbers 0..63:")
    print("  x", tuple(xb.shape), " y", tuple(yb.shape), " (longest x in this batch:", L, "tokens, e.g. 23 = twenty three)")
    print("  token embedding × √64 + PE:", (B, L, 64), " each block keeps it:", (B, L, 64))
    print("  attention scores per block (B, heads, L, L):", tuple(m.blocks[0].attn.last.shape))
    print("  logits", tuple(logits.shape), " → for the loss", tuple(logits.reshape(-1, V).shape), "vs targets", tuple(yb.reshape(-1).shape))
    counted = int((yb != PAD).sum())
    xpad = int((xb == PAD).sum())
    print(f"  target positions B×L = {B}×{L} = {B * L}; counted in the loss (answer words + <eos>): {counted}")
    print(f"  ignored: {B * L - counted} (digit/'=' targets: {int(((yb == PAD) & (xb != PAD)).sum())}, padding: {xpad})")

    def log(ep, loss, model, test):
        if ep in (1, 2, 5, 10, 20, 30, 40, 50, 60):
            print(f"epoch {ep:2d}  loss {loss:.3f}  unseen numbers right: {accuracy(model, test) * 100:.0f}%", flush=True)

    print(f"\ntraining on 900 numbers ({EPOCHS} epochs, Adam lr {LR}), testing on 100 it never saw:")
    t1 = time.time()
    model, test = train(on_epoch=log)
    print(f"training took {time.time() - t1:.1f} s")
    missed = [n for n in test if read_aloud(model, n) != words(n)]
    print("held-out numbers it gets wrong:", [(n, " ".join(read_aloud(model, n))) for n in missed] or "none")

    # the Stuck on the √d_model factor: start the token table at size 1 instead of 1/√64
    print("\ntoken table started with std 1 instead of 1/√64 = 0.125:")
    with torch.no_grad():
        torch.manual_seed(0)
        m1 = Decoder(tok_std=1.0)
        r1 = (m1.tok.weight * 8).norm(dim=1).mean()
    print(f"  length of one row at the start: token × √64 ≈ {r1:.1f}, position row = {m1.pe[0].norm():.2f}"
          f"  ({r1 / m1.pe[0].norm():.0f} times longer)")
    for seed in (0, 1, 2):
        big, test_b = train(seed=seed, tok_std=1.0)
        wrong = [(n, " ".join(read_aloud(big, n))) for n in test_b if read_aloud(big, n) != words(n)]
        print(f"  seed {seed}: unseen numbers right {accuracy(big, test_b) * 100:.0f}%   e.g. wrong: {wrong[:3]}", flush=True)
    for seed in (1, 2):
        small, test_s = train(seed=seed)
        print(f"  for comparison, std 1/√64, seed {seed}: {accuracy(small, test_s) * 100:.0f}%", flush=True)

    for n in ([427] if 427 in test else []) + test[:2]:
        steps = []
        out = read_aloud(model, n, steps)
        print(f"\nreading {n} aloud, one step at a time:")
        for k, st in enumerate(steps):
            top = st["logits"].topk(3)
            best = ", ".join(f"{VOCAB[i]} {v:.1f}" for v, i in zip(top.values.tolist(), top.indices.tolist()))
            print(f" step {k + 1}: input {st['input']} ({len(st['input'])} rows)")
            row = ", ".join(f"{v:.2f}" for v in st["last"][:4].tolist())
            att = ", ".join(f"{t}:{a:.2f}" for t, a in zip(st["input"], st["att"].tolist()))
            print(f"         last row (first 4 of 64): [{row}, ...]")
            print(f"         attention of the last row (last layer, heads averaged): {att}")
            print(f"         top scores: {best}  → pick '{st['pick']}'")
        print("answer:", " ".join(out), " (right)" if out == words(n) else f" (should be {' '.join(words(n))})")

    # the page's small questions, with their own numbers
    print("\n905 as one sequence:", sequence_tokens := [*"905", "=", *words(905), "<eos>"], f"→ {len(sequence_tokens)} tokens")
    so_far = [*"742", "=", "seven", "hundred", "forty"]
    print(f"742 after 'seven hundred forty': input {so_far} → {len(so_far)} rows")
    print("batch of 64, x (64, 8), 4 heads → attention scores", (64, 4, 8, 8), "→ logits", (64, 8, len(VOCAB)))
    print("one FFN, 64 → 128 → 64:", 64 * 128 + 128, "+", 128 * 64 + 64, "=", 64 * 128 + 128 + 128 * 64 + 64)
    print("(64, 5, 42) → reshape(-1, 42) →", tuple(torch.zeros(64, 5, 42).reshape(-1, 42).shape))

    # the greedy loop on the stand-in model of the code exercise: 0 <pad>, 1 <eos>, 2 "4", 3 "=", 4 four, 5 hundred
    T = torch.tensor([[0., 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 2, 0, 0],
                      [0, 0, 0, 0, 2, 1], [0, 1, 0, 0, 0, 3], [0, 2, 0, 0, 1, 0]])

    def greedy_decode(model, prompt, eos=1, max_new=6):
        ids = list(prompt)
        for step in range(max_new):
            scores = model(ids)
            nxt = int(scores[-1].argmax())
            ids.append(nxt)
            if nxt == eos:
                break
        return ids

    print("\ngreedy loop, stand-in model, prompt [2, 3]:", greedy_decode(lambda ids: T[ids], [2, 3]))
    T2 = T.clone(); T2[5] = torch.tensor([0., 0, 0, 0, 5, 0])
    print("never <eos>, max_new=4:", greedy_decode(lambda ids: T2[ids], [2, 3], max_new=4))
    print("max_new=2:", greedy_decode(lambda ids: T[ids], [2, 3], max_new=2))

    # the loss that skips PAD targets, on the code exercise's numbers
    lg = torch.tensor([[2.0, 1.0, 0.0], [0.0, 3.0, 0.0], [1.0, 1.0, 1.0]])
    tg = torch.tensor([0, 1, 0])
    nll = -F.log_softmax(lg, -1)[torch.arange(3), tg]
    keep = tg != 0
    print("\nmasked loss: per row", [round(v, 3) for v in nll.tolist()], "keep", keep.tolist(),
          "→ mean over kept rows", round(nll[keep].mean().item(), 4), " (all rows:", round(nll.mean().item(), 4), ")")
    print(f"\ntotal run time {time.time() - t0:.1f} s")
