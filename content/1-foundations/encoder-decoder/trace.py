"""
Level N7 · the microscope: one number goes through a whole (tiny) Transformer, and every tensor is recorded.

The tiny model has the page model's parts with small sizes, all different from each other, so you can tell every
axis apart by its size:  B = 1, L_src = 2, L_tgt = 3, d_model = 6, d_ff = 12, 32 output words, 1 head, 1 layer.
It is trained on the numbers 0–99 (about 15 seconds), then reads "89" aloud.

Writes site/public/data/encoder-decoder/microscope.json.   Run:  python trace.py
"""
import json
import math
import pathlib
import random

import torch
import torch.nn as nn
import torch.nn.functional as F

import demo

OUT = pathlib.Path(__file__).resolve().parents[3] / "site/public/data/encoder-decoder/microscope.json"
D, D_FF = 6, 12
def num(v):
    v = float(v)
    return round(v, 2) if math.isfinite(v) else None       # −∞ (a blocked score) is written as null


r2 = lambda t: [[num(v) for v in row] for row in t]

torch.manual_seed(0)
model = demo.Transformer(d=D, heads=1, layers=1, d_ff=D_FF)
nums = list(range(100))
loss_fn = nn.CrossEntropyLoss(ignore_index=demo.PAD)
opt = torch.optim.Adam(model.parameters(), lr=1e-2)
rng = random.Random(0)
for ep in range(300):
    rng.shuffle(nums)
    for i in range(0, 100, 20):
        s, ti, to = demo.tensors(nums[i:i + 20])
        loss = loss_fn(model(s, ti).reshape(-1, len(demo.TGT)), to.reshape(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
model.eval()
print("tiny model reads 0–99 right:", sum(demo.read_aloud(model, n) == demo.words(n) for n in range(100)), "of 100")


def attention_parts(mh, q_in, kv_in, mask):
    """The inside of one attention block (1 head), step by step."""
    q, k, v = mh.Wq(q_in), mh.Wk(kv_in), mh.Wv(kv_in)
    scores = q @ k.transpose(-2, -1) / math.sqrt(mh.dk)
    if mask is not None:
        scores = scores.masked_fill(mask, float("-inf"))
    w = F.softmax(scores, dim=-1)
    return q, k, v, scores, w, mh.Wo(w @ v)


N = 89
src, tgt_in, tgt_out = demo.tensors([N])
src, tgt_in, tgt_out = src[:, :2], tgt_in[:, :3], tgt_out[:, :3]          # "89" has 2 digits; answer: 2 words + <eos>
src_tok = [demo.SRC[i] for i in src[0]]
tgt_tok = [demo.TGT[i] for i in tgt_in[0]]
steps = []


def T(name, t, axes, big, rows=None, cols=None, note=None):
    """One tensor for the page: its values (first example, first head), named axes, and the page model's shape."""
    a = t.detach()
    while a.dim() > 2:
        a = a[0]
    vals = r2(a) if a.dim() == 2 else [[num(v) for v in a]]
    return {"name": name, "axes": axes, "big": big, "values": vals, "rows": rows, "cols": cols, "note": note}


with torch.no_grad():
    enc = model.enc[0]
    dec = model.dec[0]
    steps.append({"title": "Token ids", "text": "The digits and the words become ids. The decoder input starts with <bos>.",
                  "tensors": [T("src", src, [["B", 1], ["L_src", 2]], "(64, 3)", cols=src_tok),
                              T("tgt_in", tgt_in, [["B", 1], ["L_tgt", 3]], "(64, 5)", cols=tgt_tok)]})
    e = model.src_emb(src)
    steps.append({"title": "Look up the embeddings", "text": "Each id picks one row of the embedding table: 6 numbers per digit.",
                  "tensors": [T("embedding", e, [["B", 1], ["L_src", 2], ["d_model", 6]], "(64, 3, 64)", rows=src_tok)]})
    es = e * math.sqrt(D)
    tok_len = [round(float(r.norm()), 1) for r in es[0]]
    pos_len = round(float(model.pe[0].norm()), 1)
    steps.append({"title": "Scale by √d_model", "text": f"Multiply by √6 ≈ {math.sqrt(D):.2f}. The table started with numbers of size about 1/√6, "
                  f"so the scaled rows are about as long as the position rows in the next step. Here the token rows are "
                  f"{tok_len[0]} and {tok_len[1]} long, and each position row {pos_len}. Neither one is much bigger than the other.",
                  "tensors": [T("embedding × √d_model", es, [["B", 1], ["L_src", 2], ["d_model", 6]], "(64, 3, 64)", rows=src_tok)]})
    x = es + model.pe[:2]
    steps.append({"title": "Add the positions", "text": "Add row 0 of the position table to the first digit and row 1 to the second.",
                  "tensors": [T("position rows", model.pe[:2].unsqueeze(0), [["L_src", 2], ["d_model", 6]], "(3, 64)", rows=["pos 0", "pos 1"]),
                              T("x", x, [["B", 1], ["L_src", 2], ["d_model", 6]], "(64, 3, 64)", rows=src_tok)]})
    q, k, v, sc, w, a_out = attention_parts(enc.attn, x, x, None)
    steps.append({"title": "Encoder self-attention", "text": "Every digit scores every digit (Q and K both from the digits). No causal mask: "
                  "the encoder may read the whole number. Here no PAD needs blocking.",
                  "tensors": [T("scores = Q Kᵀ / √d_k", sc, [["B", 1], ["L_src", 2], ["L_src", 2]], "(64, 4, 3, 3)", rows=src_tok, cols=src_tok,
                                note="The page model has 4 heads, so its scores have a head axis."),
                              T("weights", w, [["B", 1], ["L_src", 2], ["L_src", 2]], "(64, 4, 3, 3)", rows=src_tok, cols=src_tok)]})
    x = enc.n1(x + a_out)
    hid = F.relu(enc.ff[0](x))
    memory = enc.n2(x + enc.ff[2](hid))
    steps.append({"title": "Add & norm, then the FFN", "text": "Add x to the attention output, then LayerNorm 1 normalizes the sum. "
                  "Then the FFN widens each digit to d_ff = 12 numbers, applies ReLU, and narrows it back to 6. "
                  "Add and normalize again (LayerNorm 2). The result is the memory: one vector per digit, computed once.",
                  "tensors": [T("LN1(x + attention)", x, [["B", 1], ["L_src", 2], ["d_model", 6]], "(64, 3, 64)", rows=src_tok),
                              T("FFN hidden (after ReLU)", hid, [["B", 1], ["L_src", 2], ["d_ff", 12]], "(64, 3, 128)", rows=src_tok),
                              T("memory", memory, [["B", 1], ["L_src", 2], ["d_model", 6]], "(64, 3, 64)", rows=src_tok)]})
    y = model.tgt_emb(tgt_in) * math.sqrt(D) + model.pe[:3]
    steps.append({"title": "Decoder input", "text": "The words go through the same three steps: look up, scale by √d_model, add positions.",
                  "tensors": [T("y", y, [["B", 1], ["L_tgt", 3], ["d_model", 6]], "(64, 5, 64)", rows=tgt_tok)]})
    causal = demo.causal_mask(3)
    q, k, v, sc, w, a_out = attention_parts(dec.self_attn, y, y, causal)
    steps.append({"title": "Masked self-attention", "text": "Words score earlier words only. The causal mask is 3 × 3 because both Q and K come "
                  "from the decoder input, which has 3 tokens. Blocked scores become −∞, and their weights 0.",
                  "tensors": [T("scores (with the causal mask)", sc, [["B", 1], ["L_tgt", 3], ["L_tgt", 3]], "(64, 4, 5, 5)", rows=tgt_tok, cols=tgt_tok),
                              T("weights", w, [["B", 1], ["L_tgt", 3], ["L_tgt", 3]], "(64, 4, 5, 5)", rows=tgt_tok, cols=tgt_tok)]})
    y = dec.n1(y + a_out)
    q, k, v, sc, w, a_out = attention_parts(dec.cross, y, memory, None)
    steps.append({"title": "Cross-attention", "text": "Q comes from the 3 words, K and V from the 2 digits in memory. So the scores are 3 × 2: "
                  "for each word, how much weight it gives each digit. No causal mask: the whole number is known.",
                  "tensors": [T("scores", sc, [["B", 1], ["L_tgt", 3], ["L_src", 2]], "(64, 4, 5, 3)", rows=tgt_tok, cols=src_tok),
                              T("weights", w, [["B", 1], ["L_tgt", 3], ["L_src", 2]], "(64, 4, 5, 3)", rows=tgt_tok, cols=src_tok)]})
    y = dec.n2(y + a_out)
    out = dec.n3(y + dec.ff(y))
    steps.append({"title": "Add & norm, FFN", "text": "The same residual, LayerNorm and FFN as in the encoder. This is the decoder output.",
                  "tensors": [T("decoder output", out, [["B", 1], ["L_tgt", 3], ["d_model", 6]], "(64, 5, 64)", rows=tgt_tok)]})
    logits = model.out(out)
    probs = F.softmax(logits[0], dim=-1)
    top = [[demo.TGT[int(i)], round(float(p), 3)] for p, i in zip(*probs[-1].topk(5))]
    loss = F.cross_entropy(logits[0], tgt_out[0])
    steps.append({"title": "Output layer: logits", "text": "One row of 32 scores per position. When the model writes, only the last row "
                  "counts: its top word is the next word. When it trains, every row is compared with tgt_out.",
                  "tensors": [T("logits", logits, [["B", 1], ["L_tgt", 3], ["words", 32]], "(64, 5, 32)", rows=tgt_tok,
                                cols=list(demo.TGT))],
                  "top": top, "targets": [demo.TGT[i] for i in tgt_out[0]], "loss": round(float(loss), 3)})

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"input": str(N), "warning": "In the page model the batch (64) and d_model (64) are the same "
                           "number. To know which is which, look at the position: the batch is always the first axis.",
                           "steps": steps}, ensure_ascii=False, allow_nan=False, separators=(",", ":")))
print("wrote", OUT, OUT.stat().st_size, "bytes; next word after <bos> eighty nine:", top[0])
