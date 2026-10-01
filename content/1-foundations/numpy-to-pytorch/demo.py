"""
Level 9 · From numpy to PyTorch

Run:  python demo.py      (needs numpy and torch)

The same XOR network trained twice, once in numpy with a hand-written backward pass,
once in PyTorch with loss.backward(). Every number the page asks about is printed below.
"""
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

torch.manual_seed(0)
np.set_printoptions(precision=6, suppress=True)


def sigmoid(z):
    return 1 / (1 + np.exp(-z))


X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=float)
y = np.array([[0], [1], [1], [0]], dtype=float)

# --- 1. parameters ----------------------------------------------------------
model = nn.Sequential(nn.Linear(2, 6), nn.Tanh(), nn.Linear(6, 1))
print("model:", model)
for name, p in model.named_parameters():
    print(f"  {name:9s} shape {tuple(p.shape)}  numbers {p.numel()}  requires_grad {p.requires_grad}")
print("total numbers the model learns:", sum(p.numel() for p in model.parameters()))
print("nn.Linear(2, 6).weight.shape =", tuple(nn.Linear(2, 6).weight.shape), " (out, in): numpy's W1 is (2, 6)")

# --- 2. the same gradients both ways ----------------------------------------
# A 2→3→1 network with fixed weights, so the numbers on the page are exact.
W1 = np.array([[0.5, -0.4, 0.3], [0.2, 0.6, -0.5]])
b1 = np.array([0.0, 0.1, -0.1])
W2 = np.array([[0.7], [-0.3], [0.5]])
b2 = np.array([0.05])

# numpy, by hand (as in level 6)
a1 = np.tanh(X @ W1 + b1)
p = sigmoid(a1 @ W2 + b2)
loss_np = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
dz2 = (p - y) / len(X)
dW2 = a1.T @ dz2
db2 = dz2.sum(0)
dz1 = (dz2 @ W2.T) * (1 - a1 ** 2)
dW1 = X.T @ dz1
db1 = dz1.sum(0)

# PyTorch: copy the same weights in (note the transpose: Linear stores (out, in)), then backward()
lin1, lin2 = nn.Linear(2, 3).double(), nn.Linear(3, 1).double()
with torch.no_grad():
    lin1.weight.copy_(torch.tensor(W1.T)); lin1.bias.copy_(torch.tensor(b1))
    lin2.weight.copy_(torch.tensor(W2.T)); lin2.bias.copy_(torch.tensor(b2))
logits = lin2(torch.tanh(lin1(torch.tensor(X))))
loss_t = F.binary_cross_entropy_with_logits(logits, torch.tensor(y))
loss_t.backward()

print("\nloss   numpy", round(float(loss_np), 6), "  torch", round(loss_t.item(), 6))
print("print(loss) shows:", loss_t, "\n  loss.item() gives:", round(loss_t.item(), 4))
print("dW2 (numpy, a1.T @ dz2):", dW2.ravel())
print("W2 grad (torch, transposed back):", lin2.weight.grad.numpy().ravel())
for name, mine, theirs in [("W1", dW1, lin1.weight.grad.numpy().T), ("b1", db1, lin1.bias.grad.numpy()),
                           ("W2", dW2, lin2.weight.grad.numpy().T), ("b2", db2, lin2.bias.grad.numpy())]:
    print(f"  {name}: largest difference numpy vs torch = {np.abs(mine - theirs).max():.1e}")

# --- 3. backward() adds ------------------------------------------------------
w = torch.tensor(1.0, requires_grad=True)
x_, y_ = 2.0, 6.0
for call in range(1, 3):
    loss = (w * x_ - y_) ** 2
    loss.backward()
    print(f"\nafter backward call {call}: w.grad = {w.grad.item()}" if call == 1 else f"after backward call {call}: w.grad = {w.grad.item()}  (added, not replaced)")


def train(steps, lr, clear):
    w = torch.tensor(1.0, requires_grad=True)
    opt = torch.optim.SGD([w], lr=lr)
    for _ in range(steps):
        if clear:
            opt.zero_grad()
        loss = (w * x_ - y_) ** 2
        loss.backward()
        opt.step()
    return w.item()


print("train 1 step with zero_grad:  w =", round(train(1, 0.05, True), 4))
print("train 2 steps with zero_grad: w =", round(train(2, 0.05, True), 4))
print("train 50 steps with zero_grad: w =", round(train(50, 0.05, True), 4))
print("w after 1..7 steps WITHOUT zero_grad:", [round(train(k, 0.05, False), 3) for k in range(1, 8)])

# --- 4. shapes that broadcast -------------------------------------------------
pred = torch.tensor([[0.1], [0.9], [0.8], [0.2]])     # (4, 1)
labels = torch.tensor([0.0, 1.0, 1.0, 0.0])          # (4,)
print("\npred", tuple(pred.shape), " labels", tuple(labels.shape), " pred - labels →", tuple((pred - labels).shape))
print("wrong MSE (4x4 grid):", round(((pred - labels) ** 2).mean().item(), 4),
      "  right MSE:", round(((pred.squeeze(1) - labels) ** 2).mean().item(), 4))

# --- 5. train the 2→6→1 XOR network in PyTorch ---------------------------------
Xt, yt = torch.tensor(X, dtype=torch.float32), torch.tensor(y, dtype=torch.float32)
opt = torch.optim.SGD(model.parameters(), lr=1.0)
for step in range(2000):
    logits = model(Xt)
    loss = F.binary_cross_entropy_with_logits(logits, yt)
    opt.zero_grad()
    loss.backward()
    opt.step()
probs = torch.sigmoid(model(Xt)).detach().numpy().ravel()
print("\nXOR after 2000 steps: loss", round(loss.item(), 4), " outputs", probs.round(3), " correct:", bool(((probs > 0.5) == y.ravel()).all()))

# --- 6. the translation table: splitting into heads ------------------------------
x = torch.arange(2 * 5 * 8, dtype=torch.float32).reshape(2, 5, 8)   # (B, L, d_model)
heads = x.view(2, 5, 2, 4).transpose(1, 2)                          # (B, h, L, d_k)
print("\nx", tuple(x.shape), "→ view(2, 5, 2, 4)", tuple(x.view(2, 5, 2, 4).shape), "→ transpose(1, 2)", tuple(heads.shape))
s = torch.zeros(3, 3)
mask = torch.triu(torch.ones(3, 3, dtype=torch.bool), diagonal=1)    # True = blocked
print("masked_fill with a causal mask:\n", s.masked_fill(mask, float("-inf")))


# ---- section 3: a model is a class (the NumPy TinyMLP from the page) ----
class TinyMLP:
    def __init__(self):
        self.W1 = np.array([[1.0, -1.0], [0.5, 2.0]])
        self.b1 = np.array([0.0, 1.0])
        self.W2 = np.array([[1.0], [-1.0]])
        self.b2 = np.array([0.5])

    def forward(self, x):
        h = np.tanh(x @ self.W1 + self.b1)
        return h @ self.W2 + self.b2

    def __call__(self, x):
        return self.forward(x)


tiny = TinyMLP()
print("\nTinyMLP([1, 0]) =", tiny(np.array([[1.0, 0.0]])).ravel(), "  TinyMLP([0, 0]) =", tiny(np.array([[0.0, 0.0]])).ravel())

# a plain Python list hides its blocks from parameters(); nn.ModuleList does not
class WithList(nn.Module):
    def __init__(self):
        super().__init__()
        self.blocks = [nn.Linear(4, 4) for _ in range(3)]


class WithModuleList(nn.Module):
    def __init__(self):
        super().__init__()
        self.blocks = nn.ModuleList([nn.Linear(4, 4) for _ in range(3)])


print("parameters seen with a plain list:", sum(p.numel() for p in WithList().parameters()),
      "  with nn.ModuleList:", sum(p.numel() for p in WithModuleList().parameters()))

# ---- section 8: first_run.py ----
torch.manual_seed(0)
Xf = torch.tensor([[0., 0.], [0., 1.], [1., 0.], [1., 1.]])
yf = torch.tensor([[0.], [1.], [1.], [0.]])
first = nn.Sequential(nn.Linear(2, 6), nn.Tanh(), nn.Linear(6, 1))
optf = torch.optim.SGD(first.parameters(), lr=0.5)
for _ in range(100):
    lossf = F.binary_cross_entropy_with_logits(first(Xf), yf)
    optf.zero_grad()
    lossf.backward()
    optf.step()
print("first_run.py prints:", round(lossf.item(), 3))


# ---- section 9: the loop, by yourself ----
class P:
    def __init__(self, v):
        self.data = float(v)
        self.grad = 0.0


def run_loop(epochs, lr=0.05):
    w, b = P(0.0), P(0.0)
    for _ in range(epochs):
        for x, y in [(1.0, 3.0), (2.0, 5.0)]:
            w.grad = b.grad = 0.0                       # zero_grad
            dz = 2 * (w.data * x + b.data - y)          # backward adds
            w.grad += dz * x
            b.grad += dz
            w.data -= lr * w.grad                       # step
            b.data -= lr * b.grad
    return round(w.data, 6), round(b.data, 6)


print("loop: 1 epoch", run_loop(1), " 2 epochs", run_loop(2), " 500 epochs", run_loop(500))
