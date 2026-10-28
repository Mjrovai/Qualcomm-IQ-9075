#!/usr/bin/env python3
"""LLM energy from an FNB58 session log and the windows written by llm_windows.py.

Same definitions as power_bench.py report: idle is the mean power over the idle phase before each
run (first 5 s skipped), prefill is the mean power between the first token minus the time to first
token and the first token, and decode is the mean power from 0.3 s after the first token to the
last token. "Dynamic" subtracts idle.
Usage: llm_fnb58.py session.csv windows.csv [-o out.csv]
"""
import argparse
import csv

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session")
    ap.add_argument("windows")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    d = np.loadtxt(a.session, delimiter=",", skiprows=1, usecols=(0, 3))
    t, p = d[:, 0], d[:, 1]

    def mean(t0, t1):
        sel = (t >= t0) & (t <= t1)
        return p[sel].mean() if sel.any() else float("nan")

    cols = ["model", "prompt", "run", "idle_W", "prompt_tokens", "ttft_s", "prefill_W", "gen_tokens",
            "decode_tok_s", "decode_W", "prefill_J_total", "prefill_J_dynamic", "J_per_token_total",
            "J_per_token_dynamic"]
    rows = []
    for r in csv.DictReader(open(a.windows)):
        f = {k: float(r[k]) for k in ("t_idle0", "t_idle1", "t_first", "t_end", "ttft_s", "decode_tok_s")}
        idle = mean(f["t_idle0"] + 5, f["t_idle1"])
        pre = mean(f["t_first"] - f["ttft_s"], f["t_first"])
        dec = mean(f["t_first"] + 0.3, f["t_end"])
        tps, ttft = f["decode_tok_s"], f["ttft_s"]
        rows.append([r["model"], r["prompt"], r["run"], f"{idle:.2f}", r["prompt_tokens"], f"{ttft:.2f}",
                     f"{pre:.2f}", r["gen_tokens"], f"{tps:.1f}", f"{dec:.2f}", f"{pre * ttft:.1f}",
                     f"{(pre - idle) * ttft:.1f}", f"{dec / tps:.3f}", f"{(dec - idle) / tps:.3f}"])
    print(",".join(cols))
    for row in rows:
        print(",".join(row))
    if a.out:
        with open(a.out, "w", newline="") as fo:
            w = csv.writer(fo)
            w.writerow(cols)
            w.writerows(rows)


if __name__ == "__main__":
    main()
