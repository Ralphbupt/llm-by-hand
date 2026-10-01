"""
Level 21 · the microscope: one prompt goes through a whole (tiny) GPT, and every tensor is recorded.

The tiny GPT has your model's parts with small sizes, all different from each other:
B = 1, L = 5, d_model = 6, 2 heads of d_k = 3, d_ff = 12, 15 tokens, 1 block. It is trained on the 100 one-digit
sums (a few seconds), then reads "<bos>2+3=" and writes the next token.

Writes site/public/data/write-a-gpt/microscope.json.   Run:  python trace.py
"""
import json
import math
import pathlib
import random

import torch
import torch.nn.functional as F

import demo

OUT = pathlib.Path(__file__).resolve().parents[3] / "site/public/data/write-a-gpt/microscope.json"
D, H, D_FF = 6, 2, 12


def num(v):
    v = float(v)
    return round(v, 2) if math.isfinite(v) else None       # −∞ (a blocked score) is written as null


torch.manual_seed(0)
model = demo.GPT(d=D, heads=H, layers=1, d_ff=D_FF)
pairs = [(a, b) for a in range(10) for b in range(10)]
opt = torch.optim.Adam(model.parameters(), lr=1e-2)
rng = random.Random(0)
for ep in range(400):
    for x, y in demo.batches(pairs, 20, True, rng):
        loss = F.cross_entropy(model(x).reshape(-1, demo.VOCAB), y.reshape(-1), ignore_index=demo.IGNORE)
        opt.zero_grad()
        loss.backward()
        opt.step()
model.eval()
print("tiny GPT gets the one-digit sums right:", sum(s == str(a + b) for s, (a, b) in zip(demo.solve(model, pairs), pairs)), "of 100")

prompt = [demo.BOS] + [demo.STOI[c] for c in "2+3="]
toks = [demo.ITOS[i] for i in prompt]
x_ids = torch.tensor([prompt])
L = len(prompt)
steps = []


def T(name, t, axes, big, rows=None, cols=None, note=None):
    a = t.detach()
    while a.dim() > 2:
        a = a[0]
    vals = [[num(v) for v in row] for row in a] if a.dim() == 2 else [[num(v) for v in a]]
    return {"name": name, "axes": axes, "big": big, "values": vals, "rows": rows, "cols": cols, "note": note}


with torch.no_grad():
    blk = model.blocks[0]
    steps.append({"title": "Token ids", "text": "Five tokens: <bos>, 2, +, 3, =. Your model will see 10 tokens at a time (x of one padded problem).",
                  "tensors": [T("x", x_ids, [["B", 1], ["L", 5]], "(64, 10)", cols=toks)]})
    tok = model.tok(x_ids)
    pos = model.pos(torch.arange(L))
    h = tok + pos
    steps.append({"title": "Token and position embeddings", "text": "Each id picks a row of the token table, and position t picks row t of the "
                  "learned position table. The two are added. (This GPT learns its positions, so it doesn’t scale by √d_model.)",
                  "tensors": [T("token embedding", tok, [["B", 1], ["L", 5], ["d_model", 6]], "(64, 10, 64)", rows=toks),
                              T("h = token + position", h, [["B", 1], ["L", 5], ["d_model", 6]], "(64, 10, 64)", rows=toks)]})
    n1 = blk.norm1(h)
    steps.append({"title": "RMSNorm (pre-norm)", "text": "Normalize what goes into the attention: divide each row by its root mean square, "
                  "times the gain. The residual path keeps the un-normalized h.",
                  "tensors": [T("norm1(h)", n1, [["B", 1], ["L", 5], ["d_model", 6]], "(64, 10, 64)", rows=toks)]})
    q, k, v = blk.attn.qkv(n1).split(D, dim=-1)
    q4 = q.view(1, L, H, D // H).transpose(1, 2)
    k4 = k.view(1, L, H, D // H).transpose(1, 2)
    v4 = v.view(1, L, H, D // H).transpose(1, 2)
    steps.append({"title": "Q, split into heads", "text": "One Linear gives q, k and v. Then view + transpose: (B, L, d_model) → (B, h, L, d_k). "
                  "Head 0 gets columns 0–2 of q, head 1 gets columns 3–5. Below: q, and head 0’s slice.",
                  "tensors": [T("q", q, [["B", 1], ["L", 5], ["d_model", 6]], "(64, 10, 64)", rows=toks),
                              T("q, head 0", q4[0, 0], [["B", 1], ["h", 2], ["L", 5], ["d_k", 3]], "(64, 4, 10, 16)", rows=toks,
                                note="Shown: head 0 of example 0.")]})
    scores = q4 @ k4.transpose(-2, -1) / math.sqrt(D // H)
    masked = scores.masked_fill(demo.causal_mask(L), float("-inf"))
    w = F.softmax(masked, dim=-1)
    steps.append({"title": "Scores, causal mask, softmax", "text": "Each head scores every position against every position: (L, L) = (5, 5). "
                  "The causal mask blocks the positions after t (−∞), so “=” may look at all four tokens before it, and <bos> only at itself.",
                  "tensors": [T("masked scores, head 0", masked[0, 0], [["B", 1], ["h", 2], ["L", 5], ["L", 5]], "(64, 4, 10, 10)", rows=toks, cols=toks),
                              T("weights, head 0", w[0, 0], [["B", 1], ["h", 2], ["L", 5], ["L", 5]], "(64, 4, 10, 10)", rows=toks, cols=toks)]})
    heads_out = w @ v4
    joined = heads_out.transpose(1, 2).contiguous().view(1, L, D)
    att = blk.attn.out(joined)
    steps.append({"title": "Join the heads, output Linear", "text": "weights @ v gives (B, h, L, d_k). transpose + view join the heads back into "
                  "(B, L, d_model): head 0’s 3 numbers, then head 1’s 3. The output Linear mixes them.",
                  "tensors": [T("joined heads", joined, [["B", 1], ["L", 5], ["d_model", 6]], "(64, 10, 64)", rows=toks),
                              T("attention output", att, [["B", 1], ["L", 5], ["d_model", 6]], "(64, 10, 64)", rows=toks)]})
    h = h + att
    hid = F.relu(blk.ffn[0](blk.norm2(h)))
    h = h + blk.ffn[2](hid)
    steps.append({"title": "Add back, then the FFN", "text": "h = h + attention. Then pre-norm again: norm2, FFN (6 → 12 → 6), and add back.",
                  "tensors": [T("FFN hidden (after ReLU)", hid, [["B", 1], ["L", 5], ["d_ff", 12]], "(64, 10, 256)", rows=toks),
                              T("block output", h, [["B", 1], ["L", 5], ["d_model", 6]], "(64, 10, 64)", rows=toks)]})
    logits = model.head(model.norm(h))
    probs = F.softmax(logits[0, -1], dim=-1)
    top = [[demo.ITOS[int(i)], round(float(p), 3)] for p, i in zip(*probs.topk(5))]
    steps.append({"title": "Final norm, output layer", "text": "One more RMSNorm, then 15 scores per position. To write, only the last row "
                  "(after “=”) counts: its top token is the next token.",
                  "tensors": [T("logits", logits, [["B", 1], ["L", 5], ["tokens", 15]], "(64, 10, 15)", rows=toks, cols=list(demo.ITOS))],
                  "top": top})

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"input": "<bos>2+3=", "steps": steps}, ensure_ascii=False, allow_nan=False, separators=(",", ":")))
print("wrote", OUT, OUT.stat().st_size, "bytes; next token after <bos>2+3=:", top[0])
