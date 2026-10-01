"""
Level N7 · The 2017 encoder–decoder Transformer

A full encoder-decoder Transformer learns to read numbers aloud:

    "427"  →  four hundred twenty seven

Then it writes an answer one word at a time, and we print every step.

Run:  python demo.py      (needs torch; about 20 seconds on a laptop CPU)
"""
import math
import random

import torch
import torch.nn as nn
import torch.nn.functional as F

torch.set_printoptions(precision=2, sci_mode=False)

# ---------------------------------------------------------------------------
# 1. Data: digits in, English words out
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


PAD, BOS, EOS = 0, 1, 2
SRC = ["<pad>", "<bos>", "<eos>"] + list("0123456789")             # 13 source tokens
TGT = ["<pad>", "<bos>", "<eos>"] + ONES + TENS + ["hundred"]       # 32 target tokens
TGT_ID = {w: i for i, w in enumerate(TGT)}
SRC_LEN, TGT_LEN = 3, 5        # at most 3 digits; at most 4 words + <eos>


def encode(n):
    """n → (src, tgt_in, tgt_out). tgt_in starts with <bos>; tgt_out is the same row moved left by one."""
    s = [SRC.index(c) for c in str(n)]
    s += [PAD] * (SRC_LEN - len(s))
    w = [TGT_ID[x] for x in words(n)]
    full = [BOS] + w + [EOS] + [PAD] * (TGT_LEN - 1 - len(w))
    return s, full[:-1], full[1:]


def tensors(nums):
    s, i, o = zip(*(encode(n) for n in nums))
    return torch.tensor(s), torch.tensor(i), torch.tensor(o)


def split(seed=0):
    nums = list(range(1000))
    random.Random(seed).shuffle(nums)
    return nums[:900], nums[900:]        # 100 numbers are never trained on


# ---------------------------------------------------------------------------
# 2. The model: the parts from levels 14 to 16, stacked
# ---------------------------------------------------------------------------
def causal_mask(L):
    return torch.triu(torch.ones(L, L, dtype=torch.bool), diagonal=1)   # True = not allowed to look


def pad_mask(ids):
    return (ids == PAD).unsqueeze(1)                                     # (B, 1, L): don't look at PAD


class MultiHead(nn.Module):
    def __init__(self, d, heads):
        super().__init__()
        self.h, self.dk = heads, d // heads
        self.Wq = nn.Linear(d, d, bias=False)
        self.Wk = nn.Linear(d, d, bias=False)
        self.Wv = nn.Linear(d, d, bias=False)
        self.Wo = nn.Linear(d, d)
        self.last = None                       # attention weights, kept only for the picture

    def forward(self, q_in, kv_in, mask=None):
        B, Lq, d = q_in.shape
        Lk = kv_in.size(1)
        q = self.Wq(q_in).view(B, Lq, self.h, self.dk).transpose(1, 2)
        k = self.Wk(kv_in).view(B, Lk, self.h, self.dk).transpose(1, 2)
        v = self.Wv(kv_in).view(B, Lk, self.h, self.dk).transpose(1, 2)
        scores = q @ k.transpose(-2, -1) / math.sqrt(self.dk)
        if mask is not None:
            scores = scores.masked_fill(mask.unsqueeze(1), float("-inf"))
        w = F.softmax(scores, dim=-1)
        self.last = w.detach()
        return self.Wo((w @ v).transpose(1, 2).reshape(B, Lq, d))


def ffn(d, d_ff):
    return nn.Sequential(nn.Linear(d, d_ff), nn.ReLU(), nn.Linear(d_ff, d))


class EncoderLayer(nn.Module):
    def __init__(self, d, h, d_ff):
        super().__init__()
        self.attn, self.n1 = MultiHead(d, h), nn.LayerNorm(d)
        self.ff, self.n2 = ffn(d, d_ff), nn.LayerNorm(d)

    def forward(self, x, m):
        x = self.n1(x + self.attn(x, x, m))
        return self.n2(x + self.ff(x))


class DecoderLayer(nn.Module):
    def __init__(self, d, h, d_ff):
        super().__init__()
        self.self_attn, self.n1 = MultiHead(d, h), nn.LayerNorm(d)
        self.cross, self.n2 = MultiHead(d, h), nn.LayerNorm(d)
        self.ff, self.n3 = ffn(d, d_ff), nn.LayerNorm(d)

    def forward(self, y, memory, tgt_m, src_m):
        y = self.n1(y + self.self_attn(y, y, tgt_m))        # look only at earlier output words
        y = self.n2(y + self.cross(y, memory, src_m))       # Q from the output, K and V from memory
        return self.n3(y + self.ff(y))


class Transformer(nn.Module):
    def __init__(self, d=64, heads=4, layers=2, d_ff=128, emb_std=None):
        super().__init__()
        self.d = d
        self.src_emb, self.tgt_emb = nn.Embedding(len(SRC), d), nn.Embedding(len(TGT), d)
        std = d ** -0.5 if emb_std is None else emb_std           # as in level 17: 1/√d_model
        nn.init.normal_(self.src_emb.weight, std=std)            # so emb × √d has numbers of size about 1, like the PE
        nn.init.normal_(self.tgt_emb.weight, std=std)
        pos = torch.arange(16).unsqueeze(1)
        div = torch.exp(-math.log(10000.0) * torch.arange(0, d, 2) / d)
        pe = torch.zeros(16, d)
        pe[:, 0::2], pe[:, 1::2] = torch.sin(pos * div), torch.cos(pos * div)
        self.register_buffer("pe", pe)                       # fixed, not trained
        self.enc = nn.ModuleList(EncoderLayer(d, heads, d_ff) for _ in range(layers))
        self.dec = nn.ModuleList(DecoderLayer(d, heads, d_ff) for _ in range(layers))
        self.out = nn.Linear(d, len(TGT))

    def encode(self, src):
        x = self.src_emb(src) * math.sqrt(self.d) + self.pe[: src.size(1)]
        for l in self.enc:
            x = l(x, pad_mask(src))
        return x                                             # memory: one vector per input digit

    def decode(self, tgt, memory, src):
        y = self.tgt_emb(tgt) * math.sqrt(self.d) + self.pe[: tgt.size(1)]
        m = causal_mask(tgt.size(1)) | pad_mask(tgt)
        for l in self.dec:
            y = l(y, memory, m, pad_mask(src))
        return y

    def forward(self, src, tgt_in):
        return self.out(self.decode(tgt_in, self.encode(src), src))     # (B, L, 32)


def count(m):
    return sum(p.numel() for p in m.parameters())


# ---------------------------------------------------------------------------
# 3. Training: batch → forward → loss → backward → update
# ---------------------------------------------------------------------------
def train(epochs=60, seed=0, on_epoch=None, emb_std=None):
    torch.manual_seed(seed)
    rng = random.Random(seed)
    train_nums, test_nums = split()
    model = Transformer(emb_std=emb_std)
    loss_fn = nn.CrossEntropyLoss(ignore_index=PAD, label_smoothing=0.1)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    for ep in range(1, epochs + 1):
        rng.shuffle(train_nums)
        total, n = 0.0, 0
        for i in range(0, len(train_nums), 64):
            src, tgt_in, tgt_out = tensors(train_nums[i:i + 64])          # 1. a batch
            logits = model(src, tgt_in)                                   # 2. forward (B, 5, 32)
            loss = loss_fn(logits.reshape(-1, len(TGT)), tgt_out.reshape(-1))  # 3. loss on (B*5, 32)
            opt.zero_grad()
            loss.backward()                                               # 4. backward
            opt.step()                                                    #    and update
            total, n = total + loss.item(), n + 1
        if on_epoch:
            on_epoch(ep, total / n, model, test_nums)
    return model, test_nums


@torch.no_grad()
def read_aloud(model, n, steps=None):
    """Greedy decoding. Returns the words, and (if steps is a list) a record of every step."""
    model.eval()
    src = tensors([n])[0]
    memory = model.encode(src)
    ys = [BOS]
    while len(ys) <= TGT_LEN:
        h = model.decode(torch.tensor([ys]), memory, src)       # (1, len(ys), 64)
        last = h[0, -1]                                          # only the last row predicts the next word
        logits = model.out(last)                                 # (32,)
        nxt = int(logits.argmax())
        if steps is not None:
            cross = torch.stack([l.cross.last for l in model.dec[-1:]])[0, 0].mean(0)[-1]   # heads averaged
            steps.append({"input": [TGT[t] for t in ys], "last": last, "logits": logits,
                          "pick": TGT[nxt], "cross": cross[: len(str(n))]})
        ys.append(nxt)
        if nxt == EOS:
            break
    model.train()
    return [TGT[t] for t in ys[1:] if t != EOS]


def accuracy(model, nums):
    return sum(read_aloud(model, n) == words(n) for n in nums) / len(nums)


if __name__ == "__main__":
    s, ti, to = encode(427)
    print("427 →", words(427))
    print("src    :", s, [SRC[i] for i in s])
    print("tgt_in :", ti, [TGT[i] for i in ti])
    print("tgt_out:", to, [TGT[i] for i in to])

    m = Transformer()
    print("\nparameters (d_model=64, heads=4, layers=2, d_ff=128):", count(m))
    print("  one FFN:", count(m.enc[0].ff), "   one attention block:", count(m.enc[0].attn))
    print("  encoder layer:", count(m.enc[0]), "   decoder layer:", count(m.dec[0]),
          "   difference:", count(m.dec[0]) - count(m.enc[0]))
    print("  one LayerNorm:", count(m.enc[0].n1))
    print("  embeddings:", count(m.src_emb) + count(m.tgt_emb), "   output layer:", count(m.out))
    print("  with 8 heads instead of 4:", count(Transformer(heads=8)))

    # memory: one vector per source token (the "memory-shape" question: 32 numbers, 3 digits each)
    src32, tgt32, _ = tensors(list(range(100, 132)))
    print("\nbatch of 32: src", tuple(src32.shape), " tgt_in", tuple(tgt32.shape),
          " memory", tuple(m.encode(src32).shape), "(B, L_src, d_model)")

    # why × √d_model: row lengths at the start of training (word table, × 8) against a position row
    for std, name in ((None, "1/√64"), (1.0, "1    ")):
        torch.manual_seed(0)
        t = Transformer(emb_std=std)
        tok = (t.tgt_emb.weight * math.sqrt(t.d)).norm(dim=1).mean().item()
        pos = t.pe[:6].norm(dim=1).mean().item()
        print(f"table std {name}: a word's row after × 8 is about {tok:.1f} long, a position's row {pos:.1f}"
              f"  (ratio {tok / pos:.1f})")

    # label smoothing 0.1 over 32 words: the lowest possible loss is the entropy of the smoothed target
    hi, lo = 0.9 + 0.1 / len(TGT), 0.1 / len(TGT)
    floor = -(hi * math.log(hi) + (len(TGT) - 1) * lo * math.log(lo))
    print(f"smoothed target: {hi:.3f} on the right word, {lo:.3f} on each of the other 31 → lowest loss {floor:.3f}")

    src, tgt_in, tgt_out = tensors(list(range(64)))
    logits = m(src, tgt_in)
    print("\nbatch of 64: src", tuple(src.shape), " tgt_in", tuple(tgt_in.shape), " logits", tuple(logits.shape))
    print("for the loss: logits", tuple(logits.reshape(-1, len(TGT)).shape), " targets", tuple(tgt_out.reshape(-1).shape))
    print("PAD targets in this batch (not counted):", int((tgt_out == PAD).sum()), "of", tgt_out.numel())
    print("cross-attention weights (B, heads, L_tgt, L_src):", tuple(m.dec[0].cross.last.shape))
    print("decoder causal mask when tgt_in has 6 tokens:", tuple(causal_mask(6).shape), "(it follows tgt_in, not the source)")

    # The greedy loop on a 5-token stand-in model (the "greedy-loop" exercise).
    # Tokens: 0 <pad>, 1 <bos>, 2 <eos>, 3 four, 4 hundred. Row i of T scores the token after token i.
    T = torch.tensor([[0., 0, 0, 0, 0], [0, 0, 0, 2, 1], [0, 0, 0, 0, 0], [0, 0, 1, 0, 3], [0, 0, 2, 1, 0]])

    def greedy_decode(model_fn, bos=1, eos=2, max_new=6):
        ids = [bos]
        for step in range(max_new):
            scores = model_fn(ids)                 # (len(ids), 5)
            nxt = int(scores[-1].argmax())         # only the last row picks the next token
            print(f"  step {step}: rows in {len(ids)}, last row {scores[-1].tolist()} → pick {nxt}")
            ids.append(nxt)
            if nxt == eos:
                break
        return ids

    print("\ngreedy loop on the stand-in model:")
    print("ids:", greedy_decode(lambda ids: T[ids]))
    T2 = T.clone(); T2[4] = torch.tensor([0., 0, 0, 5, 0])   # "hundred" now never leads to <eos>
    print("never <eos>, max_new=4:")
    print("ids:", greedy_decode(lambda ids: T2[ids], max_new=4))
    print("max_new=2:")
    print("ids:", greedy_decode(lambda ids: T[ids], max_new=2))

    at20 = {}

    def log(ep, loss, model, test):
        if ep in (1, 10, 20, 40, 60):
            at20.setdefault(ep, accuracy(model, test))
            print(f"epoch {ep:2d}  loss {loss:.3f}  unseen numbers right: {at20[ep] * 100:.0f}%")

    print("\ntraining on 900 numbers, testing on 100 it never saw:")
    model, test = train(60, on_epoch=log)

    # The same run with a token table that starts at size 1 (std 1, PyTorch's default) instead of 1/√64.
    def log_std1(ep, loss, model, test):
        if ep in (20, 60):
            print(f" after {ep} epochs: table std 1/√64 = {64 ** -0.5:.3f} (this model): {at20[ep] * 100:.0f}%,"
                  f"  table std 1 (PyTorch's default): {accuracy(model, test) * 100:.0f}%")

    print("\nunseen numbers right, by the token table's starting size:")
    train(60, on_epoch=log_std1, emb_std=1.0)

    n = 427 if 427 in test else test[0]
    steps = []
    out = read_aloud(model, n, steps)
    print(f"\nreading {n} aloud, one step at a time:")
    for k, st in enumerate(steps):
        top = st["logits"].topk(3)
        best = ", ".join(f"{TGT[i]} {v:.1f}" for v, i in zip(top.values.tolist(), top.indices.tolist()))
        print(f" step {k + 1}: decoder input {st['input']} ({len(st['input'])} rows)")
        row = ", ".join(f"{v:.2f}" for v in st["last"][:4].tolist())
        print(f"         last row (first 4 of 64): [{row}, ...]  → top scores: {best}  → pick '{st['pick']}'")
    print("answer:", " ".join(out))
    so_far = ["<bos>", "seven", "hundred", "forty"]   # reading 742, after "seven hundred forty"
    print(f"\n742 after 'seven hundred forty': decoder input {so_far} → {len(so_far)} rows")

    # the three masks of one example (True = blocked): "42" padded to 3 digits, <bos> forty two PAD PAD
    print("\nthree masks for '42' (src padded to 3) and tgt_in <bos> forty two PAD PAD:")
    src = torch.tensor([SRC.index("4"), SRC.index("2"), PAD])
    tgt_in = torch.tensor([BOS, TGT.index("forty"), TGT.index("two"), PAD, PAD])
    print(" src ids:", src.tolist(), "  tgt_in ids:", tgt_in.tolist())
    Ls, Lt = len(src), len(tgt_in)
    enc = (src == PAD).expand(Ls, Ls)
    dec = torch.triu(torch.ones(Lt, Lt, dtype=torch.bool), 1) | (tgt_in == PAD).expand(Lt, Lt)
    cross = (src == PAD).expand(Lt, Ls)
    for name, m in (("enc", enc), ("dec", dec), ("cross", cross)):
        print(f" {name} {tuple(m.shape)}, {int(m.sum())} blocked:\n{m.int()}")

    # cross-attention weights of one head: batch 2, decoder input 3 tokens, source 6 tokens
    q, k = torch.randn(2, 3, 8), torch.randn(2, 6, 8)
    print("\nbatch 2, decoder input 3, source 6 → cross-attention weights", tuple(F.softmax(q @ k.transpose(-2, -1), -1).shape))
    print("source 5 tokens, decoder input <bos> + 5 words → causal mask", tuple(causal_mask(6).shape))
