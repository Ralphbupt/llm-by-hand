"""
Level 19 · Modern blocks

Run:  python demo.py      (needs numpy)

Today's block: one stack and pre-norm (which levels 16 and 17 already use), plus three new parts
(RMSNorm, RoPE, SwiGLU), each checked with numbers small enough to follow by hand.
"""
import numpy as np

np.set_printoptions(precision=4, suppress=True)

# ---------------------------------------------------------------------------
# 1. Decoder-only: one stack, one kind of attention per layer
# ---------------------------------------------------------------------------
print("=== 1. decoder-only ===")
print("2017 encoder-decoder, decoder layer: 2 attention sublayers (self + cross)  (side trip N7)")
print("decoder-only layer:            1 attention sublayer (masked self)")
prompt, answer = "23+58=", "81"
seq = list(prompt + answer)
print("prompt and answer become one sequence:", seq)
print("the answer characters sit at positions", list(range(len(prompt), len(seq))),
      "; the guesses that produce them happen one step earlier, at", list(range(len(prompt) - 1, len(seq) - 1)))

# ---------------------------------------------------------------------------
# 2. Pre-norm vs post-norm: count the normalizations on the straight path
# ---------------------------------------------------------------------------
print("\n=== 2. pre-norm vs post-norm ===")
for n_layers in (2, 12, 48):
    print(f"{n_layers:2d} layers: post-norm puts {n_layers} LayerNorms on the residual path, pre-norm puts 1 (the final one)")


def layernorm(x, eps=1e-5):
    return (x - x.mean()) / np.sqrt(x.var() + eps)


# one real effect: post-norm squeezes the residual path back to size 1 after every layer,
# so a large update from one sublayer wipes out what came before.
x0 = np.array([1.0, -1.0, 0.5, -0.5])
update = np.array([3.0, 3.0, -3.0, -3.0])
post = layernorm(x0 + update)
pre = x0 + update
print("x0 =", x0, " sublayer output =", update)
print("post-norm keeps", np.round(post, 4), " pre-norm keeps", pre, "(x0 is still in there, added)")

# ---------------------------------------------------------------------------
# 3. RMSNorm vs LayerNorm on one vector
# ---------------------------------------------------------------------------
print("\n=== 3. RMSNorm vs LayerNorm ===")
x = np.array([1.0, 1.0, 3.0, 5.0])
mean = x.mean()
std = np.sqrt(((x - mean) ** 2).mean())
rms = np.sqrt((x ** 2).mean())
print("x =", x)
print(f"LayerNorm: mean = {mean:.4f}, std = {std:.4f}, out = {np.round((x - mean) / std, 4)}")
print(f"RMSNorm:   rms = sqrt(({' + '.join(f'{v:g}²' for v in x)}) / 4) = sqrt({(x ** 2).mean():g}) = {rms:.4f}")
print("           out =", np.round(x / rms, 4))
print("LayerNorm computes two averages (the mean, then the std); RMSNorm computes one (the mean of the squares) and subtracts nothing")


def rmsnorm(x, eps=1e-6):
    return x / np.sqrt(np.mean(x ** 2, axis=-1, keepdims=True) + eps)


print("rmsnorm([3, 4]) =", np.round(rmsnorm(np.array([3.0, 4.0])), 4))
tiny = np.array([0.001, 0.001])
print("rmsnorm([0.001, 0.001]) =", np.round(rmsnorm(tiny), 4), "  (mean square", np.mean(tiny ** 2),
      "is the size of eps; eps outside the root would give", np.round(tiny / (np.sqrt(np.mean(tiny ** 2)) + 1e-6), 4), ")")

# ---------------------------------------------------------------------------
# 4. RoPE: rotate by position, and the score only sees the distance
# ---------------------------------------------------------------------------
print("\n=== 4. RoPE ===")
THETA = 0.5   # radians per position, for this one pair of numbers


def rotate(v, pos, theta=THETA):
    a = pos * theta
    c, s = np.cos(a), np.sin(a)
    return np.array([c * v[0] - s * v[1], s * v[0] + c * v[1]])


q = np.array([1.0, 0.0])
k = np.array([0.0, 1.0])
print("rotate([1, 0] by position 2) =", np.round(rotate(q, 2), 4), "(angle 2 × 0.5 = 1 rad)")
for m, n in ((2, 0), (5, 3), (12, 10), (0, 2)):
    print(f"q at position {m:2d}, k at position {n:2d}: score = {rotate(q, m) @ rotate(k, n):.4f}   (distance {m - n})")
print("without RoPE the score is q·k =", q @ k)

# several pairs, several speeds: d = 4 has two pairs
d = 4
freqs = 10000.0 ** (-np.arange(0, d, 2) / d)
print("d = 4 uses", len(freqs), "pairs, rotating at", np.round(freqs, 4), "radians per position")


def rope(v, pos):
    out = v.copy()
    for i, f in enumerate(freqs):
        out[2 * i:2 * i + 2] = rotate(v[2 * i:2 * i + 2], pos, f)
    return out


rng = np.random.default_rng(0)
qv, kv = rng.normal(size=d), rng.normal(size=d)
a = rope(qv, 7) @ rope(kv, 4)
b = rope(qv, 107) @ rope(kv, 104)
print(f"random 4-number q, k: score at (7, 4) = {a:.6f}, at (107, 104) = {b:.6f}, difference {abs(a - b):.1e}")

# ---------------------------------------------------------------------------
# 5. SwiGLU: a gate times a value
# ---------------------------------------------------------------------------
print("\n=== 5. SwiGLU ===")


def silu(z):
    return z / (1 + np.exp(-z))


for z in (-2.0, -1.0, 0.0, 1.0, 2.0):
    print(f"  SiLU({z:4.1f}) = {silu(z):.4f}   ReLU = {max(z, 0):.1f}")
g, u = 1.0, 3.0
print(f"gate input {g}, value {u}: SiLU({g}) × {u} = {silu(g):.4f} × {u} = {silu(g) * u:.4f}")
d_model, d_ff = 512, 2048
plain = 2 * d_model * d_ff
h = plain / (3 * d_model)
print(f"plain FFN, d = {d_model}, hidden {d_ff}: 2 × {d_model} × {d_ff} = {plain:,} weights")
print(f"SwiGLU has 3 matrices; same weights when hidden = {plain:,} / (3 × {d_model}) = {h:.2f}")
print(f"with hidden 1365: 3 × 512 × 1365 = {3 * 512 * 1365:,}")
print(f"d_ff′ / d_ff = {h / d_ff:.4f}   (= 2/3, whatever d_model and d_ff are)")

# The "swiglu-code" exercise: a whole SwiGLU FFN with d_model = 2, d_ff = 3.
W_gate = np.array([[2.0, 0.0, 1.0], [0.0, 2.0, 1.0]])
W_up = np.array([[1.0, 1.0, 0.0], [0.0, 1.0, 1.0]])
W_down = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
for xs in ([[1.0, -1.0]], [[0.0, 1.0]], [[2.0, 1.0]]):
    xs = np.array(xs)
    gate, value = silu(xs @ W_gate), xs @ W_up
    out = (gate * value) @ W_down
    print(f"x = {xs[0]}: x @ W_gate = {xs @ W_gate}, gate = {gate.round(4)}, value = {value}, "
          f"gate × value = {(gate * value).round(4)}, out = {out.round(4)}")
x21 = np.array([[2.0, 1.0]])
print("SiLU around the product instead (wrong):", (silu((x21 @ W_gate) * (x21 @ W_up)) @ W_down).round(4))
print("two words in:", (silu(np.zeros((2, 2)) @ W_gate) * (np.zeros((2, 2)) @ W_up) @ W_down).shape)

print("\n2017 sizes, for comparison: d_model 512, 8 heads → d_k =", 512 // 8, "  d_ff =", 4 * 512)
