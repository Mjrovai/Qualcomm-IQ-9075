#!/usr/bin/env python3
"""Average power and energy of an fnb58_log.py CSV between two instants.

Times are Unix seconds or local HH:MM:SS[.fff] (same day as the log).

Usage:
    fnb58_slice.py run.csv 14:02:10 14:02:40
    fnb58_slice.py run.csv 14:02:10 14:02:40 --idle 6.85 --count 39500
"""
import argparse
import csv
import datetime as dt


def to_unix(s, day):
    try:
        return float(s)
    except ValueError:
        fmt = "%H:%M:%S.%f" if "." in s else "%H:%M:%S"
        t = dt.datetime.strptime(s, fmt).time()
        return dt.datetime.combine(day, t).timestamp()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("start")
    ap.add_argument("end")
    ap.add_argument("--idle", type=float, help="idle power (W) to subtract")
    ap.add_argument("--count", type=int, help="inferences/tokens in the window")
    args = ap.parse_args()

    with open(args.csv) as f:
        rows = [(float(r["t_unix"]), float(r["power_W"])) for r in csv.DictReader(f)]
    day = dt.datetime.fromtimestamp(rows[0][0]).date()
    t0, t1 = to_unix(args.start, day), to_unix(args.end, day)
    p = [w for t, w in rows if t0 <= t <= t1]
    if not p:
        raise SystemExit("no samples in that window")

    dur = t1 - t0
    avg = sum(p) / len(p)
    print(f"window   {dur:8.2f} s  ({len(p)} samples)")
    print(f"power    avg {avg:7.3f} W  min {min(p):7.3f}  max {max(p):7.3f}")
    print(f"energy   {avg * dur:8.2f} J")
    if args.idle is not None:
        dyn = avg - args.idle
        print(f"dynamic  {dyn:7.3f} W  ->  {dyn * dur:8.2f} J above idle")
        if args.count:
            print(f"per item {dyn * dur / args.count * 1000:8.3f} mJ dynamic, "
                  f"{avg * dur / args.count * 1000:8.3f} mJ total")


if __name__ == "__main__":
    main()
