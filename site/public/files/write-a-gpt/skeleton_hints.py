"""
Level 21 · Write your own GPT — starter file WITH HINTS

Every class and function you need, with no code inside, and comments that say which lines to write.
Try skeleton.py first: it has the same names, but no hints. Use this file if you are stuck.
Fill in each TODO, step by step (the steps on the page).
Copy this file (for example to my_gpt.py) and run it with:  python my_gpt.py      (setup: /setup/ on the course site)

Keep the class names and the attribute names written in the comments (tok, pos, blocks, norm1, attn, qkv, out,
norm2, ffn, norm, head, gain). The boss check (check.py) loads fixed weights into your model by these names.
"""
import math
import random

import torch
import torch.nn as nn
import torch.nn.functional as F

# ---------------------------------------------------------------- Step 1: data
PAD, BOS, EOS = 0, 1, 2
ITOS = ["<pad>", "<bos>", "<eos>"] + list("0123456789") + ["+", "="]   # 15 tokens, ids 0–14
STOI = {c: i for i, c in enumerate(ITOS)}   # {'<pad>': 0, '<bos>': 1, '<eos>': 2, '0': 3, …, '+': 13, '=': 14}
MAXLEN = 11          # the longest sequence: <bos> 9 9 + 9 9 = 1 9 8 <eos>
IGNORE = -100        # F.cross_entropy(..., ignore_index=IGNORE) skips these targets


def encode(a, b):
    """(23, 58) → [1, 5, 6, 13, 8, 11, 14, 11, 4, 2, 0]: <bos>, the characters, <eos>, padded to MAXLEN."""
    # TODO
    raise NotImplementedError


def make_xy(ids):
    """x = ids without the last, y = ids without the first.
    In y, set PAD and every target before the answer to IGNORE (the loss counts the answer digits only)."""
    # TODO
    raise NotImplementedError


def split(seed=0):
    """All 10,000 pairs (a, b) with 0 ≤ a, b ≤ 99, shuffled: 8,500 to train on, 500 for validation, 1,000 kept unseen.
    Given, not a TODO: check.py uses exactly this split, so your 1,000 unseen problems are the same as the page's.
    Pick the best epoch on the 500 validation problems; the 1,000 unseen ones are only for check.py's grade."""
    pairs = [(a, b) for a in range(100) for b in range(100)]
    random.Random(seed).shuffle(pairs)
    return pairs[:8500], pairs[8500:9000], pairs[9000:]


# ---------------------------------------------------------------- Step 2: the model
class RMSNorm(nn.Module):
    def __init__(self, d, eps=1e-6):
        super().__init__()
        # TODO: self.gain = nn.Parameter(torch.ones(d))   (one learned number per dimension)
        #       nn.Parameter registers it, so model.parameters() and the optimizer can see it

    def forward(self, x):                 # (B, L, d) → (B, L, d)
        # TODO: divide each row by sqrt(mean(x²) + eps) over the last axis (keepdim=True), then multiply by self.gain
        raise NotImplementedError


class Attention(nn.Module):
    def __init__(self, d, heads):
        super().__init__()
        # TODO: self.heads = heads              (forward needs it to split the heads)
        #       self.qkv = nn.Linear(d, 3 * d)   (q, k and v from one Linear, with bias)
        #       self.out = nn.Linear(d, d)

    def forward(self, x):                 # (B, L, d) → (B, L, d)
        # TODO: q, k, v = self.qkv(x).split(d, dim=-1)      (q is the first d columns, then k, then v; check.py's
        #                                                      weights assume this order)
        #       split into heads: .view(B, L, h, d_k).transpose(1, 2)       → (B, h, L, d_k)
        #       scores = q @ k.transpose(-2, -1) / sqrt(d_k)                → (B, h, L, L)
        #       causal mask: torch.triu(torch.ones(L, L, dtype=torch.bool), diagonal=1)   (True = blocked;
        #                    PyTorch calls the argument diagonal, NumPy calls it k), then masked_fill(mask, -inf)
        #       softmax over the last axis, then weights @ v                → (B, h, L, d_k)
        #       join the heads: .transpose(1, 2).contiguous().view(B, L, d)  (or .reshape(B, L, d))
        #           .view after a transpose fails without .contiguous(); see step 2 on the page
        #       then self.out
        raise NotImplementedError


class Block(nn.Module):
    def __init__(self, d, heads, d_ff):
        super().__init__()
        # TODO: self.norm1 = RMSNorm(d); self.attn = Attention(d, heads)
        #       self.norm2 = RMSNorm(d); self.ffn = nn.Sequential(nn.Linear(d, d_ff), nn.ReLU(), nn.Linear(d_ff, d))

    def forward(self, x):
        # TODO: pre-norm:  x = x + self.attn(self.norm1(x));  x = x + self.ffn(self.norm2(x))
        raise NotImplementedError


class GPT(nn.Module):
    """Keep the four argument names d, heads, layers, d_ff: check.py builds GPT(d=32, heads=4, layers=2, d_ff=64).
    d is the width of every vector (the d_model of levels 16–20). The token embeddings are not multiplied by sqrt(d)."""

    def __init__(self, d=64, heads=4, layers=2, d_ff=256):
        super().__init__()
        # TODO: self.tok = nn.Embedding(15, d)          token embedding
        #       self.pos = nn.Embedding(MAXLEN, d)      learned position embedding: one row per position 0–10
        #       self.blocks = nn.ModuleList(Block(d, heads, d_ff) for _ in range(layers))
        #           (a plain Python list hides the blocks from model.parameters(): they would never train)
        #       self.norm = RMSNorm(d)                  a final norm (pre-norm models need one)
        #       self.head = nn.Linear(d, 15)            the output layer

    def forward(self, x):                 # (B, L) ids → (B, L, 15) logits
        # TODO: h = self.tok(x) + self.pos(torch.arange(L))   (positions 0, 1, …, L−1, added to every example)
        #       h through every block, then self.norm, then self.head
        raise NotImplementedError


# ---------------------------------------------------------------- Steps 3–4: training
def overfit_one_batch():
    """8 fixed examples, 300 steps of Adam. The loss on the answer digits should fall close to 0."""
    # TODO: X, Y = tensors of the x and y rows of the first 8 training examples   (make_xy(encode(a, b)) for each)
    #       model = GPT();  opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    #       300 times:  logits = model(X)                                           (8, 10, 15)
    #                   loss = F.cross_entropy(logits.reshape(-1, 15), Y.reshape(-1), ignore_index=IGNORE)
    #                   (one row per position, as in level 17; without the reshape PyTorch says
    #                    "Expected target size [8, 15], got [8, 10]")
    #                   opt.zero_grad(); loss.backward(); opt.step()
    #       print the loss every 50 steps: it should fall from about 2.7 to near 0
    raise NotImplementedError


def train(epochs):
    """Batches of 64, Adam lr 1e-3, a new random order every epoch. The page uses train(40).
    Train on the 8,500 training problems. After every epoch, print the loss and the accuracy on the 500 validation problems.
    Accuracy can dip for an epoch or two, so keep the best: each time validation accuracy beats its best so far, save the
    model for check.py:
        torch.save({"config": {"d": 64, "heads": 4, "layers": 2, "d_ff": 256}, "state": model.state_dict()}, "model.pt")
    (use the sizes you actually built).

    One epoch, in batches (level U4 shows this in NumPy):
        perm = torch.randperm(len(X))              # X, Y: tensors of all training x and y rows
        for i in range(0, len(X), 64):
            idx = perm[i:i + 64]
            xb, yb = X[idx], Y[idx]
            ...                                    # forward, loss, zero_grad, backward, step
    """
    # TODO: the same four lines as in overfit_one_batch, inside the loop above
    #       (loss: F.cross_entropy(logits.reshape(-1, 15), yb.reshape(-1), ignore_index=IGNORE));
    #       after each epoch, count how many of the 500 validation pairs solve() gets right
    raise NotImplementedError


# ---------------------------------------------------------------- Step 5: evaluate
@torch.no_grad()
def solve(model, a, b):
    """Greedy: start from <bos>a+b=, append the top token until <eos>. Return the answer as a string."""
    # TODO: ids = [BOS] + [STOI[c] for c in f"{a}+{b}="]
    #       at most 4 times (3 digits + <eos>):
    #           nxt = model(torch.tensor([ids]))[0, -1].argmax()      the last position's top token
    #           stop if it is EOS; else add ITOS[nxt] to the answer and append nxt to ids
    #       call model.eval() before solving and model.train() before training again
    raise NotImplementedError


if __name__ == "__main__":
    # TODO: step by step — print examples, check the forward shape, overfit one batch, train, evaluate
    #       1. print(encode(23, 58)) and make_xy of it                          (step 1 on the page)
    #       2. print(GPT()(torch.tensor([x])).shape) → torch.Size([1, 10, 15])   (step 2)
    #       3. overfit_one_batch()                                              (step 3)
    #       4. model = train(40) (let train return the model), then print(solve(model, 23, 58))   (steps 4, 5)
    pass
