#!/usr/bin/env python3
"""Reproduce the provincial-GDP figure: read provincial-gdp-sum-vs-national.csv →
HTML+SVG → 2x PNG via headless Chrome.

Sits in public/data/ because it is published: readers can regenerate the figure from the CSV.
Not part of the site build — the PNG is rendered once here and committed.

Usage:
  python3 public/data/make_figure_provincial_gdp.py
Writes build/fig-provincial-gdp.html + public/figures/provincial-gdp-sum-vs-national.png
Data source: National Bureau of Statistics of China, see the CSV header.
"""
import csv
import json
import os
import re
import subprocess
import sys
from decimal import Decimal, ROUND_HALF_UP

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CSV = os.path.join(HERE, "provincial-gdp-sum-vs-national.csv")
FONT = os.path.join(ROOT, "public", "fonts", "inter-var.woff2")
OUT_HTML = os.path.join(ROOT, "build", "fig-provincial-gdp.html")
OUT_PNG = os.path.join(ROOT, "public", "figures", "provincial-gdp-sum-vs-national.png")
W = 1440
WIN = W - 80
SCALE = 2

rows = []
with open(CSV) as f:
    for r in csv.DictReader([l for l in f if not l.startswith("#")]):
        rows.append({k: (int(v) if k == "year" else float(v)) for k, v in r.items()})
by_year = {r["year"]: r for r in rows}
YEARS = [r["year"] for r in rows]
assert YEARS == list(range(2015, 2025)), YEARS

# gaps as printed in the article's table (percent of the national preliminary figure),
# carried in the CSV so the figure and the table agree; the computed value is checked against it.
GAP = {y: by_year[y]["gap_vs_prelim_pct"] for y in YEARS}
for y in YEARS:
    r = by_year[y]
    calc = (r["provincial_sum_trn"] - r["national_prelim_trn"]) / r["national_prelim_trn"] * 100
    assert abs(calc - GAP[y]) < 0.02, (y, calc, GAP[y])
assert abs(GAP[2015] - 6.81) < 0.001 and abs(GAP[2019] + 0.56) < 0.001, GAP


def fmt1(v):
    """One decimal, half away from zero — printed labels must not depend on float repr."""
    return f"{Decimal(str(v)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP):+.1f}"


OFFSCALE = []


def panel(x0, y0, w, h, title, unit, lo, hi, yticks, draw, note=None):
    pad_l, pad_b, pad_t, pad_r = 96, 52, 60, 300
    px, py = x0 + pad_l, y0 + pad_t
    pw, ph = w - pad_l - pad_r, h - pad_t - pad_b

    def sx(year):
        return px + (year - YEARS[0]) / (YEARS[-1] - YEARS[0]) * pw

    def sy(v):
        return py + ph - (v - lo) / (hi - lo) * ph

    out = [f'<text class="ptitle" x="{x0}" y="{y0 + 26}">{title}</text>',
           f'<text class="pun" x="{x0}" y="{y0 + 50}">{unit}</text>']
    for t in yticks:
        yy = sy(t)
        out.append(f'<line class="hair" x1="{px}" y1="{yy:.1f}" x2="{px + pw:.1f}" y2="{yy:.1f}"/>')
        lbl = f"{t:+g}" if lo < 0 else f"{t:g}"
        out.append(f'<text class="tick" x="{px - 12}" y="{yy + 5:.1f}" text-anchor="end">{lbl}</text>')
    for yr in YEARS:
        xx = sx(yr)
        out.append(f'<text class="tick" x="{xx:.1f}" y="{py + ph + 30:.1f}" text-anchor="middle">{yr}</text>')
    if lo < 0:                      # zero line, heavier
        out.append(f'<line class="zero" x1="{px}" y1="{sy(0):.1f}" x2="{px + pw:.1f}" y2="{sy(0):.1f}"/>')
    out.append(f'<line class="axis" x1="{px}" y1="{py}" x2="{px}" y2="{py + ph}"/>')
    out += draw(px, py, pw, ph, sx, sy)
    if note:
        out.append(note(px, py, pw, ph, sx, sy))
    return "\n".join(out)


def draw_levels(px, py, pw, ph, sx, sy):
    out = []
    for key, cls, label in (("national_prelim_trn", "l-grey", "National figure (preliminary)"),
                            ("provincial_sum_trn", "l-focus", "Sum of the 31 provinces")):
        pts = [(y, by_year[y][key]) for y in YEARS]
        for y, v in pts:
            if v > hi_levels or v < lo_levels:
                OFFSCALE.append((key, y, v))
        d = " ".join(f'{"M" if i == 0 else "L"}{sx(y):.1f},{sy(v):.1f}' for i, (y, v) in enumerate(pts))
        out.append(f'<path class="{cls}" d="{d}"/>')
        ys, vs = pts[-1]
        out.append(f'<circle class="{"dot-focus" if cls == "l-focus" else "dot"}" cx="{sx(ys):.1f}" '
                   f'cy="{sy(vs):.1f}" r="4"/>')
        out.append(f'<text class="endlabel {"el-focus" if cls == "l-focus" else ""}" '
                   f'x="{sx(ys) + 12:.1f}" y="{sy(vs) + 5:.1f}">{label}</text>')
    return out


def draw_gap(px, py, pw, ph, sx, sy):
    out = []
    slot = pw / len(YEARS)
    bw = slot * 0.46
    for y in YEARS:
        g = GAP[y]
        x = sx(y) - bw / 2
        top, bot = (sy(g), sy(0)) if g > 0 else (sy(0), sy(g))
        cls = "bar-pos" if g > 0 else "bar-neg"
        out.append(f'<rect class="{cls}" x="{x:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{bot - top:.1f}"/>')
        ty = top - 12 if g > 0 else bot + 24
        out.append(f'<text class="barval" x="{x + bw / 2:.1f}" y="{ty:.1f}" text-anchor="middle">'
                   f'{fmt1(g)}</text>')
    return out


def note_levels(px, py, pw, ph, sx, sy):
    return (f'<text class="annot" x="{sx(2019) + 12:.1f}" y="{sy(74):.1f}">'
            f'the lines cross in 2019</text>')


def note_gap(px, py, pw, ph, sx, sy):
    x19 = sx(2019)
    return "\n".join([
        f'<line class="vline" x1="{x19:.1f}" y1="{py}" x2="{x19:.1f}" y2="{py + ph}"/>',
        f'<text class="annot" x="{x19 + 14:.1f}" y="{py + 34}">2019: unified regional accounting begins</text>',
    ])


lo_levels, hi_levels = 60.0, 140.0

panels = [
    panel(0, 0, WIN, 430, "The two totals", "trillion yuan, current prices",
          lo_levels, hi_levels, [60, 80, 100, 120, 140], draw_levels, note_levels),
    panel(0, 490, WIN, 500, "The difference", "sum of the provinces minus the national figure, %",
          -1.5, 7.5, [-1, 0, 2, 4, 6, 7.5 - 0.5], draw_gap, note_gap),
]

HTML = f"""<!doctype html><meta charset="utf-8"><title>provincial GDP figure</title>
<style>
  @font-face {{ font-family:'Inter'; src:url('file://{FONT}') format('woff2-variations');
               font-weight:100 900; font-style:normal; }}
  :root {{ --ink:#1c1a17; --ink2:#57534b; --ink3:#8b857a; --hair:#e6e1d8; --accent:#b8562f;
           --grey:#8d8880; --neg:#4f6f8f; --paper:#fdfcfa; }}
  * {{ box-sizing:border-box }}
  html,body {{ margin:0; background:var(--paper); }}
  .fig {{ width:{W}px; padding:44px 40px 28px; font-family:'Inter','Helvetica Neue',Arial,sans-serif; color:var(--ink); }}
  .headline {{ font-size:38px; font-weight:700; letter-spacing:-.01em; margin:0 0 12px; line-height:1.15 }}
  .deck {{ font-size:19px; color:var(--ink2); margin:0 0 26px; max-width:1180px; line-height:1.45 }}
  .ptitle {{ font-size:23px; font-weight:650; fill:var(--ink) }}
  .pun {{ font-size:17px; fill:var(--ink2) }}
  .tick {{ font-size:16px; fill:var(--ink3); font-variant-numeric:tabular-nums }}
  .hair {{ stroke:var(--hair); stroke-width:1 }}
  .axis {{ stroke:#b9b2a6; stroke-width:1.4 }}
  .zero {{ stroke:#8b857a; stroke-width:1.6 }}
  .l-focus {{ fill:none; stroke:var(--accent); stroke-width:3.4; stroke-linejoin:round }}
  .l-grey {{ fill:none; stroke:var(--grey); stroke-width:2.4 }}
  .dot {{ fill:var(--grey) }} .dot-focus {{ fill:var(--accent) }}
  .endlabel {{ font-size:17px; fill:var(--ink2) }} .el-focus {{ fill:var(--accent); font-weight:650 }}
  .bar-pos {{ fill:var(--accent) }} .bar-neg {{ fill:var(--neg) }}
  .barval {{ font-size:16px; fill:var(--ink2); font-variant-numeric:tabular-nums }}
  .annot {{ font-size:21px; fill:var(--ink2) }}
  .annot2 {{ font-size:17px; fill:var(--ink3) }}
  .vline {{ stroke:var(--ink3); stroke-width:1; stroke-dasharray:5 5; opacity:.7 }}
  .foot {{ margin-top:26px; font-size:15px; color:var(--ink3); line-height:1.5 }}
  .foot b {{ color:var(--ink2); font-weight:600 }}
</style>
<div class="fig" data-qa>
  <div class="headline" data-qa>China&rsquo;s provinces used to add up to more than the country.</div>
  <div class="deck" data-qa>China publishes GDP twice: once nationally, once for each of its 31 provincial-level units.
    Add the provinces up and the total does not match the national figure &mdash; 6.81% above it in 2015, and
    between 0.35% and 0.77% below it in every year since the 2019 unified accounting reform.</div>
  <svg width="{WIN}" height="1030" viewBox="0 0 {WIN} 1030" data-qa>
    {"".join(panels)}
  </svg>
  <div class="foot" data-qa><b>Data:</b> National Bureau of Statistics of China &mdash; the 31 provincial GDP values are from the
    China Statistical Yearbook regional table (3-9, one edition per data year); the national figures are the annual GDP
    communiqu&eacute;s and the later verification or census revisions. All reads 2026-10-11 (CST). The national line is the
    preliminary vintage; against the later revisions the same years run from &minus;0.10% to &minus;1.00%, with 2023 at
    &minus;3.35% after the fifth economic census.
    <b>Reuse:</b> figure and data CC BY 4.0 &mdash; copy them, link back to this page.</div>
</div>
<pre id="qa" style="display:none"></pre>
<script>
  const innermost = [...document.querySelectorAll('[data-qa]')].filter(el => !el.querySelector('[data-qa]'));
  const fig = document.querySelector('.fig').getBoundingClientRect();
  const boxes = innermost.map(el => ({{ el, r: el.getBoundingClientRect(), t: (el.textContent||'').trim().slice(0,40) }}))
                         .filter(b => b.t.length);
  const outOfBox = boxes.filter(b => b.r.left < fig.left - 0.5 || b.r.right > fig.right + 0.5 ||
                                     b.r.top < fig.top - 0.5 || b.r.bottom > fig.bottom + 0.5)
                        .map(b => b.t);
  const overlaps = [];
  for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {{
    const a = boxes[i].r, b = boxes[j].r;
    const ox = Math.min(a.right,b.right) - Math.max(a.left,b.left);
    const oy = Math.min(a.bottom,b.bottom) - Math.max(a.top,b.top);
    if (ox > 0 && oy > 0 && ox * oy > 80) overlaps.push([boxes[i].t, boxes[j].t, Math.round(ox*oy)]);
  }}
  const svg = document.querySelector('svg');
  const svgBox = svg.getBoundingClientRect();
  const clipped = [...svg.querySelectorAll('text')].filter(t => {{
    const r = t.getBoundingClientRect();
    return r.left < svgBox.left - 0.5 || r.right > svgBox.right + 0.5 || r.top < svgBox.top - 0.5 || r.bottom > svgBox.bottom + 0.5;
  }}).map(t => (t.textContent||'').slice(0,40));
  document.getElementById('qa').textContent = JSON.stringify({{
    height: Math.ceil(document.body.scrollHeight), width: document.body.scrollWidth,
    outOfBox, overlaps, clipped,
    overflowX: document.body.scrollWidth > {W}
  }});
</script>
"""

os.makedirs(os.path.dirname(OUT_HTML), exist_ok=True)
os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)
open(OUT_HTML, "w").write(HTML)
print("wrote", OUT_HTML)

dump = subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                       "--force-device-scale-factor=1", "--virtual-time-budget=4000", "--dump-dom",
                       f"file://{OUT_HTML}"], capture_output=True, text=True).stdout
m = re.search(r'<pre id="qa"[^>]*>(.*?)</pre>', dump, re.S)
qa = json.loads(m.group(1)) if m else {"error": "qa not found"}
print("QA:", json.dumps(qa, ensure_ascii=False)[:600])
print("OFFSCALE (points outside the y range):", OFFSCALE if OFFSCALE else "0")
if OFFSCALE:
    print("!! series point outside the drawn y range — widen it", file=sys.stderr)
    sys.exit(4)

subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                f"--force-device-scale-factor={SCALE}", "--virtual-time-budget=4000",
                f"--window-size={W},{qa.get('height', 1200)}", f"--screenshot={OUT_PNG}",
                f"file://{OUT_HTML}"], capture_output=True)
print("wrote", OUT_PNG, os.path.getsize(OUT_PNG), "bytes")
sys.exit(0 if not (qa.get("overlaps") or qa.get("clipped") or qa.get("overflowX") or qa.get("outOfBox")) else 3)
