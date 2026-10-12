"""自包含 HTML 报告生成器（无外部依赖，单文件可分享）。"""

from __future__ import annotations

import html as _html

from .core import Report

_SEV_STYLE = {
    "HIGH": ("#dc2626", "#fef2f2", "高风险"),
    "CAUTION": ("#d97706", "#fffbeb", "待留意"),
    "INFO": ("#2563eb", "#eff6ff", "提示"),
}


def _esc(s: str) -> str:
    return _html.escape(str(s))


def render_html(rep: Report) -> str:
    order = {"HIGH": 0, "CAUTION": 1, "INFO": 2}
    findings = sorted(rep.findings, key=lambda x: order.get(x.severity, 9))
    band_color = {"HIGH": "#dc2626", "MEDIUM": "#d97706", "LOW": "#16a34a"}.get(rep.band, "#334155")

    rows = []
    for f in findings:
        c, bg, name = _SEV_STYLE.get(f.severity, ("#334155", "#f8fafc", f.severity))
        rows.append(f"""
        <div class="card" style="border-left:5px solid {c};background:{bg}">
          <div class="card-head">
            <span class="sev" style="background:{c}">{name}</span>
            <span class="clause">{_esc(f.label)}</span>
            <span class="inv">{_esc(f.invoice)}</span>
          </div>
          <p><b>问题：</b>{_esc(f.detail)}</p>
          <p><b>建议：</b>{_esc(f.advice)}</p>
        </div>""")

    inv_rows = "".join(
        f"<tr><td>{i.index}</td><td>{_esc(i.vendor or '—')}</td><td>{_esc(i.invoice_no or '—')}</td>"
        f"<td>{_esc(i.date_str or '—')}</td><td>{'—' if i.total is None else f'{i.total:,.2f}'}</td>"
        f"<td>{_esc(i.status or '—')}</td></tr>"
        for i in rep.invoices)

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>InvoiceAudit 发票风险审查报告</title>
<style>
  body{{font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;margin:0;background:#f1f5f9;color:#0f172a}}
  .wrap{{max-width:880px;margin:0 auto;padding:28px 20px 60px}}
  h1{{font-size:24px;margin:0 0 4px}}
  .sub{{color:#64748b;font-size:13px;margin-bottom:20px}}
  .score{{display:flex;align-items:center;gap:18px;background:#fff;border-radius:14px;padding:20px 24px;box-shadow:0 1px 3px rgba(0,0,0,.08);margin-bottom:22px}}
  .gauge{{font-size:40px;font-weight:800;color:{band_color}}}
  .band{{display:inline-block;color:#fff;background:{band_color};padding:3px 12px;border-radius:999px;font-size:13px;font-weight:600}}
  .summary{{color:#334155;font-size:14px}}
  .card{{border-radius:10px;padding:14px 16px;margin-bottom:12px;box-shadow:0 1px 2px rgba(0,0,0,.05)}}
  .card-head{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:6px}}
  .sev{{color:#fff;font-size:12px;font-weight:700;padding:2px 9px;border-radius:6px}}
  .clause{{font-weight:700;font-size:15px}}
  .inv{{color:#64748b;font-size:13px;margin-left:auto}}
  .card p{{margin:5px 0;font-size:14px;line-height:1.55}}
  table{{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08);font-size:13px;margin-top:8px}}
  th,td{{padding:8px 10px;text-align:left;border-bottom:1px solid #e2e8f0}}
  th{{background:#e2e8f0;font-weight:600}}
  h2{{font-size:17px;margin:26px 0 10px}}
  .foot{{margin-top:26px;color:#94a3b8;font-size:12px}}
</style></head><body><div class="wrap">
  <h1>InvoiceAudit 发票风险审查报告</h1>
  <div class="sub">离线生成 · 零依赖 · 数据不出本机 · 非财务/税务建议</div>
  <div class="score">
    <div class="gauge">{rep.score}<span style="font-size:16px;color:#94a3b8">/100</span></div>
    <div>
      <div style="margin-bottom:6px"><span class="band">风险 {rep.band}</span></div>
      <div class="summary">{_esc(rep.summary)}</div>
    </div>
  </div>
  <h2>风险发现（{len(rep.findings)}）</h2>
  {''.join(rows) if rows else '<div class="card" style="border-left:5px solid #16a34a;background:#f0fdf4"><p>未发现明显风险。</p></div>'}
  <h2>发票清单（{len(rep.invoices)}）</h2>
  <table><thead><tr><th>#</th><th>供应商</th><th>票号</th><th>日期</th><th>总额</th><th>状态</th></tr></thead>
  <tbody>{inv_rows}</tbody></table>
  <div class="foot">由 InvoiceAudit 生成 · github.com/Zhiyilang/invoiceaudit · MIT · 仅供辅助核对，不替代专业财务/税务审核</div>
</div></body></html>"""
