# 中文翻译指南

English is the source language. This file is for whoever translates the course into Chinese (people or models).
Everything below is written in Chinese, because that is the language the rules are about.

## 文件放在哪里

| 英文原文 | 中文译文 | 内容 |
| --- | --- | --- |
| `content/<part>/<slug>/lesson.en.mdx` | `lesson.zh.mdx`（同一目录） | 正文。frontmatter 里只放 `recap`（和需要时的 `glossarySkip`），其余字段都从英文版读 |
| `content/<part>/<slug>/exercises.yaml` | `exercises.zh.yaml`（同一目录） | 只放题目的文字，见下文“题目文件” |
| 各关 frontmatter 的 `title` / `short` / `question` / `boss` | `content/levels.zh.yaml` | 每一关都有，没翻译正文的关也有，侧栏和地图要用 |
| `content/glossary.yaml` | `content/glossary.zh.yaml` | 以英文术语为键：`term`、`aliases`、`def` |
| 组件里的界面文字 | `site/src/i18n/zh.ts`，或组件自己的 `ZH` 表 | 以英文原句为键 |

翻完一关后运行 `.venv/bin/python scripts/check_zh.py <slug>`，它检查组件、代码、公式和题目结构是否和英文一致。
实验台（`site/src/components/viz/*.svelte`）的文字在组件里用 `useT({ 英文: 中文 })` 翻译；正文里提到按钮名时，要和实验台上的中文一致。

某一关没有 `lesson.zh.mdx` 时，`/zh/learn/<slug>/` 仍然存在：导航是中文，正文显示英文原文，并告诉读者这一关还在翻译。
所以可以一关一关地翻，随时上线。

## 文风

- 和英文版一样：短句，直接对读者说“你”，一次只讲一件事。不要写成教科书腔，也不要写成营销腔。
- 是翻译，不是改写。英文版的每个例子、每个数字、每个步骤都要保留，顺序不变。不要加英文版没有的内容，也不要删。
- 意思准确优先于字面对应。英文的长句可以拆开，被动句改成主动句。
- 用简体中文和中文标点：，。：；？！“”（）。但在代码、公式、形状 `(3, 4)`、向量 `[1, 2]` 里保持原样。
- 中文和英文单词、数字之间加一个空格：“第 3 关”、“用 NumPy 写”、“形状是 (2, 3)”。中文标点前后不加空格。
- 引用其他关：“第 12 关”、“支线 U3”。
- 术语第一次出现时可以在括号里附英文：**矩阵**（matrix）。之后只用中文。下表里写“保留英文”的直接用英文。
- `**粗体**`、`*斜体*`、`行内代码`、链接、`$公式$`、`$$公式$$` 的位置和英文版对应。公式和代码一个字都不改（代码注释可以翻成中文）。

## MDX 正文

- 站内链接照英文写（`/learn/x/`、`/glossary/`）：构建时会自动指向中文页面。

- 原样保留：`import` 行、所有组件标签和它们的属性（`id`、`hide={{…}}`、`requires` 等）、代码块里的代码、公式。
- 要翻译的组件属性：`<Deeper title="…">`、`<Stuck q="…">`、`<TryIt title="…">` 里给人看的文字。
- 标题保留编号：`## 1. 一次算一格`。
- 每个 `<Gate>`、`<Deeper>` 等组件的开闭标签前后保留空行，和英文版一致（MDX 需要）。
- frontmatter 只写：

```yaml
---
recap:
  can: [...]
  keys: [...]
  mistakes: [...]
---
```

## 题目文件 `exercises.zh.yaml`

键和 `exercises.yaml` 一样，每题只写文字字段；答案、测试、提示的触发条件都留在英文文件里，不要复制过来。

```yaml
c-0-1:
  prompt: "A = [[1, 2, 3], [0, 1, 0]]，B = [[1, 0], [0, 1], [1, 1]]。C[0][1] 是多少？"
  after: "A 的第 0 行是 [1, 2, 3]，B 的第 1 列是 [0, 1, 1]。1×0 + 2×1 + 3×1 = 5。"
  hints:                     # 每条提示的 say，按英文文件里的顺序一一对应
    - "4 是 C[0][0]，用的是 B 的第 0 列。第 1 列是 [0, 1, 1]。"
    - ["第一次答错时的提示", "第二次", "第三次"]   # 英文是列表（提示阶梯）时，这里也是同样长度的列表
same-shape:
  prompt: "…"
  options: ["…", "…", "…"]   # 选项，顺序和英文一致（答案按位置判定）
  reveal: "…"
matmul-loop:
  prompt: "…"
  template: |                # 可选：代码模板，只能改注释，代码和 ____ 的位置不变
    …
  tests: ["应该是 [[4, 5], [0, 1]]", "1×3 + 2×4 = 11", "…"]   # 每条测试的 say，按顺序
```

- 可以翻的字段：`prompt`、`promptShort`、`after`、`reveal`、`unit`、`options`、`hints`、`tests`、`template`（只改注释）。
- `hints` 的条数必须和英文一样；英文某条 `say` 是阶梯列表时，中文也给同样长度的列表。不想翻的一条写 `null`。
- 提示里不能直接给出答案（英文版本来就没有），翻译时也不要“顺手”说出答案。

## 术语表

### 课程界面

| 英文 | 中文 |
| --- | --- |
| level | 关（第 3 关） |
| main line / main level | 主线 / 主线关卡 |
| side trip | 支线 |
| boss level | Boss 关 |
| Foundations / Theory / Engineering | 基础 / 原理 / 工程 |
| Classic networks / Under the hood / Diffusion | 经典网络 / 深入底层 / 扩散模型 |
| lab | 实验台 |
| Predict | 先猜一猜 |
| hint | 提示 |
| Show answer | 显示答案 |
| Skip for now | 先跳过 |
| Go deeper | 深入一点 |
| I got stuck here | 我卡在这里了 |
| Try it | 动手试试 |
| Recap | 小结 |
| Warm-up | 热身 |
| test out | 小测跳关 |
| reading mode | 阅读模式 |
| Mistakes (the mistake book) | 错题本 |
| cleared | 通关 |
| star | 星 |

### 概念

| 英文 | 中文 | 英文 | 中文 |
| --- | --- | --- | --- |
| matrix | 矩阵 | shape | 形状 |
| matrix multiplication | 矩阵乘法 | transpose | 转置 |
| broadcasting | 广播 | batch | 批（batch） |
| axis | 轴 | element-wise | 逐元素 |
| dot product | 点积 | vector | 向量 |
| tensor | 张量 | dimension | 维度 |
| loss | 损失 | gradient | 梯度 |
| gradient descent | 梯度下降 | learning rate | 学习率 |
| step (of training) | 一步 | slope | 斜率 |
| derivative | 导数 | partial derivative | 偏导数 |
| neuron | 神经元 | weight | 权重 |
| bias | 偏置 | activation function | 激活函数 |
| activation (a value) | 激活值 | decision boundary | 决策边界 |
| binary cross-entropy | 二元交叉熵 | cross-entropy | 交叉熵 |
| entropy | 熵 | perplexity | 困惑度 |
| classification | 分类 | label | 标签 |
| probability | 概率 | logit / logits | 保留英文 logit |
| sigmoid / tanh / ReLU / GELU / softmax | 保留英文 | saturation | 饱和 |
| dead ReLU | 死 ReLU | vanishing / exploding gradient | 梯度消失 / 梯度爆炸 |
| layer | 层 | hidden layer | 隐藏层 |
| hidden unit | 隐藏单元 | MLP | 多层感知机（MLP） |
| parameter | 参数 | forward pass | 前向传播 |
| backpropagation | 反向传播 | chain rule | 链式法则 |
| gradient check | 梯度检验 | autograd | 自动求导（autograd） |
| computation graph | 计算图 | optimizer | 优化器 |
| momentum | 动量 | Adam / AdamW | 保留英文 |
| running average | 滑动平均 | initialization | 初始化 |
| fan-in | 扇入 | learning-rate schedule | 学习率调度 |
| warmup | 预热 | decay | 衰减 |
| overfitting | 过拟合 | generalization | 泛化 |
| regularization | 正则化 | held-out set | 留出集 |
| training set / test set | 训练集 / 测试集 | weight decay | 权重衰减 |
| dropout | 保留英文 dropout | early stopping | 早停 |
| capacity | 容量 | epoch | 轮（epoch） |
| temperature | 温度 | sampling | 采样 |
| Gaussian | 高斯分布 | variance / standard deviation | 方差 / 标准差 |
| mean squared error | 均方误差 | language model | 语言模型 |
| bigram | 二元模型（bigram） | token | 保留英文 token |
| tokenizer | 分词器 | vocabulary | 词表 |
| context window | 上下文窗口 | BPE | 保留英文 BPE |
| embedding | 嵌入（embedding） | one-hot | 独热（one-hot） |
| cosine similarity | 余弦相似度 | attention | 注意力 |
| self-attention | 自注意力 | query / key / value | 查询 / 键 / 值（Q / K / V） |
| mask | 掩码 | causal mask | 因果掩码 |
| multi-head attention | 多头注意力 | head | 头 |
| positional encoding | 位置编码 | feed-forward network | 前馈网络 |
| residual connection | 残差连接 | LayerNorm / RMSNorm | 保留英文 |
| normalization | 归一化 | pre-norm / post-norm | 保留英文 |
| encoder / decoder | 编码器 / 解码器 | cross-attention | 交叉注意力 |
| decoder-only | 仅解码器（decoder-only） | prompt | 提示词 |
| greedy decoding | 贪心解码 | beam search | 束搜索 |
| top-k / top-p | 保留英文 | repetition penalty | 重复惩罚 |
| label smoothing | 标签平滑 | inference | 推理 |
| KV cache | KV 缓存 | prefill / decode | 预填充 / 解码 |
| FLOPs | 保留英文 | memory bandwidth | 显存带宽 |
| convolution | 卷积 | filter / kernel | 卷积核 |
| stride (convolution) | 步幅 | stride (memory) | 步长 |
| padding | 填充 | receptive field | 感受野 |
| pooling | 池化 | feature map | 特征图 |
| channel | 通道 | RNN / LSTM / GRU | 保留英文 |
| hidden state | 隐藏状态 | cell state | 细胞状态 |
| gate | 门 | forget / input / output gate | 遗忘门 / 输入门 / 输出门 |
| backpropagation through time | 随时间反向传播（BPTT） | teacher forcing | 教师强制 |
| autoencoder | 自编码器 | VAE | 保留英文 VAE |
| latent | 潜变量 / 潜空间 | bottleneck | 瓶颈 |
| diffusion | 扩散 | noise schedule | 噪声调度 |
| guidance | 引导 | patch | 图块（patch） |
| mantissa / exponent | 尾数 / 指数 | overflow / underflow | 上溢 / 下溢 |
| mixed precision | 混合精度 | view / contiguous | 视图 / 连续 |
| seed | 随机种子 | data pipeline | 数据管道 |
| Jacobian | 雅可比矩阵 | plateau | 平台期 |

### 翻译第 1–3 关和术语表时补充的词

| 英文 | 中文 | 英文 | 中文 |
| --- | --- | --- | --- |
| line up (shapes) | 对得上 / 对不上 | stretch (broadcasting) | 拉伸 |
| inner / outer (sizes) | 内侧 / 外侧 | cell (of a matrix) | 格 |
| feature | 特征 | example (a row of data) | 样本 |
| batch size | 批大小 | mean | 均值 |
| error (prediction − truth) | 误差 | squared error | 平方误差 |
| prediction / target / truth | 预测值 / 目标值 / 真实值 | weighted sum | 加权和 |
| loss surface | 损失曲面 | minimum | 最低点 |
| steepness | 陡度 | natural logarithm | 自然对数 |
| training loop | 训练循环 | fit (a line) | 拟合 |
| attention scores | 注意力分数 | padding mask | 填充掩码 |
| padding (convolution) | 边缘填充 | exponent (of a float) | 指数位 |
| contiguous | 内存连续 | range (of a number format) | 表示范围 |
| memory (encoder output) | 保留英文 memory | concat | 拼接 |
| start / end token | 起始 token / 结束 token | decoder block | 解码器块 |
| residual path | 残差通路 | weight sharing | 权重共享 |
| context vector | 上下文向量 | KL divergence | KL 散度 |
| reparameterization trick | 重参数化技巧 | bidirectional RNN | 双向 RNN |
| word vector | 词向量 | topological order | 拓扑序 |
| update / reset gate | 更新门 / 重置门 | local gradient | 局部梯度 |
| numeric gradient | 数值梯度 | in place | 原地 |
| fused kernel | 融合算子 | recomputation | 重计算 |
| sublayer | 子层 | loss scaling | 损失缩放 |
| lab button “Map” | 平面图 | math page | 数学页 |

表里没有的词：先看 `content/glossary.zh.yaml` 有没有，再按业界最常见的中文说法，并在这里补一行。
