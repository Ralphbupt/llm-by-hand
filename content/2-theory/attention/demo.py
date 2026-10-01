"""
Level 14 · Self-attention

Run:  python demo.py      (needs numpy)

Three words, two numbers each. Every number the page asks about is printed here.
    attention(Q, K, V) = softmax(Q @ K.T / sqrt(d_k)) @ V
"""
import numpy as np

np.set_printoptions(precision=3, suppress=True)


def softmax(x, axis=-1):
    e = np.exp(x - x.max(axis=axis, keepdims=True))   # subtract the max so exp never overflows
    return e / e.sum(axis=axis, keepdims=True)         # each row now adds up to 1


# ---------------------------------------------------------------------------
# 0. Why not read left to right: in an RNN, word 1's effect is multiplied by w at every later step
# ---------------------------------------------------------------------------
w = 0.5
print("=== 0. reading left to right (RNN, w = 0.5, ignoring tanh) ===")
print("after 3 more words: 0.5 × 0.5 × 0.5 =", w ** 3)
for later in (1, 2, 5, 10, 50):
    print(f"  {later:2d} words later: word 1's effect × {w ** later:.3g}")
print()

words = ["cat", "dog", "car"]
X = np.array([[2.0, 0.0],    # cat
              [1.0, 1.0],    # dog
              [0.0, 2.0]])   # car
d_k = X.shape[1]
print("X, shape", X.shape, "(one row per word)")
print(X)

# ---------------------------------------------------------------------------
# 1. Attention is a weighted average  (Q = K = V = X, no projections yet)
# ---------------------------------------------------------------------------
print("\n=== 1. weighted average ===")
scores = X @ X.T                       # (3,2) @ (2,3) → (3,3): every word dotted with every word
print("scores = X @ X.T, shape", scores.shape)
print(scores)
print("cat · dog = 2×1 + 0×1 =", scores[0, 1])

w_plain = softmax(scores)
print("\nweights without scaling (softmax of each row):")
print(w_plain)
scaled = scores / np.sqrt(d_k)
print("\nscores / sqrt(2):")
print(scaled)
weights = softmax(scaled)
print("weights with scaling:")
print(weights)
print("each row adds up to", weights.sum(axis=1))
print(f"cat looks at itself: {w_plain[0, 0]:.3f} without scaling, {weights[0, 0]:.3f} with scaling")

out = weights @ X
print("\noutput = weights @ X, shape", out.shape)
print(out)
w = weights[0]
print(f"cat's output = {w[0]:.3f}×cat + {w[1]:.3f}×dog + {w[2]:.3f}×car")
print(f"  x = {w[0]:.3f}×2 + {w[1]:.3f}×1 + {w[2]:.3f}×0 = {out[0, 0]:.3f}")

print("rows are the words that look, columns the words being looked at:")
print(f"  weights[0][2] = {weights[0, 2]:.3f}: cat (row 0) looks at car (column 2)")

X5 = np.array([[2.0, 0.0], [1.0, 1.0], [5.0, 5.0]])
w5 = softmax(X5 @ X5.T / np.sqrt(d_k))
print("\nmake car [5, 5]: car's row of weights =", w5[2], "(it looks almost only at itself)")

# ---------------------------------------------------------------------------
# 2. Q, K, V projections
# ---------------------------------------------------------------------------
print("\n=== 2. Q, K, V ===")
W_Q = np.eye(2)
W_K = np.array([[0.0, 1.0], [1.0, 0.0]])   # swaps the two numbers of every key
W_V = np.eye(2)
Q, K, V = X @ W_Q, X @ W_K, X @ W_V
print("K = X @ W_K (columns swapped):")
print(K)
s2 = Q @ K.T
print("scores = Q @ K.T:")
print(s2)
w2 = softmax(s2 / np.sqrt(d_k))
print("weights:")
print(w2)
print("cat now looks mostly at:", words[int(w2[0].argmax())])
print("still symmetric?", np.allclose(s2, s2.T), "(W_Q @ W_K.T is symmetric, so the scores are too)")

W_K = np.array([[0.0, 0.0], [1.0, 0.0]])   # "one-way" keys: each key is [y, 0]
K = X @ W_K
s3 = (X @ np.eye(2)) @ K.T
print("\none-way W_K:")
print(W_K)
print("K = X @ W_K:")
print(K)
print("scores = Q @ K.T:")
print(s3)
print("symmetric?", np.allclose(s3, s3.T), " scores[0,2] =", s3[0, 2], " scores[2,0] =", s3[2, 0])
print("weights:")
print(softmax(s3 / np.sqrt(d_k)))

# ---------------------------------------------------------------------------
# 3. Attention is learned: one knob
# ---------------------------------------------------------------------------
print("\n=== 3. one knob ===")
# two words: apple = [1, 0], sweet = [0, 1]. "sweet" should copy apple's content: target output [1, 0].
# W_Q = [[0, 0], [c, 0]] so sweet's query is [c, 0]; its scores are [c, 0] / sqrt(2).
def knob(c):
    p = 1 / (1 + np.exp(-c / np.sqrt(2)))           # softmax of two numbers = sigmoid of their difference
    loss = (p - 1) ** 2 + ((1 - p) - 0) ** 2         # output is [p, 1 - p], target [1, 0]
    grad = -4 * (1 - p) * p * (1 - p) / np.sqrt(2)  # dloss/dc
    return p, loss, grad

c, lr = 0.0, 1.0
p, loss, _ = knob(c)
print(f"c = 0: sweet puts {p:.3f} on apple, loss = {loss:.3f}")
for step in range(1, 1001):
    p, loss, g = knob(c)
    c -= lr * g
    if step in (1, 10, 100, 1000):
        p, loss, _ = knob(c)
        print(f"step {step:4d}: c = {c:.3f}, weight on apple = {p:.3f}, loss = {loss:.5f}")
print("c keeps growing: softmax only reaches exactly 1 at infinity")

# ---------------------------------------------------------------------------
# 4. Why divide by sqrt(d_k)
# ---------------------------------------------------------------------------
print("\n=== 4. why sqrt(d_k) ===")
rng = np.random.default_rng(0)
for d in (2, 64, 512):
    q, k = rng.standard_normal((10000, d)), rng.standard_normal((10000, d))
    dots = (q * k).sum(1)
    print(f"d_k = {d:3d}: spread (std) of q·k = {dots.std():6.2f},  after / sqrt(d_k) = {(dots / np.sqrt(d)).std():.2f}")

# ---------------------------------------------------------------------------
# 5. The loss never looks at the weights: train W_V too, and the attention changes
# ---------------------------------------------------------------------------
print("\n=== 5. same loss, different attention ===")
# apple = [1, 0], sweet = [0, 1]; sweet's output should be apple's content [1, 0].
XA = np.array([[1.0, 0.0], [0.0, 1.0]])
target = np.array([1.0, 0.0])

def sweet_out(P):
    W_Q, W_K, W_V = P
    q = XA[1] @ W_Q                                    # sweet's query
    w = softmax(q @ (XA @ W_K).T / np.sqrt(2))         # sweet's weights over [apple, sweet]
    return w, w @ (XA @ W_V)

def loss_of(P):
    return float(((sweet_out(P)[1] - target) ** 2).sum())

def train(P, which, steps=3000, lr=0.5, h=1e-5):
    P = [p.copy() for p in P]
    for _ in range(steps):
        for i in which:                                # numeric gradient: nudge each number up and down
            g = np.zeros_like(P[i])
            for idx in np.ndindex(P[i].shape):
                old = P[i][idx]
                P[i][idx] = old + h; up = loss_of(P)
                P[i][idx] = old - h; dn = loss_of(P)
                P[i][idx] = old
                g[idx] = (up - dn) / (2 * h)
            P[i] -= lr * g
    return P

I = np.eye(2)
runs = [("W_V fixed (identity), train W_Q and W_K", [I, I, I], [0, 1]),
        ("train all three, start from identity", [I, I, I], [0, 1, 2])]
for seed in (0, 1):
    r = np.random.default_rng(seed)
    runs.append((f"train all three, random start (seed {seed})", [r.normal(size=(2, 2)) for _ in range(3)], [0, 1, 2]))
for name, P0, which in runs:
    P = train(P0, which)
    w, o = sweet_out(P)
    print(f"{name:45s} weight on apple = {w[0]:.2f}, output = {o.round(3)}, loss = {loss_of(P):.4f}")
print("every run reaches (almost) the right output, but the attention weights differ: the loss only checks the output")

# ---------------------------------------------------------------------------
# 6. One attention head from start to end (the checkpoint)
# ---------------------------------------------------------------------------
print("\n=== 6. self-attention ===")
def self_attention(X, W_Q, W_K, W_V):
    d_k = W_Q.shape[1]
    Q, K, V = X @ W_Q, X @ W_K, X @ W_V
    scores = Q @ K.T / np.sqrt(d_k)
    return softmax(scores) @ V

W_swap = np.array([[0.0, 1.0], [1.0, 0.0]])
print("every matrix the identity:\n", self_attention(X, np.eye(2), np.eye(2), np.eye(2)))
print("swapped keys:\n", self_attention(X, np.eye(2), W_swap, np.eye(2)))
print("V keeps only x:\n", self_attention(X, np.eye(2), np.eye(2), np.array([[1.0, 0.0], [0.0, 0.0]])))
