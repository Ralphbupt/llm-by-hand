"""
Level 21 · Write your own GPT  (reference solution, read it only after you tried)

A decoder-only Transformer learns two-digit addition by predicting the next character:

    <bos>23+58=81<eos>

Run:
    python demo.py            40 epochs, about a minute on a laptop CPU
    python demo.py --full     150 epochs, the run recorded for the page
    python demo.py --all-loss count the loss on every position, not only the answer

Needs torch.
"""
import argparse
import copy
import math
import random
import time

import torch
import torch.nn as nn
import torch.nn.functional as F

# ---------------------------------------------------------------------------
# 1. Data: characters → ids, shifted by one
# ---------------------------------------------------------------------------
PAD, BOS, EOS = 0, 1, 2
ITOS = ["<pad>", "<bos>", "<eos>"] + list("0123456789") + ["+", "="]   # 15 tokens
STOI = {c: i for i, c in enumerate(ITOS)}
VOCAB = len(ITOS)
MAXLEN = 11            # <bos> 99+99=198 <eos>  → 11 tokens
IGNORE = -100          # cross_entropy skips targets equal to this


def encode(a, b):
    """(23, 58) → [bos, 2, 3, +, 5, 8, =, 8, 1, eos, pad]"""
    ids = [BOS] + [STOI[c] for c in f"{a}+{b}={a + b}"] + [EOS]
    return ids + [PAD] * (MAXLEN - len(ids))


def make_xy(ids, answer_only=True):
    """x is the sequence without its last token, y without its first: y[t] is the token after x[t].
    PAD targets are ignored. With answer_only, everything before the answer is ignored too."""
    x, y = ids[:-1], ids[1:]
    y = [IGNORE if t == PAD else t for t in y]
    if answer_only:
        eq = x.index(STOI["="])                      # y[eq] is the first digit of the answer
        y = [IGNORE if t < eq else v for t, v in enumerate(y)]
    return x, y


def split(seed=0):
    pairs = [(a, b) for a in range(100) for b in range(100)]     # 10,000 problems
    random.Random(seed).shuffle(pairs)
    # 8,500 to train on, 500 to pick the best epoch (validation), 1,000 never used for any choice (unseen)
    return pairs[:8500], pairs[8500:9000], pairs[9000:]


def batches(pairs, size, answer_only, rng):
    order = list(range(len(pairs)))
    rng.shuffle(order)                                           # new order every epoch
    for i in range(0, len(order), size):
        xs, ys = zip(*(make_xy(encode(*pairs[j]), answer_only) for j in order[i:i + size]))
        yield torch.tensor(xs), torch.tensor(ys)


# ---------------------------------------------------------------------------
# 2. The model: embeddings + N pre-norm blocks (attention with a causal mask, then FFN) + output layer
#    Two level-16 upgrades: pre-norm (normalize before each sublayer, the residual path stays clean)
#    and RMSNorm instead of LayerNorm.
# ---------------------------------------------------------------------------
def causal_mask(L):
    """True above the diagonal: position t may not look at positions after t."""
    return torch.triu(torch.ones(L, L, dtype=torch.bool), diagonal=1)


class RMSNorm(nn.Module):
    """Divide each row by its root mean square, then multiply by a learned gain (level 19)."""
    def __init__(self, d, eps=1e-6):
        super().__init__()
        self.gain = nn.Parameter(torch.ones(d))
        self.eps = eps

    def forward(self, x):
        rms = torch.sqrt((x * x).mean(-1, keepdim=True) + self.eps)
        return x / rms * self.gain


class Attention(nn.Module):
    def __init__(self, d, heads):
        super().__init__()
        self.h, self.dk = heads, d // heads
        self.qkv = nn.Linear(d, 3 * d)
        self.out = nn.Linear(d, d)

    def forward(self, x):
        B, L, d = x.shape
        q, k, v = self.qkv(x).split(d, dim=-1)
        # (B, L, d) → (B, heads, L, dk): every head works on its own slice
        q, k, v = (t.view(B, L, self.h, self.dk).transpose(1, 2) for t in (q, k, v))
        scores = q @ k.transpose(-2, -1) / math.sqrt(self.dk)        # (B, heads, L, L)
        scores = scores.masked_fill(causal_mask(L).to(x.device), float("-inf"))
        w = F.softmax(scores, dim=-1)
        y = (w @ v).transpose(1, 2).reshape(B, L, d)                 # glue the heads back together
        return self.out(y)


class Block(nn.Module):
    def __init__(self, d, heads, d_ff):
        super().__init__()
        self.norm1, self.attn = RMSNorm(d), Attention(d, heads)
        self.norm2 = RMSNorm(d)
        self.ffn = nn.Sequential(nn.Linear(d, d_ff), nn.ReLU(), nn.Linear(d_ff, d))

    def forward(self, x):
        x = x + self.attn(self.norm1(x))      # pre-norm: normalize, attend, add back
        x = x + self.ffn(self.norm2(x))       # pre-norm: normalize, FFN, add back
        return x


class GPT(nn.Module):
    def __init__(self, d=64, heads=4, layers=2, d_ff=256):
        super().__init__()
        self.tok = nn.Embedding(VOCAB, d)
        self.pos = nn.Embedding(MAXLEN, d)    # learned positions
        self.blocks = nn.ModuleList(Block(d, heads, d_ff) for _ in range(layers))
        self.norm = RMSNorm(d)                # pre-norm models normalize once more at the very end
        self.head = nn.Linear(d, VOCAB)

    def forward(self, x):                     # x: (B, L) ids
        h = self.tok(x) + self.pos(torch.arange(x.size(1), device=x.device))
        for b in self.blocks:
            h = b(h)
        return self.head(self.norm(h))                  # (B, L, 15): at t, a score for every possible next token


# ---------------------------------------------------------------------------
# 3. Generation and evaluation
# ---------------------------------------------------------------------------
@torch.no_grad()
def solve(model, pairs):
    """Greedy: feed <bos>a+b=, append the top token, repeat until <eos>. Returns strings."""
    model.eval()
    out = {}
    by_len = {}
    for p in pairs:                                  # same-length prompts go in one batch
        prompt = [BOS] + [STOI[c] for c in f"{p[0]}+{p[1]}="]
        by_len.setdefault(len(prompt), []).append((p, prompt))
    for items in by_len.values():
        x = torch.tensor([pr for _, pr in items])
        done = torch.zeros(len(items), dtype=torch.bool)
        for _ in range(4):                           # at most 3 digits + <eos>
            nxt = model(x)[:, -1].argmax(-1)
            nxt[done] = PAD
            done |= nxt == EOS
            x = torch.cat([x, nxt[:, None]], 1)
        for (p, pr), row in zip(items, x.tolist()):
            s = ""
            for t in row[len(pr):]:
                if t in (EOS, PAD):
                    break
                s += ITOS[t]
            out[p] = s
    model.train()
    return [out[p] for p in pairs]


def accuracy(model, pairs):
    return sum(s == str(a + b) for s, (a, b) in zip(solve(model, pairs), pairs)) / len(pairs)


def train(epochs, answer_only=True, seed=0, on_epoch=None):
    torch.manual_seed(seed)
    rng = random.Random(seed)
    train_pairs, val_pairs, test_pairs = split()
    model = GPT()
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    best_val, best_state = -1.0, None
    for ep in range(1, epochs + 1):
        total, n = 0.0, 0
        for x, y in batches(train_pairs, 64, answer_only, rng):
            logits = model(x)                                            # 1. forward  (B, 10, 15)
            loss = F.cross_entropy(logits.reshape(-1, VOCAB), y.reshape(-1), ignore_index=IGNORE)  # 2. loss
            opt.zero_grad()
            loss.backward()                                              # 3. backward
            opt.step()                                                   # 4. update
            total, n = total + loss.item(), n + 1
        val, acc = accuracy(model, val_pairs), accuracy(model, test_pairs)
        if val > best_val:                                           # the best epoch is chosen on validation only
            best_val, best_state = val, copy.deepcopy(model.state_dict())
        if on_epoch:
            on_epoch(ep, total / n, acc, model, val)
    last = model
    best = GPT()
    best.load_state_dict(best_state)
    return best, test_pairs, last


def overfit_one_batch(answer_only, steps=300):
    """Step 3: 8 fixed examples, 300 steps. A correct model brings this loss close to 0."""
    torch.manual_seed(0)
    model = GPT()
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    xs, ys = zip(*(make_xy(encode(*p), answer_only) for p in split()[0][:8]))
    x, y = torch.tensor(xs), torch.tensor(ys)
    log = {}
    for s in range(1, steps + 1):
        loss = F.cross_entropy(model(x).reshape(-1, VOCAB), y.reshape(-1), ignore_index=IGNORE)
        opt.zero_grad()
        loss.backward()
        opt.step()
        if s in (1, 50, 100, 300):
            log[s] = round(loss.item(), 4)
    return log


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--all-loss", action="store_true")
    args = ap.parse_args()

    ids = encode(23, 58)
    x, y = make_xy(ids)
    print("vocab size:", VOCAB)
    print("tokens  :", [ITOS[i] for i in ids])
    print("ids     :", ids, " length", len(ids))
    print("x       :", x)
    print("y       :", y, "  (-100 = not counted in the loss)")
    print("x then y, aligned:")
    for t, (a, b) in enumerate(zip(x, y)):
        print(f"  t={t}: sees {ITOS[a]:>5}  → must predict {'(ignored)' if b == IGNORE else ITOS[b]}")
    print("tokens in <bos>23+58=81<eos>:", len([BOS] + [STOI[c] for c in "23+58=81"] + [EOS]),
          "  longest, <bos>99+99=198<eos>:", len([BOS] + [STOI[c] for c in "99+99=198"] + [EOS]), "→ pad to", MAXLEN)
    print("targets that count with the loss on the answer only:", sum(v != IGNORE for v in y))
    q = torch.zeros(32, 10, 64)       # batch 32, length 10, d_model 64: all different, so no axis can be mixed up
    split_q = q.view(32, 10, 4, 16).transpose(1, 2)
    print("q", tuple(q.shape), "→ view(32, 10, 4, 16).transpose(1, 2) →", tuple(split_q.shape))
    out = torch.zeros(32, 4, 10, 16)  # what weights @ v gives: (B, h, L, d_k), freshly computed
    try:
        out.transpose(1, 2).view(32, 10, 64)
    except RuntimeError as e:
        print("joining the heads with .view right after transpose fails:", str(e).split(".")[0])
    print("joining with .contiguous().view →", tuple(out.transpose(1, 2).contiguous().view(32, 10, 64).shape))
    print("causal mask for L=4 (1 = blocked):")
    print(causal_mask(4).int())

    m = GPT()
    print("\nparameters:", sum(p.numel() for p in m.parameters()))
    xb = torch.tensor([x, x])
    print("forward shape: x", tuple(xb.shape), "→ logits", tuple(m(xb).shape))

    print(f"\nbefore training, guessing evenly over 15 tokens costs ln 15 = {math.log(15):.2f}")
    print("\noverfit one batch of 8, loss after steps 1/50/100/300:")
    print("  answer only  :", overfit_one_batch(True))
    print("  every position:", overfit_one_batch(False), " (the first digits can't be guessed)")

    epochs = 150 if args.full else 40
    print(f"\ntraining for {epochs} epochs, loss on {'every position' if args.all_loss else 'the answer only'}:")
    t0 = time.time()

    def log(ep, loss, acc, model, val):
        if ep == 1 or ep % 5 == 0:
            print(f"epoch {ep:3d}  loss {loss:.3f}  validation {val * 100:5.1f}%  unseen {acc * 100:5.1f}%  ({time.time() - t0:.0f}s)")

    model, test_pairs, _ = train(epochs, answer_only=not args.all_loss, on_epoch=log)
    print("kept the epoch with the best validation accuracy (500 problems); the 1,000 unseen ones only grade it")
    preds = solve(model, test_pairs[:8])
    print("\neight unseen problems:")
    for (a, b), s in zip(test_pairs[:8], preds):
        print(f"  {a:>2}+{b:<2}= {s:<4} {'ok' if s == str(a + b) else 'wrong, should be ' + str(a + b)}")
    print(f"\nfinal accuracy on 1000 unseen problems: {accuracy(model, test_pairs) * 100:.1f}%")
    wrong = [(a, b, s) for (a, b), s in zip(test_pairs, solve(model, test_pairs)) if s != str(a + b)]
    print("every miss:", " ".join(f"{a}+{b}={s}" for a, b, s in wrong[:20]), "…" if len(wrong) > 20 else "")

    # the boss check, run on this reference instead of on your own file
    import pathlib
    import tempfile

    import check
    print("\nboss check, part 1 (fixed weights):")
    check.part1(__import__(__name__))
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "model.pt"
        torch.save({"config": {"d": 64, "heads": 4, "layers": 2, "d_ff": 256}, "state": model.state_dict()}, path)
        print("boss check, part 2 (this trained model):")
        check.part2(__import__(__name__), path)
