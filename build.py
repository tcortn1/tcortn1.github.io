"""Build index.html from template.html + data. Charts are generated as inline SVG.

    python3 build.py
"""

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).parent

# Numbers copied from each project's README / results files.
FINETUNE = [  # variant, size GB, accuracy %, tok/s
    ("Base Mistral 7B (no fine-tune)", 14.5, 52.3, 34.6),
    ("Fine-tuned fp16", 13.5, 94.5, 34.0),
    ("GGUF Q8_0", 7.2, 94.2, 121.7),
    ("GGUF Q6_K", 5.5, 94.2, 104.0),
    ("GGUF Q5_K_M", 4.8, 94.2, 124.7),
    ("GGUF Q4_K_M", 4.1, 94.5, 137.6),
    ("GGUF Q3_K_M", 3.3, 94.5, 111.0),
]
MEMORY = [("Store everything", 588, 0.203), ("Surprise-gated", 70.6, 0.209)]
VINTAGE_SERIES = ["2022-Q2", "2023-Q4", "2024-Q2", "2025-Q1"]
# engine, accuracy without / with semantic layer (%), from lending-genie-bench eval/analysis
TEXT2SQL = [("DSPy agent (Haiku 4.5)", 72.5, 90.0), ("Databricks Genie", 57.5, 87.5)]


def bar_chart(rows, value_max, label_fn, highlight=None, muted=None, title=""):
    """Horizontal bars: name column on the left, bar + value label on the right."""
    row_h, bar_h, label_w, width = 34, 14, 230, 640
    plot_w = width - label_w - 150
    height = row_h * len(rows) + 8
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}" class="chart">']
    for i, row in enumerate(rows):
        name, value = row[0], row[1]
        y = i * row_h + 8
        w = max(4, plot_w * value / value_max)
        cls = "bar-hi" if name == highlight else ("bar-muted" if name == muted else "bar")
        parts.append(f'<text x="0" y="{y + bar_h - 2}" class="t-sec">{escape(name)}</text>')
        parts.append(f'<g class="hit"><title>{escape(label_fn(row, plain=True))}</title>'
                     f'<rect x="{label_w}" y="{y - 8}" width="{plot_w + 150}" height="{row_h}" fill="transparent"/>'
                     f'<rect x="{label_w}" y="{y}" width="{w:.1f}" height="{bar_h}" rx="4" class="{cls}"/></g>')
        parts.append(f'<text x="{label_w + w + 8:.1f}" y="{y + bar_h - 2}" class="t-pri">{label_fn(row)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def vintage_chart(data):
    width, height = 640, 300
    left, right, top, bottom = 44, 78, 16, 36
    pw, ph = width - left - right, height - top - bottom
    y_max = 8.0
    x = lambda m: left + pw * m / 24
    y = lambda r: top + ph * (1 - r / y_max)
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" class="chart" '
             f'aria-label="Cumulative default rate by months on book for four origination cohorts">']
    for r in (0, 2, 4, 6, 8):
        parts.append(f'<line x1="{left}" x2="{left + pw}" y1="{y(r):.1f}" y2="{y(r):.1f}" class="grid"/>')
        parts.append(f'<text x="{left - 8}" y="{y(r) + 4:.1f}" text-anchor="end" class="t-mut">{r}%</text>')
    for m in (0, 6, 12, 18, 24):
        parts.append(f'<text x="{x(m):.1f}" y="{height - 14}" text-anchor="middle" class="t-mut">{m}</text>')
    parts.append(f'<text x="{left + pw / 2}" y="{height}" text-anchor="middle" class="t-mut">months on book</text>')
    for i, cohort in enumerate(VINTAGE_SERIES, start=1):
        pts = [[0, 0.0]] + data[cohort]["pts"]
        path = " ".join(f"{x(m):.1f},{y(r):.1f}" for m, r in pts)
        parts.append(f'<polyline points="{path}" class="line s{i}"/>')
        last_m, last_r = pts[-1]
        parts.append(f'<circle cx="{x(last_m):.1f}" cy="{y(last_r):.1f}" r="4" class="dot s{i}"/>')
        parts.append(f'<text x="{x(last_m) + 8:.1f}" y="{y(last_r) + 4:.1f}" class="t-sec">{cohort}</text>')
        for m, r in pts[1:]:
            parts.append(f'<circle cx="{x(m):.1f}" cy="{y(r):.1f}" r="7" class="hover-pt">'
                         f'<title>{cohort}, month {m}: {r:.1f}% cumulative default</title></circle>')
    parts.append("</svg>")
    legend = "".join(f'<span class="key"><i class="sw s{i}"></i>{c} '
                     f'<span class="t-mut">({data[c]["n"]} loans)</span></span>'
                     for i, c in enumerate(VINTAGE_SERIES, start=1))
    table_rows = "".join(
        f"<tr><td>{c}</td><td>{data[c]['n']}</td>"
        + "".join(f"<td>{dict(map(tuple, data[c]['pts'])).get(m, '–')}</td>" for m in (6, 12, 18, 24))
        + "</tr>" for c in VINTAGE_SERIES)
    table = ('<details class="table-view"><summary>Show as table</summary><table><thead><tr><th>Cohort</th>'
             '<th>Loans</th><th>6m %</th><th>12m %</th><th>18m %</th><th>24m %</th></tr></thead>'
             f"<tbody>{table_rows}</tbody></table></details>")
    return f'<div class="legend">{legend}</div>' + "".join(parts) + table


def dumbbell_chart(rows):
    """Accuracy without -> with the semantic layer, one row per engine."""
    width, label_w, right, row_h, top = 640, 190, 24, 56, 30
    pw = width - label_w - right
    height = top + row_h * len(rows) + 28
    x = lambda v: label_w + pw * (v - 50) / 50
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" class="chart" '
             f'aria-label="Execution accuracy without and with a semantic layer, per engine">']
    for v in (50, 60, 70, 80, 90, 100):
        parts.append(f'<line x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{top - 10}" y2="{height - 24}" class="grid"/>')
        parts.append(f'<text x="{x(v):.1f}" y="{height - 6}" text-anchor="middle" class="t-mut">{v}%</text>')
    for i, (name, before, after) in enumerate(rows):
        y = top + i * row_h + 14
        parts.append(f'<text x="0" y="{y + 4}" class="t-sec">{escape(name)}</text>')
        parts.append(f'<line x1="{x(before):.1f}" x2="{x(after):.1f}" y1="{y}" y2="{y}" class="link"/>')
        for v, cls, label in ((before, "s-before", "without"), (after, "s-after", "with")):
            parts.append(f'<g class="hit"><title>{escape(name)}, {label} semantic layer: {v:g}%</title>'
                         f'<circle cx="{x(v):.1f}" cy="{y}" r="12" fill="transparent"/>'
                         f'<circle cx="{x(v):.1f}" cy="{y}" r="7" class="dot {cls}"/></g>')
        parts.append(f'<text x="{x(before):.1f}" y="{y - 14}" text-anchor="middle" class="t-mut">{before:g}%</text>')
        parts.append(f'<text x="{x(after):.1f}" y="{y - 14}" text-anchor="middle" class="t-pri">{after:g}%</text>')
    parts.append("</svg>")
    legend = ('<div class="legend"><span class="key"><i class="sw s-before"></i>tables + column comments only</span>'
              '<span class="key"><i class="sw s-after"></i>+ metric glossary and 20 example queries</span></div>')
    table_rows = "".join(f"<tr><td>{escape(n)}</td><td>{b:g}%</td><td>{a:g}%</td><td>+{a - b:g} pp</td></tr>"
                         for n, b, a in rows)
    table = ('<details class="table-view"><summary>Show as table</summary><table><thead><tr><th>Engine</th>'
             '<th>Without</th><th>With</th><th>Gain</th></tr></thead>'
             f"<tbody>{table_rows}</tbody></table></details>")
    return legend + "".join(parts) + table


def main():
    vintage = json.loads((ROOT / "assets" / "vintage.json").read_text())
    finetune = bar_chart(
        FINETUNE, 14.5,
        lambda r, plain=False: (f"{r[1]} GB · {r[2]}% acc · {r[3]:.0f} tok/s" if plain
                                else f"{r[1]} GB <tspan class='t-mut'>· {r[2]}%</tspan>"),
        highlight="GGUF Q4_K_M", muted="Base Mistral 7B (no fine-tune)",
        title="Model size per variant; accuracy stays at 94% down to 3.3 GB")
    memory = bar_chart(
        MEMORY, 588,
        lambda r, plain=False: (f"{r[1]} entries · F1 {r[2]}" if plain
                                else f"{r[1]:g} entries <tspan class='t-mut'>· F1 {r[2]}</tspan>"),
        highlight="Surprise-gated", title="Average memory store size and generation F1 on LoCoMo")
    html = (ROOT / "template.html").read_text()
    html = (html.replace("{{VINTAGE_CHART}}", vintage_chart(vintage))
                .replace("{{TEXT2SQL_CHART}}", dumbbell_chart(TEXT2SQL))
                .replace("{{FINETUNE_CHART}}", finetune)
                .replace("{{MEMORY_CHART}}", memory))
    (ROOT / "index.html").write_text(html)
    print("wrote index.html")


if __name__ == "__main__":
    main()
