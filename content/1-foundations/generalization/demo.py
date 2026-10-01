"""
Level 8 · Generalization

Run:  python demo.py      (needs numpy)

Train versus held-out data, overfitting and capacity, early stopping, weight decay and dropout.
Prints every number the page asks about, and re-runs the labs' experiments with the same
seeded random generator the browser uses, so the numbers here match the labs.
"""
import math

import numpy as np


# --- the labs' random generator (mulberry32 + Box-Muller), ported from site/src/lib/training.ts
def rng(seed):
    a = seed & 0xFFFFFFFF

    def imul(x, y):
        return (x * y) & 0xFFFFFFFF

    def nxt():
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = a
        t = imul(t ^ (t >> 15), t | 1)
        t ^= (t + imul(t ^ (t >> 7), t | 61)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return nxt


def gauss(r):
    u1 = 1 - r()
    u2 = r()
    return math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)


def show(title):
    print("\n" + "=" * 70 + "\n" + title + "\n" + "=" * 70)


# =============================================================================
show("1. Overfitting: 10 noisy points from sin(pi·x), 40 held-out points")
r = rng(7)
xt = np.array([-1 + 2 * i / 9 for i in range(10)])
yt = np.array([math.sin(math.pi * x) + 0.3 * gauss(r) for x in xt])
xh = np.array([-1 + 2 * (i + 0.5) / 40 for i in range(40)])
yh = np.array([math.sin(math.pi * x) + 0.3 * gauss(r) for x in xh])
print("training x:", xt.round(3).tolist())
print("training y:", yt.round(3).tolist())


def fit_poly(d, decay=0.0):
    V = np.vander(xt, d + 1, increasing=True)
    A = V.T @ V / len(xt)
    D = np.eye(d + 1)
    D[0, 0] = 0  # the constant term is not decayed
    c = np.linalg.solve(A + decay * D, V.T @ yt / len(xt))
    tr = np.mean((V @ c - yt) ** 2)
    ho = np.mean((np.vander(xh, d + 1, increasing=True) @ c - yh) ** 2)
    return c, tr, ho


print("degree  params  train loss  held-out loss")
for d in range(10):
    _, tr, ho = fit_poly(d)
    print(f"  {d}       {d + 1:2d}      {tr:.4f}      {ho:.4f}")

# =============================================================================
show("2. Regularization")
w, lam, lr = 2.0, 0.1, 0.5
print(f"weight decay: loss + {lam}·w², data gradient 0, w = {w}, lr = {lr}")
print(f"  gradient of {lam}·w² = 2·{lam}·w = {2 * lam * w}; new w = {w} - {lr}·{2 * lam * w} = {w - lr * 2 * lam * w}")
def decay_step(w, g_data, lam, lr):
    g = g_data + 2 * lam * w
    w = w - lr * g
    return w


print("code exercise decay_step(w, g_data, lam, lr):")
print("  decay_step(2.0, 0.0, 0.1, 0.5) =", decay_step(2.0, 0.0, 0.1, 0.5))
print("  decay_step([2, -1], [1, 0], 0, 0.5) =", decay_step(np.array([2.0, -1]), np.array([1.0, 0]), 0, 0.5).tolist(), " (lam = 0: plain SGD)")
print("  decay_step([2, -1], [1, 0], 0.1, 0.5) =", decay_step(np.array([2.0, -1]), np.array([1.0, 0]), 0.1, 0.5).round(6).tolist(),
      " (gradient [1 + 0.4, 0 - 0.2] = [1.4, -0.2])")
for lam in [0, 1e-4, 1e-3, 1e-2, 1e-1]:
    _, tr, ho = fit_poly(9, lam)
    print(f"  degree 9, decay {lam:g}: train {tr:.4f}, held-out {ho:.4f}")

h = np.array([2.0, 4, 6, 8])
keep = np.array([1.0, 0, 1, 0])
p = 0.5
print(f"dropout: h = {h.tolist()}, keep mask = {keep.tolist()}, p = {p}")
print(f"  h · mask / (1 - p) = {(h * keep / (1 - p)).tolist()}")
print("  expected value of one unit stays the same:", 6 * (1 - p) / (1 - p) + 0 * p)
