"""
Level N2 · Residuals and normalization

Run:  python demo.py      (needs numpy)

Prints every number the page asks about:
  1. a deep stack of tanh layers, plain vs residual: how the signal and the gradient change with depth
  2. one-number examples of why the residual path keeps gradients alive
  3. a ResNet block's shapes
  4. BatchNorm vs LayerNorm on the same 4×4 batch, the running average, and batch size 1
The deep-stack numbers use the same random generator as the lab (site/src/lib/residuals.ts), so they match it exactly.
"""
import math

import numpy as np


# --- the labs' random generator (mulberry32 + Box-Muller), the same as site/src/lib/training.ts
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


WIDTH, BATCH = 16, 32


def stack(depth, scale, residual, seed=5):
    """Same as stack() in site/src/lib/residuals.ts: input, all W, then the top gradient, drawn in that order."""
    r = rng(seed)

    def draw(rows, cols, s):
        return np.array([[s * gauss(r) for _ in range(cols)] for _ in range(rows)])

    h = draw(BATCH, WIDTH, 1)
    act = [h.std()]
    Ws, tanhs = [], []
    for _ in range(depth):
        W = draw(WIDTH, WIDTH, scale / math.sqrt(WIDTH))
        t = np.tanh(h @ W)
        Ws.append(W)
        tanhs.append(t)
        h = h + t if residual else t
        act.append(h.std())
    g = draw(BATCH, WIDTH, 1)
    grad = [0.0] * (depth + 1)
    grad[depth] = g.std()
    for l in range(depth - 1, -1, -1):
        back = (g * (1 - tanhs[l] ** 2)) @ Ws[l].T   # through tanh, then through the matmul
        g = g + back if residual else back
        grad[l] = g.std()
    return act, grad


# =============================================================================
SCALE = 0.8
show(f"1. A deep stack of tanh layers (width 16, batch 32, weights ~ N(0, ({SCALE}/√16)²))")
for depth in (10, 30):
    for residual in (False, True):
        act, grad = stack(depth, SCALE, residual)
        kind = "residual" if residual else "plain   "
        print(f"depth {depth:2d} {kind}: signal std  input {act[0]:.2f} → top {act[-1]:.4f}   "
              f"gradient std  top {grad[-1]:.2f} → input {grad[0]:.6f}   (input/top = {grad[0] / grad[-1]:.2e})")
act, grad = stack(30, SCALE, False)
print("plain, depth 30, gradient std at layers 30, 20, 10, 0:", [f"{grad[i]:.2e}" for i in (30, 20, 10, 0)])
act, grad = stack(30, SCALE, True)
print("residual, depth 30, signal std at layers 0, 10, 20, 30:", [f"{act[i]:.2f}" for i in (0, 10, 20, 30)])
print(f"residual, depth 30: the gradient at layer 0 is {grad[0] / grad[-1]:.1f} times the gradient at the top (it grows)")
print("3/4 per layer for 30 layers (the depth-guess estimate):", f"{0.75 ** 30:.1e}")

show("2. One number per layer: why the residual path matters")
f_slope = 0.5
plain4 = f_slope ** 4
print(f"plain: 4 layers, each multiplies the gradient by {f_slope} → {f_slope}^4 = {plain4}")
print(f"residual block y = x + f(x) with f(x) = 0.5·x: dy/dx = 1 + 0.5 = {1 + f_slope}")
print(f"if f has slope 0 (the block learned nothing yet): dy/dx = 1 + 0 = 1, and 30 such blocks pass 1^30 = {1 ** 30}")
print(f"plain layers with slope 0.1, 10 of them: 0.1^10 = {0.1 ** 10:.0e};  residual: (1 + 0.1)^10 = {1.1 ** 10:.2f}")

show("3. A ResNet block: x + F(x) needs F(x) to have the same shape as x")
C, H, Wd = 64, 8, 8
print(f"x is ({C}, {H}, {Wd}) → conv 3×3 pad 1 → BN → ReLU → conv 3×3 pad 1 → BN → add x → ReLU")
print(f"each 3×3 conv with padding 1 keeps {H}×{Wd}; with {C} filters it keeps {C} channels → F(x) is ({C}, {H}, {Wd})")
print(f"weights in one 3×3 conv from {C} to {C} channels: 3·3·{C}·{C} = {3 * 3 * C * C}")

show("4. BatchNorm vs LayerNorm on the same batch (rows = examples, columns = features)")
X = np.array([[1, 4, 2, 9],
              [1, 0, 6, 3],
              [5, 1, 5, 1],
              [5, 7, 3, 1]], dtype=float)
print("X =\n", X)
bn_mu, bn_sd = X.mean(axis=0), X.std(axis=0)
ln_mu, ln_sd = X.mean(axis=1), X.std(axis=1)
print("BatchNorm: one mean per column (feature) =", bn_mu, " std =", np.round(bn_sd, 3))
print("LayerNorm: one mean per row (example)    =", ln_mu, " std =", np.round(ln_sd, 3))
print(f"column 0 = {X[:, 0]}: mean {bn_mu[0]}, deviations {X[:, 0] - bn_mu[0]}, variance {((X[:, 0] - bn_mu[0]) ** 2).mean()}, std {bn_sd[0]}")
BN = (X - bn_mu) / bn_sd
LN = (X - ln_mu[:, None]) / ln_sd[:, None]
print(f"BatchNorm X[2][0] = (5 − 3) / 2 = {BN[2, 0]}")
print(f"row 2 = {X[2]}: mean {ln_mu[2]}, std {ln_sd[2]}")
print(f"LayerNorm X[2][1] = (1 − 3) / 2 = {LN[2, 1]}")
print("LayerNorm of row 2:", LN[2])
print("BatchNorm result, rounded:\n", np.round(BN, 2))
print("LayerNorm result, rounded:\n", np.round(LN, 2))
B, d = 32, 64
print(f"a batch of {B} examples with {d} features: BatchNorm computes {d} means, LayerNorm computes {B} means")
running, batch_mean = 2.0, 4.0
print(f"running mean update with 0.1: 0.9 × {running} + 0.1 × {batch_mean} = {0.9 * running + 0.1 * batch_mean:.1f}")
x1 = np.array([[3.0, 7.0, 1.0]])
print("batch of 1, BatchNorm in training mode: x − mean =", x1 - x1.mean(axis=0), "→ every output is 0")
L, dm = 10, 64
eps = 1e-5
ln_eps = (X - X.mean(axis=1, keepdims=True)) / np.sqrt(X.var(axis=1, keepdims=True) + eps)
print("layer_norm with ε = 1e-5 added to the variance, row 2:", np.round(ln_eps[2], 4))
const = np.array([[2.0, 2, 2, 2]])
print("a constant row [2, 2, 2, 2]: variance 0, with ε →", (const - const.mean(axis=1, keepdims=True)) / np.sqrt(const.var(axis=1, keepdims=True) + eps))
print(f"a (B, L, d_model) = (2, {L}, {dm}) batch of sentences: LayerNorm normalizes each of the 2·{L} = {2 * L} tokens over its {dm} numbers")
