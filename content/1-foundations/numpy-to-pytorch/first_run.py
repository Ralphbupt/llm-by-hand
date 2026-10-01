import torch, torch.nn as nn, torch.nn.functional as F
torch.manual_seed(0)
X = torch.tensor([[0., 0.], [0., 1.], [1., 0.], [1., 1.]])
y = torch.tensor([[0.], [1.], [1.], [0.]])
model = nn.Sequential(nn.Linear(2, 6), nn.Tanh(), nn.Linear(6, 1))
opt = torch.optim.SGD(model.parameters(), lr=0.5)
for step in range(100):
    loss = F.binary_cross_entropy_with_logits(model(X), y)
    opt.zero_grad()
    loss.backward()
    opt.step()
print(round(loss.item(), 3))
