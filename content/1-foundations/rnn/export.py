"""
Record the "remember the first symbol" experiment shown on the RNN and LSTM pages.

Run:  python export.py      (needs numpy + torch, about 3–4 minutes on a laptop CPU)
Writes site/public/data/rnn/memory.json

The task: a sequence starts with A or B, then k − 1 filler symbols (c, d or e, random).
At the end the network must say which symbol came first. Guessing gives 50%.
"""
import json
import pathlib
import time

import numpy as np
import torch
import torch.nn as nn

KS = [5, 10, 20, 40, 80]
STEPS, BATCH, HIDDEN, EVERY = 1500, 64, 32, 50
VOCAB = 5                                    # A B c d e


def batch(k, n, g):
    first = torch.randint(0, 2, (n,), generator=g)                  # 0 = A, 1 = B
    filler = torch.randint(2, 5, (n, k - 1), generator=g)
    seq = torch.cat([first[:, None], filler], 1)                    # (n, k)
    return nn.functional.one_hot(seq, VOCAB).float(), first


class Net(nn.Module):
    """kind: "rnn", "lstm0" (an LSTM with every bias starting at 0) or "lstm" (forget-gate bias starting at 2)."""

    def __init__(self, kind):
        super().__init__()
        self.rnn = (nn.RNN if kind == "rnn" else nn.LSTM)(VOCAB, HIDDEN, batch_first=True)
        self.out = nn.Linear(HIDDEN, 2)
        if kind != "rnn":
            with torch.no_grad():
                self.rnn.bias_ih_l0.zero_()
                self.rnn.bias_hh_l0.zero_()
                if kind == "lstm":                   # gate order in torch: input, forget, cell, output
                    self.rnn.bias_ih_l0[HIDDEN:2 * HIDDEN].fill_(2.0)

    def forward(self, x):
        h, _ = self.rnn(x)
        return self.out(h[:, -1])


def run(kind, k, seed=0):
    torch.manual_seed(seed)
    g = torch.Generator().manual_seed(seed + 1)
    net = Net(kind)
    opt = torch.optim.Adam(net.parameters(), lr=3e-3)
    xt, yt = batch(k, 1000, torch.Generator().manual_seed(999))     # fixed held-out set
    curve = []
    for step in range(STEPS + 1):
        if step % EVERY == 0:
            with torch.no_grad():
                curve.append(round((net(xt).argmax(1) == yt).float().mean().item(), 3))
        if step == STEPS:
            break
        x, y = batch(k, BATCH, g)
        loss = nn.functional.cross_entropy(net(x), y)
        opt.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        opt.step()
    return curve


if __name__ == "__main__":
    torch.set_num_threads(4)
    out = {"ks": KS, "every": EVERY, "steps": STEPS, "rnn": {}, "lstm0": {}, "lstm": {}}
    t0 = time.time()
    for kind in ("rnn", "lstm0", "lstm"):
        for k in KS:
            c = run(kind, k)
            out[kind][str(k)] = c
            print(f"{kind:5s} k={k:3d}  final accuracy {c[-1]:.3f}   ({time.time() - t0:.0f}s)")
    p = pathlib.Path(__file__).resolve().parents[3] / "site/public/data/rnn/memory.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, separators=(",", ":")))
    print("wrote", p, f"{p.stat().st_size / 1024:.1f} KB")
