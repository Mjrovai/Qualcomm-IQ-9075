# MTP speculative decoding: IQ-9075 CPU and Jetson Orin Nano Super GPU

Multi-token prediction (MTP) against plain decoding, following the method of the Raspberry Pi 5 MTP chapter of *Edge AI Engineering*. Each row is one request.

## Method

- llama.cpp commit `338fce6` on both boards. The IQ-9075 uses a CPU build. The Jetson uses a CUDA build (arch 87).
- One `llama-server` per configuration, with `--parallel 1 --flash-attn on --reasoning off`.
  - Plain decoding uses `--spec-type none`.
  - MTP uses `--spec-type draft-mtp --spec-draft-n-max N --spec-draft-n-min 0`, plus `--model-draft <sidecar>` for the models that ship a separate MTP file.
- Requests go to `/completion` with the prompt "Explain photosynthesis in 300 words.", `n_predict` 256, `seed` 42, and `cache_prompt` false. Each configuration runs 3 times, with a 15 s pause between runs.
- `draft_n` 0 means plain decoding. Otherwise it is `--spec-draft-n-max`: the number of tokens drafted per step. The verify batch is `draft_n` + 1.
- `mean_accept_len` is the "mean len" that llama-server logs: tokens accepted per verify step, including the token from the main model.
- Same GGUF files on both boards, sha256-checked:
  - `Qwen3.5-4B-Q4_0.gguf` from unsloth, with the `mtp-Qwen3.5-4B-Q4_0.gguf` sidecar from ggml-org.
  - `gemma-4-E4B-it` and `gemma-4-E2B-it` Q4_0, each with its `mtp-*` sidecar, all from ggml-org.
  - `Qwen3.5-9B-Q4_0.gguf` from `unsloth/Qwen3.5-9B-MTP-GGUF`, saved as `Qwen3.5-9B-MTP-Q4_0.gguf`. Its MTP head is embedded, so it needs no sidecar. The plain-decoding rows use the same file.

## Files

- `iq9075-ubuntu-cpu-mtp-20261117-18.csv`
  - **Setup:** IQ-9075 EVK, Canonical Ubuntu 24.04.5 Desktop, kernel `6.8.0-1089-qcom`. 8 threads, `-ngl 0`, context 8192.
  - **2026-11-17:** four passes on Qwen3.5-4B and Gemma 4 E4B.
    - The `21:32`, `21:41`, and `22:15` passes ran with the `schedutil` governor.
    - The `23:25` pass ran with `performance`, all cores at 2.3616 GHz, and htop open on the desktop.
    - The governor did not change the results: the Qwen3.5-4B baseline was 9.34, 9.37, and 9.33 tok/s.
  - **2026-11-18:** Qwen3.5-9B and Gemma 4 E2B, with the `performance` governor.
  - **How these rows were recovered:** the four 2026-11-17 passes were printed to the terminal and not saved on the board. They were recovered from the session log. The times are UTC.
- `jetson-gpu-mtp-20261118.csv`
  - **Setup:** Jetson Orin Nano Super 8 GB, JetPack 6 (L4T R36.4.7), `MAXN_SUPER`. 6 threads, `-ngl 99`, `--load-mode dio`.
  - **First pass:** 7 of 16 configurations failed to load with `cudaMalloc failed: out of memory` (NvMap error 12). The previous server had not yet released its memory. The failed configurations are not in the file.
  - **Retry pass:** the failed configurations, with a 30 s pause between servers. Qwen3.5-9B ran at context 4096, plain decoding included. Every other configuration used context 8192. The 9B plain-decoding speed was the same at both sizes: 12.18 and 12.19 tok/s.

## Summary (mean of 3 runs, tok/s)

| Model | IQ-9075 plain | IQ-9075 best MTP | Jetson plain | Jetson best MTP |
| --- | --- | --- | --- | --- |
| Qwen3.5-9B | 6.33 | 9.02 (n=3, 1.42×) | 12.19 | 17.93 (n=3, 1.47×) |
| Qwen3.5-4B | 9.33 | 12.54 (n=3, 1.34×) | 17.28 | 28.87 (n=2, 1.67×) |
| Gemma 4 E4B | 8.22 | 9.33 (n=3, 1.14×) | 15.52 | 30.95 (n=3, 1.99×) |
| Gemma 4 E2B | 14.86 | 13.53 (n=3, 0.91×) | 28.04 | 40.70 (n=2, 1.45×) |

The IQ-9075 Qwen3.5-4B and Gemma 4 E4B rows use the `performance` pass at `23:25`.

On the IQ-9075 CPU, n = 3 (a verify batch of 4) was the best setting for every model. With n = 2 or n = 4, speed dropped close to plain decoding, or below it. On the Jetson GPU, the best setting was n = 2 or n = 3, depending on the model, and n = 4 was always slower than the best one.
