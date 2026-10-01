"""
Level U3 · Build your own autograd

Run:  python demo.py      (plain Python; uses torch only to double-check, if it is installed)

A Value class that records + , × and tanh, builds the computation graph,
and finds every gradient with backward(). Every number the page asks about is printed below.
"""
import math


class Value:
    def __init__(self, data, children=(), name=""):
        self.data = data
        self.grad = 0.0
        self._children = children
        self._backward = lambda: None
        self.name = name

    def __add__(self, other):
        out = Value(self.data + other.data, (self, other))
        def _backward():
            self.grad += out.grad           # a sum passes its grad through unchanged
            other.grad += out.grad
        out._backward = _backward
        return out

    def __mul__(self, other):
        out = Value(self.data * other.data, (self, other))
        def _backward():
            self.grad += other.data * out.grad   # each input gets (the other input) × out.grad
            other.grad += self.data * out.grad
        out._backward = _backward
        return out

    def __sub__(self, other):
        out = Value(self.data - other.data, (self, other))
        def _backward():
            self.grad += out.grad           # a − b grows with a: local factor 1
            other.grad -= out.grad          # ... and shrinks with b: local factor −1
        out._backward = _backward
        return out

    def tanh(self):
        t = math.tanh(self.data)
        out = Value(t, (self,))
        def _backward():
            self.grad += (1 - t ** 2) * out.grad
        out._backward = _backward
        return out

    def backward(self, verbose=False):
        topo, seen = [], set()
        def build(v):
            if v not in seen:
                seen.add(v)
                for child in v._children:
                    build(child)
                topo.append(v)              # a node goes in after all of its inputs
        build(self)
        if verbose:
            print("  topological order:", [v.name or round(v.data, 3) for v in topo])
        self.grad = 1.0
        for v in reversed(topo):
            v._backward()


# --- 1. the lab's graph: L = (a·b + c)·d ---------------------------------------
a, b, c, d = Value(2.0, name="a"), Value(3.0, name="b"), Value(1.0, name="c"), Value(-2.0, name="d")
e = a * b; e.name = "e"
f = e + c; f.name = "f"
L = f * d; L.name = "L"
print("forward:  e = a·b =", e.data, "  f = e + c =", f.data, "  L = f·d =", L.data)
L.backward(verbose=True)
for v in [L, f, e, d, c, b, a]:
    print(f"  dL/d{v.name} = {v.grad:g}")

# check with a nudge (finite differences)
def L_of(a, b, c, d):
    return (a * b + c) * d

h = 1e-6
for name, i in [("a", 0), ("b", 1), ("c", 2), ("d", 3)]:
    x = [2.0, 3.0, 1.0, -2.0]
    x[i] += h
    print(f"  nudge check dL/d{name} ≈ {(L_of(*x) - L_of(2.0, 3.0, 1.0, -2.0)) / h:.4f}")

# the second set of numbers used by a test
a2, b2, c2, d2 = Value(1.0), Value(-1.0), Value(2.0), Value(3.0)
L2 = (a2 * b2 + c2) * d2
L2.backward()
print("a=1, b=-1, c=2, d=3 → grads", [a2.grad, b2.grad, c2.grad, d2.grad])

# --- 2. a value used twice ------------------------------------------------------
x = Value(3.0)
y = x * x
y.backward()
print("\ny = x·x at x = 3: dy/dx =", x.grad, "(2x = 6)")


class BadValue(Value):
    """Same as Value but with = instead of += in the product."""
    def __mul__(self, other):
        out = BadValue(self.data * other.data, (self, other))
        def _backward():
            self.grad = other.data * out.grad
            other.grad = self.data * out.grad
        out._backward = _backward
        return out


xb = BadValue(3.0)
yb = xb * xb
yb.backward()
print("with = instead of +=: x.grad =", xb.grad, "(wrong: the second share overwrote the first)")

x = Value(3.0)
y = x * x + x
y.backward()
print("y = x·x + x at x = 3: dy/dx =", x.grad, "(2x + 1 = 7)")

# --- the code-sub question: subtraction, visited by hand like the page ----------
def sub_grads(a, b, c):
    a, b, c = Value(a), Value(b), Value(c)
    e = a * b
    L = e - c
    L.grad = 1.0
    for v in [L, e]:
        v._backward()
    return [a.grad, b.grad, c.grad]

print("\nL = a·b − c at a=2, b=3, c=1: grads", sub_grads(2.0, 3.0, 1.0), "(c gets −1)")
x = Value(5.0)
y = x - x
y.grad = 1.0
y._backward()
print("y = x − x at x = 5: dy/dx =", x.grad, "(1 − 1 = 0; with = instead of += it would be −1)")
a, b, c = Value(4.0), Value(1.0), Value(2.0)
dd = a - b
L = dd * c
L.grad = 1.0
for v in [L, dd]:
    v._backward()
print("L = (a − b)·c at a=4, b=1, c=2: grads", [a.grad, b.grad, c.grad])

# --- 3. wrong order -----------------------------------------------------------
a, b, c, d = Value(2.0), Value(3.0), Value(1.0), Value(-2.0)
L = (a * b + c) * d
topo, seen = [], set()
def build(v):
    if v not in seen:
        seen.add(v)
        for ch in v._children:
            build(ch)
        topo.append(v)
build(L)
L.grad = 1.0
for v in topo:                      # forward order: wrong
    v._backward()
print("\nvisiting in forward order instead:", [a.grad, b.grad, c.grad, d.grad], "(only d is right)")

# --- 4. a tanh neuron -----------------------------------------------------------
w = Value(0.5)
n = (w * Value(1.0) + Value(0.0)).tanh()
n.backward()
print("\nneuron tanh(w·1 + 0) at w = 0.5: output", round(n.data, 6), " dn/dw =", round(w.grad, 6))

# --- 5. same numbers as PyTorch -------------------------------------------------
try:
    import torch
    t = [torch.tensor(v, requires_grad=True, dtype=torch.float64) for v in (2.0, 3.0, 1.0, -2.0)]
    Lt = (t[0] * t[1] + t[2]) * t[3]
    Lt.backward()
    print("\nPyTorch on the lab's graph:", [v.grad.item() for v in t])
except ImportError:
    print("\n(torch not installed: skipped the PyTorch comparison)")
