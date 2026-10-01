"""
Level 21 · Write your own GPT — starter file

Every class and function you need, with its name, its shapes and a one-line description, but no code and no hints.
Fill in each TODO, step by step (the steps on the page). If you are stuck, skeleton_hints.py is the same file with
comments that say which lines to write.
Copy this file (for example to my_gpt.py) and run it with:  python my_gpt.py      (setup: /setup/ on the course site)

Keep the class names and these attribute names. The boss check (check.py) loads fixed weights into your model by name:
    GPT:        tok, pos, blocks, norm, head
    Block:      norm1, attn, norm2, ffn
    Attention:  qkv, out          RMSNorm: gain
Block.ffn is an nn.Sequential (Linear, ReLU, Linear), so its weights are named ffn.0 and ffn.2.
tok and pos are nn.Embedding layers; head is an nn.Linear with a bias.
"""
import math
import random

import torch
import torch.nn as nn
import torch.nn.functional as F

# ---------------------------------------------------------------- Step 1: data
PAD, BOS, EOS = 0, 1, 2
ITOS = ["<pad>", "<bos>", "<eos>"] + list("0123456789") + ["+", "="]   # 15 tokens, ids 0–14
STOI = {c: i for i, c in enumerate(ITOS)}
MAXLEN = 11          # the longest sequence: <bos> 9 9 + 9 9 = 1 9 8 <eos>
IGNORE = -100        # targets with this value are not counted by the loss


def encode(a, b):
    """(23, 58) → [1, 5, 6, 13, 8, 11, 14, 11, 4, 2, 0]: <bos>, the characters, <eos>, padded to MAXLEN."""
    # TODO
    raise NotImplementedError


def make_xy(ids):
    """x and y, shifted by one. In y, only the answer digits and <eos> count; every other target is IGNORE."""
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
    """Divide each row by its root mean square, then multiply by a learned gain (one number per dimension)."""

    def __init__(self, d, eps=1e-6):
        super().__init__()
        # TODO: self.gain

    def forward(self, x):                 # (B, L, d) → (B, L, d)
        # TODO
        raise NotImplementedError


class Attention(nn.Module):
    """Masked multi-head self-attention. q, k and v come from one Linear layer (with bias).
    Column order of self.qkv(x), which is (B, L, 3d): the first d numbers are q, the next d are k, the last d are v.
    Head i uses numbers i*d_k to (i+1)*d_k - 1 of each (d_k = d / heads)."""

    def __init__(self, d, heads):
        super().__init__()
        # TODO: self.qkv (d → 3d), self.out (d → d)

    def forward(self, x):                 # (B, L, d) → (B, L, d)
        # TODO
        raise NotImplementedError


class Block(nn.Module):
    """One pre-norm block: attention, then the FFN (Linear d → d_ff, ReLU, Linear d_ff → d), each with a residual."""

    def __init__(self, d, heads, d_ff):
        super().__init__()
        # TODO: self.norm1, self.attn, self.norm2, self.ffn

    def forward(self, x):                 # (B, L, d) → (B, L, d)
        # TODO
        raise NotImplementedError


class GPT(nn.Module):
    """Token and position embeddings → the blocks → a final norm → the output layer.
    Keep the four argument names d, heads, layers, d_ff: check.py builds GPT(d=32, heads=4, layers=2, d_ff=64).
    d is the width of every vector (the d_model of levels 16–20). The token embeddings are not multiplied by sqrt(d)."""

    def __init__(self, d=64, heads=4, layers=2, d_ff=256):
        super().__init__()
        # TODO: self.tok, self.pos (one row per position 0–10), self.blocks, self.norm, self.head

    def forward(self, x):                 # (B, L) ids → (B, L, 15) logits
        # TODO
        raise NotImplementedError


# ---------------------------------------------------------------- Steps 3–4: training
def overfit_one_batch():
    """8 fixed examples, 300 steps of Adam. The loss on the answer digits should fall close to 0.
    The logits are (B, L, 15) and the targets (B, L): F.cross_entropy wants one row per position (as in level 17)."""
    # TODO
    raise NotImplementedError


def train(epochs):
    """Batches of 64, Adam lr 1e-3, a new random order every epoch. The page uses train(40).
    Train on the 8,500 training problems. After every epoch, print the loss and the accuracy on the 500 validation problems.
    Accuracy can dip for an epoch or two, so keep the best: each time validation accuracy beats its best so far, save the
    model for check.py:
        torch.save({"config": {"d": 64, "heads": 4, "layers": 2, "d_ff": 256}, "state": model.state_dict()}, "model.pt")
    (use the sizes you actually built)."""
    # TODO
    raise NotImplementedError


# ---------------------------------------------------------------- Step 5: evaluate
@torch.no_grad()
def solve(model, a, b):
    """Greedy: start from <bos>a+b=, append the top token until <eos>. Return the answer as a string."""
    # TODO
    raise NotImplementedError


if __name__ == "__main__":
    # TODO: step by step — print examples, check the forward shape, overfit one batch, train, evaluate
    pass
