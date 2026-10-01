"""
Level 12 · Tokens: from characters to BPE

Run:  python demo.py      (needs numpy)

Text has to be cut into pieces (tokens) before a model can read it.
Characters, whole words, and byte-pair encoding (BPE) cut it in different places.
Every number the page asks about is printed below.
"""

# --- 1. characters → ids -------------------------------------------------------
text = "hello"
chars = sorted(set(text))                      # the vocabulary: every distinct character, sorted
stoi = {c: i for i, c in enumerate(chars)}     # character → id
itos = {i: c for c, i in stoi.items()}         # id → character


def encode(s):
    return [stoi[c] for c in s]


def decode(ids):
    return "".join(itos[i] for i in ids)


print("text      ", repr(text))
print("vocabulary", chars, " size", len(chars))
print("stoi      ", stoi)
print("ids       ", encode(text), " decode →", repr(decode(encode(text))))
print("'hole'    ", encode("hole"))

# --- 2. whole words → ids --------------------------------------------------------
words_vocab = ["the", "a", "cat", "dog", "sat", "ran", "on", "mat", "rug", "."]   # the level 11 stories
sentence = "the cats sat ."
print("\nword tokens for", repr(sentence), "→",
      [w if w in words_vocab else "<unk>" for w in sentence.split()], " ('cats' was never seen)")


# --- 3. BPE: merge the most frequent neighboring pair, again and again ----------------
def pair_counts(segs, counts):
    """Adjacent pairs, weighted by how often each word appears. Highest first; ties keep first-seen order."""
    pc = {}
    for seg, n in zip(segs, counts):
        for a, b in zip(seg, seg[1:]):
            pc[(a, b)] = pc.get((a, b), 0) + n
    return sorted(pc.items(), key=lambda kv: -kv[1])   # sorted() is stable


def merge(seg, a, b):
    out, i = [], 0
    while i < len(seg):
        if i + 1 < len(seg) and seg[i] == a and seg[i + 1] == b:
            out.append(a + b)
            i += 2
        else:
            out.append(seg[i])
            i += 1
    return out


def bpe_train(words, steps, verbose=False):
    ws, counts = [w for w, _ in words], [n for _, n in words]
    segs = [list(w) for w in ws]
    vocab = sorted({c for w in ws for c in w})
    merges = []
    total = lambda: sum(len(s) * n for s, n in zip(segs, counts))  # noqa: E731
    if verbose:
        print(f"  start: vocab {len(vocab)}, tokens {total()}, pairs {pair_counts(segs, counts)[:4]}")
    for _ in range(steps):
        pcs = pair_counts(segs, counts)
        if not pcs or pcs[0][1] < 2:
            break
        (a, b), n = pcs[0]
        merges.append((a, b))
        vocab.append(a + b)
        segs = [merge(s, a, b) for s in segs]
        if verbose:
            print(f"  merge {len(merges)}: {a}+{b} (count {n}) → vocab {len(vocab)}, tokens {total()},"
                  f" words {[' '.join(s) for s in segs]}")
            print(f"           next pairs {pair_counts(segs, counts)[:3]}")
    return merges, vocab, segs, total()


def bpe_encode(word, merges):
    s = list(word)
    for a, b in merges:          # apply merges in the order they were learned
        s = merge(s, a, b)
    return s


hand = [("cat", 4), ("cats", 2), ("hat", 3), ("hats", 1)]
print("\nhand example:", hand)
merges, vocab, segs, total = bpe_train(hand, 3, verbose=True)
print("pair (a, t) at the start:", dict(pair_counts([list(w) for w, _ in hand], [n for _, n in hand]))[("a", "t")])
for w in ("cats", "that", "chats"):
    print(f"encode {w!r:8} with 3 merges → {bpe_encode(w, merges)}  ({len(bpe_encode(w, merges))} tokens)")
print("merge(list('cats'), 'a', 't') →", merge(list("cats"), "a", "t"))
pc0 = dict(pair_counts([list(w) for w, _ in hand], [n for _, n in hand]))
print("pair counts at the start:", pc0, " (a, t) =", pc0[("a", "t")], " (t, s) =", pc0[("t", "s")], " distinct pairs:", len(pc0))
pc1 = dict(pair_counts([merge(list(w), "a", "t") for w, _ in hand], [n for _, n in hand]))
print("after merge 1, (c, at) =", pc1[("c", "at")])

# --- 4. the generated words: vocabulary grows, sequences shrink -------------------------
STEMS = ["play", "walk", "talk", "jump", "look", "cook", "work", "park"]
SUFFIXES = ["", "s", "ed", "ing", "er"]
gen = [(st + sf, 1 + ((len(st) * 7 + fi * 5 + si * 3) % 9))
       for si, st in enumerate(STEMS) for fi, sf in enumerate(SUFFIXES)]
print("\ngenerated words:", len(gen), "e.g.", gen[:6])
m0, v0, _, t0 = bpe_train(gen, 0)
print("before merging: vocab", len(v0), " tokens", t0)
for k in (5, 10, 20, 40):
    m, v, _, t = bpe_train(gen, k)
    print(f"after {len(m):2d} merges: vocab {len(v):3d}  tokens {t:4d}")
m5, *_ = bpe_train(gen, 5)
print("first 5 merges:", ["+".join(p) for p in m5])

# --- 5. the price of a big vocabulary -----------------------------------------------------
print("\nembedding table for vocab 50,000 × 512 numbers per row:", f"{50_000 * 512:,}", "numbers")
