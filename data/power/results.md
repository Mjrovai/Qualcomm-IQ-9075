# IQ-9075 EVK: power measurements

Factory image (Qualcomm Linux 1.6), Wi-Fi only (no monitor, BT, or webcam).
Power measured at the board input: USB-C PD charger → FNIRSI FNB58 → 20 V PD trigger cable → barrel jack.
FNB58 logged at 100 samples/s on the Mac (`tools/fnb58/fnb58_log.py`); workloads launched over SSH by `tools/fnb58/power_bench.py`, which records start and end on the same clock.

Energy per inference = average power over the steady part of the run × mean latency from `benchmark_model`.
"Dynamic" subtracts the idle power; "total" does not.

## Idle

| Configuration | Power |
| --- | --- |
| Monitor (HDMI), BT mouse and keyboard, USB webcam, Wi-Fi | ~8.2 W (FNB58 display) |
| Wi-Fi only | 6.63 W (mean of three 30 s idle phases, logged) |

## Inception v3 quantized, batch 1, 40 s runs (2026-10-26, session-20261026-1312)

| Backend | Latency | Power | Above idle | Energy/inference (dynamic) | Energy/inference (total) | Inferences per joule (total) |
| --- | --- | --- | --- | --- | --- | --- |
| NPU (QNN HTP, perf mode 2) | 0.697 ms | 15.48 W | 8.85 W | 6.2 mJ | 10.8 mJ | ~93 |
| CPU (XNNPACK, 8 threads) | 13.98 ms | 12.77 W | 6.13 W | 85.8 mJ | 178.5 mJ | ~5.6 |

- The NPU draws more power than the CPU (15.5 W vs 12.8 W), but finishes each inference 20× faster, so it uses 14× less dynamic energy and 16.5× less total energy per inference.
- Power was flat during each run (NPU 15.5 W, CPU 12.7–13.0 W in 5 s buckets) and returned to idle within 5 s.
- Latencies match the 2026-10-14 tests (NPU 0.74 ms, CPU 14.0 ms).

## Ten factory models, NPU vs CPU, 30 s runs (2026-10-26, markers-20261026-models)

Same session log. 20 s idle between runs; each run's dynamic power subtracts the idle phase just before it (idle drifted from 6.63 W to 6.89 W as the board warmed). Sorted by latency speedup.

| Model | NPU ms | CPU ms | Speedup | NPU W | CPU W | NPU mJ (total) | CPU mJ (total) | Energy ratio (total) | NPU mJ (dyn) | CPU mJ (dyn) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| face_attrib_net | 0.496 | 53.59 | 108× | 15.0 | 9.7 | 7.5 | 521 | 70× | 4.2 | 164 |
| inception_v3 | 0.699 | 13.88 | 19.9× | 15.5 | 12.7 | 10.9 | 177 | 16.3× | 6.2 | 84 |
| hrnet_pose | 1.113 | 19.38 | 17.4× | 15.4 | 16.6 | 17.1 | 321 | 18.8× | 9.7 | 191 |
| midas | 1.174 | 19.23 | 16.4× | 14.1 | 14.5 | 16.6 | 278 | 16.8× | 8.7 | 148 |
| deeplabv3_plus_mobilenet | 5.150 | 61.79 | 12.0× | 13.9 | 18.8 | 71.6 | 1164 | 16.2× | 36.8 | 744 |
| yolox | 3.066 | 36.04 | 11.8× | 13.5 | 16.8 | 41.5 | 604 | 14.5× | 20.6 | 358 |
| face_det_lite | 0.528 | 4.64 | 8.8× | 11.9 | 16.4 | 6.3 | 76 | 12.1× | 2.7 | 44 |
| facemap_3dmm | 0.217 | 0.82 | 3.8× | 12.8 | 17.4 | 2.8 | 14.3 | 5.1× | 1.3 | 8.7 |
| yamnet (float) | 0.255 | 0.84 | 3.3× | 13.9 | 20.5 | 3.6 | 17.2 | 4.9× | 1.8 | 11.5 |
| quicksrnetsmall* | 3.711 | 3.137 | 0.85× | 9.7 | 12.5 | 35.8 | 39.1 | 1.09× | 10.9 | 18.0 |

\* Rerun in a new session (session-20261026-1441, markers-20261026-quicksrnet), after the FNB58 dropped off USB during the first battery. That rerun also repeated inception_v3 on the NPU as an anchor: 0.700 ms, 15.56 W, 10.89 mJ total, against 10.87 mJ in the first battery, so the two sessions agree within 0.2%. The partial first quicksrnetsmall NPU run (9.9 W, 37.0 mJ) also agrees.

GPU (TFLite GPU delegate) on inception_v3: 29.29 ms, 10.9 W, 318 mJ total (122 mJ dynamic), 1.8× more energy per inference than the CPU and 29× more than the NPU.

Observations:
- The NPU used 5× to 70× less total energy per inference than the CPU on the nine convolutional and audio models, and about the same on quicksrnetsmall.
- For most models the energy ratio is larger than the speedup, because the NPU run drew less power (12–15.5 W) than 8 CPU threads (16–20.5 W). The exceptions are face_attrib_net and inception_v3, where the CPU drew less.
- face_attrib_net on the CPU drew only 9.7 W, about 3 W above idle, far below other CPU runs. The CPU was mostly idle, which supports the earlier guess that XNNPACK runs some of its INT8 operators on slow, poorly parallelized kernels.
- Tiny models (facemap_3dmm, yamnet) still saved about 5× energy on the NPU, more than their 3–4× speedup.
- quicksrnetsmall is 18% slower on the NPU, but the NPU drew less power (9.7 W vs 12.5 W), so it still used 1.65× less dynamic energy and 9% less total energy per inference. Being slower on the accelerator did not make it the more expensive choice.

## LLMs with GenieX (2026-10-26, session-20261026-1441, markers-20261026-llm)

Same prompts as 2026-10-14: short = "Explique em três parágrafos o que é TinyML" (256 tokens generated); long = `/data/longo.txt` (1,087 words, ~2,000 tokens, ending with a one-sentence summary request). `--think=false --seed 42 --max-tokens 256`. 20 s idle before each run; dynamic power subtracts it (6.71–6.77 W).

The prefill and decode windows are reconstructed from the end of generation, which is stamped inside the container (board and Mac clocks agree within ~0.02 s), using the time to first token and the decode rate that GenieX reports. The 1 s power profiles confirm the alignment: for example, Qwen3-4B on the CPU with the long prompt shows ~2 s of model load, 30 s of prefill at ~17.2 W, then 2 s of decode at ~21 W.

### Decode (short prompt, 256 tokens)

| Model | Runtime, processor | tok/s | Decode power | Above idle | J/token (dynamic) | J/token (total) | Tokens per Wh (total) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen3-4B W4A16 | QAIRT, NPU | 17.9 | 14.0 W | 7.3 W | 0.41 | 0.78 | ~4,600 |
| Qwen3-4B Q4_0 | llama.cpp, CPU | 18.4 | 21.2 W | 14.5 W | 0.79 | 1.15 | ~3,100 |
| Qwen3.5-0.8B Q4_0 | llama.cpp, CPU | 58.0 | 20.1 W | 13.4 W | 0.23 | 0.35 | ~10,400 |
| Qwen3.5-0.8B Q4_0 | llama.cpp (Hexagon), NPU | 28.5 | 18.8 W | 12.1 W | 0.42 | 0.66 | ~5,400 |

### Prefill (long prompt, ~2,000 tokens)

| Model | Runtime, processor | Time to first token | Prefill power | Prefill energy (dynamic) | Prefill energy (total) |
| --- | --- | --- | --- | --- | --- |
| Qwen3-4B W4A16 | QAIRT, NPU | 1.7 s | 15.8 W | 15 J | 27 J |
| Qwen3-4B Q4_0 | llama.cpp, CPU | 30.7 s | 17.2 W | 322 J | 529 J |
| Qwen3.5-0.8B Q4_0 | llama.cpp (Hexagon), NPU | 1.6 s | 19.3 W | 20 J | 31 J |
| Qwen3.5-0.8B Q4_0 | llama.cpp, CPU | 5.1 s | 17.4 W | 54 J | 89 J |

Decode with the long context: Qwen3-4B NPU 15.5 tok/s, 0.91 J/token total; CPU 14.3 tok/s, 1.49 J/token. The 0.8B long-prompt answers (20–31 tokens) were too short for a decode window on the CPU.

Speeds match 2026-10-14 within 3% (for example, 4B CPU long prompt: 30.7 s vs 31.1 s to first token).

Observations:
- **4B decode: same speed, about two-thirds of the energy on the NPU.** CPU and NPU both generate ~18 tok/s, limited by memory bandwidth, but the CPU draws 21 W against 14 W, so the NPU uses 1.5× less total energy per token (1.9× less dynamic).
- **4B prefill: 20× less energy on the NPU.** The ~2,000-token prompt cost 27 J on the NPU against 529 J on the CPU. A full request (long prompt plus 256-token answer) comes to ~230 J on the NPU against ~820 J on the CPU, 3.6× less.
- **Decode on the CPU draws more power than prefill on the CPU** (21 W vs 17 W), although prefill is the compute-bound phase. Memory-bound decode keeps the DDR busy, and memory traffic costs power too.
- **0.8B: the CPU wins in decode on both speed and energy** (0.35 vs 0.66 J/token). The llama.cpp Hexagon backend draws almost as much as the CPU (18.8 W) while generating half as fast. For prefill, even this backend saves energy: 31 J against 89 J.
- The runtime matters for energy as much as for speed: on the NPU, QAIRT ran the 4B at 14 W, while llama.cpp's Hexagon backend needed 19 W for a model five times smaller.
