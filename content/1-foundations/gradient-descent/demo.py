"""
Level 2 · Gradient descent

Run:  python demo.py      (needs numpy)

Fit a line y = w·x + b to three points by gradient descent, printing every number along the way.
"""
import numpy as np

x = np.array([1.0, 2.0, 3.0])
y = np.array([2.0, 4.0, 6.0])      # the answer is w = 2, b = 0
w, b = 0.5, 0.0                     # the starting guess
lr = 0.05


def loss_and_grads(w, b):
    pred = w * x + b
    error = pred - y
    loss = np.mean(error ** 2)
    grad_w = np.mean(2 * error * x)  # chain rule: 2·error (from the square) × x (from w·x)
    grad_b = np.mean(2 * error)      # chain rule: 2·error × 1
    return pred, error, loss, grad_w, grad_b


# --- step 1: measure the mistake ---------------------------------------------
pred, error, loss, grad_w, grad_b = loss_and_grads(w, b)
print(f"start: w = {w}, b = {b}")
print("prediction w*x + b  =", pred)
print("error  pred - y     =", error)
print("error²              =", error ** 2)
print(f"loss = mean(error²) = {loss}")

# --- step 2: the gradient ----------------------------------------------------
print("\n2·error·x per point =", 2 * error * x, " → grad_w =", grad_w)
print("2·error   per point =", 2 * error, "     → grad_b =", grad_b)

# --- step 3: one step --------------------------------------------------------
new_w = w - lr * grad_w
new_b = b - lr * grad_b
print(f"\nlr = {lr}")
print(f"w ← {w} − {lr} × ({grad_w}) = {new_w:.4f}")
print(f"b ← {b} − {lr} × ({grad_b}) = {new_b:.4f}")
print(f"loss after one step = {loss_and_grads(new_w, new_b)[2]:.4f}")

# --- too large a learning rate -----------------------------------------------
big = 0.2
bw, bb = w - big * grad_w, b - big * grad_b
print(f"\nwith lr = {big}: w = {bw:.4f}, b = {bb:.4f}, loss = {loss_and_grads(bw, bb)[2]:.4f}  (it went UP)")
for k in range(5):
    *_, l, gw, gb = loss_and_grads(bw, bb)
    bw, bb = bw - big * gw, bb - big * gb
    print(f"  step {k + 2}: loss = {loss_and_grads(bw, bb)[2]:.2f}")

# --- many steps --------------------------------------------------------------
print("\ntraining with lr = 0.05:")
for step in range(1, 1001):
    *_, loss, grad_w, grad_b = loss_and_grads(w, b)
    w, b = w - lr * grad_w, b - lr * grad_b
    if step in (1, 2, 3, 10, 100, 300, 1000):
        print(f"  after step {step:3d}: w = {w:.4f}, b = {b:.4f}, loss = {loss_and_grads(w, b)[2]:.6f}")
print(f"\nw settles at {w:.2f}, b at {b:.2f}")

# --- different data, same method ------------------------------------------------
y2 = np.array([3.0, 5.0, 7.0])     # every point moved up by 1
w2, b2 = 0.5, 0.0
for _ in range(5000):
    e = w2 * x + b2 - y2
    w2, b2 = w2 - lr * np.mean(2 * e * x), b2 - lr * np.mean(2 * e)
print(f"\nwith y = {y2}: w settles at {w2:.2f}, b at {b2:.2f}")
