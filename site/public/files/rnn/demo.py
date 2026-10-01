"""
Level N3 · Recurrent networks

Run:  python demo.py      (needs numpy; torch for part 3; about 20 seconds)

Part 1: a recurrent network with a ONE-number hidden state, every step by hand.
Part 2: how much the first input still matters at the last step (the gradient through time).
Part 3: "remember the first symbol" with a real RNN: easy for short sequences, hopeless for long ones.
The course records the full curves the page plays back with a separate script.
"""
import numpy as np

np.set_printoptions(precision=4, suppress=True)

print("=" * 64)
print("PART 1 · h_t = tanh(w_x·x_t + w_h·h_(t−1) + b), a one-number hidden state")
print("=" * 64)
w_x, w_h, b, h = 1.0, 0.5, 0.0, 0.0
xs = [1, 0, 0, 0]
hs = []
for t, x in enumerate(xs, 1):
    z = w_x * x + w_h * h + b
    h = np.tanh(z)
    hs.append(h)
    print(f"t={t}  x={x}  z = {w_x}×{x} + {w_h}×{hs[-2] if t > 1 else 0.0:.4f} + {b} = {z:.4f}   h = tanh(z) = {h:.4f}")
print("the 1 at step 1 fades: h =", np.round(hs, 4))

print("\nthe same three weights are used at every step: w_x, w_h, b. A sequence of 1000 steps still has 3 weights.")

print("\n" + "=" * 64)
print("PART 2 · how much does h_1 still move h_t?   d h_t / d h_1 = product of w_h × tanh'(z_s)")
print("=" * 64)
g = 1.0
for t in range(1, 4):
    factor = w_h * (1 - hs[t] ** 2)
    g *= factor
    print(f"step {t + 1}: factor w_h·(1 − h²) = {w_h}×(1 − {hs[t]:.4f}²) = {factor:.4f}   product so far {g:.4f}")
print(f"d h_4 / d h_1 = {g:.4f}")

for wh in (0.5, 0.9, 1.5):
    print(f"no tanh, w_h = {wh}: after 30 steps the product is {wh}^29 = {wh ** 29:.3e}")
print("each step multiplies by a factor; 29 factors below 1 shrink to almost 0, above 1 blow up")


def rnn_step(x, h, Wx, Wh, b):
    """Vector version, rows as everywhere in the course: x (D,), h (H,), Wx (D, H), Wh (H, H), b (H,)."""
    return np.tanh(x @ Wx + h @ Wh + b)


rng = np.random.default_rng(0)
Wx, Wh, bb = rng.normal(0, 0.5, (2, 3)).T, rng.normal(0, 0.5, (2, 2)).T, np.zeros(2)
hv = np.zeros(2)
for x in np.eye(3):
    hv = rnn_step(x, hv, Wx, Wh, bb)
print("\nvector RNN, H = 2, D = 3, inputs one-hot 0, 1, 2 (seed 0): final h =", np.round(hv, 4))

# rnn-all: keep every hidden state, one row per step → shape (L, H)
Wx1 = np.array([[1, 0], [0, 1], [0, 0.]])       # (D, H) = (3, 2)
Wh1 = np.array([[0.5, 0], [0, 0.5]])             # (H, H)
h, hs = np.zeros(2), []
for x in np.eye(3):
    h = rnn_step(x, h, Wx1, Wh1, np.zeros(2))
    hs.append(h)
H_all = np.stack(hs)
print("\nevery hidden state for one-hot inputs 0, 1, 2 (W_x = first two rows of I, W_h = 0.5·I), shape", H_all.shape)
print(np.round(H_all, 4))
print("the last row is the final h from rnn():", np.round(H_all[-1], 4))

print("\n" + "=" * 64)
print("PART 3 · remember the first symbol (A or B) after k steps; guessing gives 50%")
print("=" * 64)
import torch  # noqa: E402
import torch.nn as nn  # noqa: E402

torch.set_num_threads(4)


def batch(k, n, g):
    first = torch.randint(0, 2, (n,), generator=g)
    seq = torch.cat([first[:, None], torch.randint(2, 5, (n, k - 1), generator=g)], 1)
    return nn.functional.one_hot(seq, 5).float(), first


class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.rnn = nn.RNN(5, 32, batch_first=True)
        self.out = nn.Linear(32, 2)

    def forward(self, x):
        return self.out(self.rnn(x)[0][:, -1])


for k in (5, 40):
    torch.manual_seed(0)
    g = torch.Generator().manual_seed(1)
    net = Net()
    opt = torch.optim.Adam(net.parameters(), lr=3e-3)
    for _ in range(1500):
        x, y = batch(k, 64, g)
        loss = nn.functional.cross_entropy(net(x), y)
        opt.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        opt.step()
    xt, yt = batch(k, 1000, torch.Generator().manual_seed(999))
    with torch.no_grad():
        acc = (net(xt).argmax(1) == yt).float().mean().item()
    print(f"k = {k:2d}: accuracy on 1000 new sequences {acc:.3f}")
