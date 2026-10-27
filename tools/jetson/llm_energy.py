#!/usr/bin/env python3
"""LLM energy on a Jetson from its on-board INA3221 sensor, with the IQ-9075 prompts.

Samples VDD_IN (module input), VDD_CPU_GPU_CV, and VDD_SOC at ~20 Hz from sysfs while
llm_prompts.py's requests run, with an idle phase before each run. The prefill and decode
readings are smoothed (a load step takes ~1 s to show), so short windows cannot be averaged:
decode J/token comes from the steady part of the 256-token short-prompt run, and prefill energy
is the dynamic energy of the whole long-prompt request, tails included, minus its decode energy.

Caveat: VDD_IN is the module's input rail. It leaves out the carrier board (Wi-Fi card, NVMe SSD,
USB, regulators) and the power supply, so it reads lower than a meter at the barrel jack would,
and is not directly comparable with the FNB58 numbers measured on the IQ-9075.

Runs on the Jetson, next to llm_prompts.py; usage:
    python3 llm_energy.py --bin /ssd/llama.cpp/build/bin --models /ssd/models --long /ssd/prompts/longo.txt \
        --only Qwen3.5-0.8B-Q4_0 -o /ssd/energy-0.8b.csv
"""
import argparse
import csv
import glob
import json
import subprocess
import threading
import time
import urllib.request

import llm_prompts as lp

IDLE_S = 20
TAIL_S = 3.0  # the INA3221 readings take ~1.5 s to settle after a load step
RISE_S = 1.0


def rails():
    hw = glob.glob("/sys/bus/i2c/drivers/ina3221/*/hwmon/hwmon*")[0]
    out = {}
    for i in (1, 2, 3):
        label = open(f"{hw}/in{i}_label").read().strip()
        out[label] = (f"{hw}/in{i}_input", f"{hw}/curr{i}_input")
    return out


class Sampler(threading.Thread):
    def __init__(self, period=0.05):
        super().__init__(daemon=True)
        self.rails, self.period, self.samples, self.stop = rails(), period, [], False

    def run(self):
        while not self.stop:
            row = [time.time()]
            for v, c in self.rails.values():
                row.append(int(open(v).read()) * int(open(c).read()) / 1e6)  # mV * mA -> W
            self.samples.append(row)
            time.sleep(self.period)

    def integral(self, t0, t1, base, col=1):
        xs = [s for s in self.samples if t0 <= s[0] <= t1]
        return sum((b[col] - base) * (b[0] - a[0]) for a, b in zip(xs, xs[1:]))

    def mean(self, t0, t1, col=1):
        xs = [s[col] for s in self.samples if t0 <= s[0] <= t1]
        return (sum(xs) / len(xs), len(xs)) if xs else (float("nan"), 0)


def stream(body):
    """Streamed chat completion; returns llama.cpp's timings and the arrival times of the first and last tokens."""
    req = urllib.request.Request(f"http://127.0.0.1:{lp.PORT}/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    t_first = t_last = None
    timings = None
    with urllib.request.urlopen(req, timeout=600) as r:
        for line in r:
            line = line.strip()
            if not line.startswith(b"data: ") or line == b"data: [DONE]":
                continue
            chunk = json.loads(line[6:])
            if chunk.get("timings"):
                timings = chunk["timings"]
            delta = (chunk.get("choices") or [{}])[0].get("delta", {})
            if delta.get("content"):
                t_last = time.time()
                t_first = t_first or t_last
    return timings, t_first, t_last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", required=True)
    ap.add_argument("--models", required=True)
    ap.add_argument("--long", required=True)
    ap.add_argument("--only", nargs="*", default=lp.MODELS)
    ap.add_argument("--repeat", type=int, default=2)
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    prompts = {"short": lp.SHORT, "long": open(a.long).read()}
    jt_dyn = {}
    s = Sampler()
    s.start()
    names = list(s.rails)
    cols = ["model", "prompt", "run", "idle_W", "prompt_tokens", "ttft_s", "request_J_dynamic", "gen_tokens",
            "decode_tok_s", "decode_W", "prefill_J_total", "prefill_J_dynamic", "J_per_token_total",
            "J_per_token_dynamic", "decode_cpu_gpu_W", "decode_soc_W"]
    print(",".join(cols), flush=True)
    with open(a.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for m in a.only:
            proc = subprocess.Popen([f"{a.bin}/llama-server", "-m", f"{a.models}/{m}.gguf", "-ngl", "99",
                                     "-c", "4096", "--port", str(lp.PORT), "--no-webui"],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                lp.wait_ready(proc)
                for name, text in prompts.items():
                    for run in range(a.repeat + 1):
                        t_idle = time.time()
                        time.sleep(IDLE_S)
                        idle, _ = s.mean(t_idle + 2, time.time())
                        t, t_first, t_end = stream({
                            "messages": [{"role": "user", "content": text}],
                            "max_tokens": 256, "seed": 42, "cache_prompt": False, "stream": True,
                            "chat_template_kwargs": {"enable_thinking": False}})
                        time.sleep(TAIL_S)
                        if run == 0:
                            continue
                        ttft, n = t["prompt_ms"] / 1000, t["predicted_n"]
                        tps = t["predicted_per_second"]
                        # whole request, sensor tails included: the smoothing keeps the area
                        e_dyn = s.integral(t_first - ttft - 0.3, t_end + TAIL_S, idle)
                        # steady decode, after the sensor's ~1 s rise
                        p_dec, n_dec = s.mean(t_first + RISE_S, t_end)
                        cg, _ = s.mean(t_first + RISE_S, t_end, names.index("VDD_CPU_GPU_CV") + 1)
                        soc, _ = s.mean(t_first + RISE_S, t_end, names.index("VDD_SOC") + 1)
                        if name == "short":
                            jt_dyn[m] = (p_dec - idle) / tps
                            pre_dyn = e_dyn - jt_dyn[m] * n
                        else:
                            # decode is too short to see; take its energy from the short-prompt run
                            pre_dyn = e_dyn - jt_dyn[m] * n
                            p_dec = idle + jt_dyn[m] * tps
                        row = [m, name, run, f"{idle:.2f}", t["prompt_n"], f"{ttft:.2f}", f"{e_dyn:.1f}",
                               n, f"{tps:.1f}", f"{p_dec:.2f}", f"{pre_dyn + idle * ttft:.1f}",
                               f"{pre_dyn:.1f}", f"{p_dec / tps:.3f}", f"{(p_dec - idle) / tps:.3f}",
                               f"{cg:.2f}", f"{soc:.2f}"]
                        w.writerow(row)
                        f.flush()
                        print(",".join(map(str, row)), flush=True)
            finally:
                proc.terminate()
                proc.wait()
    s.stop = True


if __name__ == "__main__":
    main()
