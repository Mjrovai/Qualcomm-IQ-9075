#!/usr/bin/env python3
"""Run the IQ-9075 LLM prompts (short and long) through llama-server and print llama.cpp's timings.

Same models, prompts, seed, and token limit as the GenieX runs on the IQ-9075 (Oct 14 and 26, 2026),
with thinking disabled. Runs on the target board; usage:
    python3 llm_prompts.py --bin /ssd/llama.cpp/build/bin --models /ssd/models --long /ssd/prompts/longo.txt [--ngl 99]
"""
import argparse
import json
import subprocess
import time
import urllib.request

SHORT = "Explique em três parágrafos o que é TinyML"
MODELS = ["Qwen3.5-0.8B-Q4_0", "Qwen3-4B-Q4_0"]
PORT = 8089


def post(path, body):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def wait_ready(proc):
    for _ in range(300):
        if proc.poll() is not None:
            raise SystemExit("llama-server exited")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2) as r:
                if json.load(r).get("status") == "ok":
                    return
        except Exception:
            pass
        time.sleep(1)
    raise SystemExit("llama-server not ready")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", required=True)
    ap.add_argument("--models", required=True)
    ap.add_argument("--long", required=True)
    ap.add_argument("--ngl", default="99")
    ap.add_argument("--threads", default=None)
    ap.add_argument("--repeat", type=int, default=2)
    ap.add_argument("--only", nargs="*", default=MODELS)
    a = ap.parse_args()
    prompts = {"short": SHORT, "long": open(a.long).read()}
    print("model,prompt,run,prompt_tokens,ttft_s,prefill_tok_s,gen_tokens,decode_tok_s")
    for m in a.only:
        cmd = [f"{a.bin}/llama-server", "-m", f"{a.models}/{m}.gguf", "-ngl", a.ngl, "-c", "4096",
               "--port", str(PORT), "--no-webui"]
        if a.threads:
            cmd += ["-t", a.threads]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            wait_ready(proc)
            for name, text in prompts.items():
                # run 0 warms up; the cache is cleared so every run does a full prefill
                for run in range(a.repeat + 1):
                    r = post("/v1/chat/completions", {
                        "messages": [{"role": "user", "content": text}],
                        "max_tokens": 256, "seed": 42, "cache_prompt": False,
                        "chat_template_kwargs": {"enable_thinking": False}})
                    t = r["timings"]
                    if run == 0:
                        continue
                    print(f"{m},{name},{run},{t['prompt_n']},{t['prompt_ms'] / 1000:.2f},"
                          f"{t['prompt_per_second']:.0f},{t['predicted_n']},{t['predicted_per_second']:.1f}",
                          flush=True)
        finally:
            proc.terminate()
            proc.wait()


if __name__ == "__main__":
    main()
