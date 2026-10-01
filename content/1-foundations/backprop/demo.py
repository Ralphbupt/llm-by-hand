"""
Level 6 · Backpropagation

Run:  python demo.py      (needs numpy)

1. The smallest graph, z = w·x + b → a = sigmoid(z) → L = (a − y)², backward by hand.
2. A gradient check, and what happens with too large or too small an ε.
3. A 2→6→1 network learns XOR with a hand-written backward pass that passes a gradient check.
"""
import numpy as np

np.set_printoptions(precision=4, suppress=True)


def sigmoid(z):
    return 1 / (1 + np.exp(-z))


# --- 1. one neuron, backward by hand ---------------------------------------------
x, w, b, y = 2.0, 0.5, -1.0, 1.0   # b = −1 makes z = 0 and a = 0.5: every number below is easy by hand
z = w * x + b
a = sigmoid(z)
L = (a - y) ** 2
print("forward:")
print(f"  z = w·x + b = {w}×{x} + {b} = {z}")
print(f"  a = sigmoid(z) = {a:.4f}")
print(f"  L = (a − y)² = {L:.4f}")

dL_da = 2 * (a - y)
da_dz = a * (1 - a)
dL_dz = dL_da * da_dz
dL_dw = dL_dz * x
dL_db = dL_dz * 1
print("backward (multiply local gradients along the path):")
print(f"  ∂L/∂a = 2(a − y)            = {dL_da:.4f}")
print(f"  ∂a/∂z = a(1 − a)            = {da_dz:.4f}")
print(f"  ∂L/∂z = ∂L/∂a × ∂a/∂z       = {dL_da:.4f} × {da_dz:.4f} = {dL_dz:.4f}")
print(f"  ∂L/∂w = ∂L/∂z × x           = {dL_dz:.4f} × {x} = {dL_dw:.4f}")
print(f"  ∂L/∂b = ∂L/∂z × 1           = {dL_db:.4f}")

# --- 2. gradient check -------------------------------------------------------------
loss = lambda w: (sigmoid(w * x + b) - y) ** 2
print("\nnumeric gradient (L(w+ε) − L(w−ε)) / 2ε versus the chain rule:")
for eps in [1e-1, 1e-3, 1e-5, 1e-8, 1e-12]:
    num = (loss(w + eps) - loss(w - eps)) / (2 * eps)
    print(f"  ε = {eps:.0e}:  numeric = {num:.10f}   difference = {abs(num - dL_dw):.1e}")
print("  warm-up: L = w² at w = 3, ε = 0.1 →", round((3.1 ** 2 - 2.9 ** 2) / 0.2, 6))

# --- 3. a 2→6→1 network on XOR -----------------------------------------------------
X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=float)
Y = np.array([[0], [1], [1], [0]], dtype=float)


def forward(X, W1, b1, W2, b2):
    z1 = X @ W1 + b1
    a1 = np.tanh(z1)
    p = sigmoid(a1 @ W2 + b2)
    return z1, a1, p


def backward(X, y, W1, b1, W2, b2):
    z1, a1, p = forward(X, W1, b1, W2, b2)
    dz2 = (p - y) / len(X)          # (4, 1) output error: sigmoid + cross-entropy
    dW2 = a1.T @ dz2                # (6, 4) @ (4, 1) → (6, 1)
    db2 = dz2.sum(axis=0)
    da1 = dz2 @ W2.T                # (4, 1) @ (1, 6) → (4, 6)
    dz1 = da1 * (1 - a1 ** 2)       # back through tanh
    dW1 = X.T @ dz1                 # (2, 4) @ (4, 6) → (2, 6)
    db1 = dz1.sum(axis=0)
    return dW1, db1, dW2, db2


def bce(P):
    p = forward(X, *P)[2]
    return -np.mean(Y * np.log(p) + (1 - Y) * np.log(1 - p))


rng = np.random.default_rng(0)
P = [rng.normal(size=(2, 6)), np.zeros(6), rng.normal(size=(6, 1)), np.zeros(1)]
print("\nshapes: X", X.shape, " W1", P[0].shape, " W2", P[2].shape, " dW1", backward(X, Y, *P)[0].shape)

grads = backward(X, Y, *P)
h = 1e-5
for name, i in [("W1", 0), ("b1", 1), ("W2", 2), ("b2", 3)]:
    num = np.zeros_like(P[i])
    for idx in np.ndindex(P[i].shape):
        old = P[i][idx]
        P[i][idx] = old + h; lp = bce(P)
        P[i][idx] = old - h; lm = bce(P)
        P[i][idx] = old
        num[idx] = (lp - lm) / (2 * h)
    print(f"gradient check {name}: largest gap = {np.max(np.abs(num - grads[i])):.1e}")

lr = 1.0
for step in range(1000):
    for param, grad in zip(P, backward(X, Y, *P)):
        param -= lr * grad
    if step % 200 == 0:
        print(f"step {step:4d}  loss {bce(P):.4f}")
p = forward(X, *P)[2]
print("outputs:", p.ravel().round(3), " targets:", Y.ravel(), f" final loss {bce(P):.4f}")

# --- X.T @ dz adds up each example's x · dz (section 3) --------------------------
Xh = np.array([[1.0, 2.0], [3.0, 1.0]])
dzh = np.array([[0.5], [-1.0]])
print("\nper example x·dz:", [(Xh[i] * dzh[i, 0]).tolist() for i in range(2)])
print("X.T @ dz =", (Xh.T @ dzh).ravel().tolist(), " → dW[0][0] =", (Xh.T @ dzh)[0, 0])
print("db = dz.sum(axis=0) =", dzh.sum(axis=0).tolist(), " (rule 2: one number per neuron)")
