"""
Train a small autoencoder on MNIST and export what the A3 page shows.

Run:  python export.py      (needs numpy + torch, about a minute)
Writes site/public/data/latents-and-dit/digits.json:
  six digits, their 16-number codes, the decoded pictures,
  and a walk between two digits through the 16-number space.
"""
import gzip
import json
import pathlib
import urllib.request

import numpy as np
import torch
import torch.nn as nn

torch.manual_seed(0)
CACHE = pathlib.Path.home() / ".cache/llm-by-hand/mnist"
CACHE.mkdir(parents=True, exist_ok=True)
for name in ("train-images-idx3-ubyte.gz", "train-labels-idx1-ubyte.gz"):
    if not (CACHE / name).exists():
        urllib.request.urlretrieve("https://ossci-datasets.s3.amazonaws.com/mnist/" + name, CACHE / name)
images = np.frombuffer(gzip.open(CACHE / "train-images-idx3-ubyte.gz").read(), np.uint8, offset=16).reshape(-1, 784)
labels = np.frombuffer(gzip.open(CACHE / "train-labels-idx1-ubyte.gz").read(), np.uint8, offset=8)
X = torch.tensor(images, dtype=torch.float32) / 255

enc = nn.Sequential(nn.Linear(784, 256), nn.ReLU(), nn.Linear(256, 16))
dec = nn.Sequential(nn.Linear(16, 256), nn.ReLU(), nn.Linear(256, 784), nn.Sigmoid())
opt = torch.optim.Adam([*enc.parameters(), *dec.parameters()], lr=2e-3)
for step in range(6000):
    x = X[torch.randint(0, len(X), (256,))]
    loss = ((dec(enc(x)) - x) ** 2).mean()
    opt.zero_grad(); loss.backward(); opt.step()
    if step % 1000 == 0 or step == 5999:
        print(f"step {step:4d}  reconstruction error {loss.item():.4f}")

pick = [int(np.where(labels == d)[0][0]) for d in (3, 7, 0, 5, 2, 8)]
with torch.no_grad():
    x = X[pick]
    z = enc(x)
    rec = dec(z)
    a, b = z[0], z[1]                                     # walk from the 3 to the 7
    walk = dec(torch.stack([a + (b - a) * k / 8 for k in range(9)]))

to_int = lambda t: (t.clamp(0, 1) * 255).round().int().tolist()
out = {
    "labels": [int(labels[i]) for i in pick],
    "digits": [images[i].tolist() for i in pick],
    "codes": np.round(z.numpy().astype(np.float64), 2).tolist(),
    "decoded": to_int(rec),
    "walk": to_int(walk),
}
p = pathlib.Path(__file__).resolve().parents[3] / "site/public/data/latents-and-dit/digits.json"
p.write_text(json.dumps(out, separators=(",", ":")))
print("wrote", p, f"{p.stat().st_size / 1024:.0f} KB")
print("code of the first digit (a 3):", out["codes"][0])
