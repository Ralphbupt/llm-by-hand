"""
Level 7 · Optimization

Run:  python demo.py      (needs numpy)

Mini-batches, momentum and Adam, starting weights, and a learning-rate schedule.
Prints every number the page asks about.
"""
import math

import numpy as np


def show(title):
    print("\n" + "=" * 70 + "\n" + title + "\n" + "=" * 70)


# =============================================================================
show("1. Mini-batches: y = w·x + b on (1,3) (2,3) (3,7) (4,7), start w = 0.5, b = 0")
X = np.array([1.0, 2, 3, 4])
Y = np.array([3.0, 3, 7, 7])


def grad(w, b, idx):
    err = w * X[idx] + b - Y[idx]
    return np.mean(err**2), np.mean(2 * err * X[idx]), np.mean(2 * err)


w, b = 0.5, 0.0
print("errors (prediction - truth):", (w * X + b - Y).tolist())
loss, gw, gb = grad(w, b, [0, 1, 2, 3])
print(f"full batch (all 4 points): loss = {loss}, dL/dw = {gw}, dL/db = {gb}")
loss, gw, gb = grad(w, b, [2])
print(f"batch of one point (3,7):  loss = {loss}, dL/dw = {gw}, dL/db = {gb}")
for i in range(4):
    print(f"  batch of point {i}: dL/dw = {grad(w, b, [i])[1]}")
A = np.vstack([X, np.ones(4)]).T
print("best line (least squares): w, b =", np.linalg.lstsq(A, Y, rcond=None)[0].round(6).tolist())
for i in range(4):
    print(f"  at the best line, point {i} alone still pulls with dL/dw = {grad(1.6, 1.0, [i])[1]:.2f}")
print("one epoch = one pass over all the data: 4 points in batches of 1 = 4 steps;",
      "1,000 examples in batches of 50 =", 1000 // 50, "steps")

# =============================================================================
show("2. Optimizers on f(w1, w2) = 0.5·(w1² + 25·w2²), start (-4, 1)")


def g_ravine(p):
    return np.array([p[0], 25 * p[1]])


p0 = np.array([-4.0, 1.0])
g = g_ravine(p0)
print("gradient at the start:", g.tolist())
lr = 0.03
print(f"SGD, lr {lr}: new w = {(p0 - lr * g).tolist()}  (w2 moves {lr * g[1]}, w1 moves {lr * g[0]})")
for lr_big in [0.03, 0.08, 0.09]:
    print(f"  SGD lr {lr_big}: w2 is multiplied by 1 - 25·lr = {1 - 25 * lr_big:.2f} each step")

lr_a = 0.3
m = 0.1 * g
v = 0.001 * g**2
mh, vh = m / (1 - 0.9), v / (1 - 0.999)
step = lr_a * mh / (np.sqrt(vh) + 1e-8)
print(f"Adam, lr {lr_a}, first step: m_hat = {mh.tolist()}, sqrt(v_hat) = {np.sqrt(vh).tolist()}")
print(f"  step = lr·m_hat/sqrt(v_hat) = {step.round(8).tolist()}  -> both weights move {lr_a}")
print(f"  new w = {(p0 - step).round(6).tolist()}")


def momentum_step(w, u, g, lr=0.03, beta=0.9):
    u = beta * u + g
    w = w - lr * u
    return w, u


w1, u1 = momentum_step(p0, np.zeros(2), g)
print("code exercise: momentum_step(w=[-4, 1], u=[0, 0], g=[-4, 25]) -> w =", w1.round(6).tolist(), " u =", u1.tolist())
print("  step 1 from u = 0 is the same as SGD")
w1b, u1b = momentum_step(np.array([1.0, 1.0]), np.array([2.0, -2.0]), np.array([1.0, 1.0]), lr=0.1)
print("code exercise: momentum_step(w=[1, 1], u=[2, -2], g=[1, 1], lr=0.1) -> w =", w1b.round(6).tolist(), " u =", u1b.round(6).tolist())
print("  u = 0.9*[2, -2] + [1, 1] = [2.8, -0.8]: the old velocity along w1 adds up, along w2 it cancels")

def adam_step(w, g, m, v, t, lr=0.1, beta1=0.9, beta2=0.999, eps=1e-8):
    m = beta1 * m + (1 - beta1) * g
    v = beta2 * v + (1 - beta2) * g**2
    mhat = m / (1 - beta1**t)
    vhat = v / (1 - beta2**t)
    w = w - lr * mhat / (np.sqrt(vhat) + eps)
    return w, m, v


w2, _, _ = adam_step(np.array([1.0, 1.0]), np.array([4.0, 0.01]), np.zeros(2), np.zeros(2), 1)
print("code exercise: adam_step(w=[1,1], g=[4, 0.01], t=1, lr=0.1) ->", w2.round(6).tolist())

# race: 60 steps each
def race(kind, steps=60):
    p = p0.copy()
    m = np.zeros(2)
    v = np.zeros(2)
    for t in range(1, steps + 1):
        g = g_ravine(p)
        if kind == "sgd":
            p = p - 0.03 * g
        elif kind == "momentum":
            m = 0.9 * m + g          # m plays the role of the velocity u on the page: u <- beta·u + g
            p = p - 0.03 * m
        else:
            p, m, v = adam_step(p, g, m, v, t, lr=0.3)
    return 0.5 * (p[0] ** 2 + 25 * p[1] ** 2)


for k in ["sgd", "momentum", "adam"]:
    print(f"  loss after 60 steps, {k:8s}: {race(k):.6f}")

# =============================================================================
show("3. Initialization: inputs with std 1 through square layers")
print("rule: std = 1/sqrt(fan_in); fan_in 100 ->", 1 / math.sqrt(100))
n, s = 100, 0.2
print(f"linear layers, width {n}, weight std {s}: std grows by sqrt(n)·s = {math.sqrt(n) * s} per layer")
print("  after 10 layers:", (math.sqrt(n) * s) ** 10)
print("  with std 0.01: factor", math.sqrt(n) * 0.01, "per layer, after 10 layers:", (math.sqrt(n) * 0.01) ** 10)
rs = np.random.default_rng(0)
for act in ["none", "tanh", "relu"]:
    for std in [0.01, 0.1, 0.14, 0.2]:
        h = rs.standard_normal((40, n))
        for _ in range(10):
            h = h @ (std * rs.standard_normal((n, n)))
            h = np.tanh(h) if act == "tanh" else np.maximum(0, h) if act == "relu" else h
        print(f"  {act:4s} std {std:4}: activation std after 10 layers = {h.std():.3g}")


# =============================================================================
show("4. A learning-rate schedule: linear warmup, then linear decay")


def lr_at(step, peak, warmup, total):
    if step < warmup:
        return peak * step / warmup
    return peak * (total - step) / (total - warmup)


peak, warmup, total = 0.004, 100, 1000
for t in (0, 25, 50, 100, 550, 1000):
    print(f"  step {t:4d}: lr = {lr_at(t, peak, warmup, total):.5f}")
print(f"  another run, peak 0.01, warmup 10, total 110: step 5 → {lr_at(5, 0.01, 10, 110):.4f}, step 60 → {lr_at(60, 0.01, 10, 110):.4f}")
