"""
Level 15 · Masks and multi-head attention

Run:  python demo.py      (needs numpy)

Causal and padding masks, broadcasting a mask over a batch, two heads with W_O,
and one masked attention head of a GPT. Every number the page asks about is printed here.
"""
import numpy as np

np.set_printoptions(precision=3, suppress=True)


def softmax(x, axis=-1):
    e = np.exp(x - x.max(axis=axis, keepdims=True))   # subtract the max so exp never overflows
    return e / e.sum(axis=axis, keepdims=True)         # each row now adds up to 1


X = np.array([[2.0, 0.0],    # cat   (the three words of level 14)
              [1.0, 1.0],    # dog
              [0.0, 2.0]])   # car

# ---------------------------------------------------------------------------
# 1. Masks
# ---------------------------------------------------------------------------
print("\n=== 1. masks ===")
print("a 6-token sentence: causal mask shape", np.triu(np.ones((6, 6), dtype=bool), k=1).shape)
L = 4
causal = np.triu(np.ones((L, L), dtype=bool), k=1)   # True = not allowed to look
print("causal mask, shape", causal.shape, "(1 = blocked)")
print(causal.astype(int))
toy = np.zeros((L, L))                                # equal scores, so we can read the mask off the weights
wc = softmax(np.where(causal, -np.inf, toy))
print("weights with equal scores:")
print(wc)
print("non-zero cells:", int((wc > 0).sum()), "of", L * L)

row = np.array([0.34, 0.05, 0.0])                     # the third score belongs to a PAD token
print("\nblocked score set to 0 instead of -inf: weights =", softmax(row).round(3),
      f"→ the PAD token still gets {softmax(row)[2]:.0%}")
print("with -inf:", softmax(np.array([0.34, 0.05, -np.inf])).round(3))

B, Lp = 2, 5
lengths = np.array([5, 3])                            # sentence 2 has 2 padding tokens at the end
pad = np.arange(Lp)[None, :] >= lengths[:, None]      # (B, L): True where the token is padding
pad = pad[:, None, :]                                 # (B, 1, L): the same row for every query
scores_b = np.zeros((B, Lp, Lp))
print("pad mask", pad.shape, "+ scores", scores_b.shape, "→ broadcast to", np.broadcast_shapes(pad.shape, scores_b.shape))
print("sentence 2's pad mask row:", pad[1, 0].astype(int))

print("\nnp.where([T, F, F], -inf, [0.34, 0.05, 0.9]) =", np.where(np.array([True, False, False]), -np.inf, np.array([0.34, 0.05, 0.9])))
print("np.triu(ones(3, 3), k=0):")
print(np.triu(np.ones((3, 3), dtype=int), k=0))

# ---------------------------------------------------------------------------
# 2. Multi-head: 2 heads, d_model = 4, d_k = 2
# ---------------------------------------------------------------------------
print("\n=== 2. multi-head ===")
X4 = np.array([[2.0, 0.0, 1.0, 0.0],
               [1.0, 1.0, 0.0, 1.0],
               [0.0, 2.0, 1.0, 1.0]])
SWAP = np.array([[0.0, 1.0], [1.0, 0.0]])
W_Q4, W_V4, W_O4 = np.eye(4), np.eye(4), np.eye(4)
W_K4 = np.block([[np.eye(2), np.zeros((2, 2))], [np.zeros((2, 2)), SWAP]])
Q4, K4, V4 = X4 @ W_Q4, X4 @ W_K4, X4 @ W_V4
heads = []
for h in range(2):
    cols = slice(2 * h, 2 * h + 2)                    # head h owns columns 2h and 2h+1
    wh = softmax(Q4[:, cols] @ K4[:, cols].T / np.sqrt(2))
    heads.append(wh @ V4[:, cols])
    print(f"head {h} uses columns {2 * h},{2 * h + 1}; weights:")
    print(wh)
concat = np.concatenate(heads, axis=1)
print("concat, shape", concat.shape)
print(concat)
print("head 1's output starts at column", heads[0].shape[1], "of concat")
print("W_O shape", W_O4.shape, "; rows 0-1 read head 0, rows 2-3 read head 1")
print("output = concat @ W_O, shape", (concat @ W_O4).shape)
print("d_model = 512, 8 heads → d_k =", 512 // 8, "→ sqrt(d_k) =", np.sqrt(512 // 8))

# ---------------------------------------------------------------------------
# 3. Everything at once: single-head attention with a causal mask (the checkpoint)
# ---------------------------------------------------------------------------
print("\n=== 3. masked attention ===")
def masked_attention(X, W_Q, W_K, W_V):
    L, d_k = X.shape[0], W_Q.shape[1]
    Q, K, V = X @ W_Q, X @ W_K, X @ W_V
    scores = Q @ K.T / np.sqrt(d_k)
    mask = np.triu(np.ones((L, L), dtype=bool), k=1)       # True = blocked (looking ahead)
    scores = np.where(mask, -np.inf, scores)
    return softmax(scores) @ V

W_Kt = np.array([[0.0, 1.0], [1.0, 0.0]])
res = masked_attention(X, np.eye(2), W_Kt, np.eye(2))
print("cat, dog, car with swapped keys and a causal mask:")
print(res)
print("cat can only see itself, so its output is cat itself:", res[0])
