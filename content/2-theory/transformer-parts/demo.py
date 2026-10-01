"""
Level 16 · The parts of a Transformer

Run:  python demo.py      (needs numpy)

Positional encoding, the feed-forward network, residuals and LayerNorm, and how they make
a pre-norm decoder block. Every number the page asks about is printed here.
"""
import numpy as np

np.set_printoptions(precision=3, suppress=True)


def softmax(x, axis=-1):
    e = np.exp(x - x.max(axis=axis, keepdims=True))
    return e / e.sum(axis=axis, keepdims=True)


def self_attention(X):
    # Q = K = V = X, scaled by sqrt(d), as in level 14 section 2
    return softmax(X @ X.T / np.sqrt(X.shape[1])) @ X


# ---------------------------------------------------------------------------
# 1. Positional encoding
# ---------------------------------------------------------------------------
print("=== 1. positional encoding ===")


def positional_encoding(n_pos, d):
    pe = np.zeros((n_pos, d))
    for pos in range(n_pos):
        for i in range(d):
            angle = pos / 10000 ** ((i - i % 2) / d)   # pairs of columns share one speed
            pe[pos, i] = np.sin(angle) if i % 2 == 0 else np.cos(angle)
    return pe


cat, dog, car = np.array([2.0, 0.0]), np.array([1.0, 1.0]), np.array([0.0, 2.0])
PE = positional_encoding(3, 2)
print("PE for 3 positions, d = 2 (column 0 = sin(pos), column 1 = cos(pos)):")
print(PE)
print(f"PE[0] = [sin(0), cos(0)] = {PE[0].tolist()}, so PE[0][1] = {PE[0, 1]:.0f}")
print("PE for 10 tokens, d_model 8 has shape", positional_encoding(10, 8).shape)

# the table is built once for the longest sentence; a sentence of L tokens uses its first L rows
table = positional_encoding(16, 2)
print("position table for up to 16 tokens:", table.shape, "→ a 3-token sentence uses table[:3]:", table[:3].shape)

# why the word vector is multiplied by sqrt(d_model) before the position is added
word = np.array([-0.77, -0.62, 0.91, -0.28])
pe0 = positional_encoding(1, 4)[0]
print("\nd_model = 4, word =", word, " PE[0] =", pe0)
print("  word + PE[0]           =", (word + pe0).round(2), " (the second and fourth numbers change sign)")
print("  word * sqrt(4) + PE[0] =", (word * np.sqrt(4) + pe0).round(2), " (the word is now bigger than the position)")
print("  d_model = 64 → multiply by sqrt(64) =", np.sqrt(64))

print("\nwithout PE:")
a = self_attention(np.array([cat, dog, car]))[0]
b = self_attention(np.array([car, dog, cat]))[2]
print("  cat first:", a, "  cat last:", b, "  same?", np.allclose(a, b))
print("with PE:")
a = self_attention(np.array([cat, dog, car]) + PE)[0]
b = self_attention(np.array([car, dog, cat]) + PE)[2]
print("  cat first:", a, "  cat last:", b, "  same?", np.allclose(a, b))

# ---------------------------------------------------------------------------
# 2. Feed-forward network: Linear → ReLU → Linear, the same for every word
# ---------------------------------------------------------------------------
print("\n=== 2. FFN ===")
X = np.array([cat, dog, car])
W1 = np.array([[1.0, -1.0, 0.0, 1.0],
               [0.0, 1.0, -1.0, 1.0]])            # (2, 4): widen
b1 = np.array([0.0, 0.0, 1.0, -2.0])
W2 = np.array([[1.0, 0.0],
               [0.0, 1.0],
               [-1.0, 1.0],
               [0.5, 0.5]])                       # (4, 2): narrow back
b2 = np.zeros(2)

pre = X @ W1 + b1
H = np.maximum(0, pre)
out = H @ W2 + b2
print("X @ W1 + b1, shape", pre.shape)
print(pre)
print("ReLU, shape", H.shape)
print(H)
for w, h in zip(["cat", "dog", "car"], H):
    print(f"  {w}: {int((h > 0).sum())} of 4 hidden units on")
print("output, shape", out.shape)
print(out)
alone = np.maximum(0, cat @ W1 + b1) @ W2 + b2
print("cat alone:", alone, " same as row 0?", np.allclose(alone, out[0]))
print("shape chain: (3,2) @ (2,4) → (3,4) → ReLU → (3,4) @ (4,2) → (3,2)")

# ---------------------------------------------------------------------------
# 3. LayerNorm and residuals
# ---------------------------------------------------------------------------
print("\n=== 3. LayerNorm ===")


def layer_norm(x, eps=1e-5):
    mu = x.mean(axis=-1, keepdims=True)              # one mean per word (last axis)
    var = x.var(axis=-1, keepdims=True)
    return (x - mu) / np.sqrt(var + eps)


v = np.array([1.0, 2.0, 3.0, 6.0])
print("v =", v, " mean =", v.mean(), " std =", round(v.std(), 3))
print("layer_norm(v) =", layer_norm(v))
print(f"6 becomes {layer_norm(v)[3]:.3f}")
w = np.array([1.0, 1.0, 5.0, 5.0])
print("LayerNorm [1, 1, 5, 5]: mean", w.mean(), " spread", w.std(), " ->", layer_norm(w).round(3))
Xb = np.random.default_rng(0).standard_normal((2, 5, 8))
print("X is (2, 5, 8): LayerNorm computes", Xb.mean(axis=-1).size, "means, one per word")


# eps sits inside the square root; it matters when a row's variance is tiny
tiny = np.array([0.0, 0.002])
print("tiny spread [0, 0.002]: variance", tiny.var(), " layer_norm →", layer_norm(tiny).round(4).tolist(),
      " (eps outside the root would give", ((tiny - tiny.mean()) / (tiny.std() + 1e-5)).round(4).tolist(), ")")


# the code exercise: the FFN sublayer with its residual, X + ffn(X)
def ffn_block(X):
    h = np.maximum(0, X @ W1 + b1)                   # (L, 4): widen, ReLU
    return X + h @ W2 + b2                           # (L, 2): narrow back, add the input


print("\nFFN sublayer with its residual on cat, dog, car:")
print("  FFN(X)     =", out.tolist())
print("  X + FFN(X) =", ffn_block(X).tolist(), " shape", ffn_block(X).shape)
x1 = np.array([[1.0, 1.0]])
print("  dog alone, [1, 1]: FFN", (np.maximum(0, x1 @ W1 + b1) @ W2 + b2).tolist(), " x + FFN(x) =", ffn_block(x1).tolist())
print("  without ReLU it would be", (X + (X @ W1 + b1) @ W2 + b2).tolist())
print("  post-norm (the 2017 placement) would add LayerNorm:", layer_norm(ffn_block(X)).round(3).tolist())

print("\ndepth: 30 layers of x ← x W, W random with spread gain/sqrt(d)")
rng = np.random.default_rng(1)
d = 8
x0 = np.array([1.0, -1.0, 0.5, 2.0, -0.5, 1.5, -2.0, 0.0])
for gain in (0.5, 1.5):
    Ws = [rng.standard_normal((d, d)) * gain / np.sqrt(d) for _ in range(30)]
    for mode in ("plain", "residual", "residual+norm"):
        x = x0.copy()
        for W in Ws:
            fx = x @ W
            x = fx if mode == "plain" else x + fx
            if mode == "residual+norm":
                x = layer_norm(x)
        print(f"  gain {gain}, {mode:14s}: size after 30 layers = {np.linalg.norm(x):.3g}")
print("  LayerNorm keeps the size at sqrt(8) =", round(np.sqrt(8), 3))

# ---------------------------------------------------------------------------
# 4. A pre-norm decoder block: x = x + attention(LN(x)), then x = x + ffn(LN(x))
# ---------------------------------------------------------------------------
print("\n=== 4. a decoder block (pre-norm) ===")


def attention(x):
    """masked self-attention with Q = K = V = x and no weights, as in the code exercise"""
    L, d = x.shape
    scores = x @ x.T / np.sqrt(d)
    blocked = np.triu(np.ones((L, L), dtype=bool), k=1)
    return softmax(np.where(blocked, -np.inf, scores)) @ x


def ffn2(x):
    return np.maximum(0, x @ W1 + b1) @ W2          # section 2's weights (b2 is 0)


def decoder_block(x, show=False):
    a = attention(layer_norm(x))
    if show:
        print("  layer_norm(x)            ", layer_norm(x).round(4).tolist())
        print("  attention(layer_norm(x)) ", a.round(4).tolist())
    x = x + a
    if show:
        print("  x after attention        ", x.round(4).tolist())
        print("  ffn hidden (after ReLU)  ", np.maximum(0, layer_norm(x) @ W1 + b1).round(4).tolist())
        print("  ffn(layer_norm(x))       ", ffn2(layer_norm(x)).round(4).tolist())
    x = x + ffn2(layer_norm(x))
    return x


print("worked example, one token [0, 4]:")
print("  output", decoder_block(np.array([[0.0, 4.0]]), show=True).round(4).tolist())
print("cat, dog, car:")
print("  output", decoder_block(X, show=True).round(4).tolist())
print("[3, 1] →", decoder_block(np.array([[3.0, 1.0]])).round(4).tolist())


def decoder(x, n_blocks):
    """the code exercise: n_blocks pre-norm blocks, then one final LayerNorm"""
    for i in range(n_blocks):
        x = decoder_block(x)
    return layer_norm(x)


x0 = np.array([[0.0, 4.0]])
for n in (1, 2):
    path, x = [x0[0].tolist()], x0
    for i in range(n):
        x = x + attention(layer_norm(x))
        path.append(x[0].round(4).tolist())
        x = x + ffn2(layer_norm(x))
        path.append(x[0].round(4).tolist())
    print(f"decoder([0, 4], {n}): residual path {path} → final LayerNorm", decoder(x0, n).round(4).tolist())
print("decoder(cat, dog, car, 1):", decoder(X, 1).round(4).tolist())

# the predict: a sublayer that outputs zeros leaves x unchanged in pre-norm, but not in post-norm
x1 = np.array([3.0, 1.0])
print("\nsublayer output [0, 0] for x = [3, 1]:  pre-norm x + 0 =", (x1 + 0).tolist(),
      "  post-norm LayerNorm(x + 0) =", layer_norm(x1).round(4).tolist())
print("post-norm block on cat, dog, car:",
      layer_norm(layer_norm(X + attention(X)) + ffn2(layer_norm(X + attention(X)))).round(4).tolist())

# LayerNorms in a stack: 2 per block, plus one final LayerNorm before the output layer
blocks = 3
print(f"\n{blocks} blocks: {2 * blocks} LayerNorms in the blocks + 1 final = {2 * blocks + 1}")

# every block keeps the shape (B, L, d_model), so blocks stack
rng = np.random.default_rng(2)
B, L, d_model, d_ff = 2, 5, 8, 32
Wq, Wk, Wv, Wo = (rng.standard_normal((d_model, d_model)) / np.sqrt(d_model) for _ in range(4))
Wa, Wb = rng.standard_normal((d_model, d_ff)) / np.sqrt(d_model), rng.standard_normal((d_ff, d_model)) / np.sqrt(d_ff)
x = rng.standard_normal((B, L, d_model))
causal = np.triu(np.ones((L, L), dtype=bool), k=1)
print("\ninput", x.shape)
for i in range(2):
    h = layer_norm(x)
    s = (h @ Wq) @ np.swapaxes(h @ Wk, -1, -2) / np.sqrt(d_model)
    w = softmax(np.where(causal, -np.inf, s))
    x = x + w @ (h @ Wv) @ Wo
    hidden = np.maximum(0, layer_norm(x) @ Wa)
    x = x + hidden @ Wb
    print(f"block {i + 1}: scores {s.shape}, FFN hidden {hidden.shape}, output {x.shape}")
print("final LayerNorm", layer_norm(x).shape)
