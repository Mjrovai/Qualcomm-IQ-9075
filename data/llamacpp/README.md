# Upstream llama.cpp on the IQ-9075 CPU and the Raspberry Pi 5

llama.cpp commit 338fce6, CPU build (`-DLLAMA_CURL=OFF -DCMAKE_BUILD_TYPE=Release`), the same GGUF files (sha256 checked), prompts, and settings as the Jetson runs in `data/jetson`: seed 42, max 256 tokens, thinking disabled, prompt caching off. Run with `tools/jetson/llm_prompts.py`; each row is one run after a warm-up.

- `iq9075-cpu-llamacpp-20261027.csv`: IQ-9075, inside an `ubuntu:24.04` container on the factory Qualcomm Linux 1.6 image (gcc 13.3), 8 threads, non-streaming. The FNB58 energy of these runs is in `data/power/llm-llamacpp-cpu-nostream-20261027.csv`.
- `raspi5-cpu-llamacpp-20261028.csv`: Raspberry Pi 5 8 GB, Debian 13 (kernel 6.18.34+rpt-rpi-2712, gcc 14.2), official active cooler, 4 threads, with a pause before each request until the SoC was below 50 °C (`tools/jetson/raspi_run_cool.sh`).
- `raspi5-thermal-20261028.csv`: the Pi's state every second during that run: temperature, `vcgencmd get_throttled`, ARM clock, and fan level. The current-state throttling bits stayed at 0 and the clock at 2.4 GHz whenever the SoC was above 65 °C (max 77.4 °C). `0xe0000` is the sticky flag from an earlier run; it clears only on reboot.
- `raspi5-cpu-llamacpp-20261027-throttled.csv`: the first Pi run, without pauses, which ended at 74.7 °C with the throttling flag set. Kept for reference; not used in the tutorial.
