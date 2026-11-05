/**
 * Chinese for the text in site/public/data/<level>/microscope.json (written by each level's trace.py), keyed by the
 * English string. MicroscopeLab applies it on Chinese pages. A string that trace.py changes later shows in English
 * until it gets an entry here. Tensor names that are code (x, Q, ids, logits, src, tgt_in) stay as they are.
 */
export const MICROSCOPE_ZH: Record<string, string> = {
  // ---- encoder-decoder (N7)
  'In the page model the batch (64) and d_model (64) are the same number. To know which is which, look at the position: the batch is always the first axis.':
    '在页面上的这个模型里，batch（64）和 d_model（64）恰好是同一个数。要分清哪个是哪个，看位置：batch 永远是第一个轴。',
  'Token ids': 'Token id',
  'The digits and the words become ids. The decoder input starts with <bos>.': '数字和单词都变成 id。解码器的输入以 <bos> 开头。',
  'Look up the embeddings': '查嵌入表',
  'Each id picks one row of the embedding table: 6 numbers per digit.': '每个 id 从嵌入表里取出一行：每个数字 6 个数。',
  'embedding': '嵌入',
  'Scale by √d_model': '乘以 √d_model',
  'Multiply by √6 ≈ 2.45. The table started with numbers of size about 1/√6, so the scaled rows are about as long as the position rows in the next step. Here the token rows are 3.2 and 2.3 long, and each position row 1.7. Neither one is much bigger than the other.':
    '乘以 √6 ≈ 2.45。嵌入表里的数一开始大约是 1/√6 这么大，所以缩放后的行和下一步的位置行差不多长。这里 token 行的长度是 3.2 和 2.3，每个位置行是 1.7。两者谁也不比谁大很多。',
  'embedding × √d_model': '嵌入 × √d_model',
  'Add the positions': '加上位置',
  'Add row 0 of the position table to the first digit and row 1 to the second.': '把位置表的第 0 行加到第一个数字上，第 1 行加到第二个数字上。',
  'position rows': '位置行',
  'Encoder self-attention': '编码器自注意力',
  'Every digit scores every digit (Q and K both from the digits). No causal mask: the encoder may read the whole number. Here no PAD needs blocking.':
    '每个数字给每个数字打分（Q 和 K 都来自数字）。没有因果掩码：编码器可以读整个数。这里也没有 PAD 需要挡住。',
  'scores = Q Kᵀ / √d_k': '分数 = Q Kᵀ / √d_k',
  'The page model has 4 heads, so its scores have a head axis.': '页面上的模型有 4 个头，所以它的分数多一个头的轴。',
  'weights': '权重',
  'Add & norm, then the FFN': '相加并归一化，然后是 FFN',
  'Add x to the attention output, then LayerNorm 1 normalizes the sum. Then the FFN widens each digit to d_ff = 12 numbers, applies ReLU, and narrows it back to 6. Add and normalize again (LayerNorm 2). The result is the memory: one vector per digit, computed once.':
    '把 x 加到注意力的输出上，再用 LayerNorm 1 把和归一化。然后 FFN 把每个数字加宽到 d_ff = 12 个数，经过 ReLU，再收窄回 6 个。再相加、再归一化一次（LayerNorm 2）。结果就是 memory：每个数字一个向量，只算一次。',
  'FFN hidden (after ReLU)': 'FFN 隐藏层（ReLU 之后）',
  'Decoder input': '解码器输入',
  'The words go through the same three steps: look up, scale by √d_model, add positions.': '单词也走同样的三步：查表、乘以 √d_model、加上位置。',
  'Masked self-attention': '掩码自注意力',
  'Words score earlier words only. The causal mask is 3 × 3 because both Q and K come from the decoder input, which has 3 tokens. Blocked scores become −∞, and their weights 0.':
    '单词只给它前面的单词打分。因果掩码是 3 × 3，因为 Q 和 K 都来自解码器输入，而它有 3 个 token。被挡住的分数变成 −∞，它们的权重变成 0。',
  'scores (with the causal mask)': '分数（加了因果掩码）',
  'Cross-attention': '交叉注意力',
  'Q comes from the 3 words, K and V from the 2 digits in memory. So the scores are 3 × 2: for each word, how much weight it gives each digit. No causal mask: the whole number is known.':
    'Q 来自 3 个单词，K 和 V 来自 memory 里的 2 个数字。所以分数是 3 × 2：每个单词分给每个数字多少权重。没有因果掩码：整个数都已知。',
  'scores': '分数',
  'Add & norm, FFN': '相加并归一化，FFN',
  'The same residual, LayerNorm and FFN as in the encoder. This is the decoder output.': '和编码器里一样的残差、LayerNorm 和 FFN。这就是解码器的输出。',
  'decoder output': '解码器输出',
  'Output layer: logits': '输出层：logits',
  'One row of 32 scores per position. When the model writes, only the last row counts: its top word is the next word. When it trains, every row is compared with tgt_out.':
    '每个位置一行 32 个分数。模型写的时候，只有最后一行有用：分数最高的词就是下一个词。训练的时候，每一行都和 tgt_out 比较。',

  // ---- full-model (level 17)
  'The digits and “=” become ids. There is one sequence: the words will be written after “=”.': '数字和“=”变成 id。只有一个序列：单词会写在“=”后面。',
  'Token embedding': 'Token 嵌入',
  'Each id picks one row of the embedding table: 6 numbers per token.': '每个 id 从嵌入表里取出一行：每个 token 6 个数。',
  'Multiply by √6 ≈ 2.45. The table started with small numbers (about 1/√6), so after this step they are about the size of the position numbers.':
    '乘以 √6 ≈ 2.45。嵌入表里的数一开始很小（大约 1/√6），这一步之后，它们和位置的数差不多大。',
  'Add row t of the fixed sine/cosine table to position t. This is how the same digit at position 0 and at position 1 would differ.':
    '把固定的正弦/余弦表的第 t 行加到位置 t 上。同一个数字在位置 0 和位置 1，就是靠这个区分开的。',
  'LayerNorm 1 (pre-norm)': 'LayerNorm 1（pre-norm）',
  'Normalize each row before attention: mean 0, std 1, then a learned gain and shift (γ and β). x itself is kept for the residual.':
    '在注意力之前把每一行归一化：均值 0，标准差 1，再乘上学到的增益、加上偏移（γ 和 β）。x 本身留给残差。',
  'Q, K and V': 'Q、K 和 V',
  'Three matrices (6 × 6, no bias) turn each normalized row into a query, a key and a value.': '三个矩阵（6 × 6，没有偏置）把每个归一化后的行变成一个查询、一个键和一个值。',
  'The page model splits these 64 numbers into 4 heads of 16.': '页面上的模型把这 64 个数分成 4 个头，每个头 16 个。',
  'Scores, with the causal mask': '分数，加上因果掩码',
  'Each row scores every earlier position and itself: Q Kᵀ / √d_k. Later positions are blocked (−∞), so “8” sees only itself and “=” sees all three.':
    '每一行给它前面的每个位置和它自己打分：Q Kᵀ / √d_k。后面的位置被挡住（−∞），所以“8”只看到它自己，“=”能看到全部三个。',
  'Attention weights': '注意力权重',
  'Softmax along each row. Blocked scores get weight 0; every row sums to 1.': '对每一行做 softmax。被挡住的分数权重为 0；每一行加起来等于 1。',
  'Context': '上下文',
  'weights @ V: each row is a mix of the value rows it may see.': 'weights @ V：每一行是它能看到的那些值行的混合。',
  'context = weights @ V': '上下文 = weights @ V',
  'Output matrix W_O': '输出矩阵 W_O',
  'One more 6 × 6 matrix (with a bias). In the page model it also joins the 4 heads.': '再乘一个 6 × 6 的矩阵（带偏置）。在页面上的模型里，它同时把 4 个头合起来。',
  'attention output': '注意力输出',
  'Residual add': '残差相加',
  'x = x + attention output. The block adds to x; it never replaces it.': 'x = x + 注意力输出。这个块是往 x 上加东西，从不替换它。',
  'x after attention': '注意力之后的 x',
  'Normalize again, this time before the FFN.': '再归一化一次，这次在 FFN 之前。',
  'FFN hidden': 'FFN 隐藏层',
  'Each row on its own: widen to d_ff = 12 numbers, then ReLU sets the negative ones to 0.': '每一行各算各的：加宽到 d_ff = 12 个数，然后 ReLU 把负数变成 0。',
  'FFN output': 'FFN 输出',
  'Narrow back from 12 to 6 numbers per row.': '每一行从 12 个数收窄回 6 个。',
  'x = x + FFN output. This is the block’s output. The page model has a second block here.': 'x = x + FFN 输出。这就是这个块的输出。页面上的模型在这里还有第二个块。',
  "x = x + FFN output. This is the block's output. The page model has a second block here.": 'x = x + FFN 输出。这就是这个块的输出。页面上的模型在这里还有第二个块。',
  'block output': '块的输出',
  'Final LayerNorm': '最后的 LayerNorm',
  'One last LayerNorm after all the blocks, before the output layer.': '所有块之后、输出层之前，再做最后一次 LayerNorm。',
  'A 6 × 42 matrix plus a bias gives one row of 42 scores per position. Only the last row (after “=”) picks the next token. The rows for “8” and “9” guess the next digit, which the loss ignores.':
    '一个 6 × 42 的矩阵加上偏置，给每个位置一行 42 个分数。只有最后一行（“=”之后）决定下一个 token。“8”和“9”那两行在猜下一个数字，损失不管它们。',
  'Top tokens': '最可能的 token',
  'Softmax of the last row. The top token, “eighty”, is appended, and the model runs again on 4 tokens to write the next word.':
    '对最后一行做 softmax。最可能的 token “eighty” 被接到后面，模型再在 4 个 token 上跑一遍，写出下一个词。',
  'probabilities, last row': '概率，最后一行',

  // ---- write-a-gpt (level 21)
  'Five tokens: <bos>, 2, +, 3, =. Your model will see 10 tokens at a time (x of one padded problem).': '五个 token：<bos>、2、+、3、=。你的模型一次会看到 10 个 token（一道补齐后的题的 x）。',
  'Token and position embeddings': 'Token 嵌入和位置嵌入',
  'Each id picks a row of the token table, and position t picks row t of the learned position table. The two are added. (This GPT learns its positions, so it doesn’t scale by √d_model.)':
    '每个 id 从 token 表里取出一行，位置 t 从学到的位置表里取出第 t 行。两者相加。（这个 GPT 的位置是学出来的，所以不乘 √d_model。）',
  'token embedding': 'token 嵌入',
  'RMSNorm (pre-norm)': 'RMSNorm（pre-norm）',
  'Normalize what goes into the attention: divide each row by its root mean square, times the gain. The residual path keeps the un-normalized h.':
    '把要进入注意力的东西归一化：每一行除以它的均方根，再乘上增益。残差通路保留没归一化的 h。',
  'Q, split into heads': 'Q，分成多个头',
  'One Linear gives q, k and v. Then view + transpose: (B, L, d_model) → (B, h, L, d_k). Head 0 gets columns 0–2 of q, head 1 gets columns 3–5. Below: q, and head 0’s slice.':
    '一个 Linear 给出 q、k 和 v。然后 view + transpose：(B, L, d_model) → (B, h, L, d_k)。头 0 拿到 q 的第 0–2 列，头 1 拿到第 3–5 列。下面是 q，以及头 0 的那一片。',
  'q, head 0': 'q，头 0',
  'Shown: head 0 of example 0.': '显示的是样本 0 的头 0。',
  'Scores, causal mask, softmax': '分数、因果掩码、softmax',
  'Each head scores every position against every position: (L, L) = (5, 5). The causal mask blocks the positions after t (−∞), so “=” may look at all four tokens before it, and <bos> only at itself.':
    '每个头让每个位置给每个位置打分：(L, L) = (5, 5)。因果掩码挡住 t 之后的位置（−∞），所以“=”能看它前面全部四个 token，<bos> 只能看它自己。',
  'masked scores, head 0': '加了掩码的分数，头 0',
  'weights, head 0': '权重，头 0',
  'Join the heads, output Linear': '合并多个头，输出 Linear',
  'weights @ v gives (B, h, L, d_k). transpose + view join the heads back into (B, L, d_model): head 0’s 3 numbers, then head 1’s 3. The output Linear mixes them.':
    'weights @ v 得到 (B, h, L, d_k)。transpose + view 把多个头合回 (B, L, d_model)：先是头 0 的 3 个数，再是头 1 的 3 个。输出 Linear 把它们混合起来。',
  'joined heads': '合并后的头',
  'Add back, then the FFN': '加回去，然后是 FFN',
  'h = h + attention. Then pre-norm again: norm2, FFN (6 → 12 → 6), and add back.': 'h = h + 注意力。然后再做一次 pre-norm：norm2、FFN（6 → 12 → 6），再加回去。',
  'Final norm, output layer': '最后的归一化，输出层',
  'One more RMSNorm, then 15 scores per position. To write, only the last row (after “=”) counts: its top token is the next token.':
    '再做一次 RMSNorm，然后每个位置 15 个分数。写的时候，只有最后一行（“=”之后）有用：分数最高的 token 就是下一个 token。',
}
