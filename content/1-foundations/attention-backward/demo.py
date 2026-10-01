"""
Level U6 · Backward through attention

Run:  python demo.py      (needs only numpy)

1. Softmax backward: the Jacobian diag(p) − pᵀp, the fast form p ⊙ (dp − dp·p), and a numeric check.
2. One attention head backward: dOut → dA, dV → dS → dQ, dK, with the shape of every step,
   on the page's 2-word example, then a numeric gradient check on random numbers.
3. The memory ledger: what backward keeps, bytes per parameter with mixed-precision Adam,
   and how activations and attention scores grow.
Every number the page asks about is printed below.
"""
import numpy as np

np.set_printoptions(precision=4, suppress=True)


def softmax(x, axis=-1):
    e = np.exp(x - x.max(axis=axis, keepdims=True))
    return e / e.sum(axis=axis, keepdims=True)


def softmax_backward(p, dp):
    # dz = p ⊙ (dp − (dp · p)), row by row
    return p * (dp - (dp * p).sum(axis=-1, keepdims=True))


def numeric_grad(f, X, h=1e-5):
    """∂f/∂X, one entry at a time: (f(X + h) − f(X − h)) / 2h."""
    G = np.zeros_like(X)
    for idx in np.ndindex(X.shape):
        old = X[idx]
        X[idx] = old + h
        up = f()
        X[idx] = old - h
        down = f()
        X[idx] = old
        G[idx] = (up - down) / (2 * h)
    return G


print("=" * 60)
print("1. Softmax backward")
print("=" * 60)
z = np.array([np.log(2.0), 0.0, 0.0])
p = softmax(z)
print("z =", z, " (ln 2, 0, 0)")
print("p = softmax(z) =", p)

J = np.diag(p) - np.outer(p, p)
print("\nJacobian J = diag(p) − pᵀp, J[i][j] = ∂p_i/∂z_j:")
print(J)
print("J[0][0] = p0(1 − p0) =", J[0, 0])
print("J[1][1] = p1(1 − p1) =", J[1, 1])
print("J[0][1] = −p0·p1     =", J[0, 1])
print("row sums of J:", J.sum(axis=1), " (adding c to every z leaves p unchanged)")

dp = np.array([1.0, 0.0, 2.0])
print("\ndp =", dp)
dot = dp @ p
print("dp · p =", dot)
print("dp − dp·p =", dp - dot)
dz_fast = p * (dp - dot)
dz_jac = dp @ J
print("dz = p ⊙ (dp − dp·p) =", dz_fast)
print("dz = dp @ J          =", dz_jac)

# the page's check of both ways, with dp = [1, 1, 0]
dpb = np.array([1.0, 1.0, 0.0])
print("\ndp = [1, 1, 0]: column 0 of J =", J[:, 0])
print("  long way:  dz0 = dp @ J[:, 0] =", dpb @ J[:, 0])
print("  short way: dp·p =", dpb @ p, " dz0 = p0 × (dp0 − dp·p) =", p[0] * (dpb[0] - dpb @ p))

# numeric check: L = dp · softmax(z) has dL/dp = dp
zc = z.copy()
num = numeric_grad(lambda: dp @ softmax(zc), zc)
print("numeric dz            =", num)
print("largest difference    =", f"{np.abs(num - dz_fast).max():.2e}")

# saturated softmax passes almost no gradient
zs = np.array([10.0, 0.0, 0.0])
ps = softmax(zs)
print("\nsaturated: z =", zs, "p =", ps)
print("J =\n", np.diag(ps) - np.outer(ps, ps))

# the code exercise's test rows
P2 = np.array([[0.5, 0.25, 0.25], [0.1, 0.2, 0.7]])
D2 = np.array([[1.0, 0.0, 2.0], [3.0, -1.0, 0.0]])
print("\ncode test: softmax_backward(P2, D2) =\n", softmax_backward(P2, D2))

print("\n" + "=" * 60)
print("2. One attention head, backward (2 words, d_k = 4, d_v = 2)")
print("=" * 60)
Q = np.array([[1.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 1.0]])
K = np.array([[1.0, -1.0, 0.0, 0.0], [0.0, 0.0, 1.0, -1.0]])
V = np.array([[2.0, 0.0], [1.0, 1.0]])
dO = np.array([[1.0, 0.0], [0.0, 2.0]])
d_k = Q.shape[1]
print("Q", Q.shape, "\n", Q)
print("K", K.shape, "\n", K)
print("V", V.shape, "\n", V)
print("√d_k =", np.sqrt(d_k))

S = Q @ K.T / np.sqrt(d_k)
A = softmax(S)
O = A @ V
print("\nforward")
print("S = Q @ K.T / √d_k", S.shape, "\n", S)
print("A = softmax(S)", A.shape, "\n", A)
print("O = A @ V", O.shape, "\n", O)

print("\nbackward, from dO", dO.shape, "\n", dO)
dV = A.T @ dO
dA = dO @ V.T
print("dV = A.T @ dO", dV.shape, "\n", dV)
print("dA = dO @ V.T", dA.shape, "\n", dA)
rowdot = (dA * A).sum(axis=-1, keepdims=True)
print("row by row dA·A", rowdot.shape, "\n", rowdot)
dS = A * (dA - rowdot)
print("dS = A ⊙ (dA − dA·A)", dS.shape, "\n", dS)
print("row sums of dS:", dS.sum(axis=1))
dQ = dS @ K / np.sqrt(d_k)
dK = dS.T @ Q / np.sqrt(d_k)
print("dQ = dS @ K / √d_k", dQ.shape, "\n", dQ)
print("dK = dS.T @ Q / √d_k", dK.shape, "\n", dK)
print("dK[0][2] =", dK[0, 2], " (column 0 of dS, [0.25, -0.5], times entry 2 of each query, / 2)")
print("the wrong dS @ Q / √d_k gives [0][2] =", (dS @ Q / np.sqrt(d_k))[0, 2])

print("fused kernels: dA·A row by row equals dO·O row by row (no A needed)")
print("  dA·A:", (dA * A).sum(axis=-1), " dO·O:", (dO * O).sum(axis=-1))


def attention_forward(Q, K, V):
    d_k = Q.shape[1]
    S = Q @ K.T / np.sqrt(d_k)
    A = softmax(S)
    O = A @ V
    return O, (Q, K, V, A)


def attention_backward(dO, saved):
    Q, K, V, A = saved
    d_k = Q.shape[1]
    dV = A.T @ dO
    dA = dO @ V.T
    dS = A * (dA - (dA * A).sum(axis=-1, keepdims=True))
    dQ = dS @ K / np.sqrt(d_k)
    dK = dS.T @ Q / np.sqrt(d_k)
    return dQ, dK, dV


print("\ngradient check on random numbers (L = 3, d_k = 2, d_v = 4)")
rng = np.random.default_rng(0)
Qr, Kr, Vr = rng.normal(size=(3, 2)), rng.normal(size=(3, 2)), rng.normal(size=(3, 4))
G = rng.normal(size=(3, 4))      # L = sum(G * O), so dO = G
loss = lambda: (G * attention_forward(Qr, Kr, Vr)[0]).sum()
_, saved = attention_forward(Qr, Kr, Vr)
grads = attention_backward(G, saved)
for name, X, g in zip(["dQ", "dK", "dV"], [Qr, Kr, Vr], grads):
    n = numeric_grad(loss, X)
    print(f"{name} {g.shape}: largest difference from numeric = {np.abs(n - g).max():.2e}")

# the backward pass uses the A it was given: a saved A that is not softmax(S) changes the answer
A_odd = np.array([[0.75, 0.25], [0.25, 0.75]])
dQo, dKo, dVo = attention_backward(dO, (Q, K, V, A_odd))
print("\nwith a saved A =", A_odd.tolist(), "(not softmax(S)):")
print("dV =", dVo.tolist())
print("dQ =", dQo.tolist())
print("dK =", dKo.tolist())

print("\n" + "=" * 60)
print("3. The memory ledger")
print("=" * 60)
ledger = {"weights (bf16)": 2, "gradients (bf16)": 2, "master weights (fp32)": 4, "Adam m (fp32)": 4, "Adam v (fp32)": 4}
for k, v in ledger.items():
    print(f"  {k:24s} {v} bytes")
per = sum(ledger.values())
print("bytes per parameter:", per)
for n in [1e9, 7e9]:
    print(f"{n / 1e9:.0f} billion parameters → {per * n / 1e9:.0f} GB")

B, h, L, d_model = 4, 8, 1000, 1000
scores = B * h * L * L * 2
act = B * L * d_model * 2
print(f"\nB = {B}, heads = {h}, L = {L}, d_model = {d_model}, 2 bytes per number")
print(f"one (B, L, d_model) activation: {act:,} bytes = {act / 1e6:.0f} MB")
print(f"attention weights A (B, h, L, L): {scores:,} bytes = {scores / 1e6:.0f} MB per layer")
scores2 = B * h * (2 * L) ** 2 * 2
act2 = B * (2 * L) * d_model * 2
print(f"L = {2 * L}: activation {act2 / 1e6:.0f} MB (×{act2 / act:.0f}), A {scores2 / 1e6:.0f} MB (×{scores2 / scores:.0f})")
layers = 24
print(f"A over {layers} layers at L = {L}: {layers * scores / 1e9:.3f} GB")

# what one pre-norm block keeps, in units of one (B, L, d_model) tensor
block = {"input of LayerNorm 1": 1, "input of the Q, K, V products": 1, "Q, K, V": 3, "heads' output": 1,
         "input of LayerNorm 2": 1, "input of the FFN": 1, "FFN hidden, before ReLU": 4, "FFN hidden, after ReLU": 4}
units = sum(block.values())
print(f"\none pre-norm block keeps {' + '.join(str(v) for v in block.values())} = {units} units")
print(f"  at L = {L}: {units} × {act / 1e6:.0f} MB = {units * act / 1e6:.0f} MB, A = {scores / 1e6:.0f} MB")
print(f"  at L = {2 * L}: {units * act2 / 1e6:.0f} MB, A = {scores2 / 1e6:.0f} MB")

print("\nrecomputation: keep only each layer's input, redo the forward pass during backward")
print(f"  kept per layer: one ({B}, {L}, {d_model}) input = {act / 1e6:.0f} MB, instead of A alone = {scores / 1e6:.0f} MB")
print("  peak: the kept inputs, plus one layer's values while the backward pass recomputes it")
print("  cost: one extra forward pass. Forward ≈ 1 unit, backward ≈ 2 units → 3 + 1 = 4, about 33% more arithmetic")

print("\nthe lab's model: 24 layers, d_model 1000, h 8, 300 million parameters,")
print(f"{units} (B, L, d_model) tensors per layer, plus A")
for Bl, Ll in [(4, 1000), (4, 2000), (16, 8000)]:
    pm = 300e6 * per
    ac = units * Bl * Ll * d_model * 2 * layers
    at = Bl * h * Ll * Ll * 2 * layers
    print(f"  B = {Bl}, L = {Ll}: parameters {pm / 1e9:.1f} GB, activations {ac / 1e9:.2f} GB, A {at / 1e9:.2f} GB, total {(pm + ac + at) / 1e9:.1f} GB")
