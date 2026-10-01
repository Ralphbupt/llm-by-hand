"""
Level 1 · Matrices and shapes

Run:  python demo.py      (needs numpy)

Every number the page asks you about is printed here, so you can check your answers
and see where each one comes from.
"""
import numpy as np

A = np.array([[1, 2, 3],
              [0, 1, 0]])          # 2 rows, 3 columns
B = np.array([[1, 0],
              [0, 1],
              [1, 1]])             # 3 rows, 2 columns

print("A, shape", A.shape)
print(A)
print("B, shape", B.shape)
print(B)

# --- one cell, by hand ------------------------------------------------------
# C[i][j] = row i of A · column j of B
i, j = 0, 1
row, col = A[i], B[:, j]
print(f"\nC[{i}][{j}] = row {i} of A {row.tolist()} · column {j} of B {col.tolist()}")
terms = [f"{a}×{b}" for a, b in zip(row, col)]
print("        =", " + ".join(terms), "=", int(row @ col))

# --- every cell -------------------------------------------------------------
C = A @ B
print("\nC = A @ B, shape", C.shape, "  (2,3) @ (3,2) → (2,2)")
print(C)

# --- the same thing with three loops ----------------------------------------
def mm(a, b):
    n, k, m = len(a), len(b), len(b[0])
    out = [[0] * m for _ in range(n)]
    for i in range(n):
        for j in range(m):
            for t in range(k):          # t runs over the inner size, the one that disappears
                out[i][j] += a[i][t] * b[t][j]
    return out

print("\nthree loops give the same answer:", mm(A.tolist(), B.tolist()))

# --- shapes ---------------------------------------------------------------
print("\n(3,4) @ (4,2) →", (np.ones((3, 4)) @ np.ones((4, 2))).shape)
try:
    np.ones((3, 2)) @ np.ones((3, 2))
except ValueError as e:
    print("(3,2) @ (3,2) → error:", str(e).split(" (")[0])
print("(3,2) @ (3,2).T →", (np.ones((3, 2)) @ np.ones((3, 2)).T).shape)

# --- a batch ----------------------------------------------------------------
X = np.random.randn(2, 5, 4)    # 2 sentences, 5 words, 4 numbers per word
W = np.random.randn(4, 8)
print("\nbatch: X", X.shape, "@ W", W.shape, "→", (X @ W).shape)

# --- broadcasting -------------------------------------------------------------
a = np.array([[1], [2], [3], [4]])        # (4, 1)
b = np.array([[10, 20, 30, 40, 50]])      # (1, 5)
s = a + b
print("\nbroadcasting: (4,1) + (1,5) →", s.shape)
print(s)
print("(a + b)[2][3] =", a[2, 0], "+", b[0, 3], "=", s[2, 3])
try:
    np.ones((3, 2)) + np.ones(3)
except ValueError as e:
    print("(3,2) + (3,) → error:", str(e).split("operands")[0].strip() or str(e))
print("(3,2) + (3,1) →", (np.ones((3, 2)) + np.ones((3, 1))).shape)
scores = np.zeros((2, 4, 4))
mask = np.zeros((2, 1, 4))
print("scores (2,4,4) + mask (2,1,4) →", (scores + mask).shape)


# --- adding up along one axis --------------------------------------------------
A = np.array([[1, 2], [3, 4], [5, 6]])
print("\nA.sum(axis=0) =", A.sum(axis=0), " A.sum(axis=1) =", A.sum(axis=1), " A.mean(axis=0) =", A.mean(axis=0))
print("X (4,3): X.sum(axis=0).shape =", np.ones((4, 3)).sum(axis=0).shape)
X = np.array([[1., 2.], [3., 4.], [5., 9.]])
print("center(X) = X - X.mean(axis=0):")
print(X - X.mean(axis=0))

# --- reading data code ---------------------------------------------------------
pts = np.vstack([np.zeros((60, 2)), np.ones((60, 2))])
labels = np.repeat([0, 1], 60)
print("\nvstack →", pts.shape, " repeat →", labels.shape)
