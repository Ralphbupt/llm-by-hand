"""
Level 11 · What is a language model?

Run:  python demo.py      (needs numpy)

A language model gives the probability of the next word, given the words so far.
Writing is just: pick a next word, append it, repeat.
Every number the page asks about is printed below.
"""
import numpy as np

np.set_printoptions(precision=3, suppress=True)

VOCAB = ["the", "a", "cat", "dog", "sat", "ran", "on", "mat", "rug", "."]


def make_corpus(n=200, seed=0):
    """Tiny stories from our own rules. Every sentence is:
    (the | a) (cat | dog) (sat | ran) [on the (mat | rug)] .
    """
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        s = ["the" if rng.random() < 0.7 else "a",
             "cat" if rng.random() < 0.6 else "dog",
             "sat" if rng.random() < 0.5 else "ran"]
        if rng.random() < 0.5:
            s += ["on", "the", "mat" if rng.random() < 0.5 else "rug"]
        out.append(" ".join(s + ["."]))
    return out


def counts(tokens, vocab):
    idx = {w: i for i, w in enumerate(vocab)}
    C = np.zeros((len(vocab), len(vocab)))
    for a, b in zip(tokens, tokens[1:]):          # every pair of neighbors
        C[idx[a], idx[b]] += 1
    return C


def row_probs(C):
    s = C.sum(axis=1, keepdims=True)
    return np.divide(C, s, out=np.zeros_like(C), where=s > 0)


def perplexity(ps):
    ps = np.asarray(ps, dtype=float)
    if (ps <= 0).any():
        return np.inf
    return float(np.exp(-np.mean(np.log(ps))))


def stream_probs(tokens, vocab, P):
    idx = {w: i for i, w in enumerate(vocab)}
    return [P[idx[a], idx[b]] for a, b in zip(tokens, tokens[1:])]


def softmax(z):
    e = np.exp(z - z.max(axis=-1, keepdims=True))
    return e / e.sum(axis=-1, keepdims=True)


def main():
    # --- 1. the hand example ----------------------------------------------------
    tiny_v = ["the", "a", "cat", "dog", "sat", "ran", "."]
    tiny = "the cat sat . the dog sat . a cat ran .".split()
    C = counts(tiny, tiny_v)
    P = row_probs(C)
    i = {w: k for k, w in enumerate(tiny_v)}
    print("hand example:", " ".join(tiny))
    print("pairs of neighbors:", len(tiny) - 1)
    print("counts (row = this word, column = the next word)")
    print("      " + " ".join(f"{w:>4}" for w in tiny_v))
    for w, r in zip(tiny_v, C):
        print(f"{w:>5} " + " ".join(f"{int(v):4d}" for v in r))
    print('"sat" followed by "." :', int(C[i["sat"], i["."]]), "times")
    print('P(sat | cat) =', int(C[i["cat"], i["sat"]]), "/", int(C[i["cat"]].sum()), "=", float(P[i["cat"], i["sat"]]))
    print('P(dog | a)   =', float(P[i["a"], i["dog"]]), ' → "a dog sat ." has probability 0')
    print('P(next | cat) row of the probability table (C / row totals):', P[i["cat"]], ' rows add to', P.sum(axis=1))

    ps = stream_probs(". the cat ran".split(), tiny_v, P)
    print('\nafter ".", the words "the cat ran" got probabilities:', [float(p) for p in ps])
    print("average -log p =", round(float(-np.mean(np.log(ps))), 4))
    print("perplexity     =", round(perplexity(ps), 4))
    print("ten equally likely words → perplexity", round(perplexity([0.1] * 5), 4))

    # --- 2. the generated stories ------------------------------------------------
    sents = make_corpus()
    train, held = sents[:160], sents[160:]
    tr = " ".join(train).split()
    ho = " ".join(held).split()
    print("\ngenerated stories:", len(sents), "sentences; first three:")
    for s in sents[:3]:
        print("   ", s)
    print("train tokens", len(tr), " held-out tokens", len(ho), " vocabulary", len(VOCAB))
    Ct = counts(tr, VOCAB)
    Pt = row_probs(Ct)
    print("counting model, P(next | the):", {w: round(float(p), 3) for w, p in zip(VOCAB, Pt[0]) if p > 0})
    print('P(mat | the) =', round(float(Pt[0, VOCAB.index("mat")]), 3),
          ' so the model can write "the mat ." even though no story has it')
    ppl_count = perplexity(stream_probs(ho, VOCAB, Pt))
    print("held-out perplexity: uniform guess 10.0, counting model", round(ppl_count, 3))

    # --- 3. the same thing as a tiny neural network --------------------------------
    # P(next | prev) = softmax(onehot(prev) @ W). W is (10, 10), trained by gradient descent.
    W = np.zeros((10, 10))
    N = Ct.sum()
    n_row = Ct.sum(axis=1, keepdims=True)
    lr = 5.0
    for step in range(301):
        Pw = softmax(W)
        loss = float(-(Ct * np.log(Pw)).sum() / N)
        if step in (0, 10, 50, 100, 300):
            print(f"neural step {step:3d}  train loss {loss:.4f}  held-out perplexity "
                  f"{perplexity(stream_probs(ho, VOCAB, Pw)):.3f}")
        W -= lr * (n_row * Pw - Ct) / N       # gradient of the mean cross-entropy
    print("W shape", W.shape)

    # the CodeBlank's example: loss of three pairs under a fixed W
    Wd = np.log(np.array([[0.5, 0.5], [0.9, 0.1]]))
    prev, nxt = np.array([0, 0, 1]), np.array([0, 1, 0])
    Pd = softmax(Wd[prev])
    print("\ncode example: probs of the actual next tokens", Pd[np.arange(3), nxt],
          " loss", round(float(-np.log(Pd[np.arange(3), nxt]).mean()), 4))

    # --- 4. longer contexts explode ------------------------------------------------
    for k in (1, 2, 3):
        print(f"context of {k} previous word(s), vocab 10: {10 ** k:,} rows")
    print(f"context of 3 previous words, vocab 50,000: {50_000 ** 3:,} rows")


if __name__ == "__main__":
    main()
