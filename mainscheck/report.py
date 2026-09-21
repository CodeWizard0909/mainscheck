"""Static HTML report. No build step, no framework — it must open from a raw
GitHub Pages URL on a founder's phone."""

from __future__ import annotations

from pathlib import Path

from .economics import Economics
from .perturb import CONTROL

_CSS = """
:root { --fg:#16181d; --muted:#6b7280; --line:#e5e7eb; --bg:#fff;
        --good:#15803d; --bad:#b91c1c; --accent:#1d4ed8; }
@media (prefers-color-scheme: dark) {
  :root { --fg:#e8eaed; --muted:#9aa0a6; --line:#2d3139; --bg:#14161a;
          --good:#4ade80; --bad:#f87171; --accent:#93b4ff; }
}
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

    html.append("<h2>Reliability by configuration</h2>")
    html.append(
        "<table><tr><th>Model</th><th>Rubric</th><th class='num'>Max spread</th>"
        "<th class='num'>Worst SD</th><th class='num'>Spearman &rho;</th>"
        "<th class='num'>Inversions</th><th>Control</th></tr>"
    )
    for b in blocks:
        c, m, s = b["consistency"], b["monotonicity"], b["sensitivity"]
        ok = s.control_drift <= 0.2
        html.append(
            f"<tr><td><code>{b['model']}</code></td><td>{b['rubric']}</td>"
            f"<td class='num'>{c.max_spread:.1f}</td>"
            f"<td class='num'>{c.worst_sd:.2f} <span style='color:var(--muted)'>"
            f"({c.worst_criterion})</span></td>"
            f"<td class='num'>{s_fmt(m.spearman_rho)}</td>"
            f"<td class='num'>{m.inversion_rate:.0%}</td>"
            f"<td class='{'pass' if ok else 'fail'}'>"
            f"{'flat' if ok else f'drift {s.control_drift:+.2f}'}</td></tr>"
        )
    html.append("</table>")
    html.append(
        f"<p class='note'>The control perturbation (<code>{CONTROL}</code>) changes "
        "wording only. If scores move, the harness is measuring sampling noise rather "
        "than answer quality — reported here rather than hidden.</p>"
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
