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




def main():
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
    html = (html.replace("{{FINETUNE_CHART}}", finetune)
                .replace("{{MEMORY_CHART}}", memory))
    (ROOT / "index.html").write_text(html)
    print("wrote index.html")


if __name__ == "__main__":
    main()
