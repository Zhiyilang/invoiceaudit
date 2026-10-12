"""InvoiceAudit — 离线发票/账单风险审查引擎（零依赖，纯标准库）。

输入一批发票记录（简单的 KEY: VALUE 文本块，用 --- 分隔），
输出：字段解析、7 类风险检查（重复票/税差/总价差/缺字段/整数金额/未来日期/陈旧未付）、
大白话解释 + 建议 + 风险评分。

100% 离线，数据不出本机；确定性规则引擎，可解释、可复现。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, date


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class Invoice:
    raw: str
    vendor: str = ""
    invoice_no: str = ""
    date_str: str = ""
    subtotal: float | None = None
    tax_rate: float | None = None
    tax: float | None = None
    total: float | None = None
    status: str = ""
    index: int = 0

    def label(self) -> str:
        no = self.invoice_no or f"#{self.index}"
        return f"{self.vendor or '未知供应商'} · {no}"


@dataclass
class Finding:
    severity: str          # HIGH / CAUTION / INFO
    code: str
    label: str
    invoice: str
    detail: str
    advice: str


@dataclass
class Report:
    invoices: list = field(default_factory=list)
    findings: list = field(default_factory=list)
    score: int = 0
    band: str = "LOW"
    summary: str = ""


# ---------------------------------------------------------------------------
# 解析
# ---------------------------------------------------------------------------

_FIELD_MAP = {
    "vendor": ("vendor", "supplier", "商家", "供应商", "卖方"),
    "invoice_no": ("invoice_no", "invoiceno", "invoice", "no", "number", "票号", "发票号", "编号"),
    "date_str": ("date", "date_str", "日期", "开票日期"),
    "subtotal": ("subtotal", "amount", "net", "小计", "金额", "不含税金额"),
    "tax_rate": ("tax_rate", "rate", "税率"),
    "tax": ("tax", "vat", "税额", "税金"),
    "total": ("total", "gross", "total_amount", "价税合计", "合计", "总额"),
    "status": ("status", "state", "状态"),
}

_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def _norm_key(k: str) -> str:
    return k.strip().lower().replace(" ", "_").replace("-", "_")


def _to_float(text: str) -> float | None:
    if text is None:
        return None
    m = _NUM_RE.search(text.replace(",", ""))
    return float(m.group()) if m else None


def _to_rate(text: str) -> float | None:
    """税率兼容 '13%' / '0.13' / '13' 三种写法。"""
    if text is None:
        return None
    t = text.strip()
    if "%" in t:
        v = _to_float(t)
        return v / 100.0 if v is not None else None
    v = _to_float(t)
    if v is None:
        return None
    return v / 100.0 if v > 1.0 else v


def parse_invoices(text: str) -> list[Invoice]:
    """把多张发票文本块解析成 Invoice 列表。块之间用单独一行 --- 或 === 分隔。"""
    blocks = re.split(r"(?m)^\s*(?:---|===)\s*$", text)
    invoices: list[Invoice] = []
    idx = 0
    for block in blocks:
        if not block.strip():
            continue
        idx += 1
        inv = Invoice(raw=block.strip(), index=idx)
        for line in block.splitlines():
            if ":" not in line and "：" not in line:
                continue
            sep = "：" if ("：" in line and (":" not in line or line.index("：") < line.index(":"))) else ":"
            key, _, val = line.partition(sep)
            nk = _norm_key(key)
            for attr, aliases in _FIELD_MAP.items():
                if nk in aliases:
                    val = val.strip()
                    if attr in ("subtotal", "tax", "total"):
                        setattr(inv, attr, _to_float(val))
                    elif attr == "tax_rate":
                        setattr(inv, attr, _to_rate(val))
                    else:
                        setattr(inv, attr, val)
                    break
        invoices.append(inv)
    return invoices


# ---------------------------------------------------------------------------
# 检查规则
# ---------------------------------------------------------------------------

def _parse_date(s: str):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _money(x: float | None) -> str:
    return "—" if x is None else f"¥{x:,.2f}"


def audit(invoices: list[Invoice], today: date | None = None) -> Report:
    today = today or date.today()
    rep = Report(invoices=invoices)
    findings: list[Finding] = []

    def add(sev, code, label, inv, detail, advice):
        findings.append(Finding(sev, code, label, inv.label(), detail, advice))

    # 1) 逐票字段/算术检查
    for inv in invoices:
        # 缺字段
        missing = [n for n, v in (("供应商", inv.vendor), ("票号", inv.invoice_no),
                                  ("日期", inv.date_str), ("总额", inv.total)) if not v]
        if missing:
            add("CAUTION", "MISSING_FIELD", "关键字段缺失", inv,
                f"缺少：{'、'.join(missing)}。字段不全的票难以入账与对账。",
                "向供应商索取信息完整的发票，避免后续无法抵扣或对账。")

        # 算术：小计 + 税 = 总额
        if inv.subtotal is not None and inv.tax is not None and inv.total is not None:
            calc = inv.subtotal + inv.tax
            if abs(calc - inv.total) > 0.01:
                add("HIGH", "TOTAL_MISMATCH", "价税合计不平", inv,
                    f"小计 {_money(inv.subtotal)} + 税额 {_money(inv.tax)} = {_money(calc)}，"
                    f"但票面总额是 {_money(inv.total)}，差 {_money(abs(calc - inv.total))}。",
                    "这笔票算术对不上，极可能开错或被人为改动，务必让供应商重新开具。")

        # 税率复核
        if inv.subtotal is not None and inv.tax is not None and inv.subtotal > 0:
            implied = inv.tax / inv.subtotal
            if inv.tax_rate is not None and abs(implied - inv.tax_rate) > 0.005:
                expect = round(inv.subtotal * inv.tax_rate, 2)
                add("CAUTION", "TAX_MISMATCH", "税率与税额不符", inv,
                    f"按小计 {_money(inv.subtotal)} × 税率 {inv.tax_rate:.0%} 税额应为 {_money(expect)}，"
                    f"但票面税额 {_money(inv.tax)}（实际约 {implied:.1%}）。",
                    "核对适用税率；税率错会直接影响进项抵扣，建议重开。")

        # 整数大额
        if inv.total is not None and inv.total >= 10000 and abs(inv.total - round(inv.total)) < 1e-9 \
                and round(inv.total) % 1000 == 0:
            add("CAUTION", "ROUND_AMOUNT", "大额整数金额", inv,
                f"总额 {_money(inv.total)} 是整齐的千位整数，真实业务里较少见。",
                "确认是否为估价/框架合同结算，警惕凑整风险。")

        # 未来日期
        d = _parse_date(inv.date_str)
        if d and d > today:
            add("CAUTION", "FUTURE_DATE", "开票日期在未来", inv,
                f"开票日期 {inv.date_str} 晚于今天 {today.isoformat()}。",
                "未来日期的票不能提前入账，确认是否笔误。")

        # 陈旧未付
        if d and inv.status and inv.status.lower() in ("unpaid", "未付", "未支付", "待付"):
            age = (today - d).days
            if age > 180:
                add("CAUTION", "STALE_UNPAID", "超期未付", inv,
                    f"开票于 {inv.date_str}，已 {age} 天仍标记未付。",
                    "长期挂账易生重复付款或坏账，尽快核对并结清或做坏账处理。")

    # 2) 跨票：重复发票（双付风险，最高优先）
    seen: dict[tuple, Invoice] = {}
    for inv in invoices:
        if not inv.invoice_no and inv.total is None:
            continue
        key_no = (inv.vendor.lower(), inv.invoice_no.lower()) if inv.invoice_no else None
        key_amt = (inv.vendor.lower(), inv.total, _parse_date(inv.date_str)) \
            if inv.total is not None else None
        for key in (key_no, key_amt):
            if not key:
                continue
            if key in seen:
                first = seen[key]
                reason = "票号相同" if key is key_no else "同供应商同金额同日"
                add("HIGH", "DUPLICATE", "疑似重复发票（双付风险）", inv,
                    f"与「{first.label()}」{reason}，若两笔都付=重复付款。",
                    "立即核对是否重复录入/重复请款；确认只付一次，必要时作废其一。")
                break
            seen[key] = inv

    # 评分：HIGH 重、CAUTION 轻
    highs = sum(1 for f in findings if f.severity == "HIGH")
    cautions = sum(1 for f in findings if f.severity == "CAUTION")
    score = min(100, highs * 30 + cautions * 10)
    rep.findings = findings
    rep.score = score
    rep.band = "HIGH" if score >= 30 else ("MEDIUM" if score >= 10 else "LOW")
    n = len(invoices)
    if not findings:
        rep.summary = f"审查 {n} 张发票，未发现明显风险。"
    else:
        rep.summary = (f"审查 {n} 张发票，发现 {highs} 个高风险、{cautions} 个待留意项，"
                       f"风险等级 {rep.band}。")
    return rep
