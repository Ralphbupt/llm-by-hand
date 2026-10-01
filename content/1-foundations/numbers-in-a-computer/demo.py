"""
Level U2 · Numbers in a computer

Run:  python demo.py      (needs numpy; uses torch only to double-check bfloat16, if it is installed)

How float32, float16 and bfloat16 store a number, where they overflow and underflow,
why softmax subtracts the max, and why loss can become NaN. Every number the page asks about is printed below.
"""
import numpy as np

np.seterr(all="ignore")   # we want to SEE the inf and nan, not get warnings

FORMATS = {               # name: (exponent bits, mantissa bits)
    "float32": (8, 23),
    "float16": (5, 10),
    "bfloat16": (8, 7),
}


def decode(sign, exp_field, mant_field, E, M):
    """The value of a normal float: (−1)^sign × (1 + mant / 2^M) × 2^(exp − bias)."""
    bias = 2 ** (E - 1) - 1
    return (-1) ** sign * (1 + mant_field / 2 ** M) * 2.0 ** (exp_field - bias)


def to_bf16(x):
    """Round float32 numbers to bfloat16 (keep the top 16 bits, round to nearest, ties to even)."""
    b = np.asarray(x, dtype=np.float32).view(np.uint32).astype(np.uint64)
    b = (b + 0x7FFF + ((b >> 16) & 1)) >> 16 << 16
    return b.astype(np.uint32).view(np.float32)


def bits(x, fmt):
    if fmt == "float32":
        u = int(np.float32(x).view(np.uint32)); E, M = 8, 23; n = 32
    elif fmt == "float16":
        u = int(np.float16(x).view(np.uint16)); E, M = 5, 10; n = 16
    else:
        u = int(to_bf16(x).view(np.uint32)) >> 16; E, M = 8, 7; n = 16
    s = f"{u:0{n}b}"
    return f"{s[0]} {s[1:1 + E]} {s[1 + E:]}"


# --- section 1: three formats -----------------------------------------------------
print("--- the three formats ---")
for name, (E, M) in FORMATS.items():
    bias = 2 ** (E - 1) - 1
    largest = (2 - 2.0 ** -M) * 2.0 ** bias
    print(f"{name:9s} exponent bits {E}, mantissa bits {M}, bias {bias:3d}, "
          f"numbers in [1, 2): {2 ** M:7d}, gap after 1: {2.0 ** -M:.3g}, largest: {largest:.4g}, "
          f"smallest normal: {2.0 ** (1 - bias):.3g}")

print("\nfloat16 bits 0 10001 1000000000 →", decode(0, 0b10001, 0b1000000000, 5, 10))
print("check: bits of 6 in float16:", bits(6, "float16"))
for v in [1, 6, -2, 0.1]:
    print(f"bits of {v:>4} in float16:", bits(v, "float16"), "   bfloat16:", bits(v, "bfloat16"))

print("\n0.1 is stored as")
print("  float32 :", f"{float(np.float32(0.1)):.12f}")
print("  float16 :", f"{float(np.float16(0.1)):.12f}")
print("  bfloat16:", f"{float(to_bf16(0.1)):.12f}")

print("\ngap between neighbors in [256, 512): bfloat16", 256 * 2.0 ** -7, " float16", 256 * 2.0 ** -10)
print("256 + 0.75 in bfloat16 =", float(to_bf16(np.float32(256 + 0.75))))
print("256 + 1    in bfloat16 =", float(to_bf16(np.float32(257))), "(an exact tie: goes to the even neighbor)")
print("256 + 1.5  in bfloat16 =", float(to_bf16(np.float32(257.5))))

# --- section 2: overflow and underflow ---------------------------------------------
print("\n--- overflow and underflow ---")
a = np.float16(300)
print("float16: 300 × 300 =", a * a, "  (largest float16 is", np.finfo(np.float16).max, ")")
print("float32: 300 × 300 =", np.float32(300) * np.float32(300))
for z in [11, 12]:
    print(f"e^{z} = {np.exp(float(z)):.0f};  in float16: {np.exp(np.float16(z))}")
print("float32 overflows at z = ln(largest) =", round(float(np.log(np.finfo(np.float32).max)), 2),
      "; np.exp(np.float32(89)) =", np.exp(np.float32(89)))
print("np.exp(np.float32(-1000)) =", np.exp(np.float32(-1000)), "(underflow to 0)")
print("smallest positive float16 (subnormal):", float(np.float16(2.0 ** -24)), "; 1e-8 in float16 =", float(np.float16(1e-8)))
print("1e-8 × 1024 in float16 =", float(np.float16(1e-8 * 1024)))

# --- section 3: softmax ---------------------------------------------------------------
print("\n--- softmax ---")
z = np.array([1000.0, 1001.0], dtype=np.float32)
e = np.exp(z)
print("naive: e^z =", e, " sum =", e.sum(), " p =", e / e.sum())
print("inf / inf =", np.float32(np.inf) / np.float32(np.inf))
zm = z - z.max()
e2 = np.exp(zm)
print("stable: z − max =", zm, " e^(z − max) =", e2.round(4), " sum =", e2.sum().round(4),
      " p =", (e2 / e2.sum()).round(2))
print("small scores [1, 2]: naive p =", (np.exp([1.0, 2]) / np.exp([1.0, 2]).sum()).round(2))

# --- section 4: log-sum-exp and the loss ----------------------------------------------------
print("\n--- log-sum-exp ---")


def logsumexp(z):
    m = z.max(axis=-1, keepdims=True)
    return m[..., 0] + np.log(np.exp(z - m).sum(axis=-1))


zz = np.array([1000.0, 1000.0])
print("naive ln(e^1000 + e^1000) =", np.log(np.exp(zz).sum()))
print("logsumexp([1000, 1000]) =", round(float(logsumexp(zz)), 2), " (1000 + ln 2, ln 2 ≈", round(np.log(2), 2), ")")
print("cross-entropy, scores [1000, 1000], target 0 =", round(float(logsumexp(zz) - zz[0]), 2))

p = np.exp(np.float32(-1000)) / (np.exp(np.float32(-1000)) + np.exp(np.float32(0)))
print("naive: p of a target with score −1000 vs 0 =", p, " → −ln p =", -np.log(p))
print("stable: logsumexp([-1000, 0]) − (−1000) =", float(logsumexp(np.array([-1000.0, 0.0])) + 1000))


def cross_entropy(z, t):
    m = z.max(axis=1, keepdims=True)
    lse = m[:, 0] + np.log(np.exp(z - m).sum(axis=1))
    picked = z[np.arange(len(t)), t]
    return (lse - picked).mean()


print("cross_entropy([[1000, 1000]], [0]) =", round(float(cross_entropy(np.array([[1000.0, 1000]]), np.array([0]))), 6))
print("cross_entropy([[0, 0, 0, 0]], [2]) =", round(float(cross_entropy(np.zeros((1, 4)), np.array([2]))), 6))
print("cross_entropy([[1000, 0]], [1])    =", round(float(cross_entropy(np.array([[1000.0, 0]]), np.array([1]))), 6))

# --- NaN ------------------------------------------------------------------------------------
print("\n--- how NaN appears and spreads ---")
inf = np.float32(np.inf)
print("inf − inf =", inf - inf, "; 0 × inf =", np.float32(0) * inf, "; ln(−1) =", np.log(np.float32(-1)),
      "; 0 / 0 =", np.float32(0) / np.float32(0))
w = np.array([0.5, np.nan, -1.0], dtype=np.float32)
x = np.array([1.0, 2.0, 3.0], dtype=np.float32)
print("w =", w, " w @ x =", w @ x, " nan == nan:", np.nan == np.nan, " np.isnan:", np.isnan(w))

# --- mixed precision ------------------------------------------------------------------------
print("\n--- small updates ---")
w16 = to_bf16(np.float32(1.0))
print("bfloat16: 1 + 0.001 =", float(to_bf16(np.float32(w16) + np.float32(0.001))))
print("float32 : 1 + 0.001 =", float(np.float32(1.0) + np.float32(0.001)))
print("bfloat16 gap above 1:", 2.0 ** -7, " half of it:", 2.0 ** -8)
w = np.float32(1.0)
w_bf = to_bf16(np.float32(1.0))
for _ in range(100):
    w = w + np.float32(0.001)
    w_bf = to_bf16(np.float32(w_bf) + np.float32(0.001))
print("100 updates of +0.001: float32 →", round(float(w), 4), "  bfloat16 →", float(w_bf))
print("bytes for 7 billion weights: float32", 7e9 * 4 / 1e9, "GB, bfloat16", 7e9 * 2 / 1e9, "GB")

try:
    import torch
    print("\ntorch check: bfloat16(256 + 0.75) =", torch.tensor(256.75).to(torch.bfloat16).item(),
          " bfloat16(257) =", torch.tensor(257.0).to(torch.bfloat16).item(),
          " bfloat16(0.1) =", torch.tensor(0.1).to(torch.bfloat16).item(),
          " 1 + 0.001 in bf16 =", (torch.tensor(1.0, dtype=torch.bfloat16) + 0.001).item(),
          " finfo max =", torch.finfo(torch.bfloat16).max)
except ImportError:
    print("\n(torch not installed: skipping the bfloat16 double-check)")
