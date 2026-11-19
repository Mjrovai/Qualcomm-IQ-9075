# GenieX: Qwen3.5-9B on the IQ-9075 NPU, GPU, and CPU

Qualcomm GenieX, using its `llama_cpp` runtime, ran Qwen3.5-9B Q4_0 on each compute unit of the IQ-9075. Each row is one `geniex infer` call.

## Setup

- IQ-9075 EVK, Canonical Ubuntu 24.04.5 Desktop, kernel `6.8.0-1089-qcom`, `performance` governor.
- GenieX CLI v0.11.0, QAIRT runtime 2.50, llama.cpp runtime hash `93cf736`.
- Model: `Qwen3.5-9B-Q4_0.gguf` from `unsloth/Qwen3.5-9B-MTP-GGUF` (sha256 `1b69b7e765387778195c044b5aa1db9c5232568f9dbdc4704b940f612b7d7498`). This is the same file used in `data/mtp/` and `data/llamacpp/`. It was imported with `geniex pull local/Qwen3.5-9B --model-hub localfs --local-path <dir> --model-type llm`.
- Command: `geniex infer local/Qwen3.5-9B:Q4_0 -c <npu|gpu|cpu> --think=false --seed 42 --skip-update --verbose`, with the GenieX defaults of context 4096 and power mode `burst`.
  - Short prompt: `-p "Explain photosynthesis in 300 words." --max-tokens 256`.
  - Long prompt: `-i prompts/longo.txt --max-tokens 64` (1641 tokens). The model stopped on its own after 31 or 32 tokens.
  - MTP: `--spec-type draft-mtp --draft-tokens 3`, on the NPU only.
- A 20 s pause between calls. All values come from the `--verbose` output of GenieX.

## Notes

- The short prompt is 23 tokens here and 25 tokens in `data/llamacpp/`, because the chat template is different. The long prompt is 1641 tokens in both.
- The GPU (Adreno 663 through OpenCL) completed one run. The second run hung while loading the model, with the process at 0% CPU for 1 h 49 min, and `timeout` did not stop it. It was killed by hand, and the remaining GPU runs were skipped.

## Summary (mean of 2 runs)

| Compute | Short: prefill tok/s | Short: decode tok/s | Long: TTFT s | Long: prefill tok/s | Long: decode tok/s |
| --- | --- | --- | --- | --- | --- |
| NPU | 64.7 | 6.58 | 6.67 | 246.3 | 6.38 |
| GPU (1 run) | 23.8 | 4.02 | — | — | — |
| CPU | 30.1 | 6.99 | 44.33 | 37.1 | 6.75 |
| NPU, MTP n=3 | 47.9 | 4.67 | — | — | — |

For comparison, our own llama.cpp CPU build (commit `338fce6`, 8 threads, `data/llamacpp/iq9075-ubuntu-cpu-qwen35-9b-20261118.csv`) gave 35 tok/s prefill on the long prompt, a TTFT of 47 s, and 6.3 tok/s decode on the short prompt.

- **Prefill:** the NPU was 6.6× faster than the CPU on the long prompt. Time to first token dropped from 44 s to 6.7 s.
- **Decode:** the CPU was slightly faster than the NPU (6.99 against 6.58 tok/s). Decode is limited by memory bandwidth on both.
- **MTP on the NPU** made decode slower: 4.67 tok/s, against 6.58 without it.
- **Not tested yet:** the GenieX `hybrid` compute mode. Our CPU build with MTP n=3 reached 9.02 tok/s decode on this model (`data/mtp/`).

## GenieX qairt runtime: Qwen3-8B from AI Hub on the NPU

File: `iq9075-geniex-qairt-qwen3-8b-20261118-19.csv`.

- **Model:** `qualcomm/Qwen3-8B`, pulled with `geniex pull qualcomm/Qwen3-8B --model-hub aihub`. It is a pre-compiled QAIRT bundle: W4A16, five parts, 5.2 GiB, compiled with QAIRT 2.50 at a fixed context of 4096.
- **Command:** `geniex infer qualcomm/Qwen3-8B:W4A16 --think=false --seed 42 --skip-update --verbose`, with the same short and long prompts as above. The qairt runtime runs only on the NPU.
- **Prompt length:** the bundle's chat template adds a system prompt, so the prompts are longer than with the llama_cpp runtime: 36 tokens for the short prompt and 1895 for the long one.
- **Empty runs:** 3 of the 8 script runs printed no metrics and no error. Each was a run that started 20 s after the previous one ended. The same long prompt worked when run alone, so the cause may be the NPU not yet released by the previous process. This was not confirmed. During the 2026-11-18 session, the ssh session that started the script was also killed by mistake, but the script kept running on the board.

### Summary (mean of the valid runs)

| Prompt | Valid runs | TTFT s | Prefill tok/s | Decode tok/s |
| --- | --- | --- | --- | --- |
| Short | 3 | 0.15 | 247.5 | 9.72 |
| Long | 3 | 2.44 | 777.5 | 9.14 |

Against Qwen3.5-9B through the llama_cpp runtime on the same NPU (top of this file), the compiled Qwen3-8B bundle decoded about 1.5× faster (9.72 against 6.58 tok/s) and prefilled the long prompt about 3× faster (777.5 against 246.3 tok/s). Qwen3.5-9B is the stronger model, so this is a speed and quality trade-off.
