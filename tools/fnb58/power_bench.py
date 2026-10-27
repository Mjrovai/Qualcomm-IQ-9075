#!/usr/bin/env python3
"""Run timed workloads on the board over SSH and measure them with the FNB58 log.

Each phase is a remote command (or an idle wait). Start/end are taken on the
Mac clock, the same clock as fnb58_log.py, and appended to a markers CSV.
The report averages power over the steady part of each phase and, for
benchmark_model phases, turns it into energy per inference:

    E_dyn = (P_phase - P_idle) * latency      E_total = P_phase * latency

Usage:
    power_bench.py run  plan.txt  -m markers.csv
    power_bench.py report session.csv markers.csv
Plan lines:  label | seconds | remote command   (empty command = idle)
"""
import argparse
import csv
import os
import re
import subprocess
import sys
import time

# board address and SSH key; override with IQ9075_HOST and IQ9075_KEY
HOST = os.environ.get("IQ9075_HOST", "root@192.168.5.136")
KEY = os.path.expanduser(os.environ.get("IQ9075_KEY", "~/.ssh/id_ed25519_opi"))
SKIP_HEAD = 8.0  # s: model load, delegate setup, warm-up
SKIP_TAIL = 2.0


def run(args):
    new = not os.path.exists(args.markers)
    with open(args.markers, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["label", "t_start", "t_end", "latency_us", "count",
                        "tok_s", "n_tok", "ttft_s", "t_gen_end"])
        for line in open(args.plan):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            label, secs, cmd = (x.strip() for x in line.split("|", 2))
            secs = float(secs)
            print(f"{time.strftime('%H:%M:%S')}  {label} ({secs:.0f} s)", flush=True)
            t0 = time.time()
            lat = cnt = tok_s = n_tok = ttft = t_gen = ""
            if cmd:
                cmd = cmd.replace("{secs}", f"{secs:g}")
                out = subprocess.run(["ssh", "-i", KEY, "-o", "BatchMode=yes", HOST, cmd],
                                     capture_output=True, text=True).stdout
                m = re.findall(r"count=(\d+).*?avg=([\d.e+]+)", out)
                g = re.search(r"([\d.]+) tok/s \S+ (\d+) tok \S+ ([\d.]+) s first token", out)
                e = re.search(r"GEN_END=([\d.]+)", out)
                if m:
                    cnt, lat = m[-1]
                    print(f"          count={cnt} avg={float(lat):.1f} us", flush=True)
                elif g and e:
                    tok_s, n_tok, ttft = g.groups()
                    t_gen = e.group(1)
                    print(f"          {tok_s} tok/s, {n_tok} tok, {ttft} s first token", flush=True)
                else:
                    print("          (no benchmark summary)\n" + out[-500:], flush=True)
            else:
                time.sleep(secs)
            w.writerow([label, f"{t0:.3f}", f"{time.time():.3f}", lat, cnt, tok_s, n_tok, ttft, t_gen])
            f.flush()


def report(args):
    with open(args.session) as f:
        samples = [(float(r["t_unix"]), float(r["power_W"])) for r in csv.DictReader(f)]
    marks = list(csv.DictReader(open(args.markers)))

    def avg(t0, t1):
        p = [w for t, w in samples if t0 <= t <= t1]
        return (sum(p) / len(p), len(p)) if p else (float("nan"), 0)

    # idle drifts up as the board warms, so each workload uses the idle phase just before it
    print(f"{'phase':<30}{'P avg W':>9}{'idle W':>8}{'dyn W':>8}{'lat ms':>9}{'mJ dyn':>9}{'mJ tot':>9}")
    p_idle = float("nan")
    llm = []
    for m in marks:
        is_idle = m["label"].startswith("idle")
        head = 5 if is_idle else SKIP_HEAD
        if m.get("tok_s"):
            llm.append((m, p_idle))
            continue
        p, n = avg(float(m["t_start"]) + head, float(m["t_end"]) - SKIP_TAIL)
        if n == 0:
            print(f"{m['label']:<30}  (no samples)")
            continue
        if is_idle:
            p_idle = p
        row = f"{m['label']:<30}{p:9.3f}{p_idle:8.3f}{p - p_idle:8.3f}"
        if m["latency_us"]:
            lat = float(m["latency_us"]) / 1e6
            row += f"{lat * 1e3:9.3f}{(p - p_idle) * lat * 1e3:9.3f}{p * lat * 1e3:9.3f}"
        print(row)

    if not llm:
        return
    # LLM phases: windows are reconstructed back from the board-side end of generation
    # (board and Mac clocks agree within ~0.3 s via NTP)
    print(f"\n{'LLM phase':<30}{'tok/s':>7}{'tok':>5}{'ttft s':>7}{'dec W':>7}{'dyn W':>7}"
          f"{'J/tok dyn':>10}{'J/tok tot':>10}{'pre W':>7}{'pre J dyn':>10}{'pre J tot':>10}")
    for m, idle in llm:
        rate, ntok, ttft = float(m["tok_s"]), int(m["n_tok"]), float(m["ttft_s"])
        t_end = float(m["t_gen_end"])
        t_dec = t_end - ntok / rate
        pd, nd = avg(t_dec + 0.3, t_end - 0.3)
        row = f"{m['label']:<30}{rate:7.1f}{ntok:5d}{ttft:7.1f}{pd:7.2f}{pd - idle:7.2f}"
        row += f"{(pd - idle) / rate:10.3f}{pd / rate:10.3f}" if nd else f"{'':20}"
        if ttft >= 1.0:
            pp, npre = avg(t_dec - ttft + 0.2, t_dec - 0.1)
            if npre:
                row += f"{pp:7.2f}{(pp - idle) * ttft:10.1f}{pp * ttft:10.1f}"
        print(row)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("plan")
    r.add_argument("-m", "--markers", required=True)
    p = sub.add_parser("report")
    p.add_argument("session")
    p.add_argument("markers")
    args = ap.parse_args()
    (run if args.cmd == "run" else report)(args)


if __name__ == "__main__":
    main()
