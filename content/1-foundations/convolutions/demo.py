"""
Level N1 · Convolutions

Run:  python demo.py            about 1–2 minutes (needs numpy + torch)
      python demo.py --export   also writes site/public/data/convolutions/digits.json for the page (course use only)

Part 1 prints every number the page asks about, on a 5×5 picture you can check on paper.
Part 2 trains a tiny convolutional network and a plain MLP on handwritten digits (MNIST,
downloaded once, about 10 MB, into ~/.cache/llm-by-hand/mnist) and compares them.
"""
import argparse
import gzip
import json
import pathlib
import time
import urllib.request

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--export", action="store_true")
args = ap.parse_args()
np.set_printoptions(suppress=True)

# ============================================================== part 1: on paper
print("=" * 64)
print("PART 1 · one 3×3 filter sliding over a 5×5 picture")
print("=" * 64)
img = np.zeros((5, 5), int)
img[:, 2] = 1                                   # a vertical stroke, like the digit 1
v_edge = np.array([[-1, 0, 1], [-1, 0, 1], [-1, 0, 1]])
h_edge = v_edge.T
blur = np.ones((3, 3)) / 9


def conv2d(x, k, stride=1, pad=0):
    """Slide k over x. out[i, j] = sum of (the window under k) × k. No flipping."""
    x = np.pad(x, pad)
    kh, kw = k.shape
    oh = (x.shape[0] - kh) // stride + 1
    ow = (x.shape[1] - kw) // stride + 1
    out = np.zeros((oh, ow))
    for i in range(oh):
        for j in range(ow):
            out[i, j] = (x[i * stride:i * stride + kh, j * stride:j * stride + kw] * k).sum()
    return out


print("picture:\n", img)
print("vertical-edge filter:\n", v_edge)
w = img[0:3, 0:3]
print("\nout[0][0]: the window at the top-left\n", w)
print("window × filter, added up:", " + ".join(f"{a}×{b}" for a, b in zip(w.ravel(), v_edge.ravel()) if a), "=", (w * v_edge).sum())
out = conv2d(img, v_edge)
print("\nthe whole output, shape", out.shape, "\n", out.astype(int))
print("out[1][2] =", int(out[1, 2]))
img2 = np.zeros((5, 5), int)
img2[:, 1] = 1
print("stroke moved to column 1: out[0][1] =", int(conv2d(img2, v_edge)[0, 1]))
print("\nhorizontal-edge filter on the same picture:\n", conv2d(img, h_edge).astype(int))
print("blur filter, out[0][1] =", round(conv2d(img, blur)[0, 1], 4), "(three 1s in the window, each × 1/9)")


def out_size(n, k, s=1, p=0):
    return (n - k + 2 * p) // s + 1


print("\noutput size = floor((n − k + 2p) / s) + 1")
for n, k, s, p in [(5, 3, 1, 0), (5, 3, 1, 1), (28, 5, 1, 0), (32, 3, 2, 1), (28, 3, 1, 1)]:
    print(f"  n={n:2d} k={k} stride={s} padding={p}  →  {out_size(n, k, s, p)}")

# conv-stride: any square filter f, any stride s, no padding
a25 = np.arange(25.0).reshape(5, 5)
print("\nstride 2, 3×3 filter of 1s on np.arange(25).reshape(5, 5): windows start at rows/columns 0 and 2")
print(conv2d(a25, np.ones((3, 3)), stride=2))
print("6×6 picture, 2×2 filter [[1, 0], [0, 0]], stride 2 (keeps x[2i, 2j]):\n",
      conv2d(np.arange(36.0).reshape(6, 6), np.array([[1, 0], [0, 0]]), stride=2))
print("7×7 picture, 3×3 filter, stride 2: side (7 − 3) // 2 + 1 =", out_size(7, 3, 2),
      "\n", conv2d(np.ones((7, 7)), np.ones((3, 3)), stride=2))

small = 6 * 6 * 4 * 4
print(f"\na dense layer from 6×6 pixels to a 4×4 output: {6 * 6} × {4 * 4} = {small} weights (the filter: 9)")
dense = 28 * 28 * 26 * 26
print(f"\na dense layer from 28×28 pixels to a 26×26 output: {28 * 28} × {26 * 26} = {dense:,} weights")
print("one 3×3 filter making the same 26×26 output: 9 weights (+1 bias)")
print("16 such filters on 8 input channels: 16 × 8 × 9 =", 16 * 8 * 9, "weights")

# channels: each filter reads every input channel; one bias per output channel
def conv_params(k, c_in, c_out):
    return k * k * c_in * c_out + c_out
print("\nchannels: a 3×3 layer, 1 → 8 channels:", 3 * 3 * 1 * 8, "weights +", 8, "biases =", conv_params(3, 1, 8))
print("a 3×3 layer, 8 → 16 channels:", 3 * 3 * 8 * 16, "weights +", 16, "biases =", conv_params(3, 8, 16))
print("the final dense layer, 16 × 5 × 5 = 400 inputs → 10 scores:", 400 * 10 + 10)
print("the whole small CNN:", conv_params(3, 1, 8) + conv_params(3, 8, 16) + 400 * 10 + 10)
print(f"the dense layer has {dense / 9:,.0f} times more weights")

def receptive(layers, pool, show=False):
    width, gap = 1, 1                  # patch width in pixels; distance between neighboring cells
    for n in range(layers):
        width += 2 * gap               # a 3×3 conv adds (3 − 1) × gap
        if show: print(f"  conv {n + 1}: width {width:2d}, gap {gap}")
        if pool:
            width += gap               # a 2×2 pool adds (2 − 1) × gap ...
            gap *= 2                   # ... and doubles the gap
            if show: print(f"  pool {n + 1}: width {width:2d}, gap {gap}")
    return width


print("\nreceptive field of conv, pool, conv, pool, step by step:")
receptive(2, True, show=True)


print("conv, pool, conv, pool: one output sees", receptive(2, True), "×", receptive(2, True), "pixels")
for L in (1, 2, 3, 5):
    print(f"{L} stacked 3×3 layers: one output pixel sees a {1 + 2 * L}×{1 + 2 * L} patch of the picture")

pool_in = np.array([[1, 3, 0, 2], [4, 2, 1, 1], [0, 0, 5, 6], [1, 2, 7, 0]])
pool = pool_in.reshape(2, 2, 2, 2).max(axis=(1, 3))
print("\n2×2 max pooling of\n", pool_in, "\n→\n", pool)

# ============================================================== part 2: real digits
CACHE = pathlib.Path.home() / ".cache/llm-by-hand/mnist"
URL = "https://ossci-datasets.s3.amazonaws.com/mnist/"


def load(split):
    CACHE.mkdir(parents=True, exist_ok=True)
    pre = "train" if split == "train" else "t10k"
    out = []
    for name in (f"{pre}-images-idx3-ubyte.gz", f"{pre}-labels-idx1-ubyte.gz"):
        f = CACHE / name
        if not f.exists():
            urllib.request.urlretrieve(URL + name, f)
        out.append(gzip.open(f).read())
    return (np.frombuffer(out[0], np.uint8, offset=16).reshape(-1, 28, 28),
            np.frombuffer(out[1], np.uint8, offset=8))


print("\n" + "=" * 64)
print("PART 2 · a tiny convolutional network vs an MLP on handwritten digits")
print("=" * 64)
xtr, ytr = load("train")
xte, yte = load("test")
print("train", xtr.shape, "test", xte.shape)

if args.export:
    pick = [int(np.where(ytr == d)[0][0]) for d in (7, 1, 3, 0)]
    p = pathlib.Path(__file__).resolve().parents[3] / "site/public/data/convolutions/digits.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"labels": [int(ytr[i]) for i in pick], "digits": [xtr[i].tolist() for i in pick]},
                            separators=(",", ":")))
    print("wrote", p)

import torch  # noqa: E402
import torch.nn as nn  # noqa: E402

torch.manual_seed(0)
torch.set_num_threads(4)
Xtr = torch.tensor(xtr, dtype=torch.float32).unsqueeze(1) / 255
Xte = torch.tensor(xte, dtype=torch.float32).unsqueeze(1) / 255
Ytr, Yte = torch.tensor(ytr, dtype=torch.long), torch.tensor(yte, dtype=torch.long)

cnn = nn.Sequential(
    nn.Conv2d(1, 8, 3), nn.ReLU(), nn.MaxPool2d(2),       # 28 → 26 → 13
    nn.Conv2d(8, 16, 3), nn.ReLU(), nn.MaxPool2d(2),      # 13 → 11 → 5
    nn.Flatten(), nn.Linear(16 * 5 * 5, 10))
mlp = nn.Sequential(nn.Flatten(), nn.Linear(784, 64), nn.ReLU(), nn.Linear(64, 10))
count = lambda m: sum(p.numel() for p in m.parameters())
print(f"CNN parameters: {count(cnn):,}    MLP parameters: {count(mlp):,}")


def shifted(x, d):
    """Move every picture d pixels right and d pixels down."""
    return torch.roll(x, shifts=(d, d), dims=(2, 3))


def accuracy(m, x, y):
    with torch.no_grad():
        return (m(x).argmax(1) == y).float().mean().item()


for name, m in (("CNN", cnn), ("MLP", mlp)):
    opt = torch.optim.Adam(m.parameters(), lr=2e-3)
    t = time.time()
    g = torch.Generator().manual_seed(0)
    for step in range(1500):
        ix = torch.randint(0, len(Xtr), (128,), generator=g)
        loss = nn.functional.cross_entropy(m(Xtr[ix]), Ytr[ix])
        opt.zero_grad()
        loss.backward()
        opt.step()
    print(f"{name}: test accuracy {accuracy(m, Xte, Yte):.3f}   "
          f"test pictures moved 3 pixels: {accuracy(m, shifted(Xte, 3), Yte):.3f}   ({time.time() - t:.0f}s)")
