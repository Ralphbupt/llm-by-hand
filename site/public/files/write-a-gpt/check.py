"""
Level 21 · the boss check. Run it on YOUR model file (the skeleton you filled in), not on the reference.

    python check.py my_gpt.py              part 1: load fixed weights into your GPT, check its logits, print a code
    python check.py my_gpt.py model.pt     part 2: evaluate your trained model on the 1,000 unseen problems

Part 1 needs the names from the starter file: the arguments of GPT(d, heads, layers, d_ff), because it builds your
model as GPT(d=32, heads=4, layers=2, d_ff=64), and the attributes (tok, pos, blocks, norm1, attn.qkv, attn.out, norm2,
ffn, norm, head, gain), because it loads check_weights.json into them by name.
Part 2 needs the file your train() saved:  torch.save({"config": {...}, "state": model.state_dict()}, "model.pt")
Paste what this script prints into the level 21 page.

The "check" code in the report only shows that the line was not changed after this script printed it. Anyone can
read this file and make a code for a report they typed by hand: the local part relies on your honesty.
"""
import hashlib
import importlib.util
import json
import pathlib
import random
import sys

import torch

HERE = pathlib.Path(__file__).resolve().parent
PAD, BOS, EOS = 0, 1, 2
ITOS = ["<pad>", "<bos>", "<eos>"] + list("0123456789") + ["+", "="]
STOI = {c: i for i, c in enumerate(ITOS)}

# part 1 uses a small model with sizes that are all different from each other, so a mixed-up axis shows
CHECK_CONFIG = {"d": 32, "heads": 4, "layers": 2, "d_ff": 64}
# x for 23 + 58: <bos> 2 3 + 5 8 = 8 1 <eos>  (the padded sequence without its last token)
CHECK_X = [1, 5, 6, 13, 8, 11, 14, 11, 4, 2]


def load_module(path):
    spec = importlib.util.spec_from_file_location("learner_gpt", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_weights():
    raw = json.loads((HERE / "check_weights.json").read_text())
    return {k: torch.tensor(v) for k, v in raw.items()}


def name_problems(model, weights):
    """The hints for parameter names that don't match the starter file (an empty list when they all match)."""
    mine = set(model.state_dict())
    if mine == set(weights):
        return []
    missing, extra = sorted(set(weights) - mine), sorted(mine - set(weights))
    out = ["The parameter names don't match the starter file.",
           f"  missing in your model: {missing}",
           f"  extra in your model:   {extra}"]
    if any(k.startswith("blocks.") for k in missing) and not any(k.startswith("blocks.") for k in mine):
        # every block parameter is missing, so the gain and FFN hints below would only repeat this one cause
        out.append("  None of the blocks' parameters are in your model. Are the blocks in a plain Python list?")
        out.append("  PyTorch only sees layers in an nn.ModuleList.")
        return out
    if any(k.endswith("gain") for k in missing):
        out.append("  A gain is missing. A tensor is only a parameter of the model when it is wrapped in nn.Parameter.")
    if any(k.startswith("blocks.") and not k.endswith("gain") for k in missing):
        out.append("  Compare the names inside each block with the starter file: norm1, attn.qkv, attn.out, norm2, ffn.")
    if any(k.startswith("blocks.") and ".ffn." in k for k in missing):
        out.append("  The FFN should be one nn.Sequential(nn.Linear(d, d_ff), nn.ReLU(), nn.Linear(d_ff, d)) named ffn,")
        out.append("  so its weights are called ffn.0.weight, ffn.0.bias, ffn.2.weight, ffn.2.bias.")
    if "pos.weight" in missing or "tok.weight" in missing:
        out.append("  tok and pos should be nn.Embedding layers: self.tok = nn.Embedding(15, d), self.pos = nn.Embedding(11, d).")
    if "head.bias" in missing:
        out.append("  head should be nn.Linear(d, 15) with its bias (the default).")
    return out


ARG_HELP = ["GPT(...) must take the four arguments with exactly these names: d, heads, layers, d_ff.",
            "  check.py builds your model as  GPT(d=32, heads=4, layers=2, d_ff=64)  and part 2 as  GPT(**config).",
            "  Keep the names from the starter file, for example d, not d_model."]


def make_gpt(mod, config):
    """GPT(**config), with a clear message when the argument names differ from the starter file."""
    try:
        return mod.GPT(**config)
    except TypeError as e:
        if "argument" not in str(e):
            raise
        print("\n".join(ARG_HELP + [f"  Python said: {e}"]))
        sys.exit(1)


def check_logits(mod):
    """Load the fixed weights into the learner's GPT and run the fixed input. Returns (problems, logits)."""
    model = make_gpt(mod, CHECK_CONFIG)
    weights = check_weights()
    problems = name_problems(model, weights)
    if problems:
        return problems, None
    model.load_state_dict(weights)
    model.eval()
    with torch.no_grad():
        logits = model(torch.tensor([CHECK_X]))
    if tuple(logits.shape) != (1, 10, 15):
        return [f"logits shape is {tuple(logits.shape)} but should be (1, 10, 15)"], None
    return [], logits[0]


def part1(mod):
    """Fixed weights, fixed input: a correct pre-norm GPT with RMSNorm gives exactly these logits."""
    problems, logits = check_logits(mod)
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    code = forward_code(logits, "forward")
    if forward_code(logits, "verify") == VERIFY:
        print("Part 1: your model computes exactly what the reference computes. Paste this line into the level 21 page:")
    else:
        print("Part 1: not yet. Your model runs, but its logits differ from the reference's with the same weights.")
        factor = sqrt_d_factor(mod, check_weights())
        if factor == "times":
            print("  Found it: your model multiplies the token embeddings by sqrt(d). This model doesn't: the input to the")
            print("  first block is just tok(x) + pos(positions). Remove the factor.")
        elif factor == "over":
            print("  Found it: your model divides the token embeddings by sqrt(d). This model doesn't: the input to the")
            print("  first block is just tok(x) + pos(positions). Remove the factor.")
        elif interleaved_matches(mod, check_weights()):
            print("  Found it: your attention splits qkv per head (q, k, v of head 0, then of head 1, ...).")
            print("  The course's order is q = the first d columns of qkv(x), then k = the next d, then v = the last d:")
            print("  q, k, v = self.qkv(x).split(d, dim=-1), and only then split each into heads.")
        else:
            print("  Check pre-norm (normalize before each sublayer), the final norm before head, the RMSNorm gain,")
            print("  the causal mask, the division by sqrt(d_k), the qkv order (q, then k, then v), the positions 0..L-1,")
            print("  and that the token embeddings are not scaled (no sqrt(d) factor).")
        print("  The page will not accept this line yet:")
    # quoted, so the whole line can replace the page's  forward = "____"  line as it is
    print(f'forward = "{code}"')
    return code


# 20 logits (position, token) of the check input; each is far from a rounding edge, so tiny float differences don't matter
PICKS = [(0, 0), (0, 14), (1, 1), (1, 14), (2, 1), (2, 14), (3, 0), (3, 14), (4, 3), (4, 14),
         (5, 1), (5, 14), (6, 5), (6, 14), (7, 1), (7, 14), (8, 0), (8, 14), (9, 4), (9, 14)]
VERIFY = "bd23e640fb04"


def forward_code(logits, kind):
    """A short code made from 20 of your logits rounded to 2 places. The reference's numbers are not in this file."""
    vals = [round(float(logits[t, j]), 2) + 0.0 for t, j in PICKS]
    return hashlib.sha256(f"llm-by-hand/20/{kind}/{json.dumps(vals)}".encode()).hexdigest()[:12]


def matches_reference(mod, weights):
    """Does the learner's model, with these weights, give the reference's logits?"""
    model = make_gpt(mod, CHECK_CONFIG)
    model.load_state_dict(weights)
    model.eval()
    with torch.no_grad():
        logits = model(torch.tensor([CHECK_X]))
    return forward_code(logits[0], "verify") == VERIFY


def sqrt_d_factor(mod, weights):
    """"times" if the learner's model matches once the token table is divided by sqrt(d) (so it multiplies by
    sqrt(d)), "over" if it matches once the table is multiplied by sqrt(d), else None."""
    root = CHECK_CONFIG["d"] ** 0.5
    for word, scale in (("times", 1 / root), ("over", root)):
        moved = dict(weights)
        moved["tok.weight"] = weights["tok.weight"] * scale
        if matches_reference(mod, moved):
            return word
    return None


def interleaved_matches(mod, weights):
    """Does the learner's model match once qkv's rows are reordered head by head (q, k, v of each head together)?"""
    d, h = CHECK_CONFIG["d"], CHECK_CONFIG["heads"]
    dk = d // h
    moved = dict(weights)
    for name, w in weights.items():
        if ".attn.qkv." in name:
            q, k, v = w.split(d, dim=0)
            moved[name] = torch.cat([part[i * dk:(i + 1) * dk] for i in range(h) for part in (q, k, v)], dim=0)
    return matches_reference(mod, moved)


def report_check(correct, wrong):
    """A short code made from the report, so the page can tell that the line was pasted unchanged."""
    return hashlib.sha256(f"llm-by-hand/20/{correct}/{'|'.join(wrong)}".encode()).hexdigest()[:8]


def report_line(correct, wrong):
    return "report = " + json.dumps({"correct": correct, "wrong": wrong, "check": report_check(correct, wrong)})


def unseen_pairs(seed=0):
    """The same split as the skeleton: all 10,000 pairs in order, shuffled with random.Random(seed)."""
    pairs = [(a, b) for a in range(100) for b in range(100)]
    random.Random(seed).shuffle(pairs)
    return pairs[9000:]


@torch.no_grad()
def greedy(model, a, b):
    ids = [BOS] + [STOI[c] for c in f"{a}+{b}="]
    out = ""
    for _ in range(4):                                   # at most 3 digits + <eos>
        nxt = int(model(torch.tensor([ids]))[0, -1].argmax())
        if nxt in (EOS, PAD):
            break
        out += ITOS[nxt]
        ids.append(nxt)
    return out


def part2(mod, path):
    """Your trained model on the 1,000 problems it never saw. The same model file must pass part 1 first."""
    problems, logits = check_logits(mod)
    if problems or forward_code(logits, "verify") != VERIFY:
        print("Part 2 runs only on a model file that passes part 1. Run  python check.py my_gpt.py  first.")
        sys.exit(1)
    saved = torch.load(path, map_location="cpu", weights_only=True)
    model = make_gpt(mod, saved["config"])
    mine = model.state_dict()
    if set(saved["state"]) != set(mine) or any(saved["state"][k].shape != mine[k].shape for k in mine):
        print("model.pt doesn't fit this model file: the saved parameter names or shapes differ from GPT(**config).")
        print("Save it from the same file:  torch.save({\"config\": {...}, \"state\": model.state_dict()}, \"model.pt\")")
        sys.exit(1)
    model.load_state_dict(saved["state"])
    model.eval()
    wrong, correct = [], 0
    for a, b in unseen_pairs():
        got = greedy(model, a, b)
        if got == str(a + b):
            correct += 1
        else:
            wrong.append(f"{a}+{b}={got}")
    print(f"{correct} of 1000 unseen problems right ({correct / 10:.1f}%)")
    if correct >= 950:
        print("PASS. Paste this whole line into the level 21 page:")
    else:
        print("Not yet: you need at least 950. This is the line the page expects once you get there:")
    print(report_line(correct, wrong[:10]))
    return correct, wrong[:10]




if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    learner = load_module(sys.argv[1])
    if len(sys.argv) == 2:
        part1(learner)
    else:
        part2(learner, sys.argv[2])
