"""
Level U1 · Tensors in memory

Run:  python demo.py      (needs numpy; uses torch only for the PyTorch names, if it is installed)

An array is one long row of numbers in memory plus a little description: a shape, strides and a start.
Every number the page asks about is printed below.
"""
import numpy as np
from numpy.lib.stride_tricks import as_strided


def elem_strides(a):
    """NumPy counts strides in bytes; the page counts them in elements (bytes / itemsize)."""
    return tuple(s // a.itemsize for s in a.strides)


def start(a, base):
    """Where a view starts inside base's memory, in elements."""
    return (a.__array_interface__["data"][0] - base.__array_interface__["data"][0]) // a.itemsize


x = np.arange(12.0).reshape(3, 4)     # float64: 8 bytes per number
print("x = np.arange(12.0).reshape(3, 4)")
print(x)
print("memory (one long row):", x.ravel().tolist())
print("itemsize:", x.itemsize, "bytes")
print("x.strides in bytes:", x.strides, "→ in elements:", elem_strides(x))

# --- section 1: the address rule -----------------------------------------------
i, j = 1, 2
s0, s1 = elem_strides(x)
print(f"\nx[{i}, {j}] lives at {i}·{s0} + {j}·{s1} = {i * s0 + j * s1}; value {x[i, j]:g}")

t = np.zeros((2, 3, 4))
print("strides of a (2, 3, 4) array, in elements:", elem_strides(t))


def contiguous_strides(shape):
    strides = []
    step = 1
    for size in reversed(shape):
        strides.insert(0, step)
        step *= size
    return strides


for shp in [(3, 4), (2, 3, 4), (5,), (2, 1, 3)]:
    print("contiguous_strides", shp, "=", contiguous_strides(shp))

# --- section 2: views ----------------------------------------------------------
print("\n--- views: same memory, new shape and strides ---")
cases = {
    "x.T": x.T,
    "x[:, ::2]": x[:, ::2],
    "x[1:, 1:]": x[1:, 1:],
    "x.reshape(2, 6)": x.reshape(2, 6),
}
for name, v in cases.items():
    print(f"{name:16s} shape {v.shape}  strides {elem_strides(v)}  start {start(v, x)}  "
          f"shares memory: {np.shares_memory(v, x)}")

y = x.copy()
yT = y.T
yT[0, 1] = 100
print("\nafter y = x.copy(); yT = y.T; yT[0, 1] = 100:")
print(y)
print("y[1, 0] is now", y[1, 0])

print("x[[0, 2]] shares memory:", np.shares_memory(x[[0, 2]], x), "(a list of rows makes a copy)")

t = np.zeros((2, 3, 4))
print("np.swapaxes((2, 3, 4) array, 1, 2): shape", np.swapaxes(t, 1, 2).shape,
      "strides", elem_strides(np.swapaxes(t, 1, 2)))

# --- section 3: when reshape must copy -------------------------------------------
print("\n--- reshape after a transpose ---")
order = [int(i * elem_strides(x.T)[0] + j * elem_strides(x.T)[1]) for i in range(4) for j in range(3)]
print("x.T read in row order visits memory positions:", order)
flat = x.T.reshape(12)
print("x.T.reshape(12) =", flat.tolist())
print("x.T.reshape(12)[1] =", flat[1])
print("shares memory with x:", np.shares_memory(flat, x))
print("x.reshape(12) shares memory with x:", np.shares_memory(x.reshape(12), x))
print("C-contiguous?  x:", x.flags["C_CONTIGUOUS"], "  x.T:", x.T.flags["C_CONTIGUOUS"],
      "  x[:, ::2]:", x[:, ::2].flags["C_CONTIGUOUS"])

small = np.arange(6.0).reshape(2, 3)
print("\nsmall = np.arange(6.0).reshape(2, 3); small.T.reshape(6) =", small.T.reshape(6).tolist())

# heads: (B, h, L, d_k) → transpose(1, 2) → (B, L, h, d_k)
heads = np.zeros((2, 4, 10, 16))
moved = heads.transpose(0, 2, 1, 3)
print("\nheads (2, 4, 10, 16) strides", elem_strides(heads))
print("after transpose(1, 2): shape", moved.shape, "strides", elem_strides(moved),
      "C-contiguous:", moved.flags["C_CONTIGUOUS"])
print("joined: reshape(2, 10, 64) shares memory:", np.shares_memory(moved.reshape(2, 10, 64), heads))

try:
    import torch
    xt = torch.arange(12.0).reshape(3, 4)
    print("\ntorch: x.stride() =", xt.stride(), " x.T.stride() =", xt.T.stride(),
          " x.T.is_contiguous() =", xt.T.is_contiguous())
    try:
        xt.T.view(12)
    except RuntimeError as e:
        print("torch: x.T.view(12) raises:", str(e).split(".")[0])
    print("torch: x.T.contiguous().view(12) =", xt.T.contiguous().view(12).tolist())
    print("torch: x.T.reshape(12) =", xt.T.reshape(12).tolist())
except ImportError:
    print("\n(torch not installed: skipping the PyTorch names)")

# --- section 4: broadcasting with stride 0 ---------------------------------------
print("\n--- broadcasting: stride 0 ---")
row = x[0]
b = np.broadcast_to(row, (3, 4))
print("np.broadcast_to(x[0], (3, 4)):")
print(b)
print("strides", elem_strides(b), " shares memory:", np.shares_memory(b, x))
same = as_strided(row, shape=(3, 4), strides=(0, row.itemsize))
print("as_strided(x[0], shape=(3, 4), strides=(0, 8)) equals it:", np.array_equal(same, b))

v = np.ones(4, dtype=np.float32)
big = np.broadcast_to(v, (1000, 4))
print(f"float32 (4,) broadcast to {big.shape}: stores {v.nbytes} bytes; a real copy would be {big.copy().nbytes} bytes")

col = np.array([[10.0], [20.0], [30.0]])
print("a (3, 1) column broadcast to (3, 4): strides", elem_strides(np.broadcast_to(col, (3, 4))))


def read(buf, shape, strides, offset=0):
    rows, cols = shape
    out = []
    for i in range(rows):
        r = []
        for j in range(cols):
            r.append(buf[offset + i * strides[0] + j * strides[1]])
        out.append(r)
    return out


buf = list(range(12))
print("\nread(buf, (4, 3), (1, 4))       =", read(buf, (4, 3), (1, 4)))
print("read(buf, (3, 2), (4, 2))       =", read(buf, (3, 2), (4, 2)))
print("read(buf, (2, 3), (4, 1), 5)    =", read(buf, (2, 3), (4, 1), 5))
print("read(buf, (3, 4), (0, 1))       =", read(buf, (3, 4), (0, 1)))

# --- Deeper: sliding windows with as_strided (careful: no bounds checks) ----------
a = np.arange(6.0)
win = as_strided(a, shape=(4, 3), strides=(a.itemsize, a.itemsize))
print("\nas_strided(np.arange(6.0), shape=(4, 3), strides=(8, 8)):")
print(win)
print("same as sliding_window_view:", np.array_equal(win, np.lib.stride_tricks.sliding_window_view(a, 3)))
print("broadcast_to result is writeable:", np.broadcast_to(x[0], (3, 4)).flags.writeable)
