"""
Records the training curves shown on the level 21 page, and builds the boss check files.

    python export.py answer     loss on the answer only
    python export.py all        loss on every position
    python export.py check      check_weights.json (then scripts/sync_files.py copies the downloads)

Writes site/public/data/write-a-gpt/curve_<mode>.json: per epoch the loss, the accuracy on the
1000 unseen problems, and what the model answers for 8 fixed unseen problems.
"""
import json
import pathlib
import sys
import time

import demo

mode = sys.argv[1]

if mode == "check":
    # Fixed weights for boss part 1: a small GPT (sizes all different), gains randomized so a missing gain shows,
    # every number rounded to 4 decimals so the file is small and the learner's model sees exactly these values.
    import torch

    import check

    torch.manual_seed(1234)
    model = demo.GPT(**check.CHECK_CONFIG)
    with torch.no_grad():
        for name, p in model.named_parameters():
            if name.endswith("gain"):
                p.uniform_(0.5, 1.5)
            p.copy_(torch.round(p * 1e4) / 1e4)
    here = pathlib.Path(__file__).resolve().parent
    weights = {k: [round(x, 4) for x in v.flatten().tolist()] if v.dim() == 1 else
               [[round(x, 4) for x in row] for row in v.tolist()] for k, v in model.state_dict().items()}
    (here / "check_weights.json").write_text(json.dumps(weights, separators=(",", ":")))
    print("expected:", check.part1(demo))
    print("now run scripts/sync_files.py: it copies the files learners download to site/public/files/")
    sys.exit(0)

EPOCHS = 150
OUT = pathlib.Path(__file__).resolve().parents[3] / "site/public/data/write-a-gpt" / f"curve_{mode}.json"

_, _, test_pairs = demo.split()
probes = test_pairs[:8]
rows = []
t0 = time.time()


def log(ep, loss, acc, model, val):
    rows.append({"epoch": ep, "loss": round(loss, 4), "acc": round(acc, 4), "val": round(val, 4),
                 "answers": demo.solve(model, probes)})
    print(f"{mode} epoch {ep:3d} loss {loss:.3f} acc {acc * 100:5.1f}% ({time.time() - t0:.0f}s)", flush=True)


demo.train(EPOCHS, answer_only=(mode == "answer"), on_epoch=log)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"mode": mode, "probes": [f"{a}+{b}" for a, b in probes],
                           "truth": [str(a + b) for a, b in probes], "epochs": rows}, separators=(",", ":")))
print("wrote", OUT)
