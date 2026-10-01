"""
Train the small conditional denoiser that the A2 page runs in your browser.

Run:  python export.py        (needs numpy + torch, about a minute on a laptop CPU)
Writes site/public/data/sampling-and-guidance/cond_mlp.json

The network is tiny on purpose. The page re-implements its forward pass in JavaScript,
so the numbers in the browser are the numbers this script computes.
"""
import json
import pathlib

import numpy as np
import torch
import torch.nn as nn

T = 50
BETAS = np.linspace(1e-3, 0.2, T)          # beta_1 .. beta_T  (index 0 is t = 1)
ALPHA_BAR = np.cumprod(1 - BETAS)
SHAPES = ["spiral", "ring", "moons"]       # class 0, 1, 2; class 3 = "no class" (for guidance)
NULL = len(SHAPES)


def make_shape(name, n, rng):
    if name == "spiral":
        u = rng.uniform(0, 1, n)
        a = 0.6 + 3.6 * u * np.pi
        r = 0.25 + 1.55 * u
        p = np.stack([r * np.cos(a), r * np.sin(a)], 1)
    elif name == "ring":
        a = rng.uniform(0, 2 * np.pi, n)
        p = 1.4 * np.stack([np.cos(a), np.sin(a)], 1)
    else:  # moons
        a = rng.uniform(0, np.pi, n)
        top = rng.uniform(size=n) < 0.5
        x = np.where(top, np.cos(a), 1 - np.cos(a))
        y = np.where(top, np.sin(a), -np.sin(a) + 0.5)
        p = np.stack([x - 0.5, y - 0.25], 1) * 1.3
    return p + rng.normal(0, 0.04, p.shape)


def time_features(t):
    """t is 1..T. 12 numbers: sin and cos of t/T at 6 frequencies."""
    tn = np.asarray(t, dtype=np.float64)[:, None] / T
    f = np.pi * 2.0 ** np.arange(6)
    return np.concatenate([np.sin(tn * f), np.cos(tn * f)], 1)


def inputs(x, t, c):
    onehot = np.eye(NULL + 1)[c]
    return np.concatenate([x, time_features(t), onehot], 1)   # (n, 2 + 12 + 4) = (n, 18)


class Net(nn.Module):
    def __init__(self, h=96):
        super().__init__()
        self.layers = nn.Sequential(nn.Linear(18, h), nn.ReLU(), nn.Linear(h, h), nn.ReLU(),
                                    nn.Linear(h, h), nn.ReLU(), nn.Linear(h, 2))

    def forward(self, z):
        return self.layers(z)


def main():
    rng = np.random.default_rng(0)
    torch.manual_seed(0)
    data = {c: make_shape(s, 4000, rng) for c, s in enumerate(SHAPES)}
    net = Net()
    opt = torch.optim.Adam(net.parameters(), lr=2e-3)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, 8000)
    for step in range(8000):
        c = rng.integers(0, len(SHAPES), 512)
        x0 = np.stack([data[k][rng.integers(0, 4000)] for k in c])
        t = rng.integers(1, T + 1, 512)
        eps = rng.normal(size=x0.shape)
        ab = ALPHA_BAR[t - 1][:, None]
        xt = np.sqrt(ab) * x0 + np.sqrt(1 - ab) * eps
        c_in = np.where(rng.uniform(size=512) < 0.2, NULL, c)          # 20%: hide the class
        z = torch.tensor(inputs(xt, t, c_in), dtype=torch.float32)
        loss = ((net(z) - torch.tensor(eps, dtype=torch.float32)) ** 2).mean()
        opt.zero_grad(); loss.backward(); opt.step(); sched.step()
        if step % 1000 == 0 or step == 7999:
            print(f"step {step:5d}  loss {loss.item():.4f}")

    layers = [m for m in net.layers if isinstance(m, nn.Linear)]
    out = {
        "T": T, "betas": [round(b, 6) for b in BETAS.tolist()], "shapes": SHAPES,
        "layers": [{"W": np.round(m.weight.detach().numpy().T, 4).tolist(),   # (in, out): x @ W + b
                    "b": np.round(m.bias.detach().numpy(), 4).tolist()} for m in layers],
    }
    p = pathlib.Path(__file__).resolve().parents[3] / "site/public/data/sampling-and-guidance/cond_mlp.json"
    p.write_text(json.dumps(out, separators=(",", ":")))
    print("wrote", p, f"{p.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
