"""
Level U5 · the boss check.

    python check.py my_train.py

Runs five checks on your fixed script. Each check says what it measured, not where the bug is.
At the end it prints one line to paste into the page:
    U5 PASS 0.980 1a2b3c4d     every check passed (0.980 is the held-out accuracy)
    U5 FAIL 10110 1a2b3c4d     1 = that check passed, 0 = it failed; the page gives a hint for the first 0

The last part of the line is a short code made from the rest, so the page can tell that the line was pasted
unchanged. Anyone can read this file, so it is no proof: this part relies on your honesty.
"""
import copy
import hashlib
import importlib.util
import sys

import torch
import torch.nn.functional as F
from torch.nn.utils import parameters_to_vector

LEVEL = "U5"


def line(word, value):
    return f"{LEVEL} {word} {value} {hashlib.sha256(f'llm-by-hand/{LEVEL}/{value}'.encode()).hexdigest()[:8]}"


# >>> course-only (scripts/sync_files.py leaves this out of the downloaded copy)
def example_paste(eid):
    """What a learner who passes would paste. The course's own checks use this to test the page."""
    return line("PASS", "0.980")
# <<< course-only


def make_data(n=1000, seed=0):
    """The same points as make_data in broken_train.py."""
    g = torch.Generator().manual_seed(seed)
    X = torch.rand(n, 2, generator=g) * 2 - 1
    y = (X[:, 0] ** 2 + X[:, 1] ** 2 < 0.5).long()
    return X, y


def run(path):
    spec = importlib.util.spec_from_file_location("learner", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    ok = []

    # 1. split: tests the sizes of the two sets and whether any point is in both.
    X, y = make_data()
    X2, y2 = m.make_data()
    if not (torch.equal(X, X2) and torch.equal(y, y2)):
        print("make_data() in your file does not give the course's 1000 points. Put back the original make_data.")
        print("\nNot yet. Paste this line into the page:")
        print(line("FAIL", "00000"))
        return
    (Xt, yt), (Xh, yh) = m.split(X, y)
    rows = lambda A: {tuple(r) for r in A.tolist()}
    shared = len(rows(Xt) & rows(Xh))
    ok.append(len(Xt) + len(Xh) == len(X) and shared == 0 and len(Xh) == 200)
    print("1. split:     ", "ok" if ok[-1] else
          f"{len(Xt)} training points, {len(Xh)} held-out points, {shared} points in both sets")

    # 2. batches: tests that one epoch gives every point once, with its own class.
    label = {tuple(r): int(c) for r, c in zip(X.tolist(), y.tolist())}
    seen, wrong = [], 0
    for xb, yb in m.batches(X, y, 32, torch.Generator().manual_seed(1)):
        for r, c in zip(xb.tolist(), yb.tolist()):
            seen.append(tuple(r))
            wrong += label[tuple(r)] != c
    ok.append(sorted(seen) == sorted(label) and wrong == 0)
    print("2. batches:   ", "ok" if ok[-1] else
          f"one epoch over all {len(X)} points of make_data() gave {len(seen)} points; for {wrong} of them, the class in the batch is not the class in the data")

    # 3. forward: tests the numbers forward(x) returns for 50 points.
    torch.manual_seed(0)
    model = m.MLP()
    with torch.no_grad():
        out = model(X[:50])
    sums = out.sum(dim=-1)
    # probabilities, or probabilities times a number (2 * softmax): no negative output, and every row has the same sum
    probs = bool((out >= 0).all() and torch.allclose(sums, sums[0].expand_as(sums), atol=1e-4))
    with torch.no_grad():
        raw = torch.allclose(out, model.net(X[:50]), atol=1e-6) if isinstance(getattr(model, "net", None), torch.nn.Module) else True
    ok.append(out.shape == (50, 2) and bool(torch.isfinite(out).all()) and not probs and raw)
    print("3. forward:   ", "ok" if ok[-1] else
          f"the rows of forward(x) sum to {sums.min():.3f}…{sums.max():.3f}, "
          f"and every number lies between {out.min():.3f} and {out.max():.3f}")

    # 4. train_step: tests how far two calls on the same batch move the weights,
    #    against two plain gradient steps computed here.
    torch.manual_seed(0)
    model = m.MLP()
    ref = copy.deepcopy(model)
    start = parameters_to_vector(model.parameters()).detach().clone()
    xb, yb = X[:32], y[:32]
    opt = torch.optim.SGD(model.parameters(), lr=0.1)
    m.train_step(model, opt, xb, yb)
    m.train_step(model, opt, xb, yb)
    ref_opt = torch.optim.SGD(ref.parameters(), lr=0.1)
    for _ in range(2):
        ref_opt.zero_grad()
        F.cross_entropy(ref(xb), yb).backward()
        ref_opt.step()
    got = parameters_to_vector(model.parameters()).detach()
    want = parameters_to_vector(ref.parameters()).detach()
    ok.append(bool(torch.allclose(got, want, atol=1e-5)) and bool((want != start).any()))
    ratio = ((got - start).norm() / (want - start).norm()).item()
    print("4. train_step:", "ok" if ok[-1] else
          f"learning rate 0.1, the same batch twice: the weights moved {ratio:.2f} times as far as "
          f"two plain gradient steps move them")

    # 5. learns: trains with train(seed=0), then measures the accuracy here, on the last 200 points.
    model, _ = m.train(seed=0)
    Xh, yh = X[800:], y[800:]
    with torch.no_grad():
        acc = round((model(Xh).argmax(dim=-1) == yh).float().mean().item(), 3)
    ok.append(acc >= 0.95)
    print("5. learns:    ", "ok" if ok[-1] else f"held-out accuracy {acc:.3f}, needs 0.950")

    if all(ok):
        print("\nPASS. Paste this whole line into the page:")
        print(line("PASS", f"{acc:.3f}"))
    else:
        print("\nNot yet. For a hint on the first failing check, paste this line into the page:")
        print(line("FAIL", "".join("1" if k else "0" for k in ok)))


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "my_train.py")
