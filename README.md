# InvoiceAudit 🧾 — 离线发票/账单风险审查器

帮小微企业主、代账会计在**付款前**快速揪出发票里的坑：**重复票（双付风险）、税率不符、价税合计不平、关键字段缺失、大额整数、未来日期、超期未付**。纯标准库、**零依赖、100% 离线**——发票数据不出本机，生意隐私自己掌控。

> 透明规则引擎，不是黑箱：每一条发现都告诉你"问题是什么 + 依据哪几个数字 + 建议怎么处理"，可解释、可复现、可核对。

## 它能抓什么（7 类）

| 风险 | 等级 | 说明 |
|---|---|---|
| 🔴 疑似重复发票 | HIGH | 同供应商同票号、或同供应商同金额同日 → 两笔都付就是**重复付款** |
| 🔴 价税合计不平 | HIGH | 小计 + 税额 ≠ 票面总额 |
| 🟡 税率与税额不符 | CAUTION | 按小计×税率反推的税额与票面不符（影响进项抵扣） |
| 🟡 关键字段缺失 | CAUTION | 缺供应商/票号/日期/总额，难入账对账 |
| 🟡 大额整数金额 | CAUTION | 万元级千位整数，真实业务少见 |
| 🟡 开票日期在未来 | CAUTION | 未来日期的票不能提前入账 |
| 🟡 超期未付 | CAUTION | 挂账超 180 天仍"未付"，易生重复付款/坏账 |

## 快速开始

无需 `pip install` 任何东西，Python 3.8+ 即可：

```bash
# 直接跑自带示例（埋了 7 处风险）
python -m invoiceaudit.cli examples/invoices.txt

# 生成 HTML 报告
python -m invoiceaudit.cli examples/invoices.txt --html report.html
```

预期输出（示例文件真实跑出）：

```
风险评分：100/100    等级：HIGH
审查 7 张发票，发现 2 个高风险、5 个待留意项，风险等级 HIGH。
```

## 输入格式

每张发票一组 `KEY: VALUE`，票与票之间用**单独一行 `---`** 分隔。字段中英皆可：

```
VENDOR: 宏图办公用品有限公司
INVOICE_NO: INV-2026-0901
DATE: 2026-09-15
SUBTOTAL: 8600.00
TAX_RATE: 13%
TAX: 1118.00
TOTAL: 9718.00
STATUS: unpaid
---
VENDOR: ...
```

支持的键：`VENDOR / INVOICE_NO / DATE / SUBTOTAL / TAX_RATE / TAX / TOTAL / STATUS`（含中文别名：供应商/票号/日期/小计/税率/税额/总额/状态）。`TAX_RATE` 兼容 `13%`、`0.13`、`13` 三种写法。

## 作为库调用

```python
from invoiceaudit import parse_invoices, audit

with open("examples/invoices.txt", encoding="utf-8") as f:
    rep = audit(parse_invoices(f.read()))
print(rep.score, rep.band)
for f in rep.findings:
    print(f.severity, f.code, f.invoice)
```

## 隐私

发票是最敏感的商业数据之一。InvoiceAudit **完全离线运行**，不联网、不上传、不留日志——把含金额的票贴进去也安心。

## 适用场景

- 财务/代账：付款前批量筛查重复请款与算术错误
- 小老板：核对供应商来票，防止被多开、错开
- 教学/演示：透明规则 + 可解释输出的风控最小样例

## 免责声明

InvoiceAudit 是**辅助核对工具**，输出不构成财务、税务或法律建议；重大决策请咨询专业会计师/税务师。

## License

MIT · [github.com/Zhiyilang/invoiceaudit](https://github.com/Zhiyilang/invoiceaudit)
