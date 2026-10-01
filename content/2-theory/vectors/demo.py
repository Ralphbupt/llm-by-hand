"""
Level 13 · Embeddings and similarity

Run:  python demo.py      (needs numpy)

Token ids (from level 12) → vectors. Then: how do we compare two vectors,
and why one fixed vector per word is not enough.
Every number the page asks about is printed below.
"""
import json
import pathlib
import sys

import numpy as np

np.set_printoptions(precision=3, suppress=True)

# --- 1. the ids from level 12 ---------------------------------------------------
text = "hello"
chars = sorted(set(text))                      # the vocabulary: every distinct character, sorted
stoi = {c: i for i, c in enumerate(chars)}     # character → id
itos = {i: c for c, i in stoi.items()}         # id → character


def encode(s):
    return [stoi[c] for c in s]


def decode(ids):
    return "".join(itos[i] for i in ids)


ids = encode(text)
print("text      ", repr(text))
print("vocabulary", chars, " size", len(chars))
print("stoi      ", stoi)
print("ids       ", ids)
print("decode    ", repr(decode(ids)))


# --- 2. ids → vectors: the embedding table -------------------------------------
# A real model starts this table with random numbers and learns it.
# The lab uses a fixed rule so everyone sees the same numbers:
def start_vector(c):
    k = ord(c)
    return [round(((k * 37) % 41) / 10 - 2, 1), round(((k * 53) % 43) / 10 - 2, 1)]


E = np.array([start_vector(c) for c in chars])   # shape (vocab size, 2)
print("\nembedding table E, shape", E.shape)
for c, row in zip(chars, E):
    print(f"  id {stoi[c]} '{c}' → {row}")

X = E[ids]                                       # look up one row per token
print("\nE[ids], shape", X.shape, " (5 tokens, 2 numbers each)")
print(X)
print("the two 'l' rows are equal:", np.array_equal(X[2], X[3]))

onehot = np.eye(len(chars))[ids]                 # (5, 4): a single 1 in each row
print("\none-hot of ids, shape", onehot.shape)
print(onehot)
print("one-hot @ E equals E[ids]:", np.allclose(onehot @ E, X))

# --- 3. dot product = similarity ------------------------------------------------
a, b = np.array([2.0, 1.0]), np.array([1.0, 3.0])
print("\n[2, 1] · [1, 3] =", "2×1 + 1×3 =", a @ b)
lab = {"cat": [2.0, 1.0], "dog": [1.5, 1.5], "car": [-1.0, 2.0]}  # the dot-product lab's starting arrows
for x, y in [("cat", "dog"), ("cat", "car"), ("dog", "car")]:
    u, v = np.array(lab[x]), np.array(lab[y])
    cos = u @ v / (np.linalg.norm(u) * np.linalg.norm(v))
    print(f"  {x}·{y} = {u @ v:5.2f}   cos(angle) = {cos:5.3f}")
print("[2, 1] · [-2, -1] =", np.array([2, 1]) @ np.array([-2, -1]), " (opposite directions → negative)")
print("[2, 1] · [-1, 2]  =", np.array([2, 1]) @ np.array([-1, 2]), "  (at a right angle → zero)")
print("[2, 1] · [4, 2]   =", np.array([2, 1]) @ np.array([4, 2]), " (same direction, twice as long → twice the dot)")

# --- 3. where the vectors come from: words used in similar places --------------------
# Hand example (window 1: the word right before and right after).
small = [["cat", "eats", "fish"], ["dog", "eats", "meat"], ["cat", "drinks", "milk"], ["car", "needs", "fuel"]]
ctx_cols = ["eats", "drinks", "needs"]
def window1(sents, word):
    v = np.zeros(len(ctx_cols), dtype=int)
    for s in sents:
        for j, w in enumerate(s):
            if w != word:
                continue
            for k in (j - 1, j + 1):
                if 0 <= k < len(s) and s[k] in ctx_cols:
                    v[ctx_cols.index(s[k])] += 1
    return v
cv = {w: window1(small, w) for w in ("cat", "dog", "car")}
print("\nneighbor counts over", ctx_cols, ":", {w: v.tolist() for w, v in cv.items()})
print("cat·dog =", int(cv["cat"] @ cv["dog"]), "  cat·car =", int(cv["cat"] @ cv["car"]))

# A bigger corpus from our own rules, then the count method: neighbors within 2 words → PPMI → compare rows (cosine), draw them in 2D.
GROUPS = {
    "animal": ["cat", "dog", "horse", "cow"],
    "food": ["bread", "rice", "fish", "apple"],
    "vehicle": ["car", "bus", "truck", "train"],
}
TEMPLATES = {
    "animal": ["the {} sleeps all day", "a {} drinks water", "the {} runs in the field", "my {} is hungry", "the {} is asleep"],
    "food": ["people eat {} for lunch", "people cook {} at home", "we buy {} today", "fresh {} tastes good", "a plate of {}"],
    "vehicle": ["the {} drives fast", "the {} stops at the light", "we park the {}", "the {} needs fuel", "my {} is broken"],
}
rng = np.random.default_rng(0)
corpus = []
for _ in range(3000):
    g = rng.choice(list(GROUPS))
    t = rng.choice(TEMPLATES[g])
    w = rng.choice(GROUPS[g])
    corpus.append(t.format(w).split())
for _ in range(250):                                  # "fish" is also an animal sometimes
    corpus.append(rng.choice(["a fish swims in the river", "the fish is asleep", "a fish drinks water"]).split())
OWN = {                                               # a few sentences only one word appears in, so each word keeps a spot of its own
    "cat": "the cat chases a mouse", "dog": "the dog barks at night", "horse": "the horse pulls a cart", "cow": "the cow gives milk",
    "bread": "we slice the bread", "rice": "we boil the rice", "fish": "we grill the fish", "apple": "we peel the apple",
    "car": "the car has four doors", "bus": "the bus carries many people", "truck": "the truck carries heavy boxes", "train": "the train runs on rails",
}
for _ in range(600):
    w = rng.choice(list(OWN))
    corpus.append(OWN[w].split())
vocab_w = sorted({w for s in corpus for w in s})
ix = {w: i for i, w in enumerate(vocab_w)}
C = np.zeros((len(vocab_w), len(vocab_w)))
for s in corpus:
    for j, w in enumerate(s):
        for k in range(max(0, j - 2), min(len(s), j + 3)):
            if k != j:
                C[ix[w], ix[s[k]]] += 1
total = C.sum()
pw = C.sum(1, keepdims=True) / total
pc = C.sum(0, keepdims=True) / total
with np.errstate(divide="ignore"):
    pmi = np.log((C / total) / (pw * pc))          # np.log is ln
ppmi = np.maximum(pmi, 0)
targets = [w for g in GROUPS.values() for w in g]
# similarity: cosine between the full rows of PPMI counts
R = np.array([ppmi[ix[w]] for w in targets])
R = R / np.linalg.norm(R, axis=1, keepdims=True)
cos = R @ R.T
# the picture: 2 numbers per word, the 2 directions in which the 12 rows differ most (SVD of the centered rows)
U, S, _ = np.linalg.svd(R - R.mean(0), full_matrices=False)
vec2 = U[:, :2] * S[:2]
print(f"\ncorpus: {len(corpus)} sentences, vocabulary {len(vocab_w)} words; e.g. {' '.join(corpus[0])!r}, {' '.join(corpus[1])!r}")
def closest(w, n=3):
    i = targets.index(w)
    return sorted(((round(float(cos[i, j]), 2), targets[j]) for j in range(len(targets)) if j != i), reverse=True)[:n]
for w in ("cat", "bread", "car", "fish"):
    print(f"closest to {w}: " + ", ".join(f"{o} ({s:.2f})" for s, o in closest(w)))

if "--export" in sys.argv:
    out = {
        "groups": {g: ws for g, ws in GROUPS.items()},
        "coords": {w: [round(float(v), 3) for v in vec2[i]] for i, w in enumerate(targets)},
        "closest": {w: closest(w) for w in targets},
        "neighbors": {w: sorted(((vocab_w[j], int(C[ix[w], j])) for j in np.nonzero(C[ix[w]])[0]), key=lambda t: -t[1])[:6] for w in targets},
        "sample": [" ".join(s) for s in corpus[:8]],
        "sentences": len(corpus),
    }
    path = pathlib.Path(__file__).resolve().parents[3] / "site/public/data/vectors/word2vec.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out))
    print("wrote", path)

# --- 4. one vector per word is not enough ----------------------------------------
dims = ["fruit", "tech", "sweet", "action"]
vocab = {
    "apple":    np.array([1.0, 1.0, 0.0, 0.0]),   # both meanings at once
    "sweet":    np.array([1.0, 0.0, 1.0, 0.0]),
    "releases": np.array([0.0, 1.0, 0.0, 1.0]),
    "phone":    np.array([0.0, 1.0, 0.0, 0.0]),
}
print("\ndimensions:", dims)
for s in (["sweet", "apple"], ["apple", "releases", "phone"]):
    print("sentence:", " ".join(s))
    print("   apple's own vector      ", vocab["apple"], "(the same in every sentence)")
    print("   average of the sentence ", np.mean([vocab[w] for w in s], axis=0))

# the code exercise: look up the rows of a sentence, then average them
E4 = np.array([vocab[w] for w in ["apple", "sweet", "releases", "phone"]])   # ids 0..3
X = E4[[0, 2, 3]]                                                              # (3, 4): one row per token
print("\nE[[0, 2, 3]] shape", X.shape, "→ mean over axis 0:", X.mean(axis=0).round(4))
print("E[[1, 0]].mean(axis=0):", E4[[1, 0]].mean(axis=0), "  one id → shape", E4[[0]].mean(axis=0).shape)
