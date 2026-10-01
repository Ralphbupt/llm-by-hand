"""
Level 10 · Probability and sampling

Run:  python demo.py      (needs numpy)

A model never outputs a word directly. It outputs one score per candidate word.
softmax turns the scores into probabilities, then we roll a weighted die.
Every number the page asks about is printed below.
"""
import numpy as np

np.set_printoptions(precision=3, suppress=True)


def softmax(z):
    z = np.asarray(z, dtype=float)
    e = np.exp(z - z.max())          # subtracting the max changes nothing, but avoids overflow
    return e / e.sum()


# --- 1. scores → probabilities ---------------------------------------------
words = ["mat", "sofa", "roof", "moon"]
scores = np.array([2.0, 1.0, 0.5, -1.0])
p = softmax(scores)
print("The cat sat on the ___")
print("scores       ", scores)
print("exp(scores)  ", np.exp(scores))
print("sum of exp   ", round(float(np.exp(scores).sum()), 3))
print("probabilities", p, " sum =", round(float(p.sum()), 3))
print("rounded e^score", np.round(np.exp(scores), 1), " sum", round(float(np.round(np.exp(scores), 1).sum()), 1),
      " → p(mat) ≈", round(7.4 / 12.1, 2))

# two candidates, small enough to do by hand
s2 = np.array([2.0, 0.0])
print("\nscores [2, 0]:  e^2 / (e^2 + e^0) =", round(np.e**2, 3), "/", round(np.e**2 + 1, 3),
      "=", round(float(softmax(s2)[0]), 3))
print("add 10 to both [12, 10]:", softmax(s2 + 10), " (same: only differences matter)")

# --- 2. temperature --------------------------------------------------------
print("\ntemperature divides the scores before softmax")
for T in [0.1, 0.5, 1, 2, 3]:
    print(f"  T = {T:<4} scores/T = {scores / T}  →  {softmax(scores / T)}")
for T in [0.5, 2]:
    print(f"scores [2, 0] at T = {T}: scores/T = {s2 / T} → p(first) = {softmax(s2 / T)[0]:.3f}")

# --- 3. rolling the die ------------------------------------------------------
rng = np.random.default_rng(0)
draws = rng.choice(len(words), size=1000, p=p)
counts = np.bincount(draws, minlength=len(words))
print("\n1000 samples at T = 1:")
for w, c, q in zip(words, counts, p):
    print(f"  {w:5s} sampled {c:4d} times ({c / 1000:.3f})   probability {q:.3f}")

# --- 4. cross-entropy --------------------------------------------------------
print("\ncross-entropy loss = -ln(p of the correct answer)   (log means ln: np.log is the natural log)")
for q in [0.999, 0.9, 0.5, 0.1, 0.01]:      # the page asks about 0.1 (ln 10 ≈ 2.30) and 0.5 (ln 2 ≈ 0.69)
    print(f"  p = {q:<6} loss = {-np.log(q):.3f}")

lab = softmax([2.0, 1.0, 0.1])                      # the lab's starting scores: cat, dog, car
print("lab start: scores [2.0, 1.0, 0.1] → p =", lab, " loss if 'cat' is correct =", round(float(-np.log(lab[0])), 3))
print("                                       loss if 'car' is correct =", round(float(-np.log(lab[2])), 3))

# --- 5. the gradient of softmax + cross-entropy: p − y ----------------------
print("\ngradient of the loss w.r.t. the scores = p − y (y = one-hot target)")
pg = np.array([0.7, 0.2, 0.1])                          # the page's table: cat, dog, car; dog is correct
y = np.array([0.0, 1.0, 0.0])
print("  p =", pg, " y =", y, " p − y =", pg - y, " (dog: 0.2 − 1 = -0.8)")
print("  one step s ← s − lr·(p − y) raises dog's score and lowers cat's and car's")
g = softmax([2.0, 1.0, 0.1]) - np.eye(3)[1]
print("  code check: scores [2, 1, 0.1], correct = dog →", g, " sum =", round(float(g.sum()), 6))
eps = 1e-6                                              # check p − y against nudging each score
L = lambda s_: -np.log(softmax(s_)[1])
num = np.array([(L(np.array([2.0, 1.0, 0.1]) + eps * np.eye(3)[i]) - L(np.array([2.0, 1.0, 0.1]) - eps * np.eye(3)[i])) / (2 * eps) for i in range(3)])
print("  nudging each score gives", num)

# --- 6. entropy and perplexity -------------------------------------------
print("\nperplexity = e^(average surprise), surprise = -ln p of the right word")
print("  even over 4 words: surprise", round(float(-np.log(0.25)), 3), "→ perplexity", round(float(np.exp(-np.log(0.25))), 3))


def entropy(q):
    q = np.asarray(q, dtype=float)
    q = q / q.sum()
    nz = q[q > 0]
    return float(-(nz * np.log(nz)).sum()) + 0.0   # + 0.0 turns -0.0 into 0.0


for name, w in [("even", [1, 1, 1, 1]), ("sure", [1, 0, 0, 0]), ("torn between two", [1, 1, 0, 0]), ("skewed", [7, 1, 1, 1])]:
    H = entropy(w)
    print(f"  lab preset {name:17s} entropy {H:.3f}  perplexity {np.exp(H):.2f}")

pa = np.array([0.9] * 9 + [0.001])
pb = np.array([0.5] * 10)
for name, q in [("A", pa), ("B", pb)]:
    m = float(-np.log(q).mean())
    print(f"  model {name}: average surprise {m:.3f}  perplexity {np.exp(m):.2f}")

sent = np.array([0.5, 0.25, 0.125, 0.25, 0.25])  # "the cat sat on the mat": p of cat, sat, on, the, mat
s = np.log(1 / sent)                               # surprise -ln p, written so ln 1 prints as 0
print("  sentence surprises", s, " sum", round(float(s.sum()), 2), " average", round(float(s.mean()), 3), " perplexity", round(float(np.exp(s.mean())), 3))
print("  same as the geometric mean of 1/p:", round(float(np.prod(1 / sent) ** (1 / len(sent))), 3))

# --- 7. Gaussian noise -------------------------------------------------------
print("\nGaussian: x = mean + std * z, z from a standard normal")
mean, std, z = 3.0, 2.0, -1.5
print(f"  mean {mean}, std {std}, z {z}  →  x = {mean} + {std} × {z} = {mean + std * z}")
pts = rng.standard_normal((1000, 2)) * 2 + 3
print("  rng.standard_normal((1000, 2)) * 2 + 3  has shape", pts.shape)
print("  measured mean", pts.mean(axis=0), " measured std", pts.std(axis=0))
print("  share within one std (in x):", round(float((np.abs(pts[:, 0] - 3) <= 2).mean()), 3), "(about 0.68)")


# ---- section 4 Stuck: softmax applied twice ----
def _sm(z):
    e = np.exp(z - z.max())
    return e / e.sum()


once = _sm(np.array([2.0, 0.0]))
print("\nsoftmax([2, 0]) =", once.round(2), "  softmax of that again =", _sm(once).round(2))

# ---- section 8: put it together (safe softmax with temperature, then cross-entropy) ----
def ce_from_scores(scores, correct, T=1.0):
    z = np.array(scores, dtype=float) / T
    e = np.exp(z - z.max())
    p = e / e.sum()
    return -np.log(p[correct])


print("loss([2, 1, 0.1], cat) =", round(ce_from_scores([2.0, 1.0, 0.1], 0), 3),
      "  loss([1000, 0], 0) =", round(ce_from_scores([1000.0, 0.0], 0), 6) + 0.0,
      "  loss([2, 0], 0, T=2) =", round(ce_from_scores([2.0, 0.0], 0, 2.0), 3))
