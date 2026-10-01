"""
Level U4 · Feeding data to a model

Run:  python demo.py      (needs numpy)

Every number the page asks you about is printed here, so you can check your answers
and see where each one comes from.
"""
import numpy as np

# --- 1. a dataset and its batches --------------------------------------------
# A dataset is anything with a length and a way to get example i.
class Dataset:
    def __init__(self, xs, ys):
        self.xs, self.ys = xs, ys

    def __len__(self):
        return len(self.xs)

    def __getitem__(self, i):
        return self.xs[i], self.ys[i]

xs = np.arange(10) * 10          # 10 examples: 0, 10, 20, …, 90
ys = np.array([0] * 5 + [1] * 5)  # sorted by class: five of class 0, then five of class 1
ds = Dataset(xs, ys)
print("examples:", len(ds), " example 3 =", tuple(int(v) for v in ds[3]))

n, bs = len(ds), 4
starts = list(range(0, n, bs))
sizes = [min(bs, n - s) for s in starts]
print(f"\n{n} examples, batch size {bs}")
print("  batch starts:", starts)
print("  batch sizes: ", sizes, " → batches per epoch:", len(sizes))
print("  last batch size:", sizes[-1])
print("  with drop_last (skip the short batch):", n // bs, "batches")

epochs = 3
print(f"\n{epochs} epochs × {len(sizes)} batches = {epochs * len(sizes)} steps")

# --- 2. shuffling ---------------------------------------------------------------
print("\nno shuffle, batch size 5, classes per batch:")
for s in range(0, n, 5):
    print(f"  batch {s // 5}: classes {ys[s:s + 5].tolist()}")

def batches(n, batch_size, rng):
    idx = rng.permutation(n)                       # a new random order
    return [idx[i:i + batch_size] for i in range(0, n, batch_size)]

rng = np.random.default_rng(0)
for epoch in range(3):
    bl = batches(n, bs, rng)
    print(f"epoch {epoch}: ", [b.tolist() for b in bl],
          " classes:", [ys[b].tolist() for b in bl])
    used = np.sort(np.concatenate(bl))
    assert (used == np.arange(n)).all()             # every example exactly once per epoch
print("every epoch uses each example exactly once: True")

# --- 3. train / held-out split, seeds ------------------------------------------
N, frac, bs_split = 50, 0.2, 8
n_held = int(N * frac)
perm = np.random.default_rng(42).permutation(N)    # split ONCE, with a fixed seed
held, train = perm[:n_held], perm[n_held:]
print(f"\n{N} examples, hold out {int(frac * 100)}%: held-out {len(held)}, train {len(train)}")
print(f"  train steps per epoch with batch size {bs_split}: {len(train) // bs_split}")
print("  overlap between train and held-out:", len(set(held) & set(train)))

a = np.random.default_rng(0).permutation(10)
b = np.random.default_rng(0).permutation(10)
c = np.random.default_rng(1).permutation(10)
print("\nseed 0:", a.tolist())
print("seed 0:", b.tolist(), " same as before:", (a == b).all())
print("seed 1:", c.tolist(), " same as seed 0:", (a == c).all())

# --- 4. padding and the collate function ---------------------------------------
PAD = 0

def collate(seqs, pad=PAD):
    L = max(len(s) for s in seqs)
    X = np.full((len(seqs), L), pad)
    mask = np.ones((len(seqs), L), dtype=bool)     # True = blocked (padding)
    for i, s in enumerate(seqs):
        X[i, :len(s)] = s
        mask[i, :len(s)] = False
    return X, mask

seqs = [[5, 3, 8], [2, 9], [7]]
X, mask = collate(seqs)
print("\nsequences:", seqs)
print("X, shape", X.shape)
print(X)
print("mask (True = PAD, blocked)")
print(mask)
print("PAD cells:", int(mask.sum()), "of", mask.size)

lengths = [2, 3, 6, 1]
L = max(lengths)
cells = len(lengths) * L
print(f"\nlengths {lengths} in one batch: padded to {L}, {cells} cells, "
      f"{sum(lengths)} real, {cells - sum(lengths)} PAD")
srt = sorted(lengths)
pairs = [srt[0:2], srt[2:4]]
cells2 = sum(len(p) * max(p) for p in pairs)
print(f"sorted by length into batches of 2: {pairs} → {cells2} cells, {cells2 - sum(lengths)} PAD")
