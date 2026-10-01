"""
Level D2 · Sampling and guidance

Run:  python demo.py      (needs numpy; about 10 seconds)

Part 1 is the toy example you can do on paper.
Part 2 samples from the small trained network the page runs in your browser.
It reads site/public/data/sampling-and-guidance/cond_mlp.json; if that file is missing,
run `python export.py` first to train it.
"""
import json
import pathlib

import numpy as np

np.set_printoptions(precision=5, suppress=True)

# ============================================================== part 1: on paper
print("=" * 60)
print("PART 1 · one reverse step on the 3-step example schedule")
print("=" * 60)
betas = np.array([0.1, 0.2, 0.5])
alphas = 1 - betas
alpha_bar = np.cumprod(alphas)

t = 3
x = np.array([1.0, 0.4])            # x_3 from level D1
eps_hat = np.array([0.5, -1.0])     # suppose the network guesses this noise
b, a, ab = betas[t - 1], alphas[t - 1], alpha_bar[t - 1]
k = b / np.sqrt(1 - ab)
print(f"t={t}: beta={b}  alpha={a}  alpha_bar={ab:.2f}")
print(f"k = beta / sqrt(1 - alpha_bar) = {b} / {np.sqrt(1 - ab):.1f} = {k}")
inside = x - k * eps_hat
print(f"x_t - k * eps_hat = {x} - {k} * {eps_hat} = {inside}")
mean = inside / np.sqrt(a)
print(f"mean = that / sqrt(alpha) = {inside} / {np.sqrt(a):.5f} = {mean}")
z = np.array([0.2, -0.4])           # fresh noise for this step
x_prev = mean + np.sqrt(b) * z
print(f"x_2 = mean + sqrt(beta) * z = {mean} + {np.sqrt(b):.5f} * {z} = {x_prev}")

def reverse_step(x, eps, beta, alpha, ab, z):
    return (x - beta / np.sqrt(1 - ab) * eps) / np.sqrt(alpha) + np.sqrt(beta) * z

print("check with the function:", reverse_step(x, eps_hat, b, a, ab, z))

print("\n--- guidance: mix the two noise guesses")
eps_free = np.array([0.2, 0.0])     # guess when the network is NOT told the shape
eps_cls = np.array([0.6, -0.4])     # guess when it IS told the shape
for w in (0, 1, 3):
    g = eps_free + w * (eps_cls - eps_free)
    print(f"w={w}: eps_free + {w} * (eps_cls - eps_free) = {g}")
print("network calls to sample with guidance: 2 per step × 50 steps =", 2 * 50)

# --- checkpoint: one guided step back = guidance mix + reverse step
def guided_step(x, eps_free, eps_shape, w, beta, alpha, ab, z):
    e = eps_free + w * (eps_shape - eps_free)
    mean = (x - beta / np.sqrt(1 - ab) * e) / np.sqrt(alpha)
    return mean + np.sqrt(beta) * z
gx, gef, ges = np.array([1.0, 0.4]), np.array([0.3, -0.5]), np.array([0.5, -1.0])
print("guided step, w=2, z=0:        ", guided_step(gx, gef, ges, 2, 0.5, 0.5, 0.36, np.zeros(2)).round(4))
print("guided step, w=2, z=[0.2,-0.4]:", guided_step(gx, gef, ges, 2, 0.5, 0.5, 0.36, np.array([0.2, -0.4])).round(4))
print("guided step, w=0, z=0:        ", guided_step(gx, gef, ges, 0, 0.5, 0.5, 0.36, np.zeros(2)).round(4))

# ============================================================== part 2: real sampling
print("\n" + "=" * 60)
print("PART 2 · sample from the trained network")
print("=" * 60)
p = pathlib.Path(__file__).resolve().parents[3] / "site/public/data/sampling-and-guidance/cond_mlp.json"
if not p.exists():
    raise SystemExit(f"missing {p}\nrun `python export.py` first")
M = json.loads(p.read_text())
T = M["T"]
B = np.array(M["betas"]); A = 1 - B; AB = np.cumprod(A)
SHAPES = M["shapes"]; NULL = len(SHAPES)
layers = [(np.array(L["W"]), np.array(L["b"])) for L in M["layers"]]
print(f"T={T}, shapes={SHAPES}, layer shapes:", [W.shape for W, _ in layers])


def time_features(t):
    tn = np.asarray(t, dtype=float)[:, None] / T
    f = np.pi * 2.0 ** np.arange(6)
    return np.concatenate([np.sin(tn * f), np.cos(tn * f)], 1)


def net(x, t, c):
    z = np.concatenate([x, time_features(np.full(len(x), t)), np.eye(NULL + 1)[np.full(len(x), c)]], 1)
    for i, (W, b) in enumerate(layers):
        z = z @ W + b
        if i < len(layers) - 1:
            z = np.maximum(z, 0)
    return z


def sample(c, w, n=300, seed=1, watch=None):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(n, 2))
    for t in range(T, 0, -1):
        e_free = net(x, t, NULL)
        e_cls = net(x, t, c)
        e = e_free + w * (e_cls - e_free)
        if watch is not None and t == watch:
            print(f"   point 0 at t={t}: eps_free={e_free[0]}  eps_cls={e_cls[0]}  guided={e[0]}")
        x = (x - B[t - 1] / np.sqrt(1 - AB[t - 1]) * e) / np.sqrt(A[t - 1])
        if t > 1:
            x = x + np.sqrt(B[t - 1]) * rng.normal(size=x.shape)
    return x


def shape_points(name, n, rng):
    if name == "spiral":
        u = rng.uniform(0, 1, n); a = 0.6 + 3.6 * u * np.pi; r = 0.25 + 1.55 * u
        p = np.stack([r * np.cos(a), r * np.sin(a)], 1)
    elif name == "ring":
        a = rng.uniform(0, 2 * np.pi, n); p = 1.4 * np.stack([np.cos(a), np.sin(a)], 1)
    else:
        a = rng.uniform(0, np.pi, n); top = rng.uniform(size=n) < 0.5
        p = np.stack([np.where(top, np.cos(a), 1 - np.cos(a)) - 0.5,
                      np.where(top, np.sin(a), -np.sin(a) + 0.5) - 0.25], 1) * 1.3
    return p + rng.normal(0, 0.04, p.shape)


print("\nhow guidance strength w trades variety for accuracy (300 samples each)")
print("  on shape  = samples within 0.15 of the true shape")
print("  covered   = parts of the true shape that have a sample within 0.15")
for c, name in enumerate(SHAPES):
    ref = shape_points(name, 400, np.random.default_rng(9))
    for w in (0, 1, 3, 6, 10):
        x = sample(c, w, watch=25 if (c == 0 and w == 3) else None)
        d = np.sqrt(((x[:, None] - ref[None]) ** 2).sum(-1))
        print(f"  {name:6s} w={w:2d}: on shape {(d.min(1) < 0.15).mean():4.0%}   covered {(d.min(0) < 0.15).mean():4.0%}")
