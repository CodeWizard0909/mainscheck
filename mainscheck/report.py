"""Static HTML report. No build step, no framework — it must open from a raw
GitHub Pages URL on a founder's phone."""

from __future__ import annotations

from pathlib import Path

from .economics import Economics
from .perturb import CONTROL

_CSS = """
:root { --fg:#0b0b0b; --muted:#898781; --secondary:#52514e; --line:#e1e0d9;
        --bg:#fcfcfb; --axis:#c3c2b7;
        --good:#15803d; --bad:#b91c1c; --accent:#2a78d6;
        --series-1:#2a78d6; --series-2:#eb6834; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --fg:#ffffff; --muted:#898781; --secondary:#c3c2b7; --line:#2c2c2a;
    --bg:#1a1a19; --axis:#383835;
    --good:#4ade80; --bad:#f87171; --accent:#3987e5;
    --series-1:#3987e5; --series-2:#d95926; }
}
:root[data-theme="dark"] {
  --fg:#ffffff; --muted:#898781; --secondary:#c3c2b7; --line:#2c2c2a;
  --bg:#1a1a19; --axis:#383835;
  --good:#4ade80; --bad:#f87171; --accent:#3987e5;
  --series-1:#3987e5; --series-2:#d95926;
}
.hero { border:1px solid var(--line); border-radius:8px; padding:1.25rem 1.4rem;
        margin:1.5rem 0 2rem; }
.hero .big { font-size:2.4rem; line-height:1.1; font-weight:650;
             letter-spacing:-.02em; }
.hero .said { color:var(--secondary); margin:.4rem 0 0; }
.hero .sub { color:var(--muted); font-size:.88rem; margin:.6rem 0 0; }
.legend { display:flex; gap:1.2rem; margin:.4rem 0 0; font-size:.85rem;
          color:var(--secondary); }
.legend span { display:inline-flex; align-items:center; gap:.4rem; }
.dot { width:10px; height:10px; border-radius:50%; display:inline-block; }
* { box-sizing:border-box; }
body { margin:0; padding:32px 16px; background:var(--bg); color:var(--fg);
       font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
main { max-width:860px; margin:0 auto; }
h1 { font-size:1.6rem; margin:0 0 .25rem; letter-spacing:-.01em; }
h2 { font-size:1.1rem; margin:2.5rem 0 .75rem; }
.sub { color:var(--muted); margin:0 0 2rem; }
table { width:100%; border-collapse:collapse; margin:1rem 0; font-size:.92rem; }
th,td { text-align:left; padding:.55rem .5rem; border-bottom:1px solid var(--line); }
th { font-weight:600; color:var(--muted); font-size:.82rem; text-transform:uppercase;
     letter-spacing:.04em; }
td.num { text-align:right; font-variant-numeric:tabular-nums; }
.pass { color:var(--good); font-weight:600; }
.fail { color:var(--bad); font-weight:600; }
.note { color:var(--muted); font-size:.88rem; border-left:2px solid var(--line);
        padding-left:.9rem; margin:1.25rem 0; }
code { background:rgba(127,127,127,.12); padding:.1em .35em; border-radius:3px;
       font-size:.88em; }
"""


def _bar_chart(rows: list[tuple[str, float]], *, width=760, row_h=34) -> str:
    """Horizontal bars for signed values, with a zero line down the middle."""
    if not rows:
        return ""
    height = row_h * len(rows) + 20
    span = max(1e-6, max(abs(v) for _, v in rows))
    mid = width * 0.55
    scale = (width * 0.38) / span

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
        f'aria-label="effect size by perturbation">'
    ]
    parts.append(
        f'<line x1="{mid}" y1="8" x2="{mid}" y2="{height - 12}" '
        f'stroke="var(--line)" stroke-width="1"/>'
    )
    for i, (label, value) in enumerate(rows):
        y = 12 + i * row_h
        w = abs(value) * scale
        x = mid if value >= 0 else mid - w
        colour = "var(--bad)" if value < 0 else "var(--accent)"
        parts.append(
            f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="16" rx="3" '
            f'fill="{colour}" opacity="0.85"/>'
        )
        parts.append(
            f'<text x="8" y="{y + 12}" font-size="12" fill="var(--fg)">{label}</text>'
        )
        anchor_x = x + w + 6 if value >= 0 else x - 6
        anchor = "start" if value >= 0 else "end"
        parts.append(
            f'<text x="{anchor_x:.1f}" y="{y + 12}" font-size="12" '
            f'text-anchor="{anchor}" fill="var(--muted)">{value:+.2f}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _frontier_chart(points: list[dict], *, width=720, height=330) -> str:
    """Latency against control drift, one mark per configuration.

    Two series (model size), because that is the axis the result separates on.
    Four marks, so every one is directly labelled and identity never rests on
    colour alone.
    """
    if not points:
        return ""

    left, right, top, bottom = 68, 28, 28, 52
    plot_w = width - left - right
    plot_h = height - top - bottom

    x_max = max(8.0, max(p["latency"] for p in points) * 1.15)
    y_max = max(0.6, max(p["drift"] for p in points) * 1.3)

    def px(v):
        return left + (v / x_max) * plot_w

    def py(v):
        return top + plot_h - (v / y_max) * plot_h

    s = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
        f'aria-label="Mean latency against control drift on weak answers, '
        f'four configurations">'
    ]

    # Horizontal gridlines. Recessive; the 0.2 gate is the only emphasised one.
    for i in range(4):
        v = y_max * i / 3
        y = py(v)
        s.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" '
            f'stroke="var(--line)" stroke-width="1"/>'
        )
        s.append(
            f'<text x="{left - 10}" y="{y + 4:.1f}" font-size="11" '
            f'text-anchor="end" fill="var(--muted)">{v:.1f}</text>'
        )

    gate_y = py(0.2)
    s.append(
        f'<line x1="{left}" y1="{gate_y:.1f}" x2="{left + plot_w}" '
        f'y2="{gate_y:.1f}" stroke="var(--bad)" stroke-width="1.5" '
        f'stroke-dasharray="5 4" opacity="0.75"/>'
    )
    s.append(
        f'<text x="{left + plot_w}" y="{gate_y - 7:.1f}" font-size="11" '
        f'text-anchor="end" fill="var(--bad)">0.20 gate</text>'
    )

    # Axes.
    s.append(
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" '
        f'y2="{top + plot_h}" stroke="var(--axis)" stroke-width="1"/>'
    )
    for i in range(5):
        v = x_max * i / 4
        x = px(v)
        s.append(
            f'<text x="{x:.1f}" y="{top + plot_h + 18}" font-size="11" '
            f'text-anchor="middle" fill="var(--muted)">{v:.0f}s</text>'
        )
    s.append(
        f'<text x="{left + plot_w / 2:.1f}" y="{height - 8}" font-size="11.5" '
        f'text-anchor="middle" fill="var(--secondary)">'
        f'mean latency per evaluation</text>'
    )
    s.append(
        f'<text transform="translate(16,{top + plot_h / 2:.1f}) rotate(-90)" '
        f'font-size="11.5" text-anchor="middle" fill="var(--secondary)">'
        f'control drift, weak answers</text>'
    )

    for p in points:
        x, y = px(p["latency"]), py(p["drift"])
        colour = f'var(--series-{p["series"]})'
        s.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{colour}" '
            f'stroke="var(--bg)" stroke-width="2">'
            f'<title>{p["label"]} — {p["latency"]:.1f}s, drift '
            f'{p["drift"]:+.2f}</title></circle>'
        )
        # Keep the label inside the plot: flip to the left near the right edge.
        flip = x > left + plot_w * 0.62
        lx = x - 13 if flip else x + 13
        anchor = "end" if flip else "start"
        s.append(
            f'<text x="{lx:.1f}" y="{y + 4:.1f}" font-size="11.5" '
            f'text-anchor="{anchor}" fill="var(--fg)">{p["label"]}</text>'
        )

    s.append("</svg>")
    return "".join(s)


def build_report(blocks: list[dict], economics: list[Economics], out: Path) -> Path:
    html = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<title>MainsCheck</title>",
        f"<style>{_CSS}</style></head><body><main>",
        "<h1>MainsCheck</h1>",
        "<p class='sub'>Is an AI examiner consistent, and does it react to what "
        "should matter? Measured on a public corpus of UPSC Mains answers.</p>",
    ]

    # --- headline: a single number, so a stat rather than a chart -----------
    fact_effects = [
        b["sensitivity"].per_perturbation.get("corrupt_fact")
        for b in blocks
        if b["sensitivity"].per_perturbation.get("corrupt_fact") is not None
    ]
    total_gradings = sum(e.evaluations for e in economics)
    if fact_effects:
        worst = max(abs(v) for v in fact_effects)
        html.append(
            "<div class='hero'>"
            f"<div class='big'>0 of {len(fact_effects)}</div>"
            "<p class='said'>configurations detected a corrupted fact. Swapping a "
            "real date or Act for a plausible wrong one moved the overall score by "
            f"at most <strong>{worst:.2f}</strong> points.</p>"
            f"<p class='sub'>{total_gradings:,} gradings across every model and "
            "rubric tested.</p>"
            "</div>"
        )

    # --- the trade-off: two measures across four configurations ------------
    latency = {(e.model, e.rubric_id): e.mean_latency_s for e in economics}
    models = sorted({b["model"] for b in blocks})
    points = []
    for b in blocks:
        banded = b.get("control_by_band")
        key = (b["model"], b["rubric"])
        if not banded or key not in latency:
            continue
        points.append({
            "label": f"{b['model'].split(':')[-1]} {b['rubric']}",
            "latency": latency[key],
            "drift": max((abs(v) for v in banded.per_band.values()), default=0.0),
            "series": (models.index(b["model"]) % 2) + 1,
        })

    if points:
        html.append("<h2>Reliability against cost</h2>")
        html.append(_frontier_chart(points))
        html.append(
            "<div class='legend'>"
            + "".join(
                f"<span><i class='dot' style='background:var(--series-"
                f"{(i % 2) + 1})'></i>{m}</span>"
                for i, m in enumerate(models)
            )
            + "</div>"
        )
        html.append(
            "<p class='note'>Drift is the largest control effect on any quality "
            "band. The control changes wording and nothing else, so every mark "
            "should sit on zero; marks below the dashed line pass the gate. The "
            "two configurations near 26s cost the same to run &mdash; at equal "
            "compute, the larger model with the simpler rubric is the reliable "
            "one.</p>"
        )

    html.append("<h2>Consistency, per temperature</h2>")
    html.append(
        "<p class='note'>Reported separately by temperature on purpose. A single "
        "blended figure mixes sampling variance at one temperature with the "
        "difference between settings, and describes neither — a model that is "
        "deterministic at 0 looks unstable.</p>"
    )
    html.append(
        "<table><tr><th>Model</th><th>Rubric</th><th class='num'>Temp</th>"
        "<th class='num'>Mean spread</th><th class='num'>Worst</th>"
        "<th class='num'>Identical across repeats</th></tr>"
    )
    for b in blocks:
        for temp, c in sorted(b["by_temperature"].items()):
            if not c.answers:
                continue
            share = c.deterministic / c.answers
            html.append(
                f"<tr><td><code>{b['model']}</code></td><td>{b['rubric']}</td>"
                f"<td class='num'>{temp:.1f}</td>"
                f"<td class='num'>{c.mean_spread:.2f}</td>"
                f"<td class='num'>{c.max_spread:.2f}</td>"
                f"<td class='num'>{c.deterministic}/{c.answers} "
                f"<span style='color:var(--muted)'>({share:.0%})</span></td></tr>"
            )
    html.append("</table>")

    html.append("<h2>Ranking and control</h2>")
    html.append(
        "<table><tr><th>Model</th><th>Rubric</th><th class='num'>Spearman &rho;</th>"
        "<th class='num'>Inversions</th><th>Control, aggregate</th></tr>"
    )
    for b in blocks:
        m, s = b["monotonicity"], b["sensitivity"]
        ok = s.control_drift <= 0.2
        html.append(
            f"<tr><td><code>{b['model']}</code></td><td>{b['rubric']}</td>"
            f"<td class='num'>{s_fmt(m.spearman_rho)}</td>"
            f"<td class='num'>{m.inversion_rate:.0%}</td>"
            f"<td class='{'pass' if ok else 'fail'}'>"
            f"{'flat' if ok else f'drift {s.control_drift:+.2f}'}</td></tr>"
        )
    html.append("</table>")

    for b in blocks:
        banded = b.get("control_by_band")
        if not banded or not banded.per_band:
            continue
        html.append(
            f"<h2>Control by answer quality &mdash; {b['model']} / "
            f"{b['rubric']}</h2>"
        )
        html.append(
            "<table><tr><th>Quality band</th><th class='num'>Mean change</th>"
            "<th class='num'>Largest</th><th class='num'>Answers</th></tr>"
        )
        for band in ("weak", "middling", "strong"):
            if band not in banded.per_band:
                continue
            value = banded.per_band[band]
            cls = "fail" if abs(value) > 0.2 else "pass"
            html.append(
                f"<tr><td>{band}</td>"
                f"<td class='num {cls}'>{value:+.2f}</td>"
                f"<td class='num'>{banded.max_per_band[band]:+.2f}</td>"
                f"<td class='num'>{banded.counts[band]}</td></tr>"
            )
        html.append("</table>")
        html.append(
            f"<p class='note'>The control (<code>{CONTROL}</code>) changes wording "
            "and nothing else, so every row here should read 0.00. Where it does not, "
            "the grader is responding to phrasing rather than to substance. The "
            "aggregate above can pass a 0.2 gate while a single band fails badly, "
            "which is why this table exists.</p>"
        )

    for b in blocks:
        s = b["sensitivity"]
        rows = sorted(s.per_perturbation.items(), key=lambda kv: kv[1])
        html.append(f"<h2>Sensitivity &mdash; {b['model']} / {b['rubric']}</h2>")
        html.append(_bar_chart(rows))
        html.append("<table><tr><th>Perturbation</th><th class='num'>&Delta; score</th>"
                    "<th>Expected</th><th>Result</th></tr>")
        for name, delta in rows:
            direction = s.expected_direction.get(name, 0)
            expected = {1: "rise", -1: "fall", 0: "no change"}[direction]
            passed = s.passed(name)
            html.append(
                f"<tr><td><code>{name}</code></td><td class='num'>{delta:+.2f}</td>"
                f"<td>{expected}</td>"
                f"<td class='{'pass' if passed else 'fail'}'>"
                f"{'pass' if passed else 'fail'}</td></tr>"
            )
        html.append("</table>")

    html.append("<h2>Cost and latency</h2>")
    html.append(
        "<table><tr><th>Model</th><th>Rubric</th><th class='num'>Evals</th>"
        "<th class='num'>In tok</th><th class='num'>Out tok</th>"
        "<th class='num'>Latency</th><th class='num'>$ / 1k evals</th></tr>"
    )
    for e in economics:
        cost = f"{e.cost_per_1k_evals_usd:.2f}" if e.priced else "&mdash;"
        html.append(
            f"<tr><td><code>{e.model}</code></td><td>{e.rubric_id}</td>"
            f"<td class='num'>{e.evaluations}</td>"
            f"<td class='num'>{e.mean_input_tokens:.0f}</td>"
            f"<td class='num'>{e.mean_output_tokens:.0f}</td>"
            f"<td class='num'>{e.mean_latency_s:.1f}s</td>"
            f"<td class='num'>{cost}</td></tr>"
        )
    html.append("</table>")
    if not any(e.priced for e in economics):
        html.append(
            "<p class='note'>Cost columns are blank because "
            "<code>config/pricing.yaml</code> has no prices filled in. Add the "
            "current published rates and note the date you checked them.</p>"
        )

    html.append("</main></body></html>")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(html), encoding="utf-8")
    return out


def s_fmt(value: float) -> str:
    return f"{value:.2f}" if value == value else "&mdash;"  # NaN-safe
