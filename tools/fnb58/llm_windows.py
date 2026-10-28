#!/usr/bin/env python3
"""Run the LLM prompts through llama-server and record when each phase happened, for an external meter.

Runs on the board (next to llm_prompts.py and llm_energy.py from tools/jetson). For each request it
writes the idle window before it, the arrival of the first and last tokens (unix time, board clock),
and llama.cpp's timings. llm_fnb58.py then cuts the FNB58 log on the Mac with these windows.
Usage:
    python3 llm_windows.py --bin llama.cpp/build/bin --models models --long longo.txt --ngl 0 --threads 8 \
        --only Qwen3.5-4B-Q4_0 -o windows.csv
"""
import argparse
import csv
import subprocess
import time

import llm_energy as le
import llm_prompts as lp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", required=True)
    ap.add_argument("--models", required=True)
    ap.add_argument("--long", required=True)
    ap.add_argument("--ngl", default="0")
    ap.add_argument("--threads", default=None)
    ap.add_argument("--only", nargs="*", default=lp.MODELS)
    ap.add_argument("--repeat", type=int, default=2)
    ap.add_argument("-o", "--out", required=True)
    # streaming sends each token over HTTP, which slows decode when every core runs inference
    ap.add_argument("--no-stream", action="store_true", help="rebuild the token times from llama.cpp timings")
    a = ap.parse_args()
    prompts = {"short": lp.SHORT, "long": open(a.long).read()}
    cols = ["model", "prompt", "run", "t_idle0", "t_idle1", "t_first", "t_end", "prompt_tokens", "ttft_s",
            "gen_tokens", "decode_tok_s"]
    with open(a.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        print(",".join(cols), flush=True)
        for m in a.only:
            cmd = [f"{a.bin}/llama-server", "-m", f"{a.models}/{m}.gguf", "-ngl", a.ngl, "-c", "4096",
                   "--port", str(lp.PORT), "--no-webui"]
            if a.threads:
                cmd += ["-t", a.threads]
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                lp.wait_ready(proc)
                for name, text in prompts.items():
                    for run in range(a.repeat + 1):
                        t_idle0 = time.time()
                        time.sleep(le.IDLE_S)
                        t_idle1 = time.time()
                        body = {"messages": [{"role": "user", "content": text}],
                                "max_tokens": 256, "seed": 42, "cache_prompt": False,
                                "chat_template_kwargs": {"enable_thinking": False}}
                        if a.no_stream:
                            t = lp.post("/v1/chat/completions", body)["timings"]
                            t_end = time.time()
                            t_first = t_end - t["predicted_ms"] / 1000
                        else:
                            t, t_first, t_end = le.stream({**body, "stream": True})
                        if run == 0:
                            continue
                        row = [m, name, run, f"{t_idle0:.3f}", f"{t_idle1:.3f}", f"{t_first:.3f}", f"{t_end:.3f}",
                               t["prompt_n"], f"{t['prompt_ms'] / 1000:.2f}", t["predicted_n"],
                               f"{t['predicted_per_second']:.1f}"]
                        w.writerow(row)
                        f.flush()
                        print(",".join(map(str, row)), flush=True)
            finally:
                proc.terminate()
                proc.wait()


if __name__ == "__main__":
    main()
