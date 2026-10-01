"""
Level 5 · Multilayer perceptron

Run:  python demo.py      (needs numpy)

The forward pass as matrices, the parameter counts, and the same spiral experiment as the lab:
one hidden layer of 2, 8 or 32 tanh units, trained with Adam on two interleaved spirals.
(The lab draws its spiral with its own random numbers, so its exact accuracy differs a little.)
"""
import numpy as np

np.set_printoptions(precision=4, suppress=True)


def sigmoid(z):
    return 1 / (1 + np.exp(-z))


# --- one example by hand, ReLU hidden layer ----------------------------------------
x = np.array([2.0, 1.0])
W1 = np.array([[1.0, -1.0], [0.0, 1.0]])
b1 = np.array([0.0, 0.0])
W2 = np.array([[2.0], [-1.0]])
b2 = 0.5
pre = x @ W1 + b1
h = np.maximum(0, pre)
z = h @ W2 + b2
print("x @ W1 + b1 =", pre, " → h = ReLU(...) =", h)
print("z = h @ W2 + b2 =", z, f" → p = sigmoid(z) = {sigmoid(z)[0]:.4f}")

# --- shapes and parameter counts ---------------------------------------------------
X50 = np.zeros((50, 2))
print("\n(50, 2) @ (2, 16) →", (X50 @ np.zeros((2, 16))).shape)


def params(sizes):
    return sum(a * b + b for a, b in zip(sizes[:-1], sizes[1:]))


for sizes in ([2, 8, 1], [2, 8, 8, 1], [2, 32, 1], [2, 8, 8, 8, 1]):
    print(f"parameters of {' → '.join(map(str, sizes)):18s} = {params(sizes)}")

# --- the code exercise ---------------------------------------------------------------
Xc = np.array([[1.0, 2.0], [0.5, -1.0]])
W1c = np.array([[1.0, -1.0, 0.5], [0.0, 1.0, -0.5]])
b1c = np.array([0.0, 0.0, 0.1])
W2c = np.array([[2.0], [-1.0], [1.0]])
b2c = np.array([0.5])
print("\nmlp on two examples:", sigmoid(np.tanh(Xc @ W1c + b1c) @ W2c + b2c).ravel())
print("mlp at the origin:   ", sigmoid(np.tanh(np.zeros((1, 2)) @ W1c + b1c) @ W2c + b2c).ravel())


# --- two spirals ---------------------------------------------------------------------
def spiral(n=100, noise=0.08, seed=1):
    rng = np.random.default_rng(seed)
    X, y = [], []
    for c in (0, 1):
        for i in range(n):
            r = 0.1 + 0.9 * i / n
            th = r * 2.6 * np.pi + c * np.pi
            X.append([r * np.cos(th) + noise * rng.normal(), r * np.sin(th) + noise * rng.normal()])
            y.append(c)
    return np.array(X), np.array(y, dtype=float)[:, None]


def train(width, steps=1500, lr=0.02, seed=3):
    X, y = spiral()
    rng = np.random.default_rng(seed)
    P = [rng.normal(size=(2, width)) / np.sqrt(2), np.zeros(width),
         rng.normal(size=(width, 1)) / np.sqrt(width), np.zeros(1)]
    m = [np.zeros_like(p) for p in P]
    v = [np.zeros_like(p) for p in P]
    for t in range(1, steps + 1):
        W1, b1, W2, b2 = P
        H = np.tanh(X @ W1 + b1)
        p = sigmoid(H @ W2 + b2)
        dz2 = (p - y) / len(X)                      # level 6 explains these lines
        dH = dz2 @ W2.T * (1 - H ** 2)
        G = [X.T @ dH, dH.sum(0), H.T @ dz2, dz2.sum(0)]
        for k in range(4):                          # Adam, level 7
            m[k] = 0.9 * m[k] + 0.1 * G[k]
            v[k] = 0.999 * v[k] + 0.001 * G[k] ** 2
            P[k] -= lr * (m[k] / (1 - 0.9 ** t)) / (np.sqrt(v[k] / (1 - 0.999 ** t)) + 1e-8)
    W1, b1, W2, b2 = P
    p = sigmoid(np.tanh(X @ W1 + b1) @ W2 + b2)
    return ((p > 0.5) == y).mean()


print("\ntwo spirals, 200 points, one hidden tanh layer, 1500 Adam steps:")
for w in (2, 8, 32):
    print(f"  {w:2d} units → {train(w) * 100:.0f}% correct")


# --- two hidden ReLU layers (mlp-deep) -------------------------------------------
def mlp2(X, W1, b1, W2, b2, W3, b3):
    H1 = np.maximum(0, X @ W1 + b1)
    H2 = np.maximum(0, H1 @ W2 + b2)
    print("  H1 =", H1.tolist(), "  H1 @ W2 + b2 =", (H1 @ W2 + b2).tolist(), "  H2 =", H2.tolist())
    return H2 @ W3 + b3


Xd = np.array([[2.0, 1.0], [1.0, 3.0]])
W1d, b1d = np.array([[1.0, -1.0], [0.0, 1.0]]), np.array([0.0, 0.0])
W2d, b2d = np.array([[1.0, -1.0], [1.0, 1.0]]), np.array([0.0, 1.0])
W3d, b3d = np.array([[2.0], [1.0]]), np.array([0.5])
print("\ntwo hidden ReLU layers, 2 → 2 → 2 → 1:")
print("  out =", mlp2(Xd, W1d, b1d, W2d, b2d, W3d, b3d).ravel())
print("  origin → out =", mlp2(np.zeros((1, 2)), W1d, b1d, W2d, b2d, W3d, b3d).ravel())
