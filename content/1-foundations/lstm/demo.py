"""
Level N4 · LSTM and GRU (boss)

Run:  python demo.py            about 1.5 minutes: the numbers on the page, then trains a character-level LSTM
      python demo.py --rnn      the same training with a plain RNN instead (it stays stuck on the color rule)
      python demo.py --export   trains both and writes site/public/data/lstm/samples.json for the page

Part 1 prints every number the page asks about.
Part 2 is the boss: an LSTM reads text one character at a time and learns to write new lines.
The text is made by our own rules (below), so we can check every line the model writes.
"""
import argparse
import json
import pathlib
import re
import time

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--rnn", action="store_true")
ap.add_argument("--export", action="store_true")
args = ap.parse_args()
np.set_printoptions(precision=4, suppress=True)


def sigmoid(z):
    return 1 / (1 + np.exp(-z))


# ============================================================== part 1: one cell by hand
print("=" * 64)
print("PART 1 · one LSTM cell, every number")
print("=" * 64)
c_prev, f, i, g, o = 1.0, 0.9, 0.5, 0.8, 0.6
c = f * c_prev + i * g
h = o * np.tanh(c)
print(f"c_prev = {c_prev}, forget f = {f}, input i = {i}, candidate g = {g}, output o = {o}")
print(f"c = f·c_prev + i·g = {f}×{c_prev} + {i}×{g} = {c:.4f}")
print(f"h = o·tanh(c) = {o}×tanh({c:.4f}) = {o}×{np.tanh(c):.4f} = {h:.4f}")

print("\nthe conveyor belt: nothing new comes in (i = 0), the cell keeps f of what it had each step")
for fk in (0.5, 0.9, 0.99):
    print(f"  f = {fk:<5}  after 10 steps c = {fk ** 10:.4f}   after 50 steps c = {fk ** 50:.4f}")
f_half = 0.5 ** (1 / 50)
print(f"to keep half of c after 50 steps: f = 0.5^(1/50) = {f_half:.4f}")

print("\nwhat reaches step 1 when the loss is at step 51 (50 steps back):")
print(f"  plain RNN, each step multiplies by w_h·tanh'(z) ≈ 0.5:   0.5^50 = {0.5 ** 50:.3e}")
print(f"  LSTM cell path, each step multiplies by f = 0.99:        0.99^50 = {0.99 ** 50:.4f}")

# the gates come from the input and the previous h through sigmoids
x, h_prev = 1.0, 0.0
w_f, u_f, b_f = 2.0, 0.0, 1.0
z_f = w_f * x + u_f * h_prev + b_f
print(f"\na gate is a sigmoid: f = sigmoid(w_f·x + u_f·h_prev + b_f) = sigmoid({w_f}×{x} + {u_f}×{h_prev} + {b_f}) "
      f"= sigmoid({z_f}) = {sigmoid(z_f):.4f}")


def lstm_step(x, h, c, W, U, b):
    """Rows, as everywhere in the course: x (D,), h (H,), W (D, 4H), U (H, 4H), b (4H,). Gate order: f, i, g, o."""
    z = x @ W + h @ U + b
    H = h.shape[0]
    f, i, g, o = sigmoid(z[:H]), sigmoid(z[H:2 * H]), np.tanh(z[2 * H:3 * H]), sigmoid(z[3 * H:])
    c = f * c + i * g
    return o * np.tanh(c), c


print("\nwhy the forget bias starts at 2: before training, the gate is f = sigmoid(bias)")
for fb in (0.0, 2.0):
    fv = sigmoid(fb)
    print(f"  bias {fb}: f = {fv:.4f}; over 79 steps the cell path keeps f^79 = {fv ** 79:.2e}")

hh, cc = lstm_step(np.array([0.0]), np.zeros(1), np.array([1.0]), np.zeros((1, 4)), np.zeros((1, 4)), np.array([2.0, 0, 1, 0]))
print("lstm_step with H = 1, bias [2, 0, 1, 0], c_prev = 1, x = 0, h = 0: c =", np.round(cc, 4), " h =", np.round(hh, 4))

rng = np.random.default_rng(0)
W, U, b = rng.normal(0, 0.5, (8, 3)).T, rng.normal(0, 0.5, (8, 2)).T, np.zeros(8)
hh, cc = lstm_step(np.array([1.0, 0.0, 0.0]), np.zeros(2), np.zeros(2), W, U, b)
print("\nlstm_step with H = 2, D = 3 (seed 0): h =", np.round(hh, 4), " c =", np.round(cc, 4))

# GRU (section 3)
z_gate, hcand, hp = 0.25, -0.2, 0.6
print(f"\nGRU: h = (1 − z)·h_prev + z·h_candidate = (1 − {z_gate})×{hp} + {z_gate}×({hcand}) = {(1 - z_gate) * hp + z_gate * hcand:.4f}")


def gru_step(x, h, P):
    """The boss, part 1: one GRU step, rows as everywhere. P holds Wz, Wr, Wh (D, H), Uz, Ur, Uh (H, H), bz, br, bh (H,)."""
    z = sigmoid(x @ P["Wz"] + h @ P["Uz"] + P["bz"])
    r = sigmoid(x @ P["Wr"] + h @ P["Ur"] + P["br"])
    h_cand = np.tanh(x @ P["Wh"] + (r * h) @ P["Uh"] + P["bh"])
    return (1 - z) * h + z * h_cand


P0 = {k: np.zeros((1, 1)) for k in ["Wz", "Uz", "Wr", "Ur", "Wh", "Uh"]}
P0.update({k: np.zeros(1) for k in ["bz", "br", "bh"]})
print("GRU step, all weights 0, h_prev = 0.8: z = r = 0.5, candidate 0 → h =", gru_step(np.array([3.0]), np.array([0.8]), P0))
rg = np.random.default_rng(3)
P3 = {k: rg.normal(0, 0.5, (3, 2) if k[0] == "W" else (2, 2) if k[0] == "U" else (2,))
      for k in ["Wz", "Uz", "bz", "Wr", "Ur", "br", "Wh", "Uh", "bh"]}
print("GRU step, D = 3, H = 2, seed 3:", np.round(gru_step(np.array([1.0, 0, -1]), np.array([0.5, -0.5]), P3), 4))
D, H = 10, 20
block = D * H + H * H + H
print(f"weights per block with D = {D}, H = {H}: {D}×{H} + {H}×{H} + {H} = {block};  GRU 3 blocks = {3 * block},  LSTM 4 blocks = {4 * block}")

# bidirectional (section 4)
sent = "he sat by the bank of the river".split()
k = sent.index("bank")
print(f"\nbidirectional, at '{sent[k]}' (word {k}): forward has read {sent[:k + 1]} ({k + 1} words), "
      f"backward has read {sent[k:][::-1]} ({len(sent) - k} words)")
print(f"output shape with H = 32 per direction, {len(sent)} words: ({len(sent)}, {32 + 32})")

# ============================================================== the text rules
COLORS = ["red", "blue", "green", "gold", "pink", "gray"]
ANIMALS = ["fox", "cat", "owl", "bee", "yak", "dog"]
VERBS = ["sees", "hides", "finds", "wants", "keeps", "likes"]
THINGS = ["box", "cup", "hat", "map", "key", "bag"]
LINE = re.compile(r"^the (\w+) (\w+) (\w+) the (\w+) (\w+)\.$")


def make_line(r):
    c = COLORS[r.integers(6)]
    a, v = ANIMALS[r.integers(6)], VERBS[r.integers(6)]
    t = THINGS[r.integers(6)]
    return f"the {c} {a} {v} the {c} {t}."


def check(line):
    """'ok' (follows every rule), 'color' (right shape, but the two colors differ) or 'broken'."""
    m = LINE.match(line)
    if not m:
        return "broken"
    c1, a, v, c2, t = m.groups()
    if c1 not in COLORS or a not in ANIMALS or v not in VERBS or c2 not in COLORS or t not in THINGS:
        return "broken"
    return "ok" if c1 == c2 else "color"


print("\n" + "=" * 64)
print("PART 2 · the boss: a character-level LSTM writes new lines")
print("=" * 64)
r = np.random.default_rng(0)
print("the rules: the <color> <animal> <verb> the <SAME color> <thing>.")
print("three lines from the generator:")
for _ in range(3):
    print("   ", make_line(r))
print("6 colors × 6 animals × 6 verbs × 6 things =", 6 ** 4, "different lines")
print(f"if the second color is a random guess, it matches the first 1 time in 6 = {100 / 6:.1f}%")
print("in \"the red fox sees the red box.\" the second color starts", len("red fox sees the "), "characters after the first one")

import torch  # noqa: E402
import torch.nn as nn  # noqa: E402

torch.manual_seed(0)
text = "\n".join(make_line(r) for _ in range(20000)) + "\n"
chars = sorted(set(text))
stoi = {ch: k for k, ch in enumerate(chars)}
data = torch.tensor([stoi[ch] for ch in text])
print(f"\ntraining text: {len(text):,} characters, {len(chars)} different characters")


class CharLSTM(nn.Module):
    def __init__(self, V, H=128):
        super().__init__()
        self.emb = nn.Embedding(V, 32)
        self.lstm = nn.LSTM(32, H, batch_first=True)
        self.out = nn.Linear(H, V)
        with torch.no_grad():                  # start the forget gates near 1 (bias 2 → f ≈ 0.88): remember by default
            self.lstm.bias_ih_l0[H:2 * H].fill_(2.0)
            self.lstm.bias_hh_l0[H:2 * H].fill_(0.0)

    def forward(self, x, state=None):
        h, state = self.lstm(self.emb(x), state)
        return self.out(h), state


class CharRNN(CharLSTM):
    """The same model with a plain RNN in place of the LSTM."""

    def __init__(self, V, H=128):
        nn.Module.__init__(self)
        self.emb = nn.Embedding(V, 32)
        self.lstm = nn.RNN(32, H, batch_first=True)
        self.out = nn.Linear(H, V)


def sample(net, n, temp, seed):
    g = torch.Generator().manual_seed(seed)
    lines, x, state, cur = [], torch.tensor([[stoi["\n"]]]), None, ""
    with torch.no_grad():
        while len(lines) < n:
            logits, state = net(x, state)
            p = torch.softmax(logits[0, -1] / temp, 0)
            k = torch.multinomial(p, 1, generator=g).item()
            ch = chars[k]
            if ch == "\n" or len(cur) > 80:
                lines.append(cur)
                cur = ""
            else:
                cur += ch
            x = torch.tensor([[k]])
    return lines


def score(lines):
    kinds = [check(l) for l in lines]
    return {k: kinds.count(k) / len(lines) for k in ("ok", "color", "broken")}




def train(kind, steps=1800, seed=0):
    torch.manual_seed(seed)
    net = CharLSTM(len(chars)) if kind == "lstm" else CharRNN(len(chars))
    opt = torch.optim.Adam(net.parameters(), lr=3e-3)
    SEQ, B = 96, 64
    snaps, start = [], time.time()
    gen = torch.Generator().manual_seed(1)
    for step in range(steps + 1):
        if step % 150 == 0 or step == 100:
            lines = sample(net, 200, 0.8, seed=step)
            s = score(lines)
            snaps.append({"step": step, "lines": lines[:8], **{k: round(v, 3) for k, v in s.items()}})
            print(f"{kind:4s} step {step:4d}  follows every rule {s['ok']:4.0%}  colors differ {s['color']:4.0%}"
                  f"  broken {s['broken']:4.0%}   e.g. {lines[0]!r}   ({time.time() - start:.0f}s)")
        if step == steps:
            break
        ix = torch.randint(0, len(data) - SEQ - 1, (B,), generator=gen)
        x = torch.stack([data[j:j + SEQ] for j in ix])
        y = torch.stack([data[j + 1:j + SEQ + 1] for j in ix])
        logits, _ = net(x)
        loss = nn.functional.cross_entropy(logits.reshape(-1, len(chars)), y.reshape(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
    return snaps


kinds = ["lstm", "rnn"] if args.export else ["rnn" if args.rnn else "lstm"]
runs = {k: train(k) for k in kinds}
final = runs[kinds[0]][-1]
print(f"\nboss target: at least 90% of 200 sampled lines follow every rule.  {kinds[0]} got {final['ok']:.0%}"
      f"  → {'PASS' if final['ok'] >= 0.9 else 'not yet'}")

if args.export:
    p = pathlib.Path(__file__).resolve().parents[3] / "site/public/data/lstm/samples.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"temp": 0.8, "runs": runs}, separators=(",", ":")))
    print("wrote", p)
