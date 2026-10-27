#!/usr/bin/env python3
"""Block diagram of the energy measurement setup, as SVG and PNG, in English and Portuguese.

Writes figures/energy-setup-{en,pt}.svg and .png (PNG via rsvg-convert).
"""
import os
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "figures")

INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8984"
SURFACE, BOX, LINE, MAC = "#fcfcfb", "#ffffff", "#c9c8c3", "#f1f0ec"
DATA = "#2a78d6"

T = {
    "en": {
        "power_path": "POWER PATH",
        "charger": ("USB-C PD charger", "65–100 W"),
        "fnb58": ("FNIRSI FNB58", "USB meter, V and I"),
        "trigger": ("PD trigger cable", "USB-C → barrel, 20 V"),
        "evk": ("IQ-9075 EVK", "barrel input, 12–36 V"),
        "usbc": "USB-C",
        "barrel": "barrel",
        "order": "Connect the data cable last: the FNB58 must power up from the charger, or PD stays at 5 V.",
        "data": "data port (HID), 100 samples/s",
        "mac": "MAC",
        "logger": ("fnb58_log.py", "one long session", "→ session.csv"),
        "bench": ("power_bench.py run", "plan of phases, idle between", "→ markers.csv (start, end)"),
        "ssh": "SSH over Wi-Fi",
        "ssh2": "benchmark_model, geniex",
        "report": ("power_bench.py report", "mean power in each steady window"),
        "formula": "E = P × t\u2003\u2003dynamic: (P − P_idle) × t",
        "out": "mJ per inference, J per token",
        "clock": "Same clock for samples and markers",
    },
    "pt": {
        "power_path": "CAMINHO DA ENERGIA",
        "charger": ("Carregador USB-C PD", "65–100 W"),
        "fnb58": ("FNIRSI FNB58", "medidor USB, V e I"),
        "trigger": ("Cabo trigger PD", "USB-C → barrel, 20 V"),
        "evk": ("IQ-9075 EVK", "entrada barrel, 12–36 V"),
        "usbc": "USB-C",
        "barrel": "barrel",
        "order": "Conecte o cabo de dados por último: o FNB58 precisa ligar pelo carregador, senão o PD fica em 5 V.",
        "data": "porta de dados (HID), 100 amostras/s",
        "mac": "MAC",
        "logger": ("fnb58_log.py", "uma sessão longa", "→ session.csv"),
        "bench": ("power_bench.py run", "roteiro de fases, repouso entre elas", "→ markers.csv (início, fim)"),
        "ssh": "SSH pelo Wi-Fi",
        "ssh2": "benchmark_model, geniex",
        "report": ("power_bench.py report", "potência média em cada janela estável"),
        "formula": "E = P × t\u2003\u2003dinâmica: (P − P_repouso) × t",
        "out": "mJ por inferência, J por token",
        "clock": "Mesmo relógio para amostras e marcadores",
    },
}


def text(x, y, s, size=14, color=INK, weight="normal", anchor="middle", family="sans", style="normal"):
    fam = "Menlo, Consolas, monospace" if family == "mono" else "Helvetica Neue, Helvetica, Arial, sans-serif"
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{size}" fill="{color}" '
            f'font-weight="{weight}" font-style="{style}" text-anchor="{anchor}">{s}</text>')


def box(x, y, w, h, lines, fill=BOX, stroke=LINE, mono_first=False):
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>']
    cy = y + h / 2 - (len(lines) - 1) * 10 + 5
    for i, s in enumerate(lines):
        if i == 0:
            out.append(text(x + w / 2, cy, s, 15, INK, "bold", family="mono" if mono_first else "sans"))
        else:
            out.append(text(x + w / 2, cy + i * 21, s, 12.5, INK2))
    return out


def arrow(points, color, width=2, dash=None, both=False):
    d = "M" + " L".join(f"{x},{y}" for x, y in points)
    da = f' stroke-dasharray="{dash}"' if dash else ""
    mid = color.lstrip("#")
    ms = f' marker-start="url(#a{mid})"' if both else ""
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"{da} '
            f'stroke-linejoin="round" marker-end="url(#a{mid})"{ms}/>')


def markers(colors):
    m = []
    for c in colors:
        cid = c.lstrip("#")
        m.append(f'<marker id="a{cid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="11" markerHeight="11" markerUnits="userSpaceOnUse" '
                 f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>')
    return m


def build(lang):
    tx = T[lang]
    W, H = 1070, 640
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
         "<defs>", *markers([INK, DATA, INK2]), "</defs>",
         f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>']

    # power path
    s.append(text(30, 38, tx["power_path"], 12, MUTED, "bold", anchor="start"))
    y, h, w = 56, 88, 190
    xs = [30, 305, 580, 855]
    s += box(xs[0], y, w, h, tx["charger"])
    s += box(xs[1], y, w, h, tx["fnb58"])
    s += box(xs[2], y, w, h, tx["trigger"])
    s += box(xs[3], y, w, h, tx["evk"], stroke=INK)
    for (a, lab) in ((0, tx["usbc"]), (1, tx["usbc"]), (2, tx["barrel"])):
        x0, x1 = xs[a] + w, xs[a + 1]
        s.append(arrow([(x0 + 4, y + h / 2), (x1 - 4, y + h / 2)], INK, 3))
        s.append(text((x0 + x1) / 2, y + h / 2 - 14, lab, 12, INK2))
    s.append(text(xs[1], 38, tx["order"], 12.5, INK2, anchor="start", style="italic"))

    # mac container
    mx, my, mw, mh = 30, 228, 730, 392
    s.append(f'<rect x="{mx}" y="{my}" width="{mw}" height="{mh}" rx="12" fill="{MAC}" stroke="{LINE}" stroke-width="1.5"/>')
    s.append(text(mx + 18, my + 28, tx["mac"], 12, MUTED, "bold", anchor="start"))

    lx, ly, lw, lh = 60, 290, 300, 100
    bx, by, bw, bh = 430, 290, 300, 100
    rx, ry, rw, rh = 260, 440, 400, 120
    s += box(lx, ly, lw, lh, tx["logger"], mono_first=True)
    s += box(bx, by, bw, bh, tx["bench"], mono_first=True)
    s.append(f'<rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" rx="8" fill="{BOX}" stroke="{INK}" stroke-width="1.5"/>')
    s.append(text(rx + rw / 2, ry + 28, tx["report"][0], 15, INK, "bold", family="mono"))
    s.append(text(rx + rw / 2, ry + 52, tx["report"][1], 12.5, INK2))
    s.append(text(rx + rw / 2, ry + 78, tx["formula"], 13, INK, family="mono"))
    s.append(text(rx + rw / 2, ry + 104, tx["out"], 12.5, INK2, "bold"))

    # FNB58 data port -> logger
    fx = xs[1] + w / 2
    s.append(arrow([(fx, y + h + 4), (fx, 205), (lx + lw / 2, 205), (lx + lw / 2, ly - 4)], DATA, 2, "6 4"))
    s.append(text(fx + 10, 192, tx["data"], 12, DATA, anchor="start"))

    # SSH bench <-> EVK
    ex = xs[3] + w / 2
    s.append(arrow([(bx + bw + 4, by + bh / 2), (ex, by + bh / 2), (ex, y + h + 4)], INK2, 2, "3 4", both=True))
    cx = (mx + mw + ex) / 2
    s.append(text(cx, by + bh / 2 - 30, tx["ssh"], 12.5, INK2, "bold"))
    s.append(text(cx, by + bh / 2 - 12, tx["ssh2"], 11.5, INK2, family="mono"))

    # into report
    s.append(arrow([(lx + lw / 2, ly + lh + 4), (lx + lw / 2, ry + rh / 2), (rx - 4, ry + rh / 2)], INK2, 1.6))
    s.append(arrow([(bx + bw / 2, by + bh + 4), (bx + bw / 2, ry - 4)], INK2, 1.6))
    s.append(text(mx + mw - 18, my + mh - 16, tx["clock"], 12, INK2, anchor="end", style="italic"))

    s.append("</svg>")
    return "\n".join(s)


CPU_C, GPU_C, NPU_C = "#eb6834", "#1baf7a", "#2a78d6"

SW = {
    "en": {
        "h1": "TFLITE (VISION)", "h2": "GENIEX · QAIRT", "h3": "GENIEX · LLAMA.CPP",
        "e1": ("benchmark_model", "gst-ai-* apps", ".tflite INT8 models"),
        "e2": ("geniex infer", "qualcomm/Qwen3-4B", "W4A16 bundle, AI Hub"),
        "e3": ("geniex infer", "unsloth/…-GGUF", "Q4_0, Hugging Face"),
        "r1": ("TensorFlow Lite",), "r2": ("QAIRT (Genie)",), "r3": ("llama.cpp",),
        "b1": [("XNNPACK", "8 threads"), ("GPU delegate", "FP16/FP32"), ("QNN delegate", "libQnnHtp")],
        "b2": [("QNN HTP", "precompiled graph")],
        "b3": [("-c cpu", "CPU kernels"), ("-c gpu", "OpenCL", "rejected by driver"),
               ("-c npu", "Hexagon backend", "0.8B ok, 4B failed")],
        "container": "GenieX container: docker --privileged, host /usr/lib mounted read-only at /opt/qcom-lib",
        "cpu": ("CPU", "8× Kryo Gen 6"), "gpu": ("GPU", "Adreno 663"), "npu": ("NPU", "Hexagon HTP V73"),
        "fastrpc": "FastRPC",
        "mem": "LPDDR5, 36 GB, ~77 GB/s, shared by every processor",
    },
    "pt": {
        "h1": "TFLITE (VISÃO)", "h2": "GENIEX · QAIRT", "h3": "GENIEX · LLAMA.CPP",
        "e1": ("benchmark_model", "apps gst-ai-*", "modelos .tflite INT8"),
        "e2": ("geniex infer", "qualcomm/Qwen3-4B", "bundle W4A16, AI Hub"),
        "e3": ("geniex infer", "unsloth/…-GGUF", "Q4_0, Hugging Face"),
        "r1": ("TensorFlow Lite",), "r2": ("QAIRT (Genie)",), "r3": ("llama.cpp",),
        "b1": [("XNNPACK", "8 threads"), ("Delegate GPU", "FP16/FP32"), ("Delegate QNN", "libQnnHtp")],
        "b2": [("QNN HTP", "grafo pré-compilado")],
        "b3": [("-c cpu", "kernels de CPU"), ("-c gpu", "OpenCL", "recusado pelo driver"),
               ("-c npu", "backend Hexagon", "0.8B ok, 4B falhou")],
        "container": "Contêiner GenieX: docker --privileged, /usr/lib do host montado só leitura em /opt/qcom-lib",
        "cpu": ("CPU", "8× Kryo Gen 6"), "gpu": ("GPU", "Adreno 663"), "npu": ("NPU", "Hexagon HTP V73"),
        "fastrpc": "FastRPC",
        "mem": "LPDDR5, 36 GB, ~77 GB/s, compartilhada por todos os processadores",
    },
}


def small_box(x, y, w, h, lines, stroke=LINE, dash=None):
    da = f' stroke-dasharray="{dash}"' if dash else ""
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="{BOX}" stroke="{stroke}" stroke-width="1.5"{da}/>']
    cy = y + h / 2 - (len(lines) - 1) * 9 + 4
    for i, t in enumerate(lines):
        if i == 0:
            out.append(text(x + w / 2, cy, t, 13, INK, "bold", family="mono" if t.startswith("-c") else "sans"))
        else:
            out.append(text(x + w / 2, cy + i * 18, t, 11.5, INK2))
    return out


def line(points, color, width=2.2, dash=None, halo=True):
    d = "M" + " L".join(f"{x},{y}" for x, y in points)
    da = f' stroke-dasharray="{dash}"' if dash else ""
    out = []
    if halo:
        out.append(f'<path d="{d}" fill="none" stroke="{SURFACE}" stroke-width="{width + 5}" stroke-linejoin="round"/>')
    out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"{da} stroke-linejoin="round"/>')
    return out


def build_software(lang):
    tx = SW[lang]
    W, H = 1090, 650
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
         "<defs>", *markers([INK2, CPU_C, GPU_C, NPU_C]), "</defs>",
         f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>']
    cols = [(30, 330), (400, 240), (680, 380)]  # x, width
    # container around the two GenieX columns
    s.append(f'<rect x="385" y="48" width="{W - 385 - 15}" height="345" rx="12" fill="{MAC}" '
             f'stroke="{INK2}" stroke-width="1.2" stroke-dasharray="6 4"/>')
    s.append(text(400, 36, tx["container"], 11.5, INK2, anchor="start", style="italic"))
    for (x, w), h in zip(cols, ("h1", "h2", "h3")):
        s.append(text(x + w / 2, 70, tx[h], 12, MUTED, "bold"))
    ey, eh, ry, rh, by, bh = 82, 74, 186, 50, 272, 80
    for (x, w), e, r in zip(cols, ("e1", "e2", "e3"), ("r1", "r2", "r3")):
        s += small_box(x, ey, w, eh, tx[e])
        s += small_box(x, ry, w, rh, tx[r])
        s.append(arrow([(x + w / 2, ey + eh + 3), (x + w / 2, ry - 3)], INK2, 1.6))
    # backends and the processor each one targets
    targets = []
    for (x, w), key, kinds in zip(cols, ("b1", "b2", "b3"),
                                  (("cpu", "gpu", "npu"), ("npu",), ("cpu", "gpu", "npu"))):
        n = len(tx[key])
        gap = 12
        bw = (w - gap * (n - 1)) / n
        for i, (lines, kind) in enumerate(zip(tx[key], kinds)):
            bx = x + i * (bw + gap)
            failed = key == "b3" and kind == "gpu"
            s += small_box(bx, by, bw, bh, lines, dash="5 4" if failed else None)
            cx = bx + bw / 2
            fan = ry + rh + 16
            s += line([(x + w / 2, ry + rh), (x + w / 2, fan), (cx, fan), (cx, by - 3)], INK2, 1.4, halo=False)
            targets.append((cx, kind, failed))
    # processors
    hy, hh = 478, 66
    hw = {"cpu": (30, 300), "gpu": (400, 240), "npu": (700, 360)}
    drop = {"cpu": 180, "gpu": 470, "npu": 880}
    bus = {"npu": 412, "gpu": 432, "cpu": 452}
    color = {"cpu": CPU_C, "gpu": GPU_C, "npu": NPU_C}
    for kind in ("npu", "gpu", "cpu"):
        xs_ = [c for c, k, _ in targets if k == kind] + [drop[kind]]
        s += line([(min(xs_), bus[kind]), (max(xs_), bus[kind])], color[kind])
    for cx, kind, failed in targets:
        s += line([(cx, by + bh), (cx, bus[kind])], color[kind], dash="5 4" if failed else None)
    for kind in ("cpu", "gpu", "npu"):
        x, w = hw[kind]
        s.append(arrow([(drop[kind], bus[kind]), (drop[kind], hy - 3)], color[kind], 2.2))
        s.append(f'<rect x="{x}" y="{hy}" width="{w}" height="{hh}" rx="8" fill="{BOX}" stroke="{color[kind]}" stroke-width="2"/>')
        name, sub = tx[kind]
        s.append(text(x + w / 2, hy + 29, name, 15, INK, "bold"))
        s.append(text(x + w / 2, hy + 50, sub, 12, INK2))
    s.append(text(drop["npu"] + 10, hy - 10, tx["fastrpc"], 11.5, INK2, anchor="start", style="italic"))
    # shared memory
    my = 586
    for kind in ("cpu", "gpu", "npu"):
        x, w = hw[kind]
        s.append(f'<path d="M{x + w / 2},{hy + hh} L{x + w / 2},{my}" stroke="{LINE}" stroke-width="3"/>')
    s.append(f'<rect x="30" y="{my}" width="{W - 60}" height="40" rx="8" fill="{MAC}" stroke="{INK2}" stroke-width="1.2"/>')
    s.append(text(W / 2, my + 25, tx["mem"], 13, INK, "bold"))
    s.append("</svg>")
    return "\n".join(s)


PL = {
    "en": {
        "title": "gst-ai-object-detection: one GStreamer pipeline, 30 FPS",
        "src": ("Source", "H.264 MP4", "or USB camera"),
        "vpu": ("VPU", "hardware decode"),
        "gpu": ("GPU", "convert, resize"),
        "npu": ("NPU", "YOLOX INT8, ~3 ms", "~10% of NPU time"),
        "cpu": ("CPU", "postprocess,", "orchestration"),
        "dpu": ("Display", "compose, HDMI"),
        "llm": ("Qwen3-4B (GenieX)", "prefill + decode, long prompt"),
        "llm_npu": "QAIRT run", "llm_cpu": "llama.cpp run",
        "mem": "LPDDR5, ~77 GB/s: frames, buffers, model weights, KV cache",
        "res1": "Video: 30 FPS, no extra dropped frames in either run.",
        "res2": "LLM decode: −6% with the LLM on the NPU, −12% on the CPU. Memory is the shared resource.",
        "npu_share": "YOLOX uses ~10% of NPU time",
    },
    "pt": {
        "title": "gst-ai-object-detection: um pipeline GStreamer, 30 FPS",
        "src": ("Fonte", "MP4 H.264", "ou câmera USB"),
        "vpu": ("VPU", "decodificação", "em hardware"),
        "gpu": ("GPU", "conversão de cor,", "redimensionamento"),
        "npu": ("NPU", "YOLOX INT8, ~3 ms", "~10% do tempo da NPU"),
        "cpu": ("CPU", "pós-processamento,", "coordenação"),
        "dpu": ("Display", "composição, HDMI"),
        "llm": ("Qwen3-4B (GenieX)", "prefill + decode, prompt longo"),
        "llm_npu": "execução QAIRT", "llm_cpu": "execução llama.cpp",
        "mem": "LPDDR5, ~77 GB/s: quadros, buffers, pesos dos modelos, cache KV",
        "res1": "Vídeo: 30 FPS, nenhum quadro perdido a mais em nenhuma das execuções.",
        "res2": "Decode do LLM: −6% com o LLM na NPU, −12% na CPU. A memória é o recurso compartilhado.",
        "npu_share": "o YOLOX ocupa ~10% do tempo da NPU",
    },
}


def build_pipeline(lang):
    tx = PL[lang]
    W, H = 1090, 470
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
         "<defs>", *markers([INK, INK2, CPU_C, NPU_C]), "</defs>",
         f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>']
    s.append(text(30, 34, tx["title"], 13, MUTED, "bold", anchor="start"))
    keys = ["src", "vpu", "gpu", "npu", "cpu", "dpu"]
    stroke = {"gpu": GPU_C, "npu": NPU_C, "cpu": CPU_C}
    bw, gap, y, h = 150, 30, 172, 96
    xs_ = [30 + i * (bw + gap) for i in range(6)]
    # LLM above NPU and CPU: one run on each
    lx, ly, lw, lh = xs_[3] - 10, 52, 2 * bw + gap + 20, 60
    s.append(f'<rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" rx="8" fill="{BOX}" stroke="{INK2}" stroke-width="1.5"/>')
    s.append(text(lx + lw / 2, ly + 25, tx["llm"][0], 15, INK, "bold"))
    s.append(text(lx + lw / 2, ly + 45, tx["llm"][1], 12, INK2))
    nx, cx = xs_[3] + bw / 2, xs_[4] + bw / 2
    s.append(arrow([(nx, ly + lh + 3), (nx, y - 3)], NPU_C, 2, "6 4"))
    s.append(arrow([(cx, ly + lh + 3), (cx, y - 3)], CPU_C, 2, "6 4"))
    s.append(text(nx - 8, ly + lh + 36, tx["llm_npu"], 11.5, NPU_C, anchor="end"))
    s.append(text(cx + 8, ly + lh + 36, tx["llm_cpu"], 11.5, CPU_C, anchor="start"))
    # pipeline row
    for k, x in zip(keys, xs_):
        st = stroke.get(k, LINE)
        s.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{h}" rx="8" fill="{BOX}" stroke="{st}" '
                 f'stroke-width="{2 if k in stroke else 1.5}"/>')
        lines = tx[k]
        cy = y + h / 2 - (len(lines) - 1) * 10 + 5
        for i, t in enumerate(lines):
            s.append(text(x + bw / 2, cy + i * 21, t, 15 if i == 0 else 12, INK if i == 0 else INK2,
                          "bold" if i == 0 else "normal"))
    for a, b in zip(xs_, xs_[1:]):
        s.append(arrow([(a + bw + 3, y + h / 2), (b - 3, y + h / 2)], INK, 2.6))
    # shared memory
    my = 316
    for x in xs_[1:]:
        s.append(f'<path d="M{x + bw / 2},{y + h} L{x + bw / 2},{my}" stroke="{LINE}" stroke-width="3"/>')
    s.append(f'<rect x="30" y="{my}" width="{W - 60}" height="44" rx="8" fill="{MAC}" stroke="{INK2}" stroke-width="1.2"/>')
    s.append(text(W / 2, my + 28, tx["mem"], 13.5, INK, "bold"))
    s.append(text(30, 404, tx["res1"], 13, INK, anchor="start"))
    s.append(text(30, 430, tx["res2"], 13, INK, anchor="start"))
    s.append("</svg>")
    return "\n".join(s)

def main():
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (("energy-setup", build), ("software-paths", build_software),
                     ("video-pipeline", build_pipeline)):
        for lang in ("en", "pt"):
            svg = os.path.join(OUT, f"{name}-{lang}.svg")
            open(svg, "w").write(fn(lang))
            png = svg[:-4] + ".png"
            subprocess.run(["rsvg-convert", "-z", "2", "-o", png, svg], check=True)
            print(png)


if __name__ == "__main__":
    main()
