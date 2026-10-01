"""
Level U5 · the boss, local part: a training script with four bugs.

Copy this file to my_train.py, find and fix every bug, then run
    python check.py my_train.py
It passes only when all four bugs are fixed and the model learns. Each check reports what it measured, not where
the bug is: finding the cause is the exercise.

The task: points (x1, x2) in the square from -1 to 1. Class 1 = inside the circle x1² + x2² < 0.5, class 0 = outside.
A small MLP should get at least 95% of the held-out points right.

Each function says what it should do. The code does not always do that. Change only what is wrong.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


def make_data(n=1000, seed=0):
    """Correct, don't change: n random points and their classes (0 or 1)."""
    g = torch.Generator().manual_seed(seed)
    X = torch.rand(n, 2, generator=g) * 2 - 1
    y = (X[:, 0] ** 2 + X[:, 1] ** 2 < 0.5).long()
    return X, y


def split(X, y):
    """The first 80% of the points to train on, the other 20% held out."""
    n = len(X)
    cut = int(0.8 * n)
    train = (X[:cut], y[:cut])
    held = (X[: n - cut], y[: n - cut])
    return train, held


def batches(X, y, batch_size, gen):
    """One epoch of batches: every point once, in a new random order."""
    px = torch.randperm(len(X), generator=gen)
    py = torch.randperm(len(y), generator=gen)
    for i in range(0, len(X), batch_size):
        yield X[px[i:i + batch_size]], y[py[i:i + batch_size]]


class MLP(nn.Module):
    """2 inputs → 32 hidden (ReLU) → 2 outputs, one score per class."""
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(2, 32), nn.ReLU(), nn.Linear(32, 2))

    def forward(self, x):
        return torch.softmax(self.net(x), dim=-1)


def train_step(model, opt, xb, yb):
    """One training step on one batch. Returns the loss."""
    loss = F.cross_entropy(model(xb), yb)
    loss.backward()
    opt.step()
    return loss.item()


def accuracy(model, X, y):
    with torch.no_grad():
        return (model(X).argmax(dim=-1) == y).float().mean().item()


def train(seed=0, epochs=40):
    """Correct, don't change: trains and returns the model and the held-out set."""
    torch.manual_seed(seed)
    X, y = make_data(seed=seed)
    (Xt, yt), (Xh, yh) = split(X, y)
    model = MLP()
    opt = torch.optim.Adam(model.parameters(), lr=0.01)
    gen = torch.Generator().manual_seed(seed)
    for epoch in range(epochs):
        losses = [train_step(model, opt, xb, yb) for xb, yb in batches(Xt, yt, 32, gen)]
        if epoch % 10 == 0 or epoch == epochs - 1:
            print(f"epoch {epoch:2d}  loss {sum(losses) / len(losses):.3f}  held-out accuracy {accuracy(model, Xh, yh):.3f}")
    return model, (Xh, yh)


if __name__ == "__main__":
    train()
