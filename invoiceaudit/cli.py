"""命令行入口：python -m invoiceaudit.cli <发票文件> [--html out.html]"""

from __future__ import annotations

import argparse
import sys

from .core import parse_invoices, audit


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="invoiceaudit",
        description="离线发票/账单风险审查器：重复票、税差、总价不平、缺字段、整数金额、未来日期、超期未付。")
    p.add_argument("file", nargs="?", help="发票文本文件（KEY: VALUE 块，--- 分隔）")
    p.add_argument("--html", metavar="OUT", help="生成 HTML 报告到指定路径")
    p.add_argument("--text", help="直接传入发票文本（替代文件）")
    args = p.parse_args(argv)

    if args.text:
        text = args.text
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            print(f"[错误] 无法读取文件：{e}")
            return 2
    else:
        print("[错误] 请提供发票文件路径，或用 --text 传入文本。")
        return 2

    invoices = parse_invoices(text)
    if not invoices:
        print("[错误] 没有解析到任何发票。请确认格式：每张票一组 KEY: VALUE，票与票之间用单独一行 --- 分隔。")
        return 2

    rep = audit(invoices)

    print("=" * 64)
    print(f"InvoiceAudit 审查结果  ·  共 {len(invoices)} 张发票")
    print("=" * 64)
    order = {"HIGH": 0, "CAUTION": 1, "INFO": 2}
    for f in sorted(rep.findings, key=lambda x: order.get(x.severity, 9)):
        tag = {"HIGH": "🔴 高风险", "CAUTION": "🟡 待留意", "INFO": "🔵 提示"}.get(f.severity, f.severity)
        print(f"\n[{tag}] {f.label}  —  {f.invoice}")
        print(f"    问题：{f.detail}")
        print(f"    建议：{f.advice}")
    print("\n" + "-" * 64)
    print(f"风险评分：{rep.score}/100    等级：{rep.band}")
    print(rep.summary)

    if args.html:
        from .report import render_html
        html = render_html(rep)
        with open(args.html, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\nHTML 报告已生成：{args.html}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
