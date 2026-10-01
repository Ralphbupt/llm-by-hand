"""
Level N5 · the boss, part 2: your own attention inside an encoder–decoder that reverses 20-digit strings.

Run:  python boss.py          (download it from /files/seq2seq-attention/boss.py into a folder of its own, run it there;
                                setup: /setup/ on the site)

Your job: fill in attend_all() below, the PyTorch version of the boss's part 1. Everything else is written for you.
The script first checks attend_all() on random batches, then trains the reverser (about a minute on a
laptop CPU) and tests it on 300 new 20-digit strings. At 90% or more it prints a line like

    N5 PASS 0.953 1a2b3c4d

Paste that whole line into the page.
"""
import hashlib
import math
import os
import random
import time

import torch
import torch.nn as nn
import torch.nn.functional as F


def attend_all(S, E):
    """Attention for every decoder step at once (the boss, part 1), now for a whole batch.
    S: (B, T, H), the decoder states.  E: (B, L, H), the encoder states.
    Return (w, ctx): w is (B, T, L), one row of attention weights over the L encoder states for each decoder step;
    ctx is (B, T, H), one context vector for each decoder step. (Softmax: level 10.)
    """
    # TODO: the same three steps as part 1, in PyTorch. Every tensor here has a batch axis in front.
    raise NotImplementedError("fill in attend_all()")


# If your check passes but the score is just under 90%, you may train longer: raise STEPS.
STEPS = 3000


# ---------------------------------------------------------------- do not edit below this line
LEVEL = "N5"
DPAD, DBOS, DEOS, DV = 10, 11, 12, 13


def verify(S, E, w, ctx):
    """Tests what attend_all(S, E) returned, using only properties that any correct answer has."""
    B, T, H = S.shape
    L = E.shape[1]
    if tuple(w.shape) != (B, T, L) or tuple(ctx.shape) != (B, T, H):
        raise SystemExit(f"attend_all returned shapes {tuple(w.shape)} and {tuple(ctx.shape)}; "
                         f"for S {tuple(S.shape)} and E {tuple(E.shape)} they should be {(B, T, L)} and {(B, T, H)}")
    w, ctx, S, E = (t.detach().double() for t in (w, ctx, S, E))
    sums = w.sum(dim=-1)
    if not (torch.isfinite(w).all() and (w >= 0).all() and torch.allclose(sums, torch.ones_like(sums), atol=1e-4)):
        raise SystemExit(f"the weights are wrong: the rows of w (one per decoder step) should each add up to 1, with no "
                         f"weight below 0; they add up to {sums.min():.3f} to {sums.max():.3f}, smallest weight {w.min():.3f}")
    # For each decoder step, log(weight) − (decoder state · encoder state) must be the same number for every encoder
    # state. Measure that number at the largest weight, then predict every weight in the row from it.
    scores = S @ E.transpose(1, 2)
    top = w.argmax(dim=-1, keepdim=True)
    base = torch.log(w.gather(-1, top)) - scores.gather(-1, top)
    predicted = base + scores                                   # the log of each weight, if the row is right
    seen = w > 1e-12
    off = torch.where(seen, (torch.log(w.clamp_min(1e-30)) - predicted).abs(), (predicted - math.log(1e-6)).clamp_min(0))
    spread = off.max().item()
    if spread > 1e-3:
        raise SystemExit(f"the weights are wrong: every row adds up to 1, but the weights don't follow the scores. "
                         f"For S {tuple(S.shape)} and E {tuple(E.shape)}, batch 0, decoder step 0 gives "
                         f"{[round(v, 4) for v in w[0, 0].tolist()]}")
    if not torch.allclose(ctx, w @ E, atol=1e-4):
        raise SystemExit(f"the weights are right, the context is not: batch 0, decoder step 0 gives "
                         f"{[round(v, 4) for v in ctx[0, 0].tolist()]}")


def check_attend():
    # new random sizes and numbers on every run, so no answer can be prepared in advance
    g = torch.Generator().manual_seed(int.from_bytes(os.urandom(4), "little"))
    for _ in range(3):
        B, T, L, H = (int(torch.randint(lo, hi, (1,), generator=g)) for lo, hi in ((1, 5), (1, 7), (2, 9), (3, 9)))
        S = torch.randn(B, T, H, generator=g)
        E = torch.randn(B, L, H, generator=g)
        verify(S, E, *attend_all(S, E))
    print("your attend_all() passes the checks on 3 random batches: OK")


class Reverser(nn.Module):
    def __init__(self, H=128):
        super().__init__()
        self.emb_src, self.emb_tgt = nn.Embedding(DV, 32), nn.Embedding(DV, 32)
        self.enc, self.dec = nn.LSTM(32, H, batch_first=True), nn.LSTM(32, H, batch_first=True)
        self.out = nn.Linear(2 * H, DV)
        self.verify_next = True

    def forward(self, src, tin):
        E, state = self.enc(self.emb_src(src))
        S, _ = self.dec(self.emb_tgt(tin), state)
        w, ctx = attend_all(S, E)
        if self.verify_next:
            verify(S, E, w, ctx)
            self.verify_next = False
        return self.out(torch.cat([S, ctx], -1))

    @torch.no_grad()
    def reverse(self, src):
        tin = torch.full((src.shape[0], 1), DBOS)
        self.verify_next = True
        for _ in range(src.shape[1] + 1):
            tin = torch.cat([tin, self(src, tin)[:, -1].argmax(-1, keepdim=True)], 1)
        return tin[:, 1:]


def main():
    check_attend()
    torch.manual_seed(0)
    random.seed(0)
    model = Reverser()
    opt = torch.optim.Adam(model.parameters(), lr=3e-3)
    start = time.time()
    for step in range(1, STEPS + 1):
        model.verify_next = step % 100 == 1
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
        if step % 500 == 0:
            print(f"step {step:4d}  loss {loss.item():.3f}  ({time.time() - start:.0f}s)")
    g = torch.Generator().manual_seed(20)
    src = torch.randint(0, 10, (300, 20), generator=g)
    want = torch.cat([torch.flip(src, [1]), torch.full((300, 1), DEOS)], 1)
    good = int((model.reverse(src) == want).all(1).sum())
    print(f"\n{good} of 300 new 20-digit strings reversed exactly (the boss needs 270, that is 90%)")
    if good >= 270:
        s = f"{good / 300:.3f}"
        print("\nPASS. Paste this whole line into the page:")
        print(pass_line(s))
    else:
        print("not yet: check attend_all() against part 1 on the page; if it is right and the score is close, raise STEPS")


def pass_line(score):
    """The line to paste into the page. Its last part is a short code made from the rest, so the page can tell that
    the line was pasted unchanged. Anyone can read this function, so it is no proof: this part relies on your honesty."""
    return f"{LEVEL} PASS {score} {hashlib.sha256(f'llm-by-hand/{LEVEL}/{score}'.encode()).hexdigest()[:8]}"




if __name__ == "__main__":
    main()
