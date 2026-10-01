"""
Level 3 · Neurons and classification loss

Run:  python demo.py      (needs numpy)

One neuron draws one straight line (its decision boundary).
Binary cross-entropy measures how wrong a yes/no answer is.
One neuron cannot do XOR: its best loss there is ln 2.
"""
import numpy as np

np.set_printoptions(precision=4, suppress=True)


def sigmoid(z):
    return 1 / (1 + np.exp(-z))


def bce(p, y):
    return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))


X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=float)
targets = {"AND": [0, 0, 0, 1], "OR": [0, 1, 1, 1], "XOR": [0, 1, 1, 0]}

# --- one neuron: the AND preset ------------------------------------------------
w, b = np.array([1.0, 1.0]), -1.5
z = X @ w + b
p = sigmoid(z)
print("AND neuron: w =", w, " b =", b)
print(f"  by hand at (1, 1): e^(−0.5) = {np.exp(-0.5):.4f} ≈ 0.6, so p ≈ 1 / 1.6 = {1 / 1.6:.3f}")
for x, zi, pi, t in zip(X, z, p, targets["AND"]):
    print(f"  x = {x}  z = {zi:5.2f}  p = sigmoid(z) = {pi:.4f}  says {int(pi > 0.5)}  target {t}")
print("  neuron(X, w, b) =", p)
print("  another check: neuron([3, −1], [0.5, 2], 0) =", round(float(sigmoid(np.array([3.0, -1.0]) @ np.array([0.5, 2.0]))), 7))

# --- can one line do XOR? Try many lines and keep the best ------------------
rng = np.random.default_rng(0)
best = 0
for _ in range(20000):
    w = rng.uniform(-4, 4, 2)
    b = rng.uniform(-6, 6)
    says = (X @ w + b > 0).astype(int)
    best = max(best, int((says == targets["XOR"]).sum()))
print(f"\nXOR: best of 20000 random lines gets {best} / 4 correct")

# --- binary cross-entropy -------------------------------------------------------
print("\n−ln p for the table:", {q: round(float(-np.log(q)), 2) + 0.0 for q in (1, 0.75, 0.5, 0.25, 0.1)})
y4 = np.array([0, 1, 1, 0], dtype=float)
p_flat = np.full(4, 0.5)
print(f"p = {p_flat} on XOR → loss = {bce(p_flat, y4):.4f}  (= ln 2, a coin flip)")

# a model that is 75% sure of the right answer on every point
p4 = np.where(y4 == 1, 0.75, 0.25)
print(f"p = {p4} → loss = {bce(p4, y4):.4f}  (= −ln 0.75)")
print(f"  by hand: ln 0.75 = {np.log(0.75):.3f}, ln 0.25 = {np.log(0.25):.3f} → every point costs {-np.log(0.75):.3f}")
print(f"bce([0.9, 0.2], [1, 1]) = {bce(np.array([0.9, 0.2]), np.array([1.0, 1.0])):.4f}")

# squared error versus cross-entropy for a confidently wrong answer (target 1)
print("\ntarget 1:  p      squared error   cross-entropy")
for q in (0.1, 0.01, 0.001):
    print(f"         {q:6.3f}   {(q - 1) ** 2:10.4f}   {-np.log(q):12.4f}")

p = np.array([0.5, 0.25])
print("\nnp.log([0.5, 0.25]) =", np.log(p), "  np.mean(...) =", round(float(np.mean(np.log(p))), 4))

# --- the neuron and its loss together (neuron_loss) ----------------------------
def neuron_loss(X, w, b, y):
    z = X @ w + b                    # one z per point, shape (4,)
    p = sigmoid(z)                   # one p per point
    return bce(p, y)


print("\nneuron_loss: z → p → loss")
for name, w, b, t in (("AND neuron on AND", [1.0, 1.0], -1.5, "AND"),
                      ("all-zero neuron on XOR", [0.0, 0.0], 0.0, "XOR"),
                      ("w = [2, 2], b = −1 on OR", [2.0, 2.0], -1.0, "OR")):
    w = np.array(w)
    y = np.array(targets[t], dtype=float)
    z = X @ w + b
    print(f"  {name}: z = {z}, p = {sigmoid(z)}, loss = {neuron_loss(X, w, b, y):.4f}")
