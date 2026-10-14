# Sum of China's 31 provincial GDP figures vs the national total, 2015–2024

`public/data/provincial-gdp-sum-vs-national.csv` — one row per year, five columns.

| column | meaning |
|---|---|
| `year` | data year |
| `provincial_sum_trn` | my addition of the 31 provincial-level GDP values printed in the China Statistical Yearbook regional table (table 3-9, one edition per data year), in trillion yuan |
| `national_prelim_trn` | the preliminary national figure from that year's annual GDP communiqué (published January/February of the following year) |
| `national_rev_trn` | the latest revision of the same year (routine revision, or the fourth/fifth economic census) |
| `gap_vs_prelim_pct` | `(provincial_sum_trn − national_prelim_trn) / national_prelim_trn` in percent, computed on the unrounded sums |

## Source and method

- Source: **National Bureau of Statistics of China** — regional table 3-9 in the China
  Statistical Yearbook (one edition per data year), retrieved 2026-10-11 (CST); national
  figures from the annual GDP communiqués and NBS revisions.
- The yearbook's regional tables are published as **images**, not as tables, so the 31
  values per year were read off the image twice — an OCR pass and a separate visual read —
  and the two reads were compared before use: of the 310 cells (10 years × 31 provinces)
  both reads returned 279 and agreed on 268. The 2020 column was additionally re-derived a
  third time by summing the 31 rows of the printed table, giving 1,012,415.02 亿元 against
  101.24 trillion yuan in this CSV (+0.001%).

## What the numbers show, in one line

Before the 2019 unified accounting reform the provincial figures added up to well **more**
than the national total (+6.81% in 2015); since then they add up to slightly **less**
(−0.35% to −0.77%). Both are official numbers — the gap is a property of how the two
levels are compiled, not of anyone's arithmetic.

## Figure

`public/figures/provincial-gdp-sum-vs-national.png` — 2880 × 2672 px, rendered from this CSV.

Regenerate it with:

```bash
python3 public/data/make_figure_provincial_gdp.py
```

The script reads the CSV, builds an HTML/SVG chart and renders a 2× PNG through headless
Chrome. It needs `public/fonts/inter-var.woff2` (Inter, SIL Open Font License — see
`public/fonts/OFL.txt`).

## Caveats

- Fixed vintages: every row mixes a yearbook edition (provinces) with a national vintage,
  and NBS revises both over time. The `national_prelim_trn` and `national_rev_trn` columns
  exist so a reader can see how large the revision is per year.
- Trillion yuan, current prices, converted from the 亿元 the yearbook prints. No deflators
  applied; no per-capita adjustment.
- The provincial figures include the four municipalities (Beijing, Tianjin, Shanghai,
  Chongqing) and the autonomous regions; that is the standard 31-unit breakdown.

## License

CC BY 4.0 — reuse freely, credit the compiler (see `../LICENSE`). The underlying
statistics belong to the National Bureau of Statistics of China.
