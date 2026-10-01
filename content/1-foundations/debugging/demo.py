"""
Level U5 · Debugging a model

Run:  python demo.py      (needs numpy)

Every number the page asks you about is printed here, so you can check your answers
and see where each one comes from. The local boss (broken_train.py, check.py) needs PyTorch.
"""
import warnings

import numpy as np

warnings.filterwarnings("ignore")      # we WANT to see inf and nan below, without warnings

x = np.array([1., 2., 3., 4.])
y = np.array([3., 3., 7., 7.])          # the four points of level 7

# --- 1. shapes: a silent broadcast -------------------------------------------
w, b = 0.5, 0.0
pred = (w * x + b).reshape(4, 1)        # (4, 1), e.g. the output of X @ W with W of shape (1, 1)
err = pred - y                          # (4, 1) - (4,) → (4, 4)  no error!
print("pred", pred.shape, "- y", y.shape, "→", err.shape)
print("mean of y:", y.mean(), " → with the bug, the best line is flat: w = 0, b =", y.mean())
print("loss of that flat line, with the bug:", ((y.mean() - y[None, :]) ** 2).mean())
fix = pred[:, 0] - y
print("fixed: pred[:, 0] - y has shape", fix.shape)

def fit(lr, steps, bug=None, dtype=np.float64):
    xs, ys = x.astype(dtype), y.astype(dtype)
    w, b, lr = dtype(0.5), dtype(0.0), dtype(lr)
    gw_acc, gb_acc = dtype(0), dtype(0)
    losses = []
    for _ in range(steps):
        if bug == "broadcast":
            e = (w * xs + b)[:, None] - ys[None, :]
            gw, gb = (2 * e * xs[:, None]).mean(), (2 * e).mean()
        else:
            e = w * xs + b - ys
            gw, gb = (2 * e * xs).mean(), (2 * e).mean()
        losses.append(float((e ** 2).mean()))
        if bug == "no zero_grad":       # .grad keeps adding up across steps
            gw_acc, gb_acc = gw_acc + gw, gb_acc + gb
            gw, gb = gw_acc, gb_acc
        w, b = w - lr * gw, b - lr * gb
    return float(w), float(b), losses

w1, b1, L1 = fit(0.05, 2000)
print(f"\ncorrect, lr 0.05, 2000 steps: w = {w1:.3f}, b = {b1:.3f}, loss = {L1[-1]:.3f}")
w2, b2, L2 = fit(0.05, 2000, "broadcast")
print(f"broadcast bug, 2000 steps:    w = {w2:.3f}, b = {b2:.3f}, loss = {L2[-1]:.3f}")
w3, b3, L3 = fit(0.01, 200, "no zero_grad")
print("no zero_grad, lr 0.01, loss every 20 steps:", [round(l, 2) for l in L3[::20]])

# --- 2. overfit one batch ----------------------------------------------------------
w4, b4, L4 = fit(0.05, 500)
print(f"\none batch (the 4 points), 500 steps: loss {L4[0]:.3f} → {L4[-1]:.3f} (best possible 0.8)")

# --- 3. gradient check ------------------------------------------------------------
f = lambda w: w ** 2
w0, h = 3.0, 0.01
print(f"\nf(w) = w², w = {w0}, h = {h}")
print(f"  f(w + h) = {f(w0 + h):.4f}, f(w - h) = {f(w0 - h):.4f}")
print(f"  numeric slope = ({f(w0 + h):.4f} - {f(w0 - h):.4f}) / {2 * h} = {(f(w0 + h) - f(w0 - h)) / (2 * h):.4f}")
print("  analytic 2w =", 2 * w0, "  a buggy 'w' would give", w0)

def num_grad(f, w, h=1e-5):
    g = np.zeros_like(w)
    for i in range(len(w)):
        w[i] += h; fp = f(w)
        w[i] -= 2 * h; fm = f(w)
        w[i] += h
        g[i] = (fp - fm) / (2 * h)
    return g

def loss_wb(p):                          # p = [w, b]
    return ((p[0] * x + p[1] - y) ** 2).mean()

p = np.array([0.5, 0.0])
e = p[0] * x + p[1] - y
print("numeric grad at w = 0.5, b = 0:", num_grad(loss_wb, p).round(4).tolist())
print("formula: dw = mean(2·e·x) =", (2 * e * x).mean(), ", db = mean(2·e) =", (2 * e).mean())
print("a buggy formula that forgets the 2:", (e * x).mean(), (e).mean())

# --- 4. NaN -------------------------------------------------------------------------
w = 1.0
print("\nf(w) = w², lr 1.5: each step w ← w − 1.5·2w = −2w")
for k in range(3):
    w = w - 1.5 * 2 * w
    print(f"  step {k + 1}: w = {w}")
print("np.log(0) =", np.log(0.0), "  inf - inf =", np.inf - np.inf, "  0 * inf =", 0 * np.inf, "  nan + 1 =", np.nan + 1)
_, _, L5 = fit(0.2, 200, dtype=np.float32)
first_inf = next(i for i, l in enumerate(L5) if not np.isfinite(l))
first_nan = next(i for i, l in enumerate(L5) if np.isnan(l))
print(f"float32, lr 0.2: loss {L5[:4]} …  inf at step {first_inf}, NaN at step {first_nan}")

# --- 5. loss not falling ------------------------------------------------------------
print("\nno zero_grad: the batch gradient is 2 at each of 3 steps; .grad after step 3 =", 2 + 2 + 2)
tokens = ["<bos>", "a", "b", "c"]
print("tokens:", tokens)
print("  right:  inputs", tokens[:-1], "targets", tokens[1:])
print("  bug:    inputs", tokens[:-1], "targets", tokens[:-1], "← each target is the input itself")

# boss part B: next-token batch with padding
P = np.array([[1, 5, 3, 8], [1, 2, 9, 0], [1, 7, 0, 0]])
X, Y = P[:, :-1], P[:, 1:]
keep = Y != 0
print("\npadded batch\n", P)
print("X\n", X, "\nY\n", Y, "\nkeep (count in the loss)\n", keep, "\nterms in the loss:", int(keep.sum()))
