"""
Level 20 · Inference cost: memory and speed

Run:  python demo.py      (needs numpy)

How much GPU memory a model needs while it writes (the KV cache), how much arithmetic one token costs (FLOPs),
how fast it can write when every weight must be read from memory once per step (decode),
and how long reading the whole prompt in one pass takes (prefill).
Every number on the page is printed here.
"""
import numpy as np

KiB, GiB = 1024, 1024 ** 3

# ---------------------------------------------------------------------------
# 1. The KV cache: K and V of every earlier token, in every layer and every K/V head
# ---------------------------------------------------------------------------
print("=== 1. KV cache ===")


def kv_bytes_per_token(n_kv_heads, d_k, n_layers, bytes_per_number=2):
    return 2 * n_kv_heads * d_k * n_layers * bytes_per_number   # 2 = one K and one V


b = kv_bytes_per_token(32, 128, 32)
print(f"32 K/V heads (one per query head), d_k 128, 32 layers, 2 bytes: 2 × 32 × 128 × 32 × 2 = {b:,} bytes = {b // KiB} KiB per token")
print(f"a 4,000-token conversation: {b * 4000:,} bytes = {b * 4000 / GiB:.2f} GiB")

# ---------------------------------------------------------------------------
# 2. Grouped-query attention: query heads share K/V heads
# ---------------------------------------------------------------------------
print("\n=== 2. grouped-query attention ===")
for n_kv in (32, 8, 1):
    b = kv_bytes_per_token(n_kv, 128, 32)
    print(f"32 query heads, {n_kv:2d} K/V heads, d_k 128, 32 layers, 2 bytes: {b:,} bytes = {b // KiB} KiB per token")
for n_kv in (8, 32):
    print(f"4,000-token conversation with {n_kv} K/V heads: {kv_bytes_per_token(n_kv, 128, 32) * 4000 / GiB:.2f} GiB")
n_q, n_kv = 32, 8
print(f"{n_q} query heads, {n_kv} K/V heads: each K/V head serves {n_q // n_kv} query heads;",
      "query head 13 uses K/V head", 13 // (n_q // n_kv))
print("lab: 8 query heads, d_k 64, 4 layers:", {kv: kv_bytes_per_token(kv, 64, 4) for kv in (8, 4, 2, 1)}, "bytes")

per_tok = kv_bytes_per_token(4, 128, 32)
free = (24 - 16) * GiB
print(f"GPU 24 GiB, weights 16 GiB, 4 K/V heads: {per_tok // KiB} KiB per token, "
      f"{free // KiB:,} KiB free → {free // per_tok:,} tokens; 16 users → {free // per_tok // 16:,} tokens each")

# ---------------------------------------------------------------------------
# 3. FLOPs per token: 2N for the weights, plus attention over the context
# ---------------------------------------------------------------------------
print("\n=== 3. FLOPs per token ===")
a_, b_ = 3, 4
x = np.ones((1, a_)); W = np.ones((a_, b_))
print(f"(1, {a_}) @ ({a_}, {b_}): {b_} outputs, each {a_} multiplies and {a_} adds → 2 × {a_} × {b_} = {2 * a_ * b_} FLOPs; result shape {(x @ W).shape}")

N = 7e9
print(f"7 billion weights: 2N = {2 * N:.2e} FLOPs per token; at 1e14 FLOP/s → 10¹⁴ / (1.4 × 10¹⁰) = 10⁴ / 1.4 = {1e14 / (2 * N):,.0f} tokens/s (arithmetic only)")
print(f"  (one FLOP per weight would give {1e14 / N:,.0f}; the 6N training rule would give {1e14 / (6 * N):,.0f})")


def block_flops(d, d_ff, L):
    weights = 4 * d * d + 2 * d * d_ff      # W_Q, W_K, W_V, W_O, then the FFN's two matrices
    w_part = 2 * weights                    # one multiply and one add per weight
    attn_part = 2 * L * d + 2 * L * d       # q·k for L keys, then the weighted sum of L values (all heads together)
    return weights, w_part, attn_part


d, d_ff, L = 64, 256, 128
w, wp, ap = block_flops(d, d_ff, L)
print(f"one block, d_model {d}, d_ff {d_ff}, context L {L}:")
print(f"  weights: 4 × {d}² + 2 × {d} × {d_ff} = {4 * d * d:,} + {2 * d * d_ff:,} = {w:,}")
print(f"  weights part: 2 × {w:,} = {wp:,} FLOPs")
print(f"  attention part: 2 × {L} × {d} (scores) + 2 × {L} × {d} (values) = {ap:,} FLOPs")
print(f"  total {wp + ap:,} FLOPs per token")
L_even = (wp) // (4 * d)
print(f"attention part = weights part when 4 × L × {d} = {wp:,} → L = {L_even}  (= 2 × d_model + d_ff = {2 * d + d_ff})")
for L2 in (128, 384, 1280):
    w2, wp2, ap2 = block_flops(d, d_ff, L2)
    print(f"  L = {L2:5d}: weights part {wp2:,}, attention part {ap2:,}, total {wp2 + ap2:,}")

N_gpt = 102_415                 # level 21's reference GPT
print(f"level 21 GPT: {N_gpt:,} weights → about {2 * N_gpt:,} FLOPs per token forward, "
      f"{6 * N_gpt * 8500 * 10:.2e} FLOPs to train one epoch (8,500 problems × 10 tokens × 6N)")

# ---------------------------------------------------------------------------
# 4. Decode speed: every weight is read from memory once per step
#    Speeds are quoted in decimal units: 1 GB = 10⁹ bytes (memory above was in GiB = 1,024³ bytes)
# ---------------------------------------------------------------------------
print("\n=== 4. decode speed ===")
GB = 1e9
bandwidth = 1e12                # bytes per second (1,000 GB/s)
flops_s = 1e14                  # FLOPs per second
w_bytes = N * 2
t_read = w_bytes / bandwidth
t_math = 2 * N / flops_s
print(f"1 GB = 10⁹ bytes; 1 GiB = {GiB:,} bytes ≈ {GiB / GB:.2f} GB")
print(f"weights: 7e9 × 2 bytes = {w_bytes:.2e} bytes = {w_bytes / GB:.0f} GB; read time {t_read * 1000:.1f} ms per step → at most {1 / t_read:.1f} tokens/s for one user")
print(f"arithmetic for one token: {t_math * 1000:.2f} ms → read time is {t_read / t_math:.0f}× the arithmetic time")
B_even = t_read / t_math
print(f"batch of B users: one read ({t_read * 1000:.0f} ms) and B × {t_math * 1000:.2f} ms of arithmetic; equal at B = {B_even:.0f}")
for B in (1, 16, 100, 256):
    step = max(t_read, B * t_math)
    print(f"  B = {B:3d}: step {step * 1000:6.2f} ms, {B / step:8,.0f} tokens/s in total, {1 / step:5.1f} per user")

users, toks = 8, 4000
kv_tok = kv_bytes_per_token(8, 128, 32)
kv_all = users * toks * kv_tok
step = (w_bytes + kv_all) / bandwidth
print(f"{users} users × {toks:,} tokens × 128 KiB = {users * toks * 128:,} KiB = {kv_all:,} bytes ≈ {kv_all / GB:.1f} GB of cache")
print(f"  a step reads {w_bytes / GB:.0f} + {kv_all / GB:.1f} ≈ {(w_bytes + kv_all) / GB:.1f} GB → {step * 1000:.1f} ms → {1 / step:.0f} tokens/s per user")

# how many users fit on an 80 GB GPU with 4,000 tokens each (the memory limit drawn in the lab)
mem = 80 * GB
one_cache = toks * kv_tok
fit = int((mem - w_bytes) // one_cache)
step_fit = (w_bytes + fit * one_cache) / bandwidth
print(f"80 GB GPU: ({mem / GB:.0f} − {w_bytes / GB:.0f}) GB / {one_cache / GB:.3f} GB per user = {(mem - w_bytes) / one_cache:.2f} → {fit} users fit")
print(f"  a step reads {w_bytes / GB:.0f} + {fit} × {one_cache / GB:.3f} ≈ {(w_bytes + fit * one_cache) / GB:.1f} GB → {step_fit * 1000:.1f} ms; "
      f"{1 / step_fit:.1f} tokens/s per user, {fit / step_fit:,.0f} in total; arithmetic only {fit * t_math * 1000:.1f} ms")

# 1 byte per weight: the read halves, the arithmetic doesn't, so the crossover halves too
t_read1 = N * 1 / bandwidth
print(f"1 byte per weight: read {t_read1 * 1000:.0f} ms, arithmetic {t_math * 1000:.2f} ms per user → equal at B = {t_read1 / t_math:.0f}")
print(f"  in general B = bytes × FLOPs/s / (2 × bandwidth) = 1 × 1e14 / (2 × 1e12) = {1 * flops_s / (2 * bandwidth):.0f}: N cancels")

# the crossover lab: read time = (weights + B caches) / bandwidth, arithmetic = B × 2N / FLOPs per second
print("crossover lab (8 K/V heads, d_k 128, 32 layers; context per user 0, 500 or 4,000 tokens):")
for ctx in (0, 500, 4000):
    t_cache = ctx * kv_tok / bandwidth            # reading one user's cache, seconds
    gap = t_math - t_cache
    meet = f"lines meet at B = {t_read / gap:.0f}" if gap > 0 else "lines never meet: reading is always the limit"
    print(f"  context {ctx:5,d}: one user's cache read {t_cache * 1000:.3f} ms per step; {meet}")
    for B in (1, 100, 256):
        r, m = t_read + B * t_cache, B * t_math
        print(f"    B = {B:3d}: read {r * 1000:6.2f} ms, arithmetic {m * 1000:6.2f} ms → step {max(r, m) * 1000:6.2f} ms")

# ---------------------------------------------------------------------------
# 5. Prefill: the whole prompt goes through in one pass
# ---------------------------------------------------------------------------
print("\n=== 5. prefill ===")
L_prompt = 2000
t_pf_math = L_prompt * 2 * N / flops_s
print(f"prompt of {L_prompt:,} tokens: read {t_read * 1000:.0f} ms once; arithmetic {L_prompt:,} × {2 * N:.1e} / 1e14 = {t_pf_math * 1000:.0f} ms "
      f"→ the pass takes {max(t_read, t_pf_math) * 1000:.0f} ms (arithmetic decides)")
print("  a prompt is like a batch of 2,000 users for one step: the first new token waits for arithmetic")
print(f"  token by token it would take {L_prompt:,} × {t_read * 1000:.0f} ms = {L_prompt * t_read:.0f} s")
L_short = 50
t_ps_math = L_short * 2 * N / flops_s
print(f"prompt of {L_short} tokens: read {t_read * 1000:.0f} ms, arithmetic {t_ps_math * 1000:.0f} ms "
      f"→ the pass takes {max(t_read, t_ps_math) * 1000:.0f} ms (reading decides: {L_short} is below the crossover of {B_even:.0f})")


def serve(n_weights, kv_heads, d_k, layers, tokens, B, bandwidth, flops, bytes_per=2):
    weights = n_weights * bytes_per                          # bytes of weights, read once per step
    kv = 2 * kv_heads * d_k * layers * bytes_per * tokens    # one user's cache, in bytes
    read = (weights + B * kv) / bandwidth                    # each user's cache is read for that user alone
    math = B * 2 * n_weights / flops                         # 2N FLOPs for each of the B tokens
    step = max(read, math)
    return step * 1000, 1 / step, B / step                  # ms per step, tokens/s per user, in total


for args in ((7e9, 8, 128, 32, 0, 1, 1e12, 1e14), (7e9, 8, 128, 32, 0, 1, 1e12, 1e14, 1),
             (7e9, 8, 128, 32, 0, 100, 1e12, 1e14), (7e9, 8, 128, 32, 0, 256, 1e12, 1e14),
             (7e9, 8, 128, 32, 0, 256, 1e12, 1e14, 1), (7e9, 8, 128, 32, 0, 8, 1e12, 1e14),
             (7e9, 8, 128, 32, 4000, 8, 1e12, 1e14), (7e9, 8, 128, 32, 4000, 8, 1e12, 1e14, 1)):
    ms, per, tot = serve(*args)
    shown = ", ".join(f"{a:g}" for a in args)
    print(f"serve({shown}) = ({ms:.2f} ms, {per:.2f} per user, {tot:,.2f} in total)")
