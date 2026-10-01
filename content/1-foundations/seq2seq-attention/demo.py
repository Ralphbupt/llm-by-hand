"""
Level N5 · Seq2seq and the first attention

1. The hand computation from the page: one attention step with 3 encoder states of 2 numbers each.
2. Where attention looks: an LSTM encoder–decoder with attention learns to read numbers aloud, the task the
   Transformer learns in level 17, stretched to six digits ("427015" → four hundred twenty seven thousand fifteen).
3. The boss: reverse 20-digit strings. With attention, then (--compare) without.

Run:  python demo.py            (needs numpy and torch; about a minute on a laptop CPU)
      python demo.py --compare  (also trains the same boss model without attention)
      python demo.py --full     (more training)
      python demo.py --export   (also writes the alignment maps the page shows)
"""
import json
import pathlib
import random
import sys
import time

import numpy as np

np.set_printoptions(precision=4, suppress=True)

# ---------------------------------------------------------------------------
# 1. One attention step by hand
# ---------------------------------------------------------------------------
print("== one attention step ==")
E = np.array([[1., 0.], [0., 1.], [0., -1.]])     # 3 encoder states, 2 numbers each (one row per input word)
s = np.array([2., 0.])                             # the decoder's current state
scores = E @ s                                     # one score per encoder state
print("scores = E @ s =", scores)
e = np.exp(scores)
print("e^scores =", e.round(2), " (e^2 ≈ 7.39, e^0 = 1)")
w = e / e.sum()
print("weights = e / sum =", w.round(4), " sum =", e.sum().round(2))
ctx = w @ E                                        # weighted average of the encoder states
print("context = weights @ E =", ctx.round(4))
print("shapes: E", E.shape, " s", s.shape, " scores", scores.shape, " context", ctx.shape)

# the boss's browser exercise, checked here with the same numbers as its tests
def attend(E, s):
    scores = E @ s
    w = np.exp(scores - scores.max())
    w = w / w.sum()
    return w, w @ E

w2, c2 = attend(np.array([[2., 0.], [0., 2.], [1., 1.]]), np.array([1., 0.]))
print("attend(E=[[2,0],[0,2],[1,1]], s=[1,0]): weights", w2.round(4), " context", c2.round(4))


def attend_all(S, E):
    """The boss, part 1: every decoder step at once. S (T, H), E (L, H) → W (T, L), C (T, H)."""
    scores = S @ E.T
    W = np.exp(scores - scores.max(axis=-1, keepdims=True))
    W = W / W.sum(axis=-1, keepdims=True)
    return W, W @ E


Wa, Ca = attend_all(np.array([[2., 0.], [0., 2.]]), E)
print("attend_all(S=[[2,0],[0,2]], E): W =", Wa.round(4).tolist(), " C =", Ca.round(4).tolist())

# bottleneck count from section 1: an LSTM hands over h and c
H_SMALL = 32
print(f"\nan LSTM with H = {H_SMALL} hands the decoder h and c: {2 * H_SMALL} numbers, whatever the input length")

# ---------------------------------------------------------------------------
# 2. Where does attention look? Numbers → words
# ---------------------------------------------------------------------------
import torch
import torch.nn as nn
import torch.nn.functional as F

torch.manual_seed(0)
random.seed(0)
torch.set_num_threads(4)

ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen "
        "fourteen fifteen sixteen seventeen eighteen nineteen").split()
TENS = "twenty thirty forty fifty sixty seventy eighty ninety".split()


def words(n):
    """427015 → ['four', 'hundred', 'twenty', 'seven', 'thousand', 'fifteen']"""
    if n >= 1000:
        return words(n // 1000) + ["thousand"] + (words(n % 1000) if n % 1000 else [])
    if n < 20:
        return [ONES[n]]
    if n < 100:
        return [TENS[n // 10 - 2]] + ([ONES[n % 10]] if n % 10 else [])
    return [ONES[n // 100], "hundred"] + (words(n % 100) if n % 100 else [])


PAD, BOS, EOS = 0, 1, 2
SRC = ["<pad>", "<bos>", "<eos>"] + list("0123456789")
TGT = ["<pad>", "<bos>", "<eos>"] + ONES + TENS + ["hundred", "thousand"]
TGT_ID = {w: i for i, w in enumerate(TGT)}
SRC_LEN, TGT_LEN = 6, 10        # up to 6 digits; up to 9 words + <eos>


def encode(n):
    s = [SRC.index(c) for c in str(n)]
    s = [PAD] * (SRC_LEN - len(s)) + s                  # pad on the left, so the last encoder state is the last digit
    w = [TGT_ID[x] for x in words(n)]
    full = [BOS] + w + [EOS] + [PAD] * (TGT_LEN - 1 - len(w))
    return s, full[:-1], full[1:]


def tensors(nums):
    s, i, o = zip(*(encode(n) for n in nums))
    return torch.tensor(s), torch.tensor(i), torch.tensor(o)


rng = random.Random(0)
test_nums = rng.sample(range(1_000_000), 1000)          # never trained on
test_set = set(test_nums)


def random_numbers(k):
    """k training numbers, never from the test set; a mix of lengths so short numbers appear too"""
    out = []
    while len(out) < k:
        n = int(10 ** rng.uniform(0, 6))
        if n not in test_set and n < 1_000_000:
            out.append(n)
    return out


class Seq2seq(nn.Module):
    def __init__(self, H=64, attention=True):
        super().__init__()
        self.attention = attention
        self.emb_src = nn.Embedding(len(SRC), 32)
        self.emb_tgt = nn.Embedding(len(TGT), 32)
        self.enc = nn.LSTM(32, H, batch_first=True)
        self.dec = nn.LSTM(32, H, batch_first=True)
        self.out = nn.Linear(2 * H if attention else H, len(TGT))

    def forward(self, src, tin):
        E, state = self.enc(self.emb_src(src))          # (B, L_src, H): one state per input token
        S, _ = self.dec(self.emb_tgt(tin), state)      # (B, L_tgt, H): starts from the encoder's final (h, c)
        if not self.attention:
            return self.out(S), None
        scores = S @ E.transpose(1, 2)                 # (B, L_tgt, L_src)
        scores = scores.masked_fill((src == PAD).unsqueeze(1), float("-inf"))   # True = blocked: never look at padding
        w = F.softmax(scores, dim=-1)
        ctx = w @ E                                    # (B, L_tgt, H)
        return self.out(torch.cat([S, ctx], -1)), w

    @torch.no_grad()
    def read_aloud(self, n):
        src = torch.tensor([encode(n)[0]])
        tin = torch.tensor([[BOS]])
        for _ in range(TGT_LEN):
            logits, w = self(src, tin)
            nxt = logits[0, -1].argmax().item()
            tin = torch.cat([tin, torch.tensor([[nxt]])], 1)
            if nxt == EOS:
                break
        out = [TGT[t] for t in tin[0, 1:].tolist() if t != EOS]
        return out, (w[0].tolist() if w is not None else None)


def accuracy(m, ns):
    return sum(m.read_aloud(n)[0] == words(n) for n in ns) / len(ns)


def train(attention, steps):
    model = Seq2seq(attention=attention)
    opt = torch.optim.Adam(model.parameters(), lr=3e-3)
    for step in range(1, steps + 1):
        src, tin, tout = tensors(random_numbers(128))
        logits, _ = model(src, tin)
        loss = F.cross_entropy(logits.reshape(-1, len(TGT)), tout.reshape(-1), ignore_index=PAD)
        opt.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        if step % 500 == 0:
            print(f"  step {step:5d}  loss {loss.item():.3f}  exact on the 1,000 unseen numbers {accuracy(model, test_nums):.1%}")
    return model


full = "--full" in sys.argv
print("\n== numbers → words, up to 6 digits, 1,200 training steps of 128 numbers ==")
t0 = time.time()
m = train(True, 1200)
acc = accuracy(m, test_nums)
print(f"with attention: {acc:.1%} of the 1,000 unseen numbers read exactly right ({time.time() - t0:.0f}s)")

for n in (427015, 815, 40, 906300):
    print(f"{n:4d} →", " ".join(m.read_aloud(n)[0]))

# where does each output word look?
out, w = m.read_aloud(427015)
print("\nattention for 427015 (rows: output words, columns: digits 4 2 7 0 1 5):")
for word, row in zip(out + ["<eos>"], w):
    print(f"  {word:9s}", np.array(row).round(2))

# ---------------------------------------------------------------------------
# 3. The boss: reverse 20-digit strings
# ---------------------------------------------------------------------------
# Source "3 8 1 5 …" (20 digits), target the same digits backwards. Trained on lengths 2..24, tested on 300 new
# strings of length 20. The page's bottleneck chart comes from export.py, which runs this at many lengths.
DPAD, DBOS, DEOS, DV = 10, 11, 12, 13


class Reverser(nn.Module):
    def __init__(self, H=128, attention=True):
        super().__init__()
        self.attention = attention
        self.emb_src, self.emb_tgt = nn.Embedding(DV, 32), nn.Embedding(DV, 32)
        self.enc, self.dec = nn.LSTM(32, H, batch_first=True), nn.LSTM(32, H, batch_first=True)
        self.out = nn.Linear(2 * H if attention else H, DV)

    def forward(self, src, tin):
        E, state = self.enc(self.emb_src(src))
        S, _ = self.dec(self.emb_tgt(tin), state)
        if not self.attention:
            return self.out(S)
        w = F.softmax(S @ E.transpose(1, 2), dim=-1)
        return self.out(torch.cat([S, w @ E], -1))

    @torch.no_grad()
    def reverse(self, src):
        tin = torch.full((src.shape[0], 1), DBOS)
        for _ in range(src.shape[1] + 1):
            tin = torch.cat([tin, self(src, tin)[:, -1].argmax(-1, keepdim=True)], 1)
        return tin[:, 1:]


def train_reverser(attention, steps):
    model = Reverser(attention=attention)
    opt = torch.optim.Adam(model.parameters(), lr=3e-3)
    for step in range(steps):
        L = random.randint(2, 24)
        src = torch.randint(0, 10, (64, L))
        tgt = torch.flip(src, [1])
        tin = torch.cat([torch.full((64, 1), DBOS), tgt], 1)
        tout = torch.cat([tgt, torch.full((64, 1), DEOS)], 1)
        loss = F.cross_entropy(model(src, tin).reshape(-1, DV), tout.reshape(-1))
        opt.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
    g = torch.Generator().manual_seed(20)
    src = torch.randint(0, 10, (300, 20), generator=g)
    want = torch.cat([torch.flip(src, [1]), torch.full((300, 1), DEOS)], 1)
    return model, (model.reverse(src) == want).all(1).float().mean().item()


steps = 6000 if full else 3000
print(f"\n== boss: reverse 20-digit strings, {steps} training steps ==")
t0 = time.time()
rev, acc20 = train_reverser(True, steps)
print(f"with attention: {acc20:.1%} of 300 new 20-digit strings reversed exactly ({time.time() - t0:.0f}s)")
print("boss target: at least 90% →", "PASSED" if acc20 >= 0.90 else "not yet: try --full")
if "--compare" in sys.argv:
    t0 = time.time()
    _, plain20 = train_reverser(False, steps)
    print(f"without attention (same size, same steps): {plain20:.1%} ({time.time() - t0:.0f}s)")

if "--export" in sys.argv:
    examples = []
    for n in [427015, 906300, 815, 40, 13, 70707] + sorted(test_nums)[::100]:
        out, w = m.read_aloud(n)
        examples.append({"n": n, "src": [d for d in str(n)], "pad": SRC_LEN - len(str(n)), "out": out,
                         "right": out == words(n), "weights": [[round(x, 3) for x in row] for row in w]})
    path = pathlib.Path(__file__).resolve().parents[3] / "site/public/data/seq2seq-attention/alignments.json"
    path.write_text(json.dumps({"accuracy": acc, "steps": 1200, "examples": examples}))
    print("wrote", path)
