#!/usr/bin/env python3
"""Energy charts for the IQ-9075 docs, in English and Portuguese.

Reads the FNB58 session logs and power_bench markers in data/power and writes
PNGs to figures/ (suffix -en / -pt).

Usage: make_charts.py            (run from anywhere)
"""
import csv
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "data", "power")
OUT = os.path.join(ROOT, "figures")

# reference palette, light mode: slots 1-3 validated all-pairs
NPU, CPU, GPU = "#2a78d6", "#eb6834", "#1baf7a"
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
COLOR = {"npu": NPU, "cpu8": CPU, "gpu": GPU}

SKIP_HEAD, SKIP_TAIL = 8.0, 2.0

T = {
    "en": {
        "npu": "NPU", "cpu": "CPU (8 threads)", "gpu": "GPU", "idle": "idle",
        "power": "Power at the board input (W)", "minutes": "Time (min)", "seconds": "Time from start of prefill (s)",
        "trace_title": "Ten vision models, NPU then CPU, 30 s each with 20 s idle between runs",
        "energy_x": "Energy per inference (mJ, total, log scale)",
        "energy_title": "Energy per inference: NPU vs CPU",
        "ratio": "CPU / NPU",
        "llm_title": "Qwen3-4B, ~2,000-token prompt: the area above idle is the energy spent",
        "prefill": "prefill", "decode": "decode",
        "npu_llm": "NPU (QAIRT)", "cpu_llm": "CPU (llama.cpp)",
        "tok_title": "LLM decode: energy per generated token",
        "tok_x": "Energy per token (J, total)",
        "load": "model load",
    },
    "pt": {
        "npu": "NPU", "cpu": "CPU (8 threads)", "gpu": "GPU", "idle": "repouso",
        "power": "Potência na entrada da placa (W)", "minutes": "Tempo (min)", "seconds": "Tempo desde o início do prefill (s)",
        "trace_title": "Dez modelos de visão, NPU e depois CPU, 30 s cada, com 20 s de repouso entre execuções",
        "energy_x": "Energia por inferência (mJ, total, escala log)",
        "energy_title": "Energia por inferência: NPU × CPU",
        "ratio": "CPU / NPU",
        "llm_title": "Qwen3-4B, prompt de ~2.000 tokens: a área acima do repouso é a energia gasta",
        "prefill": "prefill", "decode": "decode",
        "npu_llm": "NPU (QAIRT)", "cpu_llm": "CPU (llama.cpp)",
        "tok_title": "Decode de LLM: energia por token gerado",
        "tok_x": "Energia por token (J, total)",
        "load": "carga do modelo",
    },
}

SHORT = {
    "face_attrib_net": "face_attrib", "inception_v3": "inception_v3", "hrnet_pose": "hrnet_pose",
    "midas": "midas", "deeplabv3_plus_mobilenet": "deeplabv3+", "yolox": "yolox",
    "face_det_lite": "face_det_lite", "facemap_3dmm": "facemap_3dmm", "yamnet": "yamnet",
    "quicksrnetsmall": "quicksrnet",
}


def num(x, lang, fmt="{:.2f}"):
    s = fmt.format(x)
    if lang == "pt":
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def load_session(name):
    a = np.loadtxt(os.path.join(DATA, name), delimiter=",", skiprows=1, usecols=(0, 3))
    return a[:, 0], a[:, 1]


def load_marks(name):
    return list(csv.DictReader(open(os.path.join(DATA, name))))


def mean_power(t, p, t0, t1):
    sel = (t >= t0) & (t <= t1)
    return p[sel].mean() if sel.any() else float("nan")


def style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def new_fig(w, h):
    fig, ax = plt.subplots(figsize=(w, h), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    style(ax)
    return fig, ax


def save(fig, name, lang):
    path = os.path.join(OUT, f"{name}-{lang}.png")
    fig.savefig(path, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    print(path)


def vision_energy():
    """Total mJ per inference per (model, backend), from both sessions."""
    res = {}
    for sess, marks in (("session-20261026-1312.csv", "markers-20261026-models.csv"),
                        ("session-20261026-1441.csv", "markers-20261026-quicksrnet.csv")):
        t, p = load_session(sess)
        for m in load_marks(marks):
            if not m["latency_us"]:
                continue
            model, backend = m["label"].rsplit("-", 1)
            if model == "quicksrnetsmall" and sess.endswith("1312.csv"):
                continue  # partial run; the rerun is complete
            if model == "inception_v3" and sess.endswith("1441.csv"):
                continue  # anchor rerun, keep the first battery
            pw = mean_power(t, p, float(m["t_start"]) + SKIP_HEAD, float(m["t_end"]) - SKIP_TAIL)
            res[(model, backend)] = pw * float(m["latency_us"]) / 1e3  # W * us / 1e3 = mJ
    return res


def chart_trace(lang):
    tx = T[lang]
    t, p = load_session("session-20261026-1312.csv")
    marks = load_marks("markers-20261026-models.csv")
    t0 = float(marks[0]["t_start"])
    t_end = next(float(m["t_start"]) for m in marks if m["label"].startswith("quicksrnet"))
    sel = (t >= t0) & (t < t_end)
    # 1 s means
    sec = np.floor(t[sel] - t0).astype(int)
    p1 = np.bincount(sec, weights=p[sel]) / np.maximum(np.bincount(sec), 1)
    x = np.arange(len(p1)) / 60

    fig, ax = new_fig(12, 4.2)
    groups = {}
    for m in marks:
        if m["label"].startswith("idle") or float(m["t_start"]) >= t_end:
            continue
        model, backend = m["label"].rsplit("-", 1)
        a, b = (float(m["t_start"]) - t0) / 60, (float(m["t_end"]) - t0) / 60
        ax.axvspan(a, b, color=COLOR[backend], alpha=0.16, linewidth=0)
        groups.setdefault(model, []).append((a, b))
    ax.plot(x, p1, color=INK, linewidth=1.0)
    for model, spans in groups.items():
        mid = (spans[0][0] + spans[-1][1]) / 2
        ax.text(mid, 21.6, SHORT[model], ha="center", va="bottom", fontsize=8, color=INK2)
    ax.set_ylim(0, 22.5)
    ax.set_xlim(0, x[-1])
    ax.set_ylabel(tx["power"], color=INK2, fontsize=9)
    ax.set_xlabel(tx["minutes"], color=INK2, fontsize=9)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c, alpha=0.35) for c in (NPU, CPU, GPU)]
    ax.legend(handles, [tx["npu"], tx["cpu"], tx["gpu"]], loc="lower right", frameon=False,
              fontsize=9, ncol=3, labelcolor=INK)
    ax.set_title(tx["trace_title"], loc="left", fontsize=11, color=INK, pad=22)
    save(fig, "power-trace-vision", lang)


def chart_energy(lang):
    tx = T[lang]
    e = vision_energy()
    models = sorted({m for m, _ in e}, key=lambda m: e[(m, "cpu8")] / e[(m, "npu")])
    fig, ax = new_fig(9, 5.2)
    y = np.arange(len(models))
    for i, m in enumerate(models):
        n, c = e[(m, "npu")], e[(m, "cpu8")]
        ax.plot([n, c], [i, i], color=GRID, linewidth=2.2, zorder=1, solid_capstyle="round")
        ax.scatter([n], [i], s=60, color=NPU, zorder=3, edgecolors=SURFACE, linewidths=1.5)
        ax.scatter([c], [i], s=60, color=CPU, zorder=3, edgecolors=SURFACE, linewidths=1.5)
        ax.text(2600, i, num(c / n, lang, "{:.1f}") + "×", va="center", ha="right", fontsize=9, color=INK)
        if (m, "gpu") in e:
            g = e[(m, "gpu")]
            ax.scatter([g], [i], s=60, color=GPU, zorder=3, edgecolors=SURFACE, linewidths=1.5, marker="D")
            ax.text(g, i + 0.32, tx["gpu"], ha="center", va="bottom", fontsize=8, color=INK2)
    ax.set_xscale("log")
    ax.set_xlim(1.5, 2700)
    ax.set_yticks(y, [SHORT[m] for m in models])
    ax.tick_params(axis="y", length=0, labelcolor=INK)
    ax.grid(axis="y", visible=False)
    ax.set_xticks([2, 5, 10, 20, 50, 100, 200, 500, 1000],
                  [num(v, lang, "{:,.0f}") for v in (2, 5, 10, 20, 50, 100, 200, 500, 1000)])
    ax.minorticks_off()
    ax.text(2600, len(models) - 0.35, tx["ratio"], ha="right", va="bottom", fontsize=8, color=INK2)
    ax.set_xlabel(tx["energy_x"], color=INK2, fontsize=9)
    h = [plt.Line2D([], [], marker="o", linestyle="", color=c, markersize=7) for c in (NPU, CPU)]
    h.append(plt.Line2D([], [], marker="D", linestyle="", color=GPU, markersize=6))
    ax.legend(h, [tx["npu"], tx["cpu"], tx["gpu"]], loc="lower center", bbox_to_anchor=(0.45, 1.0),
              ncol=3, frameon=False, fontsize=9, labelcolor=INK)
    ax.set_title(tx["energy_title"], loc="left", fontsize=11, color=INK, pad=26)
    save(fig, "energy-per-inference", lang)


def chart_llm_trace(lang):
    tx = T[lang]
    t, p = load_session("session-20261026-1441.csv")
    marks = {m["label"]: m for m in load_marks("markers-20261026-llm.csv")}
    fig, ax = new_fig(10, 4.6)
    idle = mean_power(t, p, float(marks["idle-03"]["t_start"]) + 5, float(marks["idle-03"]["t_end"]) - 1)
    for label, color, name in (("qwen3-4b-cpu-llamacpp-long", CPU, tx["cpu_llm"]),
                               ("qwen3-4b-npu-qairt-long", NPU, tx["npu_llm"])):
        m = marks[label]
        rate, ntok, ttft = float(m["tok_s"]), int(m["n_tok"]), float(m["ttft_s"])
        t_gen = float(m["t_gen_end"])
        t_dec = t_gen - ntok / rate
        t_pre = t_dec - ttft
        sel = (t >= t_pre - 4) & (t <= t_gen + 3)
        # 0.2 s means
        b = np.floor((t[sel] - t_pre) / 0.2).astype(int)
        b -= b.min()
        pb = np.bincount(b, weights=p[sel]) / np.maximum(np.bincount(b), 1)
        xb = (np.arange(len(pb)) * 0.2) + (t[sel][0] - t_pre)
        ax.plot(xb, pb, color=color, linewidth=1.6, label=name)
        w = (xb >= 0) & (xb <= t_gen - t_pre)
        ax.fill_between(xb[w], idle, pb[w], color=color, alpha=0.14, linewidth=0)
        e_pre = mean_power(t, p, t_pre + 0.2, t_dec - 0.1) * ttft
        pre_txt = f"{tx['prefill']} {num(ttft, lang, '{:.1f}')} s · {num(e_pre, lang, '{:.0f}')} J"
        if color == CPU:
            ax.text(ttft / 2, 18.4, pre_txt, ha="center", fontsize=9, color=INK)
            ax.text(ttft + 0.6, 22.6, f"{tx['decode']} {ntok} tok", ha="left", fontsize=8, color=INK2)
        else:
            ax.text(2.6, 15.3, pre_txt, ha="left", fontsize=9, color=INK)
    ax.axhline(idle, color=INK2, linewidth=0.9, linestyle=(0, (4, 3)))
    ax.text(12, idle - 0.4, f"{tx['idle']} {num(idle, lang, '{:.1f}')} W", ha="center", va="top",
            fontsize=8, color=INK2)
    ax.text(-2.2, idle - 0.4, tx["load"], ha="center", va="top", fontsize=8, color=INK2)
    ax.set_ylim(0, 24.5)
    ax.set_xlim(-4, 36)
    ax.set_ylabel(tx["power"], color=INK2, fontsize=9)
    ax.set_xlabel(tx["seconds"], color=INK2, fontsize=9)
    ax.legend(loc="lower right", frameon=False, fontsize=9, labelcolor=INK)
    ax.set_title(tx["llm_title"], loc="left", fontsize=11, color=INK)
    save(fig, "llm-prefill-trace", lang)


def chart_tokens(lang):
    tx = T[lang]
    t, p = load_session("session-20261026-1441.csv")
    marks = load_marks("markers-20261026-llm.csv")
    rows = []
    for m in marks:
        if not m["label"].endswith("-short"):
            continue
        rate, ntok = float(m["tok_s"]), int(m["n_tok"])
        t_gen = float(m["t_gen_end"])
        pw = mean_power(t, p, t_gen - ntok / rate + 0.3, t_gen - 0.3)
        name = m["label"].replace("-short", "")
        proc = "npu" if "-npu-" in name else "cpu8"
        model = "Qwen3-4B" if "4b" in name else "Qwen3.5-0.8B"
        rt = "QAIRT" if "qairt" in name else ("llama.cpp Hexagon" if proc == "npu" else "llama.cpp")
        rows.append((f"{model}\n{rt}, {'NPU' if proc == 'npu' else 'CPU'}", pw / rate, rate, proc))
    fig, ax = new_fig(8, 3.6)
    y = np.arange(len(rows))[::-1]
    for yi, (lab, jt, rate, proc) in zip(y, rows):
        ax.barh(yi, jt, height=0.55, color=COLOR[proc])
        ax.text(jt + 0.02, yi, f"{num(jt, lang)} J · {num(rate, lang, '{:.1f}')} tok/s",
                va="center", fontsize=9, color=INK)
    ax.set_yticks(y, [r[0] for r in rows])
    ax.tick_params(axis="y", length=0, labelcolor=INK, labelsize=9)
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, 1.6)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: num(v, lang, "{:.1f}")))
    ax.set_xlabel(tx["tok_x"], color=INK2, fontsize=9)
    h = [plt.Rectangle((0, 0), 1, 1, color=c) for c in (NPU, CPU)]
    ax.legend(h, [tx["npu"], "CPU"], loc="lower right", frameon=False, fontsize=9, labelcolor=INK)
    ax.set_title(tx["tok_title"], loc="left", fontsize=11, color=INK)
    save(fig, "llm-energy-per-token", lang)


def main():
    os.makedirs(OUT, exist_ok=True)
    plt.rcParams["font.family"] = ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]
    for lang in ("en", "pt"):
        chart_trace(lang)
        chart_energy(lang)
        chart_llm_trace(lang)
        chart_tokens(lang)


if __name__ == "__main__":
    main()
