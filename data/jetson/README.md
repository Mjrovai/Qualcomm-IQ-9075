# Jetson Orin Nano Super, LLM prompts (Oct 27, 2026)

JetPack 6.2.1 (L4T 36.4.7), MAXN_SUPER, GUI running, page cache dropped before the 4B run.
llama.cpp commit 338fce6, CUDA, all layers on the GPU (`-ngl 99`), context 4096.
Same GGUF files as the IQ-9075 runs (sha256 checked) and the same prompts: short = "Explique em três parágrafos o que é TinyML", long = `longo.txt`. Seed 42, max 256 tokens, thinking disabled.
Run with `tools/jetson/llm_prompts.py`; each row is one run after a warm-up run, with prompt caching off.

llama-bench (same build, GPU): Qwen3.5-0.8B pp512 2352, pp2048 2535, tg256 74.4 tok/s; Qwen3-4B pp512 754, pp2048 740, tg256 21.1 tok/s.

## Energy (on-board sensor)

`energy-0.8b-20261027.csv`, `energy-4b-20261027.csv`, and `energy-q35-4b-20261027.csv` (Qwen3.5-4B, loaded with `--load-mode dio` so the page cache does not refill), from `tools/jetson/llm_energy.py`: the INA3221 rails read from sysfs at ~20 Hz, 20 s idle before each run.
The sensor readings are smoothed (a load step takes ~1 s to rise and ~1.5 s to settle), so decode J/token comes from the steady part of the 256-token short-prompt run, and prefill energy is the dynamic energy of the whole long-prompt request, tails included, minus its decode energy. On the short prompt, the integral and the steady decode mean agree within 1%.

Caveat: VDD_IN is the module's input rail. It leaves out the carrier board (Wi-Fi, NVMe SSD, USB, regulators) and the power supply, so these numbers are lower than a meter at the barrel jack would show, and are not directly comparable with the FNB58 numbers from the IQ-9075. The dynamic (above idle) values are the fairer comparison.
