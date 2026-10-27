#!/usr/bin/env python3
"""Annotated top view of the IQ-9075 EVK mainboard, in English and Portuguese.

Base image: Qualcomm (used with permission), figures/qualcomm-iq9075-board-top.jpg, which is the
PNG embedded in source/kit-front.svg resized to 1600 px. figures/qualcomm-iq9075-evk-front.jpg is
source/9075-EVK7.svg rendered with rsvg-convert at 1756 px.
Connector functions checked against Qualcomm's IQ-9075 EVK device overview.
Writes figures/board-annotated-{en,pt}.jpg.
"""
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FIG = os.path.join(ROOT, "figures")

INK, INK2, SURFACE, ACCENT = "#0b0b0b", "#52514e", "#fcfcfb", "#2a78d6"
FONT = "/System/Library/Fonts/HelveticaNeue.ttc"
L, R, T, B = 440, 480, 40, 300  # margins around the board image
PREVIEW_W = 1377  # point coordinates below were read on a 1377 px wide preview

# (side, point x, point y, label y or x) in preview pixels; side: left, right, bottom
ITEMS = [
    ("left", 300, 98, 70, "jls"),
    ("left", 135, 140, 190, "power"),
    ("left", 30, 470, 470, "jtag"),
    ("left", 85, 640, 640, "debug"),
    ("left", 230, 820, 820, "jexp12"),
    ("right", 895, 95, 90, "sw2"),
    ("right", 1325, 400, 400, "jcam"),
    ("right", 765, 520, 560, "m2"),
    ("right", 1050, 820, 820, "jexp34"),
    ("right", 1300, 1080, 1080, "pcie"),
    ("bottom", 130, 1340, 0, "usb2"),
    ("bottom", 300, 1330, 1, "usb0"),
    ("bottom", 495, 1330, 0, "usb1"),
    ("bottom", 705, 1310, 1, "eth"),
    ("bottom", 1010, 1320, 0, "dp"),
]

TX = {
    "en": {
        "jls": ("40-pin header (JLS1)", "3.3 V: CAN, SPI, I2C, UART, I2S"),
        "power": ("Power input", "barrel, 12–36 V"),
        "jtag": ("JTAG header", "JTAG1"),
        "debug": ("DEBUG micro-USB", "debug UART (FTDI)"),
        "jexp12": ("Mezzanine connectors", "JEXP1, JEXP2"),
        "sw2": ("DIP switch SW2", "SW2-3 on: EDL mode for flashing"),
        "jcam": ("Camera inputs", "JCAM0–3, 4× MIPI CSI"),
        "m2": ("M.2 E-key Wi-Fi", "NFA765A, Wi-Fi 6E + BT 5.3"),
        "jexp34": ("Mezzanine connectors", "JEXP3, JEXP4"),
        "pcie": ("PCIe x4 slot", "JPCIE"),
        "usb2": ("USB2", "micro-USB 2.0"),
        "usb0": ("USB0, Type-C", "host/device, ADB, flashing"),
        "usb1": ("USB1, Type-C", "host only"),
        "eth": ("ETH0", "2.5GbE"),
        "dp": ("Mini DisplayPort ×2", "JEDP0, JEDP1; HDMI via adapter"),
        "credit": "Board image: Qualcomm",
    },
    "pt": {
        "jls": ("Header de 40 pinos (JLS1)", "3,3 V: CAN, SPI, I2C, UART, I2S"),
        "power": ("Entrada de energia", "barrel, 12–36 V"),
        "jtag": ("Header JTAG", "JTAG1"),
        "debug": ("Micro-USB DEBUG", "UART de depuração (FTDI)"),
        "jexp12": ("Conectores de mezanino", "JEXP1, JEXP2"),
        "sw2": ("Chave DIP SW2", "SW2-3 ligada: modo EDL (gravação)"),
        "jcam": ("Entradas de câmera", "JCAM0–3, 4× MIPI CSI"),
        "m2": ("Wi-Fi M.2 E-key", "NFA765A, Wi-Fi 6E + BT 5.3"),
        "jexp34": ("Conectores de mezanino", "JEXP3, JEXP4"),
        "pcie": ("Slot PCIe x4", "JPCIE"),
        "usb2": ("USB2", "micro-USB 2.0"),
        "usb0": ("USB0, Type-C", "host/dispositivo, ADB, gravação"),
        "usb1": ("USB1, Type-C", "só host"),
        "eth": ("ETH0", "2.5GbE"),
        "dp": ("Mini DisplayPort ×2", "JEDP0, JEDP1; HDMI por adaptador"),
        "credit": "Imagem da placa: Qualcomm",
    },
}


def font(size, bold=False):
    return ImageFont.truetype(FONT, size, index=1 if bold else 0)


def build(lang):
    tx = TX[lang]
    board = Image.open(os.path.join(FIG, "qualcomm-iq9075-board-top.jpg"))
    k = board.width / PREVIEW_W
    W, H = L + board.width + R, T + board.height + B
    im = Image.new("RGB", (W, H), SURFACE)
    im.paste(board, (L, T))
    d = ImageDraw.Draw(im)
    f1, f2 = font(30, True), font(25)

    def pt(x, y):
        return L + x * k, T + y * k

    def leader(p, q):
        d.line([p, q], fill="white", width=9)
        d.line([p, q], fill=ACCENT, width=4)
        x, y = p
        d.ellipse([x - 11, y - 11, x + 11, y + 11], fill="white")
        d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=ACCENT)

    for side, px, py, lab, key in ITEMS:
        title, sub = tx[key]
        p = pt(px, py)
        if side in ("left", "right"):
            ly = T + lab * k
            if side == "left":
                ax = L - 22
                leader(p, (ax, ly))
                d.text((ax - 8, ly - 4), title, font=f1, fill=INK, anchor="rs")
                d.text((ax - 8, ly + 30), sub, font=f2, fill=INK2, anchor="rs")
            else:
                ax = L + board.width + 22
                leader(p, (ax, ly))
                d.text((ax + 8, ly - 4), title, font=f1, fill=INK, anchor="ls")
                d.text((ax + 8, ly + 30), sub, font=f2, fill=INK2, anchor="ls")
        else:
            ly = T + board.height + 50 + lab * 110
            leader(p, (p[0], ly))
            d.text((p[0], ly + 34), title, font=f1, fill=INK, anchor="ms")
            d.text((p[0], ly + 68), sub, font=f2, fill=INK2, anchor="ms")
    d.text((W - 30, H - 24), tx["credit"], font=font(24), fill=INK2, anchor="rs")
    out = os.path.join(FIG, f"board-annotated-{lang}.jpg")
    im.save(out, quality=88, optimize=True)
    print(out, im.size)


if __name__ == "__main__":
    for lang in ("en", "pt"):
        build(lang)
