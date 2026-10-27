#!/usr/bin/env python3
"""Log FNIRSI FNB58 readings (100 samples/s) to CSV on macOS via hidapi.

Protocol from baryluk/fnirsi-usb-power-data-logger (MIT, see LICENSE).

On macOS the meter streams for only one session per power cycle: a second
open hangs it (frozen display) and a USB reset does not recover it. Start
one long logging session, slice it with fnb58_slice.py, and power-cycle the
meter before logging again.

Usage:
    fnb58_log.py -o run.csv            # Ctrl+C to stop
    fnb58_log.py -o run.csv -t 60      # stop after 60 s
"""
import argparse
import sys
import time

import hid

VID, PID = 0x2E3C, 0x5558
SPS = 100
DT = 1.0 / SPS


def cmd(code, crc):
    # report id 0x00 + 64-byte packet: 0xaa, code, 61 zeros, crc
    return bytes([0x00, 0xAA, code]) + bytes(61) + bytes([crc])


def crc8(data):
    # width=8 poly=0x39 init=0x42, no reflection
    c = 0x42
    for b in data:
        c ^= b
        for _ in range(8):
            c = ((c << 1) ^ 0x39) & 0xFF if c & 0x80 else (c << 1) & 0xFF
    return c


def u32(d, o):
    return d[o] | d[o + 1] << 8 | d[o + 2] << 16 | d[o + 3] << 24


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", help="CSV file (default: stdout)")
    ap.add_argument("-t", "--seconds", type=float, help="stop after N seconds")
    ap.add_argument("-q", "--quiet", action="store_true", help="no 1 s status line on stderr")
    args = ap.parse_args()

    dev = hid.device()
    try:
        dev.open(VID, PID)
    except OSError:
        sys.exit("FNB58 not found (connect its data USB-C port to the Mac)")

    out = open(args.out, "w") if args.out else sys.stdout
    out.write("t_unix,voltage_V,current_A,power_W,energy_J\n")

    for c in (cmd(0x81, 0x8E), cmd(0x82, 0x96), cmd(0x82, 0x96)):
        if dev.write(c) < 0:
            sys.exit(f"write to FNB58 failed ({dev.error()}); unplug and replug its data cable")
    time.sleep(0.1)

    t_start = time.time()
    next_keepalive = t_start + 1.0
    energy = 0.0
    n = 0
    bad = 0
    p_sum, p_cnt = 0.0, 0
    try:
        while True:
            d = dev.read(64, 2000)
            now = time.time()
            if args.seconds and now - t_start >= args.seconds:
                break
            if not d:
                print("timeout reading FNB58", file=sys.stderr)
                continue
            if d[1] == 0x04:
                if crc8(d[1:-1]) != d[-1]:
                    bad += 1
                else:
                    t0 = now - 4 * DT
                    for i in range(4):
                        o = 2 + 15 * i
                        v = u32(d, o) / 1e5
                        a = u32(d, o + 4) / 1e5
                        p = v * a
                        energy += p * DT
                        p_sum += p
                        p_cnt += 1
                        out.write(f"{t0 + (i + 1) * DT:.3f},{v:.5f},{a:.5f},{p:.5f},{energy:.4f}\n")
                        n += 1
            if now >= next_keepalive:
                dev.write(cmd(0x83, 0x9E))
                next_keepalive = now + 1.0
                if not args.quiet and p_cnt:
                    print(f"\r{time.strftime('%H:%M:%S')}  P(1 s) = {p_sum / p_cnt:6.3f} W  "
                          f"E = {energy:9.2f} J  samples = {n}", end="", file=sys.stderr)
                p_sum, p_cnt = 0.0, 0
                out.flush()
    except KeyboardInterrupt:
        pass
    finally:
        # drain so the meter's display does not freeze
        while dev.read(64, 500):
            pass
        dev.close()
        if out is not sys.stdout:
            out.close()
        print(f"\n{n} samples, {energy:.2f} J, {bad} bad CRC", file=sys.stderr)


if __name__ == "__main__":
    main()
