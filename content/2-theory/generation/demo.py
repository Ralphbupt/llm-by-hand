"""
Level 18 · Generation strategies

Run:  python demo.py      (needs numpy)

The model gives one score per candidate word. This script shows every way the page
turns those scores into a choice, and prints every number the page asks about.
"""
import json
import numpy as np

np.set_printoptions(precision=4, suppress=True)


def softmax(x):
    e = np.exp(x - np.max(x))
    return e / e.sum()


# ---------------------------------------------------------------------------
# 1. One step: five candidates after "the cat sat on the"
# ---------------------------------------------------------------------------
WORDS = ["mat", "sofa", "rug", "roof", "moon"]
SCORES = np.array([2.0, 1.5, 1.0, 0.0, -1.0])

p = softmax(SCORES)
print("=== 1. one step: the cat sat on the ___ ===")
for w, s, q in zip(WORDS, SCORES, p):
    print(f"  {w:5s} score {s:5.1f}  p = {q:.4f}")
print("greedy picks", WORDS[int(np.argmax(p))], "with p =", round(float(p.max()), 4))

# temperature (level 10): divide the scores by T before softmax
for T in (0.5, 1.0, 2.0):
    print(f"T = {T}: p(mat) = {softmax(SCORES / T)[0]:.4f}")


def top_k(probs, k):
    keep = np.zeros_like(probs, dtype=bool)
    keep[np.argsort(-probs)[:k]] = True
    out = np.where(keep, probs, 0.0)
    return out / out.sum()


def top_p(probs, p_cut):
    order = np.argsort(-probs)
    sorted_p = probs[order]
    cum = np.cumsum(sorted_p)
    keep_sorted = cum - sorted_p < p_cut        # keep a word if the words before it are not enough yet
    keep = np.zeros_like(probs, dtype=bool)
    keep[order] = keep_sorted
    out = np.where(keep, probs, 0.0)
    return out / out.sum()


print("\n=== 2. top-k ===")
pk = top_k(p, 2)
print("k = 2 keeps", [w for w, q in zip(WORDS, pk) if q > 0], "->", pk)
print("p(sofa) after top-2 =", round(float(pk[1]), 4))

print("\n=== 3. top-p ===")
cum = np.cumsum(np.sort(p)[::-1])
print("sorted probs     ", np.sort(p)[::-1])
print("cumulative sum   ", cum)
pp = top_p(p, 0.9)
print("p = 0.9 keeps", int((pp > 0).sum()), "words ->", pp)
print("p = 0.5 keeps", int((top_p(p, 0.5) > 0).sum()), "words")

# ---------------------------------------------------------------------------
# 4. Beam search on a tiny two-step tree
# ---------------------------------------------------------------------------
print("\n=== 4. beam search ===")
FIRST = {"a": 0.5, "the": 0.4, "one": 0.1}
SECOND = {
    "a":   {"dog": 0.4, "cat": 0.3, "fox": 0.3},
    "the": {"dog": 0.9, "cat": 0.05, "fox": 0.05},
    "one": {"dog": 0.5, "cat": 0.25, "fox": 0.25},
}
seqs = {(w1, w2): FIRST[w1] * SECOND[w1][w2] for w1 in FIRST for w2 in SECOND[w1]}
g1 = max(FIRST, key=FIRST.get)
g2 = max(SECOND[g1], key=SECOND[g1].get)
print(f"greedy: {g1} {g2}  p = {FIRST[g1]} × {SECOND[g1][g2]} = {seqs[(g1, g2)]:.2f}")


def beam(width):
    beams = sorted(FIRST, key=FIRST.get, reverse=True)[:width]
    cands = [((w1, w2), np.log(FIRST[w1]) + np.log(SECOND[w1][w2])) for w1 in beams for w2 in SECOND[w1]]
    return max(cands, key=lambda c: c[1])


for width in (1, 2, 3):
    (w1, w2), lp = beam(width)
    print(f"beam width {width}: {w1} {w2}  ln p = {lp:.3f}  p = {np.exp(lp):.2f}")
best = max(seqs, key=seqs.get)
print("best of all", len(seqs), "sequences:", " ".join(best), f"p = {seqs[best]:.2f}")
print("ln p of greedy sequence =", round(float(np.log(seqs[(g1, g2)])), 3))
three = [0.5, 0.4, 0.9]
print("three steps with p =", three, ": ln sum =", " + ".join(f"{np.log(v):.4f}" for v in three),
      f"= {np.log(three).sum():.4f}   (product {np.prod(three):.2f}, and e^{np.log(three).sum():.4f} = {np.exp(np.log(three).sum()):.2f})")
print("a 100-word sentence at p = 0.1 per word: product =", 0.1 ** 100, " ln sum =", round(100 * np.log(0.1), 1))


# ---------------------------------------------------------------------------
# 5. A real (counting) model on synthetic text, and why greedy repeats itself
# ---------------------------------------------------------------------------
SLOTS = [["the"], ["cat", "dog", "bird"], ["sat", "ran", "slept"], ["on", "in"], ["the"],
         ["mat", "rug", "roof", "park"], ["."]]
WEIGHTS = [[1], [0.5, 0.3, 0.2], [0.5, 0.3, 0.2], [0.6, 0.4], [1], [0.35, 0.25, 0.2, 0.2], [1]]
MIX = 0.04   # 4% of every prediction is spread evenly over all words, so unseen words are possible but rare


def make_corpus(n_sentences=3000, seed=0):
    """Our own rule-made text: "the <animal> <verb> <prep> the <place> ." again and again."""
    rng = np.random.default_rng(seed)
    words = []
    for _ in range(n_sentences):
        words += [slot[rng.choice(len(slot), p=w)] for slot, w in zip(SLOTS, WEIGHTS)]
    return words


def build_trigram(words):
    """p(next | previous two words): count, then mix in a little of 'any word'."""
    vocab = sorted(set(words))
    ix = {w: i for i, w in enumerate(vocab)}
    V = len(vocab)
    counts = np.zeros((V, V, V))
    for a, b, c in zip(words, words[1:], words[2:]):
        counts[ix[a], ix[b], ix[c]] += 1
    totals = counts.sum(axis=2, keepdims=True)
    seen = np.divide(counts, totals, out=np.full_like(counts, 1 / V), where=totals > 0)
    return vocab, (1 - MIX) * seen + MIX / V


def is_sentence(seq):
    """Does every word sit in a slot our rules allow? (the text starts at slot 0)"""
    return all(w in SLOTS[i % 7] for i, w in enumerate(seq))


def generate(start, n, penalty=0.0):
    out = list(start)
    seen = np.zeros(len(vocab))
    for w in out:
        seen[ix[w]] += 1
    for _ in range(n):
        scores = np.log(probs[ix[out[-2]], ix[out[-1]]]) - penalty * seen
        k = int(np.argmax(scores))
        out.append(vocab[k])
        seen[k] += 1
    return out


words = make_corpus()
vocab, probs = build_trigram(words)
ix = {w: i for i, w in enumerate(vocab)}
V = len(vocab)
print("\n=== 5. counting model on", len(words), "synthetic words, vocabulary", V, "===")
print("vocab:", vocab)
row = probs[ix["on"], ix["the"]]
print("after 'on the':")
for w in sorted(vocab, key=lambda w: -row[ix[w]])[:5]:
    print(f"  p({w:5s} | on the) = {row[ix[w]]:.4f}   ln p = {np.log(row[ix[w]]):.4f}")
print(f"  any unseen word: p = {MIX / V:.4f}")
kept = top_p(row, 0.9) > 0
print("top-p 0.9 after 'on the': running totals", np.round(np.cumsum(np.sort(row)[::-1])[:5], 4),
      "-> keeps", int(kept.sum()), "words:", [w for w, k in zip(vocab, kept) if k])

START = [".", "the"]                     # a sentence is just starting
g = generate(START, 14)[1:]
print("greedy, no penalty:   ", " ".join(g))
loop = next(L for L in range(1, 14) if g[L:2 * L] == g[:L])
print("it repeats every", loop, "words")
g2 = generate(START, 14, penalty=1.0)[1:]
print("greedy, penalty 1.0:  ", " ".join(g2))
r2 = probs[ix["."], ix["the"]]
lp_cat = np.log(r2[ix["cat"]])
lp_dog = np.log(r2[ix["dog"]])
print(f"second sentence, after '. the': score(cat) = {lp_cat:.4f} - 1.0 × 1 = {lp_cat - 1:.4f}"
      f"   score(dog) = {lp_dog:.4f}")


# ---------------------------------------------------------------------------
# 6. Diversity vs quality: 200 continuations of 6 words with each strategy
#    quality = the share that follows our sentence rules (we wrote the rules, so we can check)
# ---------------------------------------------------------------------------
def temp(T):
    return lambda q: softmax(np.log(q) / T)


def greedy_one_hot(q):
    return np.eye(len(q))[int(np.argmax(q))]


def sample_run(strategy, n_runs=200, length=6, seed=1):
    rng = np.random.default_rng(seed)
    outs, ok = [], 0
    for _ in range(n_runs):
        seq = list(START)
        for _ in range(length):
            k = rng.choice(V, p=strategy(probs[ix[seq[-2]], ix[seq[-1]]]))
            seq.append(vocab[k])
        outs.append(" ".join(seq[1:]))
        ok += is_sentence(seq[1:])
    return len(set(outs)), ok / n_runs


STRATEGIES = [("greedy", greedy_one_hot), ("T = 0.5", temp(0.5)), ("T = 1", temp(1.0)), ("T = 2", temp(2.0)),
              ("top-k 3", lambda q: top_k(q, 3)), ("top-p 0.9", lambda q: top_p(q, 0.9))]
print("\n=== 6. diversity vs quality (200 continuations of 6 words) ===")
for name, f in STRATEGIES:
    distinct, valid = sample_run(f)
    print(f"  {name:10s} distinct = {distinct:3d}   follow the rules = {valid:.0%}")

print("\n=== 7. writing is a loop: the KV cache ===")
# tokens count from 0. Tokens 0..98 are in the cache; token 99 was just picked and is fed in to predict token 100.
print("tokens 0–98 cached, token 99 fed in: k and v computed for 1 token (without a cache: 100)")
print("tokens 0–2 cached, token 3 fed in: Q has 1 row, K and V have 4 rows, scores are 1 × 4 (without a cache: 4 × 4)")
print("k computations to write tokens 0–99 one at a time: without a cache", sum(range(1, 101)), "  with a cache", 100)

print("\n=== 8. a full filter: temperature, then top-k, then softmax ===")


def filter_probs(scores, T, k):
    z = scores / T
    cut = np.sort(z)[::-1][k - 1]
    z = np.where(z >= cut, z, -np.inf)
    e = np.exp(z - z.max())
    return e / e.sum()


s4 = np.array([2.0, 1.0, 0.5, -1.0])
print("T = 1, k = 2:", np.round(filter_probs(s4, 1.0, 2), 4))
print("T = 2, k = 3:", np.round(filter_probs(s4, 2.0, 3), 4))
for T, k in [(1.0, 2), (2.0, 3)]:
    z4 = s4 / T
    print(f"  T = {T}, k = {k}: z = {z4}, cut (k-th largest) = {np.sort(z4)[::-1][k - 1]}")
print("k = 1 on [-1, 3, 0]:", np.round(filter_probs(np.array([-1.0, 3.0, 0.0]), 1.0, 1), 4), "(greedy)")


def export():
    """The counting model for the page's lab (rounded)."""
    return {"vocab": vocab, "mix": MIX, "probs": np.round(probs, 5).tolist(), "n_words": len(words)}


if __name__ == "__main__":
    import pathlib
    import sys
    if "--export" in sys.argv:
        out = pathlib.Path(__file__).resolve().parents[3] / "site/public/data/generation/trigram.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(export()))
        print("wrote", out, f"({out.stat().st_size // 1024} KB)")
