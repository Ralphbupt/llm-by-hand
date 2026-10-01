"""
Level N5 · records the bottleneck experiment shown on the page.

Task: reverse a string of digits ("3 8 1 5" → "5 1 8 3"). Two LSTM encoder–decoders, the same size:
  plain — the decoder only gets the encoder's final (h, c): one fixed-size memory for the whole input.
  attn  — the same, plus attention: at every output step it scores all encoder states and mixes them.
Each is trained on lengths 2..24 and tested on new strings of each length. Memory sizes H = 32 and H = 128.

Writes site/public/data/seq2seq-attention/bottleneck.json. Run:  python export.py   (about 4 minutes on a laptop CPU)
"""
import json
import pathlib
import random
import time

import torch
import torch.nn as nn
import torch.nn.functional as F

torch.manual_seed(0)
random.seed(0)
torch.set_num_threads(4)
OUT = pathlib.Path(__file__).resolve().parents[3] / "site/public/data/seq2seq-attention/bottleneck.json"

PAD, BOS, EOS = 10, 11, 12          # digits are tokens 0..9
V = 13
LENGTHS = [4, 8, 12, 16, 20, 24]
STEPS = 3000


def batch(L, B=64):
    src = torch.randint(0, 10, (B, L))
    tgt = torch.flip(src, dims=[1])
    tin = torch.cat([torch.full((B, 1), BOS), tgt], 1)
    tout = torch.cat([tgt, torch.full((B, 1), EOS)], 1)
    return src, tin, tout


class Seq2seq(nn.Module):
    def __init__(self, H, attention):
        super().__init__()
        self.attention = attention
        self.emb_src = nn.Embedding(V, 32)
        self.emb_tgt = nn.Embedding(V, 32)
        self.enc = nn.LSTM(32, H, batch_first=True)
        self.dec = nn.LSTM(32, H, batch_first=True)
        self.out = nn.Linear(2 * H if attention else H, V)

    def forward(self, src, tin):
        E, state = self.enc(self.emb_src(src))           # E: (B, L_src, H), every encoder state
        S, _ = self.dec(self.emb_tgt(tin), state)       # S: (B, L_tgt, H), decoder states
        if not self.attention:
            return self.out(S), None
        scores = S @ E.transpose(1, 2)                  # (B, L_tgt, L_src): decoder state · each encoder state
        w = F.softmax(scores, dim=-1)                   # each row adds up to 1
        ctx = w @ E                                     # (B, L_tgt, H): weighted average of encoder states
        return self.out(torch.cat([S, ctx], -1)), w

    @torch.no_grad()
    def greedy(self, src, n):
        B = src.shape[0]
        tin = torch.full((B, 1), BOS)
        for _ in range(n + 1):
            logits, w = self(src, tin)
            tin = torch.cat([tin, logits[:, -1].argmax(-1, keepdim=True)], 1)
        return tin[:, 1:], w


def train(H, attention):
    m = Seq2seq(H, attention)
    opt = torch.optim.Adam(m.parameters(), lr=3e-3)
    for step in range(STEPS):
        src, tin, tout = batch(random.randint(2, 24))
        logits, _ = m(src, tin)
        loss = F.cross_entropy(logits.reshape(-1, V), tout.reshape(-1))
        opt.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        opt.step()
    return m


def accuracy(m, L, n=300):
    g = torch.Generator().manual_seed(1000 + L)
    src = torch.randint(0, 10, (n, L), generator=g)
    pred, _ = m.greedy(src, L)
    want = torch.cat([torch.flip(src, [1]), torch.full((n, 1), EOS)], 1)
    return (pred == want).all(1).float().mean().item()


result = {"lengths": LENGTHS, "steps": STEPS, "plain": {}, "attn": {}}
example = None
for H in (32, 128):
    for kind in ("plain", "attn"):
        t = time.time()
        m = train(H, kind == "attn")
        accs = [round(accuracy(m, L), 3) for L in LENGTHS]
        result[kind][str(H)] = accs
        print(f"H={H:3d} {kind:5s}", " ".join(f"L{L}:{a:.0%}" for L, a in zip(LENGTHS, accs)), f"({time.time() - t:.0f}s)")
        if kind == "attn" and H == 32:
            src = torch.tensor([[3, 8, 1, 5, 9, 0, 2, 7]])
            pred, w = m.greedy(src, src.shape[1])
            example = {"src": src[0].tolist(), "pred": pred[0].tolist(), "weights": [[round(x, 3) for x in row] for row in w[0].tolist()]}

result["example"] = example
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(result))
print("wrote", OUT, f"{OUT.stat().st_size / 1024:.1f} KB")
