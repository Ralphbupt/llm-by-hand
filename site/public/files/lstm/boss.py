"""
Level N4 · the boss, part 2: your own LSTM cell writes lines that follow the rules.

Run:  python boss.py          (download it from /files/lstm/boss.py into a folder of its own, run it there;
                                setup: /setup/ on the site)

Your job: fill in LSTMCell.forward below. Everything else is written for you.
The script first checks your cell against the formulas on the page, then trains a character-level model built on it
(a few minutes on a laptop CPU), samples 200 lines and counts how many follow every rule.
At 90% or more it prints a line like

    N4 PASS 0.935 1a2b3c4d

Paste that whole line into the page.
"""
import hashlib
import re
import time

import numpy as np
import torch
import torch.nn as nn


class LSTMCell(nn.Module):
    """One LSTM step for a batch. Rows, as on the page: x (B, D), h and c (B, H).
    W (D, 4H), U (H, 4H), b (4H,). Gate order: f, i, g, o (the page's order, not PyTorch's)."""

    def __init__(self, D, H):
        super().__init__()
        self.H = H
        k = 1 / H ** 0.5  # the same starting range PyTorch uses for its own LSTM
        self.W = nn.Parameter(torch.empty(D, 4 * H).uniform_(-k, k))
        self.U = nn.Parameter(torch.empty(H, 4 * H).uniform_(-k, k))
        self.b = nn.Parameter(torch.empty(4 * H).uniform_(-k, k))
        with torch.no_grad():
            self.b[:H] = 2.0  # forget gate starts near sigmoid(2) ≈ 0.88: keep by default

    def forward(self, x, h, c):
        # TODO: compute z from x, h and the weights; split it into f, i, g, o (H numbers each);
        #       use torch.sigmoid for f, i, o and torch.tanh for g; update c, then h.
        #       Return (h, c). About six lines. The NumPy version is section 6 of the page.
        raise NotImplementedError("fill in LSTMCell.forward")


# If your check passes but the score is just under 90%, you may train longer: raise STEPS.
STEPS = 1800


# ---------------------------------------------------------------- do not edit below this line
LEVEL = "N4"
COLORS = ["red", "blue", "green", "gold", "pink", "gray"]
ANIMALS = ["fox", "cat", "owl", "bee", "yak", "dog"]
VERBS = ["sees", "hides", "finds", "wants", "keeps", "likes"]
THINGS = ["box", "cup", "hat", "map", "key", "bag"]
LINE = re.compile(r"^the (\w+) (\w+) (\w+) the (\w+) (\w+)\.$")


def make_line(r):
    c = COLORS[r.integers(6)]
    return f"the {c} {ANIMALS[r.integers(6)]} {VERBS[r.integers(6)]} the {c} {THINGS[r.integers(6)]}."


def follows_rules(line):
    m = LINE.match(line)
    if not m:
        return False
    c1, a, v, c2, t = m.groups()
    return c1 in COLORS and a in ANIMALS and v in VERBS and t in THINGS and c1 == c2


def _fixed(n, k, scale, fn):
    """Fixed, varied numbers for the check (no randomness, so the expected values below never change)."""
    return fn(torch.arange(n, dtype=torch.float32) * k) * scale


# What a correct cell returns for the fixed batch built in check_cell (4 rows, H = 3), rounded to 4 places.
WANT_H = [[0.036, 0.3795, -0.0922], [-0.2562, 0.3227, 0.0959], [-0.1378, -0.0716, 0.0163], [0.1218, -0.2108, -0.0503]]
WANT_C = [[0.0775, 0.8674, -0.2596], [-0.506, 0.5521, 0.2495], [-0.3026, -0.1229, 0.0397], [0.2333, -0.3699, -0.1437]]


def check_cell():
    D, H = 5, 3
    cell = LSTMCell(D, H)
    with torch.no_grad():
        cell.W.copy_(_fixed(D * 4 * H, 0.9, 0.6, torch.sin).reshape(D, 4 * H))
        cell.U.copy_(_fixed(H * 4 * H, 1.3, 0.6, torch.cos).reshape(H, 4 * H))
        cell.b.copy_(_fixed(4 * H, 2.1, 0.5, torch.sin))
    x = _fixed(4 * D, 0.7, 1.0, torch.sin).reshape(4, D)
    h = _fixed(4 * H, 1.1, 0.8, torch.cos).reshape(4, H)
    c = _fixed(4 * H, 1.7, 1.0, torch.sin).reshape(4, H)
    with torch.no_grad():
        got_h, got_c = cell(x, h, c)
    if got_h.shape != (4, H) or got_c.shape != (4, H):
        raise SystemExit(f"your cell returned shapes {tuple(got_h.shape)} and {tuple(got_c.shape)}; both should be (B, H) = (4, 3)")
    if not torch.allclose(got_c, torch.tensor(WANT_C), atol=1e-3):
        raise SystemExit(f"the new c is wrong: row 0 gives {[round(v, 4) for v in got_c[0].tolist()]}, "
                         f"not {WANT_C[0]} (the check uses 4 fixed rows with D = 5, H = 3).")
    if not torch.allclose(got_h, torch.tensor(WANT_H), atol=1e-3):
        raise SystemExit(f"the new c is right but the new h is wrong: row 0 gives {[round(v, 4) for v in got_h[0].tolist()]}, "
                         f"not {WANT_H[0]}.")
    print("your cell gives the expected numbers on a fixed batch: OK")


class CharModel(nn.Module):
    def __init__(self, V, H=128):
        super().__init__()
        self.emb = nn.Embedding(V, 32)
        self.cell = LSTMCell(32, H)
        self.out = nn.Linear(H, V)
        self.H = H

    def forward(self, x, state=None):  # x (B, L) of character ids
        B, L = x.shape
        h, c = state if state is not None else (torch.zeros(B, self.H), torch.zeros(B, self.H))
        e, outs = self.emb(x), []
        for t in range(L):
            h, c = self.cell(e[:, t], h, c)
            outs.append(h)
        return self.out(torch.stack(outs, 1)), (h, c)


def main():
    check_cell()
    r = np.random.default_rng(0)
    text = "\n".join(make_line(r) for _ in range(20000)) + "\n"
    chars = sorted(set(text))
    stoi = {ch: k for k, ch in enumerate(chars)}
    data = torch.tensor([stoi[ch] for ch in text])

    torch.manual_seed(0)
    net = CharModel(len(chars))
    if any(isinstance(m, (nn.LSTM, nn.LSTMCell, nn.GRU, nn.RNN)) for m in net.modules()):
        raise SystemExit("the boss is to use your own cell, not a built-in recurrent layer")
    opt = torch.optim.Adam(net.parameters(), lr=3e-3)
    SEQ, B = 96, 64
    gen, start = torch.Generator().manual_seed(1), time.time()
    for step in range(1, STEPS + 1):
        ix = torch.randint(0, len(data) - SEQ - 1, (B,), generator=gen)
        x = torch.stack([data[j:j + SEQ] for j in ix])
        y = torch.stack([data[j + 1:j + SEQ + 1] for j in ix])
        logits, _ = net(x)
        loss = nn.functional.cross_entropy(logits.reshape(-1, len(chars)), y.reshape(-1))
        opt.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        opt.step()
        if step % 250 == 0:
            print(f"step {step:4d}  loss {loss.item():.3f}  ({time.time() - start:.0f}s)")

    g = torch.Generator().manual_seed(7)
    lines, x, state, cur = [], torch.tensor([[stoi["\n"]]]), None, ""
    with torch.no_grad():
        while len(lines) < 200:
            logits, state = net(x, state)
            k = torch.multinomial(torch.softmax(logits[0, -1] / 0.8, 0), 1, generator=g).item()
            if chars[k] == "\n" or len(cur) > 80:
                lines.append(cur)
                cur = ""
            else:
                cur += chars[k]
            x = torch.tensor([[k]])
    good = sum(follows_rules(l) for l in lines)
    s = f"{good / len(lines):.3f}"
    print("three of its lines:", *lines[:3], sep="\n    ")
    print(f"\n{good} of {len(lines)} lines follow every rule (the boss needs 180, that is 90%)")
    if good >= 180:
        print("\nPASS. Paste this whole line into the page:")
        print(pass_line(s))
    else:
        print(f"not yet: {good} of {len(lines)} lines follow every rule, and the boss needs 180. If the cell check above "
              "passed and the score is close, raise STEPS")


def pass_line(score):
    """The line to paste into the page. Its last part is a short code made from the rest, so the page can tell that
    the line was pasted unchanged. Anyone can read this function, so it is no proof: this part relies on your honesty."""
    return f"{LEVEL} PASS {score} {hashlib.sha256(f'llm-by-hand/{LEVEL}/{score}'.encode()).hexdigest()[:8]}"




if __name__ == "__main__":
    main()
