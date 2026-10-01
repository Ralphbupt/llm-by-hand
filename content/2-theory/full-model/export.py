"""
Records what the level 17 page shows: a training curve and, for six numbers the model never saw,
every step of greedy decoding, once early in training (epoch 2) and once at the end (the last epoch).

Writes site/public/data/full-model/decode.json.   Run:  python export.py
"""
import json
import pathlib

import demo

OUT = pathlib.Path(__file__).resolve().parents[3] / "site/public/data/full-model/decode.json"
r2 = lambda xs: [round(float(v), 2) for v in xs]

_, test = demo.split()


def pick(cond):
    return next(n for n in test if cond(n) and n not in chosen)


chosen = []
for cond in [lambda n: n < 10, lambda n: 10 <= n < 20, lambda n: 20 <= n < 100 and n % 10,
             lambda n: n >= 100 and n % 100 == 0 or n >= 100 and n % 100 < 10,
             lambda n: n >= 100 and n % 100 >= 20 and n % 10, lambda n: n >= 100 and 10 <= n % 100 < 20]:
    chosen.append(pick(cond))

curve, snaps = [], {}


def record(ep, loss, model, nums):
    acc = demo.accuracy(model, nums)
    curve.append({"epoch": ep, "loss": round(loss, 3), "acc": round(acc, 3)})
    print(f"epoch {ep:2d} loss {loss:.3f} acc {acc:.2f}", flush=True)
    if ep in (2, demo.EPOCHS):
        snap = []
        for n in chosen:
            steps = []
            out = demo.read_aloud(model, n, steps)
            print(f"  epoch {ep}: {n} → {' '.join(out)}")
            snap.append({"n": n, "truth": demo.words(n), "steps": [
                {"input": s["input"], "last": r2(s["last"]), "logits": r2(s["logits"]),
                 "pick": s["pick"], "att": r2(s["att"])} for s in steps]})
        snaps[f"epoch{ep}"] = snap


demo.train(on_epoch=record)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"vocab": demo.VOCAB, "curve": curve, **snaps}, separators=(",", ":")))
print("wrote", OUT, OUT.stat().st_size, "bytes; numbers:", chosen)
