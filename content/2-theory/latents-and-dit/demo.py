"""
Level D3 · Latents and DiT (boss)

Run:  python demo.py           about 3 minutes; trains a tiny DiT and draws digits
      python demo.py --full    about 10 minutes; better digits

Needs numpy + torch. Downloads MNIST (about 10 MB) once into ~/.cache/llm-by-hand/mnist.
If the download fails it falls back to simple drawn digits, so it always runs.
Writes samples.png next to this file: one row per digit 0–9.
"""
import argparse
import gzip
import math
import pathlib
import struct
import time
import urllib.request
import zlib

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

ap = argparse.ArgumentParser()
ap.add_argument("--full", action="store_true", help="train longer for better digits")
args = ap.parse_args()
np.set_printoptions(precision=3, suppress=True)
torch.manual_seed(0)
rng = np.random.default_rng(0)

# ============================================================== part 1: on paper
print("=" * 60)
print("PART 1 · cutting a picture into patch tokens")
print("=" * 60)
img = np.arange(16).reshape(4, 4)
print("a 4×4 picture:\n", img)


def patchify(x, p):
    """(H, W) → (number of patches, p*p). Patches go left to right, then top to bottom."""
    H, W = x.shape
    return x.reshape(H // p, p, W // p, p).transpose(0, 2, 1, 3).reshape(-1, p * p)


tok = patchify(img, 2)
print("2×2 patches → tokens, shape", tok.shape)
print(tok)
print("a 6×6 picture with 2×2 patches → tokens, shape", patchify(np.arange(36).reshape(6, 6), 2).shape)
for p in (2, 4, 7, 14):
    n = (28 // p) ** 2
    print(f"28×28 digit, patch {p:2d}: {n:3d} tokens of {p*p:3d} numbers   attention scores per head: {n}×{n} = {n*n}")
print("an autoencoder that squeezes 784 numbers into 16 makes diffusion work on", 784 // 16, "times fewer numbers")
_codes = pathlib.Path(__file__).resolve().parents[3] / "site/public/data/latents-and-dit/digits.json"
if _codes.exists():
    import json
    _c = np.array(json.load(open(_codes))["codes"])
    print(f"std of the lab's 16-number codes: {_c.std():.2f} (about 4) → divide every code by 4 so its variance is 1 before adding noise")

# ============================================================== data
CACHE = pathlib.Path.home() / ".cache/llm-by-hand/mnist"
URL = "https://ossci-datasets.s3.amazonaws.com/mnist/"


def load_mnist():
    CACHE.mkdir(parents=True, exist_ok=True)
    out = []
    for name in ("train-images-idx3-ubyte.gz", "train-labels-idx1-ubyte.gz"):
        f = CACHE / name
        if not f.exists():
            urllib.request.urlretrieve(URL + name, f)
        out.append(gzip.open(f).read())
    imgs = np.frombuffer(out[0], np.uint8, offset=16).reshape(-1, 28, 28)
    labels = np.frombuffer(out[1], np.uint8, offset=8)
    return imgs, labels


def drawn_digits(n):
    """Fallback: seven-segment style digits with random thickness and shift."""
    segs = {0: "abcdef", 1: "bc", 2: "abged", 3: "abgcd", 4: "fgbc", 5: "afgcd", 6: "afgedc", 7: "abc", 8: "abcdefg", 9: "abcdfg"}
    lines = {"a": (6, 7, 6, 20), "b": (6, 20, 14, 20), "c": (14, 20, 22, 20), "d": (22, 7, 22, 20),
             "e": (14, 7, 22, 7), "f": (6, 7, 14, 7), "g": (14, 7, 14, 20)}
    imgs, labels = np.zeros((n, 28, 28), np.uint8), rng.integers(0, 10, n)
    yy, xx = np.mgrid[0:28, 0:28]
    for i, d in enumerate(labels):
        dy, dx, w = rng.integers(-2, 3), rng.integers(-3, 4), rng.uniform(1.2, 2.2)
        for s in segs[d]:
            y0, x0, y1, x1 = lines[s]
            t = np.clip(((yy - y0 - dy) * (y1 - y0) + (xx - x0 - dx) * (x1 - x0)) / max((y1 - y0) ** 2 + (x1 - x0) ** 2, 1), 0, 1)
            dist = np.hypot(yy - (y0 + dy + t * (y1 - y0)), xx - (x0 + dx + t * (x1 - x0)))
            imgs[i] = np.maximum(imgs[i], (np.clip(w + 0.5 - dist, 0, 1) * 255).astype(np.uint8))
    return imgs, labels


try:
    images, labels = load_mnist()
    source = "MNIST"
except Exception as e:  # noqa: BLE001
    print("could not download MNIST:", e, "\nusing drawn digits instead")
    images, labels = drawn_digits(20000)
    source = "drawn digits"
X = torch.tensor(images, dtype=torch.float32).unsqueeze(1) / 127.5 - 1      # (N, 1, 28, 28) in [-1, 1]
Y = torch.tensor(labels, dtype=torch.long)
print(f"\ndata: {source}, {len(X)} pictures, shape {tuple(X.shape[1:])}")

# ============================================================== part 2: a tiny DiT
print("\n" + "=" * 60)
print("PART 2 · a tiny DiT: a Transformer that guesses the noise in a picture")
print("=" * 60)
dev = "mps" if torch.backends.mps.is_available() else "cpu"
T = 200
betas = torch.linspace(1e-4, 0.02, T)
alphas = 1 - betas
abar = torch.cumprod(alphas, 0)
P, D, LAYERS, HEADS = 4, 96, 4, 4          # patch 4 → 49 tokens of 16 numbers
NTOK = (28 // P) ** 2
NULL = 10                                   # class id meaning "no label" (for guidance)


def time_embedding(t, dim=D):
    half = dim // 2
    f = torch.exp(-math.log(1000) * torch.arange(half, device=t.device) / half)
    a = t.float()[:, None] * f[None]
    return torch.cat([a.sin(), a.cos()], 1)


class Block(nn.Module):
    """The same pre-norm block as level 16 (attention + feed-forward, each with LayerNorm and a residual), with no causal mask."""

    def __init__(self):
        super().__init__()
        self.n1, self.n2 = nn.LayerNorm(D), nn.LayerNorm(D)
        self.attn = nn.MultiheadAttention(D, HEADS, batch_first=True)
        self.ff = nn.Sequential(nn.Linear(D, 4 * D), nn.GELU(), nn.Linear(4 * D, D))

    def forward(self, h):
        a = self.n1(h)
        h = h + self.attn(a, a, a, need_weights=False)[0]
        return h + self.ff(self.n2(h))


class TinyDiT(nn.Module):
    def __init__(self):
        super().__init__()
        self.inp = nn.Linear(P * P, D)                         # each patch (16 numbers) → one token (96 numbers)
        self.pos = nn.Parameter(torch.randn(1, NTOK, D) * 0.02)
        self.t_mlp = nn.Sequential(nn.Linear(D, D), nn.SiLU(), nn.Linear(D, D))
        self.cls = nn.Embedding(11, D)                         # digits 0–9, plus 10 = "no label"
        self.blocks = nn.ModuleList(Block() for _ in range(LAYERS))
        self.out = nn.Sequential(nn.LayerNorm(D), nn.Linear(D, P * P))

    def forward(self, x, t, y):
        B = x.shape[0]
        tok = x.reshape(B, 28 // P, P, 28 // P, P).permute(0, 1, 3, 2, 4).reshape(B, NTOK, P * P)  # patchify
        h = self.inp(tok) + self.pos
        h = h + (self.t_mlp(time_embedding(t)) + self.cls(y))[:, None, :]   # step and label, added to every token
        for b in self.blocks:
            h = b(h)
        out = self.out(h)                                                    # (B, 49, 16): noise guess per patch
        return out.reshape(B, 28 // P, 28 // P, P, P).permute(0, 1, 3, 2, 4).reshape(B, 1, 28, 28)


net = TinyDiT().to(dev)
print(f"tokens per picture: {NTOK}, token size {D}, layers {LAYERS}, parameters {sum(p.numel() for p in net.parameters()):,}")
STEPS = 40000 if args.full else 8000                                         # a fixed count, so every run gives the same numbers
opt = torch.optim.AdamW(net.parameters(), lr=1e-3)
ab_d = abar.to(dev)
start, avg = time.time(), None
for step in range(1, STEPS + 1):
    idx = torch.randint(0, len(X), (128,))
    x0, y = X[idx].to(dev), Y[idx].to(dev)
    y = torch.where(torch.rand(128, device=dev) < 0.1, torch.full_like(y, NULL), y)   # hide the label 10% of the time
    t = torch.randint(0, T, (128,), device=dev)
    eps = torch.randn_like(x0)
    a = ab_d[t][:, None, None, None]
    xt = a.sqrt() * x0 + (1 - a).sqrt() * eps                               # level D1, on 784 numbers
    loss = F.mse_loss(net(xt, t, y), eps)
    opt.zero_grad(); loss.backward(); opt.step()
    avg = loss.item() if avg is None else 0.98 * avg + 0.02 * loss.item()
    if step % 500 == 0:
        print(f"step {step:5d} of {STEPS}  loss {avg:.4f}  ({time.time() - start:.0f}s)")
print(f"trained {STEPS} steps in {time.time() - start:.0f}s, final loss {avg:.4f}")


@torch.no_grad()
def sample(digits, w=3.0):
    """Level D2: reverse steps with guidance, now on 28×28 pictures."""
    n = len(digits)
    y = torch.tensor(digits, device=dev)
    x = torch.randn(n, 1, 28, 28, device=dev)
    for i in reversed(range(T)):
        t = torch.full((n,), i, device=dev)
        e_free = net(x, t, torch.full_like(y, NULL))
        e_cls = net(x, t, y)
        e = e_free + w * (e_cls - e_free)
        b, a, ab = betas[i].item(), alphas[i].item(), abar[i].item()
        x = (x - b / math.sqrt(1 - ab) * e) / math.sqrt(a)
        if i > 0:
            x = x + math.sqrt(b) * torch.randn_like(x)
    return x.clamp(-1, 1).cpu().numpy()[:, 0]


net.eval()
digits = [d for d in range(10) for _ in range(8)]
pics = sample(digits)


def write_png(path, a):
    """Grayscale PNG writer, so we need nothing beyond numpy."""
    h, w = a.shape
    raw = b"".join(b"\x00" + a[r].tobytes() for r in range(h))
    chunk = lambda k, d: struct.pack(">I", len(d)) + k + d + struct.pack(">I", zlib.crc32(k + d))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


grid = np.ones((10 * 30, 8 * 30), np.uint8) * 255
for k, p in enumerate(pics):
    r, c = divmod(k, 8)
    grid[r * 30 + 1:r * 30 + 29, c * 30 + 1:c * 30 + 29] = ((1 - (p + 1) / 2) * 255).astype(np.uint8)
out = pathlib.Path(__file__).with_name("samples.png")
write_png(out, grid)
print("wrote", out, "(one row per digit 0–9, dark ink on white)")
print("mean pixel per row (sanity check, should differ by digit):", [round(float(pics[i * 8:(i + 1) * 8].mean()), 2) for i in range(10)])
