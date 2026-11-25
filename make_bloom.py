#!/usr/bin/env python3
"""
make_bloom.py  --  builds bloom.html, a self-contained ASCII animation:

    abstract glitch artifacts  ->  converge into a bud  ->  a 3D rose blooms
    ->  "Alina, I love you" assembles out of the artifacts  ->  everything
    dissolves back into noise and the loop restarts.

Python's job : generate the rose geometry (Nylander's parametric rose),
               rasterise the message into ASCII-cell masks with Pillow,
               and write the HTML file.
Browser's job: animate + rasterise to characters (canvas, ~60 fps).

Usage:  python3 make_bloom.py [out.html] [--text "Alina, I love you"]
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
CELL_ASPECT = 0.52           # monospace cell width / height
N_POINTS = 15000
SEED = 7


# ------------------------------------------------------------------ rose ---
def rose_points(n, rng):
    """Sample the parametric rose: returns x, theta, R (petal modulation)."""
    # theta runs from the outer petals (-2pi) to the tight centre (15pi)
    theta = rng.uniform(-2 * math.pi, 15 * math.pi, n)
    # more samples toward the tip (bigger area), but keep the base covered
    x = np.sqrt(rng.uniform(0.01, 1.0, n))
    R = 1 - 0.5 * ((5 / 4) * (1 - np.mod(3.6 * theta, 2 * math.pi) / math.pi) ** 2 - 0.25) ** 2
    return x, theta, R


# ------------------------------------------------------------------ text ---
def find_font():
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return p
    raise SystemExit("No bold font found; edit FONT_CANDIDATES.")


def text_mask(lines, rows_per_line, gap_rows, font_path):
    """Rasterise text into a grid of ASCII cells -> (w, h, flat [r,c,v,...])."""
    font = ImageFont.truetype(font_path, 220)
    imgs = []
    for ln in lines:
        l, t, r, b = font.getbbox(ln)
        im = Image.new("L", (r - l + 40, b - t + 40), 0)
        ImageDraw.Draw(im).text((20 - l, 20 - t), ln, font=font, fill=255)
        imgs.append(im.crop(im.getbbox()))
    # one shared scale so every line has the same letter size
    line_h = max(im.height for im in imgs)
    cells = []
    for im in imgs:
        h = rows_per_line
        w = max(1, round(im.width / line_h * h / CELL_ASPECT))
        cells.append(np.asarray(im.resize((w, round(h * im.height / line_h)), Image.LANCZOS)))
    W = max(c.shape[1] for c in cells)
    H = rows_per_line * len(lines) + gap_rows * (len(lines) - 1)
    grid = np.zeros((H, W), dtype=np.uint8)
    y = 0
    for c in cells:
        x0 = (W - c.shape[1]) // 2
        # align every line to the same row band (bottom aligned inside band)
        yy = y + rows_per_line - c.shape[0]
        grid[yy:yy + c.shape[0], x0:x0 + c.shape[1]] = c
        y += rows_per_line + gap_rows
    flat = []
    for r, c in zip(*np.nonzero(grid > 45)):
        flat += [int(r), int(c), int(grid[r, c])]
    return {"w": int(W), "h": int(H), "cells": flat}


# ------------------------------------------------------------------ main ---
def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = Path(args[0]) if args else Path(__file__).with_name("bloom.html")
    msg = "Alina you so beatiful"
    if "--text" in sys.argv:
        msg = sys.argv[sys.argv.index("--text") + 1]

    rng = np.random.default_rng(SEED)
    x, th, R = rose_points(N_POINTS, rng)
    font = find_font()

    words = msg.split(" ")
    # two-line layout for narrow screens: first word | rest
    two = [words[0], " ".join(words[1:])] if len(words) > 1 else [msg]
    data = {
        "x": [round(float(v), 4) for v in x],
        "th": [round(float(v), 4) for v in th],
        "R": [round(float(v), 4) for v in R],
        "single": text_mask([msg], 9, 0, font),
        "double": text_mask(two, 7, 2, font),
        "msg": msg,
    }
    tpl = Path(__file__).with_name("template.html").read_text(encoding="utf-8")
    html = tpl.replace("__DATA__", json.dumps(data, separators=(",", ":"))).replace("__TITLE__", msg)
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out}  ({out.stat().st_size/1024:.0f} KB, {N_POINTS} rose points, "
          f"text {data['single']['w']}x{data['single']['h']} cells)")


if __name__ == "__main__":
    main()
