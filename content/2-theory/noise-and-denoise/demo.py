"""
Level D1 · Adding and removing noise

Run:  python demo.py      (needs numpy, about 5 seconds)

Every number the page asks about is printed here.
Part 1 is the 3-step toy schedule you can do on paper.
Part 2 trains the same small noise-guessing network the page trains in your browser.
"""
import numpy as np

np.set_printoptions(precision=4, suppress=True)

# ============================================================== part 1: on paper
print("=" * 60)
print("PART 1 · a 3-step example schedule")
print("=" * 60)
betas = np.array([0.1, 0.2, 0.5])          # how much noise each step adds
alphas = 1 - betas                          # how much of the signal each step keeps
alpha_bar = np.cumprod(alphas)              # how much signal is left after t steps
for t in range(1, 4):
    print(f"t={t}  beta={betas[t-1]:.1f}  alpha={alphas[t-1]:.1f}  alpha_bar={alpha_bar[t-1]:.2f}")
print("alpha_bar after 3 steps = 0.9 × 0.8 × 0.5 =", round(alpha_bar[2], 4))

x0 = np.array([1.0, 2.0])                   # one clean point
eps = np.array([0.5, -1.0])                 # the noise we draw for it
print("\nx0 =", x0, "  eps =", eps)

for t in range(1, 4):
    ab = alpha_bar[t - 1]
    xt = np.sqrt(ab) * x0 + np.sqrt(1 - ab) * eps
    print(f"t={t}: sqrt(ab)={np.sqrt(ab):.4f}  sqrt(1-ab)={np.sqrt(1-ab):.4f}  x_t = {xt}")

ab = alpha_bar[2]
x3 = np.sqrt(ab) * x0 + np.sqrt(1 - ab) * eps
print("\nwhy square roots: 0.6² + 0.8² =", round(0.6**2 + 0.8**2, 4), "(signal variance + noise variance = 1)")
print(f"\nx_3 = 0.6 × {x0} + 0.8 × {eps} = {x3}")


# --- from the list of betas straight to step t (the noisy_at question)
def noisy_at(x0, eps, betas, t):
    ab = np.prod(1 - betas[:t])              # what the first t steps keep, multiplied
    return np.sqrt(ab) * x0 + np.sqrt(1 - ab) * eps


print("\nnoisy_at([1, 2], [0.5, -1], betas, t=3) =", noisy_at(x0, eps, betas, 3))
print("noisy_at([2, 0], [0, 3], betas, t=2)     =", noisy_at(np.array([2.0, 0.0]), np.array([0.0, 3.0]), betas, 2),
      " (alpha_bar = 0.9 × 0.8 = 0.72)")
print("noisy_at two points, betas [0.5, 0.5], t=2 =\n",
      noisy_at(np.array([[4.0, 0.0], [0.0, 4.0]]), np.array([[0.0, 2.0], [2.0, 0.0]]), np.array([0.5, 0.5]), 2),
      " (alpha_bar = 0.25)")

# --- running it backwards: if you know the noise, you get x0 back exactly
x0_back = (x3 - np.sqrt(1 - ab) * eps) / np.sqrt(ab)
print("undo with the true noise: (x_3 - 0.8 × eps) / 0.6 =", x0_back)
other_x3, other_eps = np.array([0.7, 1.0]), np.array([0.5, 0.5])
print(f"another point: x_3 = {other_x3}, eps = {other_eps} → x0 =",
      (other_x3 - np.sqrt(1 - ab) * other_eps) / np.sqrt(ab))

# --- the loss: how wrong is a noise guess?
guess = np.array([0.0, 0.0])
print("\nguess [0, 0] for this point: loss = mean((guess - eps)^2) =",
      np.mean((guess - eps) ** 2))
big = np.random.default_rng(0).normal(size=(100_000, 2))
print("guess [0, 0] for 100,000 random noises: loss =", round(np.mean(big ** 2), 3))

# ============================================================== part 2: train
print("\n" + "=" * 60)
print("PART 2 · train a noise guesser on the spiral (same as the page)")
print("=" * 60)
T = 50
BETAS = np.linspace(1e-3, 0.2, T)
AB = np.cumprod(1 - BETAS)
for t in (1, 10, 25, 50):
    print(f"site schedule: t={t:2d}  alpha_bar={AB[t-1]:.4f}  signal kept sqrt(ab)={np.sqrt(AB[t-1]):.3f}")

rng = np.random.default_rng(0)


def spiral(n):
    u = rng.uniform(0, 1, n)
    a = 0.6 + 3.6 * u * np.pi
    r = 0.25 + 1.55 * u
    return np.stack([r * np.cos(a), r * np.sin(a)], 1) + rng.normal(0, 0.04, (n, 2))


def time_features(t):
    """12 numbers that say which step we are on: sin and cos of t/T at 6 frequencies."""
    tn = t[:, None] / T
    f = np.pi * 2.0 ** np.arange(6)
    return np.concatenate([np.sin(tn * f), np.cos(tn * f)], 1)


data = spiral(2000)
print(f"variance of the spiral data (mean of x² over both numbers): {np.mean(data ** 2):.2f}  → grows to 1.00 as it becomes pure noise")
sizes = [14, 64, 64, 2]                      # input: x, y + 12 time numbers → noise guess (2 numbers)
Ws = [rng.normal(size=(a, b)) * np.sqrt(2 / a) for a, b in zip(sizes, sizes[1:])]
bs = [np.zeros(b) for b in sizes[1:]]
m = [np.zeros_like(p) for p in Ws + bs]
v = [np.zeros_like(p) for p in Ws + bs]


def net(z):
    acts = [z]
    for i in range(3):
        h = acts[-1] @ Ws[i] + bs[i]
        acts.append(np.maximum(h, 0) if i < 2 else h)
    return acts


def batch(n, t=None):
    x0 = data[rng.integers(0, len(data), n)]
    t = rng.integers(1, T + 1, n) if t is None else np.full(n, t)
    e = rng.normal(size=x0.shape)
    ab = AB[t - 1][:, None]
    xt = np.sqrt(ab) * x0 + np.sqrt(1 - ab) * e
    return x0, xt, np.concatenate([xt, time_features(t)], 1), e, ab


x0v, xtv, zv, ev, abv = batch(1000, t=25)     # a fixed test set at t = 25
print("\none batch going in:", zv.shape, "(points, x y + 12 time numbers)")


def clean_error():
    eh = net(zv)[-1]
    guess = (xtv - np.sqrt(1 - abv) * eh) / np.sqrt(abv)
    return np.sqrt(((guess - x0v) ** 2).sum(1)).mean()


print(f"before training: avg distance from guessed x0 to true x0 at t=25: {clean_error():.3f}")
running = []
for step in range(1, 4001):
    _, _, z, e, _ = batch(128)
    acts = net(z)
    out = acts[-1]
    loss = ((out - e) ** 2).mean()
    running.append(loss)
    g = 2 * (out - e) / out.size
    gW, gb = [None] * 3, [None] * 3
    for i in (2, 1, 0):
        gW[i], gb[i] = acts[i].T @ g, g.sum(0)
        if i > 0:
            g = (g @ Ws[i].T) * (acts[i] > 0)
    for k, (p, gr) in enumerate(zip(Ws + bs, gW + gb)):
        m[k] = 0.9 * m[k] + 0.1 * gr
        v[k] = 0.999 * v[k] + 0.001 * gr * gr
        p -= 3e-3 * (m[k] / (1 - 0.9 ** step)) / (np.sqrt(v[k] / (1 - 0.999 ** step)) + 1e-8)
    if step % 500 == 0:
        print(f"step {step:4d}  loss (avg of last 500) {np.mean(running[-500:]):.3f}")
print(f"after training:  avg distance from guessed x0 to true x0 at t=25: {clean_error():.3f}")
print("guessing zero noise would give loss about 1.0; a perfect guesser still can't reach 0")
