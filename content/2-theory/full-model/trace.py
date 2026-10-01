"""
Level 17 · the microscope: one input goes through a whole (tiny) decoder-only Transformer, and every tensor is recorded.

The tiny model has the page model's parts with small sizes, all different from each other, so you can tell every
axis apart by its size:  B = 1, L = 3, d_model = 6, d_ff = 12, 42 tokens, 1 head, 1 block.
It is trained on the numbers 0–99 (a few seconds), then reads "8 9 =" and writes the next token.

Writes site/public/data/full-model/microscope.json.   Run:  python trace.py
"""
import json
import math
import pathlib
import random

import torch
import torch.nn as nn
import torch.nn.functional as F

import demo

OUT = pathlib.Path(__file__).resolve().parents[3] / "site/public/data/full-model/microscope.json"
D, D_FF = 6, 12


def num(v):
    v = float(v)
    return round(v, 2) if math.isfinite(v) else None       # −∞ (a blocked score) is written as null


r2 = lambda t: [[num(v) for v in row] for row in t]

torch.manual_seed(0)
model = demo.Decoder(d=D, heads=1, layers=1, d_ff=D_FF)
nums = list(range(100))
loss_fn = nn.CrossEntropyLoss(ignore_index=demo.PAD)
opt = torch.optim.Adam(model.parameters(), lr=1e-2)
rng = random.Random(0)
for ep in range(300):
    rng.shuffle(nums)
    for i in range(0, 100, 20):
        x, y = demo.tensors(nums[i:i + 20])
        loss = loss_fn(model(x).reshape(-1, demo.V), y.reshape(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
model.eval()
print("tiny model reads 0–99 right:", sum(demo.read_aloud(model, n) == demo.words(n) for n in range(100)), "of 100")

N = 89
ids = torch.tensor([[demo.ID[c] for c in str(N)] + [demo.EQ]])      # "8 9 =": (1, 3)
tok = [demo.VOCAB[i] for i in ids[0]]
L = ids.size(1)
steps = []


def T(name, t, axes, big, rows=None, cols=None, note=None):
    """One tensor for the page: its values (first example), named axes, and the page model's shape."""
    a = t.detach()
    while a.dim() > 2:
        a = a[0]
    vals = r2(a) if a.dim() == 2 else [[num(v) for v in a]]
    return {"name": name, "axes": axes, "big": big, "values": vals, "rows": rows, "cols": cols, "note": note}


BLd = [["B", 1], ["L", L], ["d_model", D]]
BIG = "(64, 8, 64)"
dims = [f"dim {j}" for j in range(D)]

with torch.no_grad():
    blk = model.blocks[0]
    at = blk.attn
    steps.append({"title": "Token ids", "text": "The digits and “=” become ids. There is one sequence: the words will be written after “=”.",
                  "tensors": [T("ids", ids, [["B", 1], ["L", L]], "(64, 8)", cols=tok)]})
    e = model.tok(ids)
    steps.append({"title": "Token embedding", "text": "Each id picks one row of the embedding table: 6 numbers per token.",
                  "tensors": [T("embedding", e, BLd, BIG, rows=tok)]})
    es = e * math.sqrt(D)
    steps.append({"title": "Scale by √d_model", "text": f"Multiply by √6 ≈ {math.sqrt(D):.2f}. The table started with small numbers "
                  "(about 1/√6), so after this step they are about the size of the position numbers.",
                  "tensors": [T("embedding × √d_model", es, BLd, BIG, rows=tok)]})
    x = es + model.pe[:L]
    steps.append({"title": "Add the positions", "text": "Add row t of the fixed sine/cosine table to position t. This is how the same digit at "
                  "position 0 and at position 1 would differ.",
                  "tensors": [T("position rows", model.pe[:L].unsqueeze(0), [["L", L], ["d_model", D]], "(8, 64)",
                                rows=[f"pos {t}" for t in range(L)]),
                              T("x", x, BLd, BIG, rows=tok)]})
    h = blk.n1(x)
    steps.append({"title": "LayerNorm 1 (pre-norm)", "text": "Normalize each row before attention: mean 0, std 1, then a learned "
                  "gain and shift (γ and β). x itself is kept for the residual.",
                  "tensors": [T("LN1(x)", h, BLd, BIG, rows=tok)]})
    q, k, v = at.Wq(h), at.Wk(h), at.Wv(h)
    steps.append({"title": "Q, K and V", "text": "Three matrices (6 × 6, no bias) turn each normalized row into a query, a key and a value.",
                  "tensors": [T("Q", q, BLd, BIG, rows=tok, note="The page model splits these 64 numbers into 4 heads of 16."),
                              T("K", k, BLd, BIG, rows=tok), T("V", v, BLd, BIG, rows=tok)]})
    sc = (q @ k.transpose(-2, -1) / math.sqrt(at.dk)).masked_fill(demo.causal_mask(L), float("-inf"))
    steps.append({"title": "Scores, with the causal mask", "text": "Each row scores every earlier position and itself: Q Kᵀ / √d_k. "
                  "Later positions are blocked (−∞), so “8” sees only itself and “=” sees all three.",
                  "tensors": [T("scores = Q Kᵀ / √d_k", sc, [["B", 1], ["L", L], ["L", L]], "(64, 4, 8, 8)", rows=tok, cols=tok,
                                note="The page model has 4 heads, so its scores have a head axis.")]})
    w = F.softmax(sc, dim=-1)
    steps.append({"title": "Attention weights", "text": "Softmax along each row. Blocked scores get weight 0; every row sums to 1.",
                  "tensors": [T("weights", w, [["B", 1], ["L", L], ["L", L]], "(64, 4, 8, 8)", rows=tok, cols=tok)]})
    ctx = w @ v
    steps.append({"title": "Context", "text": "weights @ V: each row is a mix of the value rows it may see.",
                  "tensors": [T("context = weights @ V", ctx, BLd, BIG, rows=tok)]})
    a_out = at.Wo(ctx)
    steps.append({"title": "Output matrix W_O", "text": "One more 6 × 6 matrix (with a bias). In the page model it also joins the 4 heads.",
                  "tensors": [T("attention output", a_out, BLd, BIG, rows=tok)]})
    x = x + a_out
    steps.append({"title": "Residual add", "text": "x = x + attention output. The block adds to x; it never replaces it.",
                  "tensors": [T("x after attention", x, BLd, BIG, rows=tok)]})
    h = blk.n2(x)
    steps.append({"title": "LayerNorm 2", "text": "Normalize again, this time before the FFN.",
                  "tensors": [T("LN2(x)", h, BLd, BIG, rows=tok)]})
    hid = F.relu(blk.ff[0](h))
    steps.append({"title": "FFN hidden", "text": "Each row on its own: widen to d_ff = 12 numbers, then ReLU sets the negative ones to 0.",
                  "tensors": [T("FFN hidden (after ReLU)", hid, [["B", 1], ["L", L], ["d_ff", D_FF]], "(64, 8, 128)", rows=tok)]})
    f_out = blk.ff[2](hid)
    steps.append({"title": "FFN output", "text": "Narrow back from 12 to 6 numbers per row.",
                  "tensors": [T("FFN output", f_out, BLd, BIG, rows=tok)]})
    x = x + f_out
    steps.append({"title": "Residual add", "text": "x = x + FFN output. This is the block's output. The page model has a second block here.",
                  "tensors": [T("block output", x, BLd, BIG, rows=tok)]})
    hf = model.norm(x)
    steps.append({"title": "Final LayerNorm", "text": "One last LayerNorm after all the blocks, before the output layer.",
                  "tensors": [T("final LN(x)", hf, BLd, BIG, rows=tok)]})
    logits = model.head(hf)
    steps.append({"title": "Output layer: logits", "text": "A 6 × 42 matrix plus a bias gives one row of 42 scores per position. "
                  "Only the last row (after “=”) picks the next token. The rows for “8” and “9” guess the next digit, "
                  "which the loss ignores.",
                  "tensors": [T("logits", logits, [["B", 1], ["L", L], ["tokens", demo.V]], "(64, 8, 42)", rows=tok,
                                cols=list(demo.VOCAB))]})
    probs = F.softmax(logits[0, -1], dim=-1)
    top = [[demo.VOCAB[int(i)], round(float(p), 3)] for p, i in zip(*probs.topk(5))]
    steps.append({"title": "Top tokens", "text": f"Softmax of the last row. The top token, “{top[0][0]}”, is appended, and the "
                  "model runs again on 4 tokens to write the next word.",
                  "tensors": [T("probabilities, last row", probs.unsqueeze(0), [["L", 1], ["tokens", demo.V]], "(64, 42)",
                                rows=["="], cols=list(demo.VOCAB))],
                  "top": top})

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"input": "8 9 =", "warning": "In the page model the batch (64) and d_model (64) are the same "
                           "number. To know which is which, look at the position: the batch is always the first axis.",
                           "steps": steps}, ensure_ascii=False, allow_nan=False, separators=(",", ":")))
print("wrote", OUT, OUT.stat().st_size, "bytes;", len(steps), "steps; next token after 8 9 =:", top[0], " top 5:", top)
for s in steps:
    print(" -", s["title"])
