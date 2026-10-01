"""
Level D3 · Boss, part 2: draw digits with a diffusion model you finish yourself.

Run:  python boss.py          (download it from /files/latents-and-dit/boss.py into a folder of its own, run it there;
                                setup: /setup/ on the site)

Fill in the three functions marked TODO. Each one is a step you already did in the browser:
  add_noise    level D1   make a noisy picture x_t from x0 and eps
  guide        level D2   mix the two noise guesses with weight w
  step_back    level D2   one reverse step, with no fresh noise on the last step
Everything else (data, the tiny DiT, the training loop, the check) is written for you.

The script first tests your three functions on small numbers, so a mistake shows up in seconds, not after training.
Then it trains for STEPS steps (a few minutes on a laptop), draws 8 pictures of every digit, saves them as
my_digits.png (one row per digit, 0 at the top), and asks a separate digit classifier to read them. You beat the
boss when the classifier reads at least 70% of your 80 pictures as the digit you asked for. Then it prints a line like

    D3 PASS 0.863 1a2b3c4d

Paste that whole line into the page.
"""
import gzip
import hashlib
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


# ============================================================== your part
def add_noise(x0, eps, ab):
    """Level D1. x0 and eps are tensors of the same shape; ab is alpha-bar, a tensor that broadcasts against them."""
    raise NotImplementedError("TODO: add_noise")  # return ...


def guide(eps_free, eps_label, w):
    """Level D2. Mix the guess without the label and the guess with the label (level D2 called it eps_shape).
    w = 0 gives eps_free; w = 1 gives eps_label."""
    raise NotImplementedError("TODO: guide")  # return ...


def step_back(x, eps, beta, alpha, ab, last):
    """Level D2. One reverse step. beta, alpha, ab are plain numbers. last is True on the final step (t = 1 → 0).
    Fresh noise: torch.randn_like(x)."""
    raise NotImplementedError("TODO: step_back")  # return ...


# Training steps. If the small checks pass but the score is under 70%, raise STEPS.
STEPS = 8000


# ============================================================== checks on small numbers
def check_functions():
    x0, eps = torch.tensor([1.0, 2.0]), torch.tensor([0.5, -1.0])
    got = add_noise(x0, eps, torch.tensor(0.36))
    assert torch.allclose(got, torch.tensor([1.0, 0.4]), atol=1e-4), f"add_noise: expected [1.0, 0.4] (level D1's example), got {got.tolist()}"
    got = guide(torch.tensor([0.2]), torch.tensor([0.6]), 3)
    assert torch.allclose(got, torch.tensor([1.4]), atol=1e-4), f"guide: with w = 3, 0.2 and 0.6 should give 1.4 (level D2), got {got.tolist()}"
    got = guide(torch.tensor([0.2]), torch.tensor([0.6]), 0)
    assert torch.allclose(got, torch.tensor([0.2]), atol=1e-4), f"guide: with w = 0 the label is ignored, expected 0.2, got {got.tolist()}"
    x, e = torch.tensor([1.0, 0.4]), torch.tensor([0.5, -1.0])
    got = step_back(x, e, 0.2, 0.8, 0.36, last=True)
    assert torch.allclose(got, torch.tensor([0.9783, 0.7267]), atol=1e-3), (
        f"step_back on the last step (beta 0.2, alpha 0.8, alpha-bar 0.36): expected [0.9783, 0.7267], got {got.tolist()}")
    torch.manual_seed(1)
    a = step_back(x, e, 0.2, 0.8, 0.36, last=False)
    assert torch.allclose(a, torch.tensor([1.2740, 0.8461]), atol=1e-3), (
        f"step_back before the last step (same numbers, torch.manual_seed(1) just before the call): "
        f"expected [1.2740, 0.8461], got {a.tolist()}")
    print("your three functions pass the small checks")


# ============================================================== data (given)
CACHE = pathlib.Path.home() / ".cache/llm-by-hand/mnist"
URL = "https://ossci-datasets.s3.amazonaws.com/mnist/"


def load(kind):
    CACHE.mkdir(parents=True, exist_ok=True)
    out = []
    for name in (f"{kind}-images-idx3-ubyte.gz", f"{kind}-labels-idx1-ubyte.gz"):
        f = CACHE / name
        if not f.exists():
            urllib.request.urlretrieve(URL + name, f)
        out.append(gzip.open(f).read())
    imgs = np.frombuffer(out[0], np.uint8, offset=16).reshape(-1, 28, 28)
    return torch.tensor(imgs, dtype=torch.float32).unsqueeze(1) / 127.5 - 1, torch.tensor(np.frombuffer(out[1], np.uint8, offset=8), dtype=torch.long)


# ============================================================== the tiny DiT (given; the same as demo.py)
T, P, D, LAYERS, HEADS, NULL = 200, 4, 96, 4, 4, 10
NTOK = (28 // P) ** 2
betas = torch.linspace(1e-4, 0.02, T)
alphas = 1 - betas
abar = torch.cumprod(alphas, 0)


def time_embedding(t, dim=D):
    f = torch.exp(-math.log(1000) * torch.arange(dim // 2, device=t.device) / (dim // 2))
    a = t.float()[:, None] * f[None]
    return torch.cat([a.sin(), a.cos()], 1)


class Block(nn.Module):
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
        self.inp = nn.Linear(P * P, D)
        self.pos = nn.Parameter(torch.randn(1, NTOK, D) * 0.02)
        self.t_mlp = nn.Sequential(nn.Linear(D, D), nn.SiLU(), nn.Linear(D, D))
        self.cls = nn.Embedding(11, D)
        self.blocks = nn.ModuleList(Block() for _ in range(LAYERS))
        self.out = nn.Sequential(nn.LayerNorm(D), nn.Linear(D, P * P))

    def forward(self, x, t, y):
        B = x.shape[0]
        tok = x.reshape(B, 28 // P, P, 28 // P, P).permute(0, 1, 3, 2, 4).reshape(B, NTOK, P * P)
        h = self.inp(tok) + self.pos + (self.t_mlp(time_embedding(t)) + self.cls(y))[:, None, :]
        for b in self.blocks:
            h = b(h)
        return self.out(h).reshape(B, 28 // P, 28 // P, P, P).permute(0, 1, 3, 2, 4).reshape(B, 1, 28, 28)


class Reader(nn.Module):
    """A small digit classifier, trained separately, that reads your pictures and grades them."""

    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(nn.Conv2d(1, 16, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
                                 nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
                                 nn.Flatten(), nn.Linear(32 * 7 * 7, 10))

    def forward(self, x):
        return self.net(x)


def save_grid(pics, path):
    """Writes the 80 pictures as one grayscale PNG (10 rows of 8, dark ink on white, every pixel drawn 3 times as
    large), with nothing beyond numpy."""
    grid = np.ones((10 * 30, 8 * 30), np.uint8) * 255
    for k, p in enumerate(pics[:, 0].numpy()):
        r, c = divmod(k, 8)
        grid[r * 30 + 1:r * 30 + 29, c * 30 + 1:c * 30 + 29] = ((1 - (p + 1) / 2) * 255).astype(np.uint8)
    grid = grid.repeat(3, axis=0).repeat(3, axis=1)
    h, w = grid.shape
    raw = b"".join(b"\x00" + grid[r].tobytes() for r in range(h))
    chunk = lambda k, d: struct.pack(">I", len(d)) + k + d + struct.pack(">I", zlib.crc32(k + d))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def main():
    check_functions()
    torch.manual_seed(0)
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    X, Y = load("train")
    print(f"data: {len(X)} digit pictures")

    # 1. train the noise guesser with YOUR add_noise
    net = TinyDiT().to(dev)
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3)
    ab_d = abar.to(dev)
    start, avg = time.time(), None
    for step in range(1, STEPS + 1):
        idx = torch.randint(0, len(X), (128,))
        x0, y = X[idx].to(dev), Y[idx].to(dev)
        y = torch.where(torch.rand(128, device=dev) < 0.1, torch.full_like(y, NULL), y)
        t = torch.randint(0, T, (128,), device=dev)
        eps = torch.randn_like(x0)
        xt = add_noise(x0, eps, ab_d[t][:, None, None, None])
        loss = F.mse_loss(net(xt, t, y), eps)
        opt.zero_grad(); loss.backward(); opt.step()
        avg = loss.item() if avg is None else 0.98 * avg + 0.02 * loss.item()
        if step % 500 == 0:
            print(f"step {step:5d} of {STEPS}  loss {avg:.4f}  ({time.time() - start:.0f}s)")
    print(f"trained {STEPS} steps in {time.time() - start:.0f}s, final loss {avg:.4f}")

    # 2. sample with YOUR guide and step_back
    net.eval()
    asked = torch.tensor([d for d in range(10) for _ in range(8)], device=dev)
    with torch.no_grad():
        x = torch.randn(len(asked), 1, 28, 28, device=dev)
        for i in reversed(range(T)):
            t = torch.full((len(asked),), i, device=dev)
            e = guide(net(x, t, torch.full_like(asked, NULL)), net(x, t, asked), 3.0)
            x = step_back(x, e, betas[i].item(), alphas[i].item(), abar[i].item(), last=(i == 0))
    pics = x.clamp(-1, 1)
    save_grid(pics.cpu(), pathlib.Path("my_digits.png"))
    print("saved your 80 pictures as my_digits.png: one row per digit, 0 at the top. Open it.")

    # 3. a separate classifier reads the pictures
    reader = Reader().to(dev)
    ropt = torch.optim.Adam(reader.parameters(), lr=1e-3)
    for _ in range(2):
        for idx in torch.randperm(len(X)).split(256):
            out = reader(X[idx].to(dev))
            rloss = F.cross_entropy(out, Y[idx].to(dev))
            ropt.zero_grad(); rloss.backward(); ropt.step()
    Xt, Yt = load("t10k")
    with torch.no_grad():
        acc_real = (reader(Xt[:2000].to(dev)).argmax(1).cpu() == Yt[:2000]).float().mean().item()
        read = reader(pics).argmax(1)
    print(f"the reader gets {acc_real:.0%} right on real test digits")
    per_digit = [(read[asked == d] == d).sum().item() for d in range(10)]
    score = sum(per_digit) / len(asked)
    print("read as the digit you asked for, out of 8:", dict(enumerate(per_digit)))
    print(f"score: {score:.0%} of your 80 pictures")
    if score >= 0.7:
        print("\nPASS. Paste this whole line into the page:")
        print(pass_line(f"{score:.3f}"))
    else:
        print("not yet: you need 70%. Look at my_digits.png. If the small checks passed and the pictures look like "
              "digits, raise STEPS near the top of the file and run again. If you changed the guidance weight, a low "
              "score is expected: put it back to 3.0.")


LEVEL = "D3"


def pass_line(score):
    """The line to paste into the page. Its last part is a short code made from the rest, so the page can tell that
    the line was pasted unchanged. Anyone can read this function, so it is no proof: this part relies on your honesty."""
    return f"{LEVEL} PASS {score} {hashlib.sha256(f'llm-by-hand/{LEVEL}/{score}'.encode()).hexdigest()[:8]}"




if __name__ == "__main__":
    main()
