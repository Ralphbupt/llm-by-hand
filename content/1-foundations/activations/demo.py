"""
Level 4 · Activation functions

Run:  python demo.py      (needs numpy)

Linear layers stacked are still one line. A nonlinearity between the layers is what
lets a network learn XOR. Then: sigmoid, tanh, ReLU and GELU, their slopes,
saturation and the vanishing gradient.
"""
import numpy as np

np.set_printoptions(precision=4, suppress=True)


def sigmoid(z):
    return 1 / (1 + np.exp(-z))


X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=float)
targets = {"AND": [0, 0, 0, 1], "OR": [0, 1, 1, 1], "XOR": [0, 1, 1, 0]}

# --- two linear layers collapse into one ----------------------------------------
x = np.array([2.0, 1.0])
W1 = np.array([[1.0, 2.0], [0.0, 1.0]])
W2 = np.array([[1.0], [1.0]])
h = x @ W1
print("\ntwo linear layers:  h = x @ W1 =", h, "  out = h @ W2 =", h @ W2)
print("merged: W1 @ W2 =", (W1 @ W2).ravel(), "  x @ (W1 @ W2) =", x @ (W1 @ W2))


# --- a 2→6→1 network on XOR, with and without tanh -----------------------------
def train(activation, steps=3000, seed=0):
    rng = np.random.default_rng(seed)
    W1, b1 = rng.normal(size=(2, 6)), np.zeros(6)
    W2, b2 = rng.normal(size=(6, 1)), np.zeros(1)
    y = np.array(targets["XOR"], dtype=float)[:, None]
    for _ in range(steps):
        z1 = X @ W1 + b1
        a1 = np.tanh(z1) if activation else z1
        p = sigmoid(a1 @ W2 + b2)
        dz2 = (p - y) / 4
        da1 = dz2 @ W2.T
        dz1 = da1 * (1 - a1 ** 2) if activation else da1
        W2 -= a1.T @ dz2; b2 -= dz2.sum(0)
        W1 -= X.T @ dz1; b1 -= dz1.sum(0)
    loss = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
    return p.ravel(), loss


for act in (True, False):
    p, loss = train(act)
    print(f"\nXOR, 2→6→1, activation {'on (tanh)' if act else 'off'}:")
    print("  outputs", p, f"  loss {loss:.4f}")
print(f"\nln 2 = {np.log(2):.4f}  (the loss when every answer is 0.5)")


# --- four activation functions and their slopes -----------------------------------
from math import erf, exp, pi, sqrt

def Phi(x):  # chance that a standard normal number is below x
    return 0.5 * (1 + erf(x / sqrt(2)))

def phi(x):  # the bell curve
    return exp(-x * x / 2) / sqrt(2 * pi)

acts = {
    "sigmoid": (lambda x: 1 / (1 + exp(-x)), lambda x: (1 / (1 + exp(-x))) * (1 - 1 / (1 + exp(-x)))),
    "tanh":    (np.tanh,                      lambda x: 1 - np.tanh(x) ** 2),
    "ReLU":    (lambda x: max(0.0, x),        lambda x: 1.0 if x > 0 else 0.0),
    "GELU":    (lambda x: x * Phi(x),          lambda x: Phi(x) + x * phi(x)),
}
print("\nactivation   f(-2)     f'(-2)    f(0)      f'(0)     f(3)      f'(3)")
for name, (f, df) in acts.items():
    print(f"{name:10s}" + "".join(f"{f(x):9.4f} {df(x):9.4f}" for x in (-2.0, 0.0, 3.0)))

print("\nsigmoid'(0) = 0.5 × (1 − 0.5) =", acts["sigmoid"][1](0.0))
print("ReLU'(−2) =", acts["ReLU"][1](-2.0))
print(f"best case through 5 sigmoid layers: 0.25**5 = 1/{int(1 / 0.25 ** 5)}")
print(f"best case through 10 sigmoid layers: 0.25**10 = {0.25 ** 10:.4e}")
print(f"tanh'(3) = {acts['tanh'][1](3.0):.4f}   (saturated)")
print(f"Phi(−1) = {Phi(-1):.4f}   GELU(−1) = {-1 * Phi(-1):.4f}   GELU'(−1) = {acts['GELU'][1](-1.0):.4f}")


def relu_grad(x):
    return (x > 0).astype(float)


x = np.array([-2.0, -0.5, 0.0, 0.5, 3.0])
print("\nrelu_grad", x, "→", relu_grad(x))



def sigmoid_grad(x):
    s = 1 / (1 + np.exp(-x))   # σ(x), computed once
    return s * (1 - s)         # σ(x)·(1 − σ(x))


x = np.array([-2.0, 0.0, 3.0])
print("\nsigmoid_grad", x, "→", sigmoid_grad(x).round(4))
print("five layers at x = 0: 0.25**5 =", sigmoid_grad(np.array([0.0]))[0] ** 5)
