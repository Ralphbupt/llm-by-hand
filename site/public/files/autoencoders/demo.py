"""
Level N6 · Autoencoders and VAEs

Run:  python demo.py            hand-checked numbers, then train an autoencoder and a VAE on MNIST (about a minute on a CPU)
      python demo.py --export   (course authors only) also write the lab's data into the course's site/ folder

Needs numpy + torch. Downloads MNIST (about 10 MB) once into ~/.cache/llm-by-hand/mnist.
How to set up Python and torch on your computer: see the site's /setup/ page.
"""
import base64
import gzip
import json
import pathlib
import sys
import time
import urllib.request

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent.parent.parent / "site/public/data/autoencoders"


def show(title):
    print("\n" + "=" * 70 + "\n" + title + "\n" + "=" * 70)


# =============================================================================
show("1. Squeeze and rebuild: the numbers the page asks about")
print("a 28×28 picture has", 28 * 28, "numbers; a 2-number code is", 784 // 2, "times fewer")
print("a batch of 32 pictures (32, 784) → encoder → codes of shape (32, 2) → decoder → (32, 784)")
x = np.array([1.0, 0, 1, 1])
x_hat = np.array([0.5, 0, 1, 0.5])
print(f"reconstruction loss (mean squared): x = {x}, x̂ = {x_hat} → squares {(x - x_hat) ** 2} → mean {np.mean((x - x_hat) ** 2)}")
mu, sigma, eps = 1.0, 0.5, -2.0
print(f"VAE sample: z = μ + σ·ε = {mu} + {sigma} × ({eps}) = {mu + sigma * eps}")


def vae_loss(x, x_hat, mu, sigma):
    """The checkpoint: binary cross-entropy summed over the pixels + KL summed over the code numbers."""
    rebuild = -(x * np.log(x_hat) + (1 - x) * np.log(1 - x_hat)).sum()
    kl = 0.5 * (mu ** 2 + sigma ** 2 - 1 - np.log(sigma ** 2)).sum()
    return rebuild + kl


print("VAE loss, x = [1, 0], x̂ = [0.5, 0.5], μ = 0, σ = 1:", round(vae_loss(np.array([1., 0]), np.array([.5, .5]), np.zeros(2), np.ones(2)), 4))
print("VAE loss, x = [1, 0], x̂ = [0.9, 0.1], μ = [2, 0], σ = 1:", round(vae_loss(np.array([1., 0]), np.array([.9, .1]), np.array([2., 0]), np.ones(2)), 4))
print("summed vs averaged over 784 pixels: averaging divides the rebuild error by 784, so the KL term outweighs it")
for m, s in ((0.0, 1.0), (2.0, 1.0), (0.0, 0.5)):
    kl = 0.5 * (m ** 2 + s ** 2 - 1 - np.log(s ** 2))
    print(f"KL(N({m}, {s}²) ‖ N(0, 1)) = ½(μ² + σ² − 1 − ln σ²) = {kl:.3f}")

# =============================================================================
show("2. Train a 2-number autoencoder and a 2-number VAE on MNIST")
import torch
import torch.nn as nn
import torch.nn.functional as F

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
    imgs = np.frombuffer(out[0], np.uint8, offset=16).reshape(-1, 784).astype(np.float32) / 255
    labels = np.frombuffer(out[1], np.uint8, offset=8)
    return imgs, labels


Xtr, Ytr = load("train")
Xte, Yte = load("t10k")
torch.manual_seed(0)
rng = np.random.default_rng(0)
Xtr_t, Xte_t = torch.tensor(Xtr), torch.tensor(Xte)
H = 128


class Encoder(nn.Module):
    def __init__(self, out):
        super().__init__()
        self.l1, self.l2 = nn.Linear(784, H), nn.Linear(H, out)

    def forward(self, x):
        return self.l2(F.relu(self.l1(x)))


class Decoder(nn.Module):
    """2 numbers → 128 → 784 pixels in [0, 1]. The browser lab runs exactly this."""
    def __init__(self):
        super().__init__()
        self.l1, self.l2 = nn.Linear(2, H), nn.Linear(H, 784)

    def forward(self, z):
        return torch.sigmoid(self.l2(F.relu(self.l1(z))))


def train(vae, epochs=6, batch=128):
    enc, dec = Encoder(4 if vae else 2), Decoder()
    opt = torch.optim.Adam(list(enc.parameters()) + list(dec.parameters()), lr=2e-3)
    n = len(Xtr_t)
    for ep in range(epochs):
        perm = torch.randperm(n)
        tot_rec, tot_kl = 0.0, 0.0
        for i in range(0, n, batch):
            xb = Xtr_t[perm[i:i + batch]]
            h = enc(xb)
            if vae:
                mu, logvar = h[:, :2], h[:, 2:]
                z = mu + torch.exp(0.5 * logvar) * torch.randn_like(mu)   # z = μ + σ·ε
                kl = 0.5 * (mu ** 2 + logvar.exp() - 1 - logvar).sum(1).mean()
            else:
                z, kl = h, torch.tensor(0.0)
            xr = dec(z)
            rec = F.binary_cross_entropy(xr, xb, reduction="none").sum(1).mean()
            loss = rec + kl
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot_rec += rec.item() * len(xb)
            tot_kl += kl.item() * len(xb)
        print(f"  {'VAE' if vae else 'AE '} epoch {ep + 1}: reconstruction {tot_rec / n:.1f}  KL {tot_kl / n:.2f}  (per picture, summed over 784 pixels)")
    return enc, dec


t0 = time.time()
print("plain autoencoder (784 → 128 → 2 → 128 → 784):")
ae_enc, ae_dec = train(False)
print("VAE (encoder outputs μ and ln σ², 2 numbers each):")
vae_enc, vae_dec = train(True)
print(f"trained both in {time.time() - t0:.0f} s")

with torch.no_grad():
    def mse(enc, dec, vae):
        h = enc(Xte_t)
        z = h[:, :2] if vae else h
        return float(((dec(z) - Xte_t) ** 2).mean())

    print(f"test mean squared error per pixel: autoencoder {mse(ae_enc, ae_dec, False):.4f}, VAE (using μ) {mse(vae_enc, vae_dec, True):.4f}")

    # holes: decode random codes drawn from N(0, 1), scaled to each model's code spread, and compare with real digits
    ae_codes = ae_enc(Xte_t).numpy()
    vae_codes = vae_enc(Xte_t)[:, :2].numpy()
    print(f"code spread (std per number): autoencoder {ae_codes.std(0).round(2)}, VAE μ {vae_codes.std(0).round(2)}")
    # holes: draw 1000 random codes the way you would sample a new picture, and count how many land
    # far from every real digit's code (farther than 0.25 of that model's code std)
    def empty_share(codes, z):
        r = 0.25 * codes.std(0).mean()
        d = np.min(np.linalg.norm(codes[:4000][None, :, :] - z[:, None, :], axis=2), axis=1)
        return float((d > r).mean())

    g = np.random.default_rng(1).standard_normal((1000, 2))
    ae_z = ae_codes.mean(0) + g * ae_codes.std(0)
    print(f"random codes far from every real code: autoencoder {100 * empty_share(ae_codes, ae_z):.0f}%, "
          f"VAE {100 * empty_share(vae_codes, g):.0f}%   (autoencoder sampled with its own mean and std; VAE from N(0, 1))")

    if "--export" in sys.argv:
        OUT.mkdir(parents=True, exist_ok=True)
        pick = np.concatenate([np.where(Yte == d)[0][:40] for d in range(10)])

        def q8(t):
            a = t.detach().numpy().astype(np.float32)
            s = float(np.abs(a).max()) / 127 or 1.0
            return {"shape": list(a.shape), "scale": s, "b64": base64.b64encode(np.round(a / s).astype(np.int8).tobytes()).decode()}

        def pack(dec, codes):
            return {
                "codes": np.round(codes[pick], 3).tolist(),
                "decoder": {"W1": q8(dec.l1.weight.T), "b1": np.round(dec.l1.bias.numpy(), 4).tolist(),
                            "W2": q8(dec.l2.weight.T), "b2": np.round(dec.l2.bias.numpy(), 4).tolist()},
            }

        data = {"labels": Yte[pick].tolist(), "ae": pack(ae_dec, ae_codes), "vae": pack(vae_dec, vae_codes)}
        (OUT / "models.json").write_text(json.dumps(data, separators=(",", ":")))
        print(f"wrote {OUT / 'models.json'} ({(OUT / 'models.json').stat().st_size / 1024:.0f} KB)")
